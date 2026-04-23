from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, List, Sequence

from .config import BehaviorConfig
from .interfaces import BehaviorService


def _safe_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = ["BehaviorAnalyzer"]


class BehaviorAnalyzer(BehaviorService):
    @staticmethod
    def classify_regime(field_strength: float, coupling: float, config: BehaviorConfig) -> str:
        denom = max(abs(float(coupling)), 1e-12)
        ratio = abs(float(field_strength)) / denom
        if ratio < config.weak_field_ratio:
            return "weak_field"
        if ratio <= config.near_critical_ratio:
            return "near_critical"
        return "strong_field"

    @staticmethod
    def classify_noise_regime(gate_error: float, config: BehaviorConfig) -> str:
        value = abs(float(gate_error))
        if value == 0.0:
            return "ideal"
        if value <= config.low_noise_threshold:
            return "low_noise"
        if value <= config.moderate_noise_threshold:
            return "moderate_noise"
        return "high_noise"

    @staticmethod
    def _mean(values: Sequence[float | None]) -> float | None:
        cleaned = [float(v) for v in values if v is not None]
        return mean(cleaned) if cleaned else None

    @staticmethod
    def _std(values: Sequence[float | None]) -> float | None:
        cleaned = [float(v) for v in values if v is not None]
        return None if not cleaned else (pstdev(cleaned) if len(cleaned) > 1 else 0.0)

    @staticmethod
    def _valid_fraction(rows: Sequence[Dict[str, object]]) -> float:
        return 0.0 if not rows else float(sum(1 for row in rows if bool(row.get("physical_valid"))) / len(rows))

    @staticmethod
    def _counts_by_label(crossover: Sequence[Dict[str, object]], field: str) -> Counter:
        counter: Counter = Counter()
        for row in crossover:
            label = row.get(field)
            if label:
                counter[str(label)] += 1
        return counter

    @staticmethod
    def _line_slope(xs: Sequence[float], ys: Sequence[float]) -> float | None:
        if len(xs) < 2 or len(set(xs)) < 2:
            return None
        xbar, ybar = mean(xs), mean(ys)
        denom = sum((x - xbar) ** 2 for x in xs)
        if denom <= 0.0:
            return None
        numer = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys))
        return float(numer / denom)

    @staticmethod
    def _cost_sigma(left: Dict[str, object], right: Dict[str, object]) -> float | None:
        lv = _safe_float(left.get("cost_value"))
        rv = _safe_float(right.get("cost_value"))
        lse = _safe_float(left.get("cost_standard_error")) or _safe_float(left.get("measurement_total_standard_error"))
        rse = _safe_float(right.get("cost_standard_error")) or _safe_float(right.get("measurement_total_standard_error"))
        if lv is None or rv is None or lse is None or rse is None:
            return None
        denom = math.sqrt(max(lse * lse + rse * rse, 0.0))
        return None if denom <= 0.0 else abs(lv - rv) / denom

    @staticmethod
    def _dominant(counter: Counter) -> str | None:
        return None if not counter else counter.most_common(1)[0][0]

    @staticmethod
    def _behavior_risk(rows: Sequence[Dict[str, object]], config: BehaviorConfig) -> float | None:
        components = []
        for row in rows:
            gap = _safe_float(row.get("filtered_exact_gap"))
            if gap is None:
                gap = _safe_float(row.get("exact_gap"))
            symmetry = _safe_float(row.get("symmetry_breaking_error")) or 0.0
            obs = _safe_float(row.get("filtered_observable_error_l2")) or _safe_float(row.get("observable_error_l2")) or 0.0
            unc = _safe_float(row.get("measurement_total_standard_error")) or _safe_float(row.get("cost_standard_error")) or 0.0
            if gap is None:
                continue
            components.append(float(gap) + config.symmetry_risk_weight * symmetry + config.observable_risk_weight * obs + config.uncertainty_risk_weight * unc)
        return mean(components) if components else None

    @staticmethod
    def enrich_crossover(rows: Sequence[Dict[str, object]], crossover: Sequence[Dict[str, object]], coupling: float, config: BehaviorConfig) -> List[Dict[str, object]]:
        row_map = {str(row["label"]): row for row in rows}
        enriched: List[Dict[str, object]] = []
        for entry in crossover:
            regime_label = BehaviorAnalyzer.classify_regime(float(entry["field_strength"]), coupling, config)
            noise_regime = BehaviorAnalyzer.classify_noise_regime(float(entry["gate_error"]), config)
            energy_row = row_map.get(str(entry["energy_winner_label"]))
            physics_row = row_map.get(str(entry["physics_winner_label"]))
            budget_row = row_map.get(str(entry["budget_winner_label"]))
            enriched_entry = dict(entry)
            enriched_entry.update({
                "regime_label": regime_label,
                "noise_regime": noise_regime,
                "energy_vs_physics_cost_sigma": None if energy_row is None or physics_row is None else BehaviorAnalyzer._cost_sigma(energy_row, physics_row),
                "physics_vs_budget_cost_sigma": None if physics_row is None or budget_row is None else BehaviorAnalyzer._cost_sigma(physics_row, budget_row),
                "energy_vs_physics_energy_delta": None if energy_row is None or physics_row is None else _safe_float(energy_row.get("energy")) - _safe_float(physics_row.get("energy")),
                "physics_vs_budget_shot_delta": None if physics_row is None or budget_row is None else (_safe_float(physics_row.get("estimated_total_shots_used")) or 0.0) - (_safe_float(budget_row.get("estimated_total_shots_used")) or 0.0),
                "physics_vs_budget_two_qubit_delta": None if physics_row is None or budget_row is None else (_safe_float(physics_row.get("transpiled_two_qubit_gate_count")) or 0.0) - (_safe_float(budget_row.get("transpiled_two_qubit_gate_count")) or 0.0),
            })
            enriched.append(enriched_entry)
        return enriched

    @staticmethod
    def regime_profiles(rows: Sequence[Dict[str, object]], crossover: Sequence[Dict[str, object]], coupling: float, config: BehaviorConfig) -> List[Dict[str, object]]:
        crossover_by_key = {(c["n_qubits"], c["field_strength"], c["gate_error"]): c for c in crossover}
        buckets = defaultdict(list)
        for row in rows:
            regime_label = BehaviorAnalyzer.classify_regime(float(row["field_strength"]), coupling, config)
            noise_regime = BehaviorAnalyzer.classify_noise_regime(float(row["gate_error"]), config)
            buckets[(int(row["n_qubits"]), regime_label, noise_regime, float(row["gate_error"]))].append(row)
        profiles = []
        for key, bucket in sorted(buckets.items()):
            n_qubits, regime_label, noise_regime, gate_error = key
            crossover_rows = [crossover_by_key[(row["n_qubits"], row["field_strength"], row["gate_error"])] for row in bucket if (row["n_qubits"], row["field_strength"], row["gate_error"]) in crossover_by_key]
            energy_winners = Counter(str(item["energy_winner_ansatz"]) for item in crossover_rows)
            physics_winners = Counter(str(item["physics_winner_ansatz"]) for item in crossover_rows)
            budget_winners = Counter(str(item["budget_winner_ansatz"]) for item in crossover_rows)
            profiles.append({
                "n_qubits": n_qubits,
                "regime_label": regime_label,
                "noise_regime": noise_regime,
                "gate_error": gate_error,
                "num_runs": len(bucket),
                "valid_fraction": BehaviorAnalyzer._valid_fraction(bucket),
                "false_winner_rate": float(sum(bool(item.get("false_winner_flag")) for item in crossover_rows) / len(crossover_rows)) if crossover_rows else 0.0,
                "mean_filtered_exact_gap": BehaviorAnalyzer._mean([_safe_float(row.get("filtered_exact_gap")) for row in bucket]),
                "std_filtered_exact_gap": BehaviorAnalyzer._std([_safe_float(row.get("filtered_exact_gap")) for row in bucket]),
                "mean_fidelity_to_exact": BehaviorAnalyzer._mean([_safe_float(row.get("fidelity_to_exact")) for row in bucket]),
                "mean_symmetry_breaking_error": BehaviorAnalyzer._mean([_safe_float(row.get("symmetry_breaking_error")) for row in bucket]),
                "mean_measurement_total_standard_error": BehaviorAnalyzer._mean([_safe_float(row.get("measurement_total_standard_error")) for row in bucket]),
                "mean_estimated_total_shots_used": BehaviorAnalyzer._mean([_safe_float(row.get("estimated_total_shots_used")) for row in bucket]),
                "mean_transpiled_two_qubit_gate_count": BehaviorAnalyzer._mean([_safe_float(row.get("transpiled_two_qubit_gate_count")) for row in bucket]),
                "mean_zne_mitigation_gain": BehaviorAnalyzer._mean([_safe_float(row.get("zne_mitigation_gain")) for row in bucket]),
                "dominant_energy_winner_ansatz": BehaviorAnalyzer._dominant(energy_winners),
                "dominant_physics_winner_ansatz": BehaviorAnalyzer._dominant(physics_winners),
                "dominant_budget_winner_ansatz": BehaviorAnalyzer._dominant(budget_winners),
                "behavior_risk_score": BehaviorAnalyzer._behavior_risk(bucket, config),
            })
        return profiles

    @staticmethod
    def competitor_profiles(rows: Sequence[Dict[str, object]], crossover: Sequence[Dict[str, object]], coupling: float, config: BehaviorConfig, field: str) -> List[Dict[str, object]]:
        winner_field_map = {"ansatz": ("energy_winner_ansatz", "physics_winner_ansatz", "budget_winner_ansatz"), "optimizer": ("energy_winner_optimizer", "physics_winner_optimizer", "budget_winner_optimizer")}
        ew_field, pw_field, bw_field = winner_field_map[field]
        buckets = defaultdict(list)
        for row in rows:
            regime_label = BehaviorAnalyzer.classify_regime(float(row["field_strength"]), coupling, config)
            buckets[(str(row[field]), regime_label)].append(row)
        energy_counts = BehaviorAnalyzer._counts_by_label(crossover, ew_field)
        physics_counts = BehaviorAnalyzer._counts_by_label(crossover, pw_field)
        budget_counts = BehaviorAnalyzer._counts_by_label(crossover, bw_field)
        profiles = []
        for (name, regime_label), bucket in sorted(buckets.items()):
            gate_buckets = defaultdict(list)
            for row in bucket:
                gate_buckets[float(row["gate_error"])].append(row)
            fragility_xs, fragility_ys = [], []
            for gate_error, gate_bucket in sorted(gate_buckets.items()):
                fragility_xs.append(gate_error)
                fragility_ys.append(BehaviorAnalyzer._mean([_safe_float(row.get("filtered_exact_gap")) for row in gate_bucket]) or 0.0)
            profiles.append({
                field: name,
                "regime_label": regime_label,
                "num_runs": len(bucket),
                "valid_fraction": BehaviorAnalyzer._valid_fraction(bucket),
                "mean_filtered_exact_gap": BehaviorAnalyzer._mean([_safe_float(row.get("filtered_exact_gap")) for row in bucket]),
                "std_filtered_exact_gap": BehaviorAnalyzer._std([_safe_float(row.get("filtered_exact_gap")) for row in bucket]),
                "mean_physics_score": BehaviorAnalyzer._mean([_safe_float(row.get("physics_score")) for row in bucket]),
                "mean_fidelity_to_exact": BehaviorAnalyzer._mean([_safe_float(row.get("fidelity_to_exact")) for row in bucket]),
                "mean_symmetry_breaking_error": BehaviorAnalyzer._mean([_safe_float(row.get("symmetry_breaking_error")) for row in bucket]),
                "mean_observable_error_l2": BehaviorAnalyzer._mean([_safe_float(row.get("filtered_observable_error_l2")) or _safe_float(row.get("observable_error_l2")) for row in bucket]),
                "mean_cost_standard_error": BehaviorAnalyzer._mean([_safe_float(row.get("cost_standard_error")) for row in bucket]),
                "mean_measurement_total_standard_error": BehaviorAnalyzer._mean([_safe_float(row.get("measurement_total_standard_error")) for row in bucket]),
                "mean_estimated_total_shots_used": BehaviorAnalyzer._mean([_safe_float(row.get("estimated_total_shots_used")) for row in bucket]),
                "mean_transpiled_depth": BehaviorAnalyzer._mean([_safe_float(row.get("transpiled_depth")) for row in bucket]),
                "mean_transpiled_two_qubit_gate_count": BehaviorAnalyzer._mean([_safe_float(row.get("transpiled_two_qubit_gate_count")) for row in bucket]),
                "mean_zne_mitigation_gain": BehaviorAnalyzer._mean([_safe_float(row.get("zne_mitigation_gain")) for row in bucket]),
                "fragility_slope_vs_gate_error": BehaviorAnalyzer._line_slope(fragility_xs, fragility_ys),
                "behavior_risk_score": BehaviorAnalyzer._behavior_risk(bucket, config),
                "raw_win_count": int(energy_counts.get(name, 0)),
                "physics_win_count": int(physics_counts.get(name, 0)),
                "budget_win_count": int(budget_counts.get(name, 0)),
            })
        return profiles

    @staticmethod
    def detect_deceptive_cases(rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
        flagged = []
        for row in rows:
            exact_gap = _safe_float(row.get("exact_gap"))
            fidelity = _safe_float(row.get("fidelity_to_exact"))
            symmetry_error = _safe_float(row.get("symmetry_breaking_error")) or 0.0
            obs_error = _safe_float(row.get("filtered_observable_error_l2")) or _safe_float(row.get("observable_error_l2")) or 0.0
            if exact_gap is None:
                continue
            if exact_gap <= 0.15 and (not bool(row.get("physical_valid")) or symmetry_error > 0.05 or (fidelity is not None and fidelity < 0.9) or obs_error > 0.15):
                flagged.append({
                    "label": row["label"], "n_qubits": row["n_qubits"], "field_strength": row["field_strength"], "gate_error": row["gate_error"], "ansatz": row["ansatz"], "optimizer": row["optimizer"], "depth": row["depth"],
                    "exact_gap": exact_gap, "fidelity_to_exact": fidelity, "symmetry_breaking_error": symmetry_error, "observable_error_l2": obs_error, "physical_valid": row.get("physical_valid"), "physical_validity_reason": row.get("physical_validity_reason"),
                })
        return flagged

    @staticmethod
    def narrative(regime_profiles, ansatz_profiles, optimizer_profiles, crossover, deceptive_cases, config: BehaviorConfig) -> str:
        lines = [
            "# Detailed Behavior Study", "",
            "This report summarizes how the TFIM VQE stack behaves across regimes, noise levels, ansatz families, optimizers, and execution-cost constraints.",
            "It intentionally separates raw numerical winners from physically valid and budget-feasible winners.", "",
            "## Behavior-analysis configuration", "",
            f"- weak_field_ratio={config.weak_field_ratio}",
            f"- near_critical_ratio={config.near_critical_ratio}",
            f"- low_noise_threshold={config.low_noise_threshold}",
            f"- moderate_noise_threshold={config.moderate_noise_threshold}",
            f"- behavior risk weights: symmetry={config.symmetry_risk_weight}, observable={config.observable_risk_weight}, uncertainty={config.uncertainty_risk_weight}",
            "", "## Regime-level behavior", "",
        ]
        for profile in regime_profiles:
            lines.append(f"- n={profile['n_qubits']}, regime={profile['regime_label']}, noise={profile['noise_regime']} (gate_error={profile['gate_error']:.4f}): valid_fraction={profile['valid_fraction']:.3f}, false_winner_rate={profile['false_winner_rate']:.3f}, dominant physics winner={profile['dominant_physics_winner_ansatz']}, dominant budget winner={profile['dominant_budget_winner_ansatz']}, mean filtered gap={profile['mean_filtered_exact_gap']}, mean measurement s.e.={profile['mean_measurement_total_standard_error']}.")
        lines.extend(["", "## Ansatz behavior", ""])
        for profile in ansatz_profiles:
            lines.append(f"- ansatz={profile['ansatz']}, regime={profile['regime_label']}: raw wins={profile['raw_win_count']}, physics wins={profile['physics_win_count']}, budget wins={profile['budget_win_count']}, valid_fraction={profile['valid_fraction']:.3f}, fragility slope vs gate error={profile['fragility_slope_vs_gate_error']}, behavior risk={profile['behavior_risk_score']}.")
        lines.extend(["", "## Optimizer behavior", ""])
        for profile in optimizer_profiles:
            lines.append(f"- optimizer={profile['optimizer']}, regime={profile['regime_label']}: physics wins={profile['physics_win_count']}, budget wins={profile['budget_win_count']}, mean filtered gap={profile['mean_filtered_exact_gap']}, mean cost s.e.={profile['mean_cost_standard_error']}.")
        false_winner_count = sum(bool(row.get("false_winner_flag")) for row in crossover)
        lines.extend(["", "## Crossover integrity", "", f"- Total crossover buckets: {len(crossover)}", f"- Buckets where the raw energy winner differed from the physics winner: {false_winner_count}", "", "## Deceptive low-energy cases", "", f"- Count: {len(deceptive_cases)}"])
        for case in deceptive_cases[:10]:
            lines.append(f"- {case['label']}: gap={case['exact_gap']}, fidelity={case['fidelity_to_exact']}, symmetry_error={case['symmetry_breaking_error']}, observable_error={case['observable_error_l2']}, physical_valid={case['physical_valid']}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def build(rows, aggregate, crossover, coupling: float, config: BehaviorConfig | None = None):
        cfg = config or BehaviorConfig()
        enriched_crossover = BehaviorAnalyzer.enrich_crossover(rows, crossover, coupling, cfg)
        regime_profiles = BehaviorAnalyzer.regime_profiles(rows, enriched_crossover, coupling, cfg)
        ansatz_profiles = BehaviorAnalyzer.competitor_profiles(rows, enriched_crossover, coupling, cfg, field="ansatz")
        optimizer_profiles = BehaviorAnalyzer.competitor_profiles(rows, enriched_crossover, coupling, cfg, field="optimizer")
        deceptive_cases = BehaviorAnalyzer.detect_deceptive_cases(rows)
        report = BehaviorAnalyzer.narrative(regime_profiles, ansatz_profiles, optimizer_profiles, enriched_crossover, deceptive_cases, cfg)
        return {
            "config": cfg.to_dict(),
            "regime_profiles": regime_profiles,
            "ansatz_profiles": ansatz_profiles,
            "optimizer_profiles": optimizer_profiles,
            "crossover": enriched_crossover,
            "crossover_profiles": enriched_crossover,
            "deceptive_cases": deceptive_cases,
            "report_markdown": report,
        }

    @staticmethod
    def save(prefix: Path, behavior: Dict[str, object]) -> None:
        prefix.with_name(prefix.name + "_behavior.json").write_text(json.dumps(behavior, indent=2))
        prefix.with_name(prefix.name + "_behavior_report.md").write_text(str(behavior["report_markdown"]))
        for key, suffix in [("regime_profiles", "_behavior_regimes.csv"), ("ansatz_profiles", "_behavior_ansatz.csv"), ("optimizer_profiles", "_behavior_optimizers.csv"), ("crossover", "_behavior_crossover.csv"), ("deceptive_cases", "_behavior_deceptive_cases.csv")]:
            rows = behavior.get(key)
            if rows:
                with prefix.with_name(prefix.name + suffix).open("w", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(rows)
