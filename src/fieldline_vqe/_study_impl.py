from __future__ import annotations

import csv
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, Iterable, List

from .ansatz import CircuitFactory
from .behavior import BehaviorAnalyzer
from .config import BehaviorConfig, NoiseDeck, StudySpec
from .experiment import FieldLineExperiment
from .hamiltonian import SpinChainBuilder
from .logging_utils import get_logger
from .plotting import PlotBook
from .interfaces import StudyService

LOGGER = get_logger(__name__)

__all__ = ["row_from_record", "StudyRunner"]

KEY_FIELDS = ["n_qubits", "field_strength", "gate_error", "ansatz", "depth", "optimizer"]


def row_from_record(record, n_qubits: int, field_strength: float) -> Dict[str, object]:
    row = asdict(record)
    row.update({
        "n_qubits": n_qubits,
        "field_strength": field_strength,
        "gate_error": row.pop("noise_level"),
        "zne_extrapolator": record.measurement_plan.get("zne_extrapolator"),
        "measurement_group_count": len(record.measurement_plan.get("groups", [])),
        "measurement_allocation": json.dumps(record.measurement_plan.get("allocation", {}), sort_keys=True),
        "measurement_total_standard_error": record.measurement_plan.get("total_standard_error"),
        "template_cache_hits": record.measurement_plan.get("template_cache_hits", 0),
        "template_cache_misses": record.measurement_plan.get("template_cache_misses", 0),
        "template_cache_size": record.measurement_plan.get("template_cache_size", 0),
        "transpile_cache_enabled": record.measurement_plan.get("transpile_cache_enabled", False),
        "zne_sample_count": len(record.zne_samples),
        "zne_mitigation_gain": record.mitigation_gain,
        "runtime_layout_final_index": json.dumps(record.measurement_plan.get("runtime_layout_final_index")),
        "runtime_layout_initial_index": json.dumps(record.measurement_plan.get("runtime_layout_initial_index")),
        "runtime_layout_final_present": record.measurement_plan.get("runtime_layout_final_present"),
    })
    row.update({key: record.observables.get(key) for key in [
        "magnetization_x", "magnetization_z", "correlation_xx_mean", "correlation_zz_mean", "connected_correlation_xx_mean", "connected_correlation_zz_mean", "x_even_sector_probability", "energy_variance", "energy_stddev", "relative_energy_stddev"
    ]})
    row["zne_noise_factors"] = "|".join(str(v) for v in record.zne_noise_factors)
    row["shot_schedule"] = json.dumps(record.shot_schedule)
    return row


def _iter_jobs(spec: StudySpec, noise_template: NoiseDeck) -> Iterable[Dict[str, object]]:
    for n_qubits in spec.system_sizes:
        for field_strength in spec.field_strengths:
            for seed in spec.seeds:
                for gate_error in spec.gate_errors:
                    noise_cfg = None
                    if gate_error > 0:
                        noise_cfg = NoiseDeck(
                            gate_error=gate_error,
                            two_qubit_gate_error=noise_template.two_qubit_gate_error,
                            t1=noise_template.t1,
                            t2=noise_template.t2,
                            gate_time=noise_template.gate_time,
                            seed=seed,
                            readout_error=noise_template.readout_error,
                            readout_error_01=noise_template.readout_error_01,
                            readout_error_10=noise_template.readout_error_10,
                        )
                    for ansatz_name in spec.ansatzes:
                        for depth in spec.depths:
                            for optimizer_name in spec.optimizers:
                                yield {
                                    "n_qubits": n_qubits,
                                    "field_strength": field_strength,
                                    "seed": seed,
                                    "gate_error": gate_error,
                                    "noise_cfg": noise_cfg,
                                    "ansatz_name": ansatz_name,
                                    "depth": depth,
                                    "optimizer_name": optimizer_name,
                                }


def _execute_job(job: Dict[str, object], spec: StudySpec) -> Dict[str, object]:
    n_qubits = int(job["n_qubits"])
    field_strength = float(job["field_strength"])
    seed = int(job["seed"])
    gate_error = float(job["gate_error"])
    ansatz_name = str(job["ansatz_name"])
    depth = int(job["depth"])
    optimizer_name = str(job["optimizer_name"])
    noise_cfg = job["noise_cfg"]
    hamiltonian = SpinChainBuilder.ising_chain(n_qubits, coupling=spec.coupling, field_strength=field_strength, periodic=spec.periodic_boundary)
    experiment = FieldLineExperiment(hamiltonian, n_qubits, field_strength, spec.coupling, seed)
    circuit = CircuitFactory.build(ansatz_name, n_qubits, depth)
    label = f"n{n_qubits}_h{field_strength:.2f}_e{gate_error:.3f}_{ansatz_name}_d{depth}_{optimizer_name}_s{seed}"
    record = experiment.run_vqe(
        circuit,
        optimizer_name,
        spec.max_iter,
        label,
        ansatz_name,
        depth,
        noise_cfg,
        spec.verification_shots,
        symmetry_penalty_lambda=spec.symmetry_penalty_lambda,
        shot_allocation=spec.shot_allocation,
        base_shots=spec.base_shots,
        final_shots=spec.final_shots,
        preflight_shots=spec.preflight_shots,
        enable_dynamic_shots=spec.enable_dynamic_shots,
        enable_readout_mitigation=spec.enable_readout_mitigation,
        enable_zne=spec.enable_zne,
        zne_factors=spec.zne_factors,
        zne_extrapolator=spec.zne_extrapolator,
        physical_validity_tol=spec.physical_validity_tol,
        spsa_config=spec.spsa,
    )
    return row_from_record(record, n_qubits, field_strength)


class StudyRunner(StudyService):
    @staticmethod
    def run(spec: StudySpec, noise_template: NoiseDeck) -> Dict[str, object]:
        spec.validate()
        noise_template.validate()
        jobs = list(_iter_jobs(spec, noise_template))
        LOGGER.info("Starting study | jobs=%s | max_workers=%s", len(jobs), spec.max_workers)
        rows: List[Dict[str, object]] = []
        if spec.max_workers == 1:
            for idx, job in enumerate(jobs, start=1):
                LOGGER.info("Study job %s/%s | n=%s | h=%.3f | gate=%.4f | ansatz=%s | depth=%s | optimizer=%s", idx, len(jobs), job["n_qubits"], float(job["field_strength"]), float(job["gate_error"]), job["ansatz_name"], job["depth"], job["optimizer_name"])
                rows.append(_execute_job(job, spec))
        else:
            with ThreadPoolExecutor(max_workers=spec.max_workers) as executor:
                futures = {executor.submit(_execute_job, job, spec): job for job in jobs}
                for idx, future in enumerate(as_completed(futures), start=1):
                    job = futures[future]
                    rows.append(future.result())
                    LOGGER.info("Completed study job %s/%s | label=%s", idx, len(jobs), rows[-1]["label"])
        aggregate = StudyRunner.aggregate(rows)
        crossover = StudyRunner.build_crossover(rows, spec)
        behavior = BehaviorAnalyzer.build(rows, aggregate, crossover, spec.coupling, spec.behavior)
        return {"rows": rows, "aggregate": aggregate, "crossover": crossover, "behavior": behavior}

    @staticmethod
    def aggregate(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
        buckets = defaultdict(list)
        for row in rows:
            key = tuple(row[f] for f in KEY_FIELDS)
            buckets[key].append(row)
        aggregate = []
        metrics = [
            "exact_gap", "filtered_exact_gap", "cost_standard_error", "unmitigated_cost_standard_error", "observable_error_l2", "filtered_observable_error_l2",
            "symmetry_postselection_rate", "sampled_postselection_rate", "sampled_postselection_standard_error", "mitigated_sampled_postselection_rate",
            "mitigated_sampled_postselection_standard_error", "measurement_total_standard_error", "symmetry_breaking_error", "physics_score", "fidelity_to_exact",
            "execution_time", "zne_mitigation_gain", "estimated_total_shots_used", "avg_shots_per_eval", "transpiled_depth", "transpiled_two_qubit_gate_count",
            "transpiled_entangling_layer_count", "magnetization_x", "magnetization_z", "correlation_xx_mean", "correlation_zz_mean", "connected_correlation_xx_mean", "connected_correlation_zz_mean", "energy_variance", "energy_stddev", "relative_energy_stddev", "half_chain_entropy",
        ]
        for key, bucket in buckets.items():
            payload = {field: value for field, value in zip(KEY_FIELDS, key)}
            payload["num_seeds"] = len(bucket)
            payload["shot_allocation_strategy"] = bucket[0].get("shot_allocation_strategy")
            payload["dynamic_shots_enabled"] = bucket[0].get("dynamic_shots_enabled")
            payload["zne_enabled"] = bucket[0].get("zne_enabled")
            for metric in metrics:
                values = [float(row[metric]) for row in bucket if row.get(metric) is not None]
                payload[f"mean_{metric}"] = mean(values) if values else None
                payload[f"std_{metric}"] = pstdev(values) if len(values) > 1 else (0.0 if values else None)
            payload["mean_gap_improvement"] = None if payload["mean_exact_gap"] is None or payload["mean_filtered_exact_gap"] is None else payload["mean_exact_gap"] - payload["mean_filtered_exact_gap"]
            aggregate.append(payload)
        return sorted(aggregate, key=lambda r: (r["n_qubits"], r["field_strength"], r["gate_error"], r["ansatz"], r["depth"], r["optimizer"]))

    @staticmethod
    def build_crossover(rows: List[Dict[str, object]], spec: StudySpec) -> List[Dict[str, object]]:
        buckets = defaultdict(list)
        for row in rows:
            buckets[(row["n_qubits"], row["field_strength"], row["gate_error"])].append(row)
        crossover_rows: List[Dict[str, object]] = []
        for (n_qubits, field_strength, gate_error), bucket in sorted(buckets.items()):
            energy_winner = min(bucket, key=lambda row: float(row["energy"]))
            feasible_bucket = [row for row in bucket if bool(row.get("physical_valid"))]
            candidate_bucket = feasible_bucket or bucket
            physics_winner = min(candidate_bucket, key=lambda row: float(row["physics_score"]) if row.get("physics_score") is not None else float(row.get("filtered_exact_gap") or row["exact_gap"]) + spec.crossover_symmetry_penalty * float(row.get("symmetry_breaking_error") or 0.0) + spec.crossover_observable_penalty * float(row.get("filtered_observable_error_l2") or 0.0))
            budget_bucket = feasible_bucket or bucket
            budget_winner = min(budget_bucket, key=lambda row: (float(row.get("estimated_total_shots_used") or 1e18), float(row.get("transpiled_two_qubit_gate_count") or 1e18), float(row.get("transpiled_depth") or 1e18), float(row.get("physics_score") or 1e18)))
            false_winner = energy_winner["label"] != physics_winner["label"]
            crossover_rows.append({
                "n_qubits": n_qubits,
                "field_strength": field_strength,
                "gate_error": gate_error,
                "physical_candidate_count": len(feasible_bucket),
                "physical_validity_tol": spec.physical_validity_tol,
                "energy_winner_label": energy_winner["label"],
                "energy_winner_ansatz": energy_winner["ansatz"],
                "energy_winner_depth": energy_winner["depth"],
                "energy_winner_optimizer": energy_winner["optimizer"],
                "energy_winner_energy": energy_winner["energy"],
                "energy_winner_physical_valid": energy_winner.get("physical_valid"),
                "energy_winner_symmetry_breaking_error": energy_winner.get("symmetry_breaking_error"),
                "energy_winner_x_parity": energy_winner.get("x_parity"),
                "energy_winner_target_x_parity_sector": energy_winner.get("target_x_parity_sector"),
                "energy_winner_physical_validity_reason": energy_winner.get("physical_validity_reason"),
                "physics_winner_label": physics_winner["label"],
                "physics_winner_ansatz": physics_winner["ansatz"],
                "physics_winner_depth": physics_winner["depth"],
                "physics_winner_optimizer": physics_winner["optimizer"],
                "physics_winner_energy": physics_winner["energy"],
                "physics_winner_physical_valid": physics_winner.get("physical_valid"),
                "physics_winner_filtered_exact_gap": physics_winner.get("filtered_exact_gap"),
                "physics_winner_symmetry_breaking_error": physics_winner.get("symmetry_breaking_error"),
                "physics_winner_filtered_observable_error_l2": physics_winner.get("filtered_observable_error_l2"),
                "physics_winner_target_x_parity_sector": physics_winner.get("target_x_parity_sector"),
                "physics_winner_physical_validity_reason": physics_winner.get("physical_validity_reason"),
                "budget_winner_label": budget_winner["label"],
                "budget_winner_ansatz": budget_winner["ansatz"],
                "budget_winner_depth": budget_winner["depth"],
                "budget_winner_optimizer": budget_winner["optimizer"],
                "budget_winner_estimated_total_shots_used": budget_winner.get("estimated_total_shots_used"),
                "budget_winner_transpiled_two_qubit_gate_count": budget_winner.get("transpiled_two_qubit_gate_count"),
                "budget_winner_transpiled_depth": budget_winner.get("transpiled_depth"),
                "budget_winner_physical_valid": budget_winner.get("physical_valid"),
                "false_winner_flag": false_winner,
                "winner_selection_rule": "prefer physically valid states, then lowest filtered gap plus symmetry and observable penalties",
                "crossover_symmetry_penalty": spec.crossover_symmetry_penalty,
                "crossover_observable_penalty": spec.crossover_observable_penalty,
            })
        return crossover_rows

    @staticmethod
    def save(prefix: Path, spec: StudySpec, payload: Dict[str, object]) -> None:
        rows, aggregate, crossover = payload["rows"], payload["aggregate"], payload["crossover"]
        behavior = payload.get("behavior")
        prefix.with_suffix(".json").write_text(json.dumps({"config": spec.to_dict(), **payload}, indent=2))
        if rows:
            with prefix.with_name(prefix.name + "_raw.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
        if aggregate:
            with prefix.with_name(prefix.name + "_summary.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(aggregate[0].keys()))
                writer.writeheader()
                writer.writerows(aggregate)
        if crossover:
            with prefix.with_name(prefix.name + "_crossover.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(crossover[0].keys()))
                writer.writeheader()
                writer.writerows(crossover)
        if behavior is not None:
            BehaviorAnalyzer.save(prefix, behavior)
        PlotBook.save_study(prefix, aggregate)
