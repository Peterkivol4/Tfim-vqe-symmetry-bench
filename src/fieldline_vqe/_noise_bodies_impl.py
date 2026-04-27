from __future__ import annotations

import csv
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import numpy as np

from ._study_impl import row_from_record
from .ansatz import CircuitFactory
from .config import NoiseBodyConfig, NoiseBodySweepSpec
from .experiment import FieldLineExperiment
from .hamiltonian import SpinChainBuilder
from .logging_utils import get_logger
from .results import DeviationSignature

LOGGER = get_logger(__name__)

__all__ = [
    "BODY_MATCH_FEATURES",
    "NoiseBodyStudyRunner",
    "build_deviation_signature",
    "critical_drift_score",
    "infer_noise_body",
    "match_noise_bodies",
]

BODY_MATCH_FEATURES = (
    "energy_error",
    "fidelity_loss",
    "parity_sector_loss",
    "symmetry_breaking_error",
    "magnetization_x_error",
    "magnetization_z_error",
    "correlation_xx_error",
    "correlation_zz_error",
    "connected_correlation_error",
    "entanglement_entropy_error",
    "energy_variance",
    "gradient_norm",
    "critical_drift_score",
)
SIGNATURE_FIELDS = tuple(DeviationSignature.__dataclass_fields__.keys())

BODY_MATCH_WEIGHTS = {
    "energy_error": 1.0,
    "fidelity_loss": 1.5,
    "parity_sector_loss": 1.75,
    "symmetry_breaking_error": 1.75,
    "magnetization_x_error": 1.25,
    "magnetization_z_error": 1.0,
    "correlation_xx_error": 1.5,
    "correlation_zz_error": 1.25,
    "connected_correlation_error": 1.25,
    "entanglement_entropy_error": 1.0,
    "energy_variance": 0.75,
    "gradient_norm": 0.5,
    "critical_drift_score": 1.5,
}


def _abs_error(left: Mapping[str, object], right: Mapping[str, object], key: str) -> float:
    lhs = left.get(key)
    rhs = right.get(key)
    if lhs is None or rhs is None:
        return 0.0
    return float(abs(float(lhs) - float(rhs)))


def critical_drift_score(field_strength: float, coupling: float, metrics: Mapping[str, float | None]) -> float:
    proximity = 1.0 / (1.0 + abs(float(field_strength) / max(abs(float(coupling)), 1e-12) - 1.0))
    components = [
        metrics.get("magnetization_x_error"),
        metrics.get("magnetization_z_error"),
        metrics.get("correlation_xx_error"),
        metrics.get("correlation_zz_error"),
        metrics.get("connected_correlation_error"),
    ]
    usable = [float(value) for value in components if value is not None]
    if not usable:
        return 0.0
    return float(proximity * sum(usable) / len(usable))


def build_deviation_signature(
    *,
    record,
    exact_summary: Mapping[str, object] | None,
    n_qubits: int,
    field_strength: float,
    coupling: float,
    noise_body: str,
    noise_strength: float,
    gradient_norm: float | None,
) -> DeviationSignature:
    exact = exact_summary or {}
    observables = record.observables
    parity_sector_loss = 1.0 - float(record.target_sector_probability or 0.0)
    fidelity_loss = None if record.fidelity_to_exact is None else float(max(0.0, 1.0 - float(record.fidelity_to_exact)))
    entropy_error = None
    if observables.get("half_chain_entropy") is not None and exact.get("half_chain_entropy") is not None:
        entropy_error = float(abs(float(observables["half_chain_entropy"]) - float(exact["half_chain_entropy"])))
    payload = {
        "magnetization_x_error": _abs_error(observables, exact, "magnetization_x"),
        "magnetization_z_error": _abs_error(observables, exact, "magnetization_z"),
        "correlation_xx_error": _abs_error(observables, exact, "correlation_xx_mean"),
        "correlation_zz_error": _abs_error(observables, exact, "correlation_zz_mean"),
        "connected_correlation_error": mean(
            [
                _abs_error(observables, exact, "connected_correlation_xx_mean"),
                _abs_error(observables, exact, "connected_correlation_zz_mean"),
            ]
        ),
    }
    return DeviationSignature(
        n=int(n_qubits),
        g=float(field_strength),
        depth=int(record.depth),
        ansatz=str(record.ansatz),
        optimizer=str(record.optimizer),
        noise_body=str(noise_body),
        noise_strength=float(noise_strength),
        energy_error=float(record.exact_gap),
        fidelity_loss=fidelity_loss,
        parity_sector_loss=float(max(parity_sector_loss, 0.0)),
        symmetry_breaking_error=float(record.symmetry_breaking_error or 0.0),
        magnetization_x_error=float(payload["magnetization_x_error"]),
        magnetization_z_error=float(payload["magnetization_z_error"]),
        correlation_xx_error=float(payload["correlation_xx_error"]),
        correlation_zz_error=float(payload["correlation_zz_error"]),
        connected_correlation_error=float(payload["connected_correlation_error"]),
        entanglement_entropy_error=entropy_error,
        energy_variance=float(record.energy_variance or 0.0),
        gradient_norm=None if gradient_norm is None else float(gradient_norm),
        critical_drift_score=critical_drift_score(field_strength, coupling, payload),
    )


def _signature_row(signature: DeviationSignature) -> Dict[str, object]:
    payload = asdict(signature)
    payload["deformation_score"] = _deformation_score(payload)
    return payload


def _deformation_score(row: Mapping[str, object]) -> float:
    total = 0.0
    weight_total = 0.0
    for feature in BODY_MATCH_FEATURES:
        value = row.get(feature)
        if value is None:
            continue
        weight = float(BODY_MATCH_WEIGHTS.get(feature, 1.0))
        total += weight * abs(float(value))
        weight_total += weight
    if weight_total <= 0.0:
        return 0.0
    return float(total / weight_total)


def _compute_gradient_norm(experiment: FieldLineExperiment, ansatz, optimal_params: Sequence[float], body_cfg: NoiseBodyConfig | None, spec: NoiseBodySweepSpec) -> float:
    theta = np.asarray(optimal_params, dtype=float)

    def objective(params: np.ndarray) -> float:
        shots = spec.final_shots if body_cfg is not None else None
        value, _ = experiment._estimate_cost(
            ansatz=ansatz,
            params=np.asarray(params, dtype=float),
            noise_cfg=body_cfg,
            symmetry_penalty_lambda=spec.symmetry_penalty_lambda,
            shots=shots,
            shot_allocation=spec.shot_allocation,
            preflight_shots=spec.preflight_shots,
            enable_readout_mitigation=spec.enable_readout_mitigation,
            enable_zne=False,
            zne_factors=[1],
            zne_extrapolator="linear",
        )
        return float(value)

    gradient = experiment.optimization_executor._parameter_shift_gradient(objective, theta)
    return float(np.linalg.norm(gradient))


def _noise_body_row(record, signature: DeviationSignature, *, n_qubits: int, field_strength: float, body_cfg: NoiseBodyConfig | None) -> Dict[str, object]:
    row = row_from_record(record, n_qubits, field_strength)
    row.update(_signature_row(signature))
    row.update(
        {
            "noise_body": "ideal" if body_cfg is None else body_cfg.body,
            "noise_strength": 0.0 if body_cfg is None else float(body_cfg.strength),
            "noise_correlation": None if body_cfg is None else float(body_cfg.correlation),
            "noise_coherence_angle": None if body_cfg is None else float(body_cfg.effective_coherence_angle()),
            "noise_readout_error": 0.0 if body_cfg is None else float(max(body_cfg.readout_pair())),
        }
    )
    return row


def _iter_jobs(spec: NoiseBodySweepSpec) -> Iterable[Dict[str, object]]:
    for n_qubits in spec.system_sizes:
        for field_strength in spec.field_strengths:
            for seed in spec.seeds:
                for body in spec.bodies:
                    body_strengths = [0.0] if body == "ideal" else list(spec.strengths)
                    for strength in body_strengths:
                        body_cfg = None
                        if body != "ideal":
                            body_cfg = NoiseBodyConfig(
                                body=body,
                                strength=float(strength),
                                correlation=spec.body_correlation,
                                coherence_angle=spec.body_coherence_angle,
                                readout_error=spec.body_readout_error,
                                seed=seed,
                            )
                        for ansatz_name in spec.ansatzes:
                            for depth in spec.depths:
                                for optimizer_name in spec.optimizers:
                                    yield {
                                        "n_qubits": n_qubits,
                                        "field_strength": field_strength,
                                        "seed": seed,
                                        "body_cfg": body_cfg,
                                        "body": body,
                                        "strength": float(strength),
                                        "ansatz_name": ansatz_name,
                                        "depth": depth,
                                        "optimizer_name": optimizer_name,
                                    }


def _execute_job(job: Dict[str, object], spec: NoiseBodySweepSpec) -> Dict[str, object]:
    n_qubits = int(job["n_qubits"])
    field_strength = float(job["field_strength"])
    seed = int(job["seed"])
    body_cfg = job["body_cfg"]
    body = str(job["body"])
    strength = float(job["strength"])
    ansatz_name = str(job["ansatz_name"])
    depth = int(job["depth"])
    optimizer_name = str(job["optimizer_name"])
    hamiltonian = SpinChainBuilder.ising_chain(n_qubits, coupling=spec.coupling, field_strength=field_strength, periodic=spec.periodic_boundary)
    experiment = FieldLineExperiment(hamiltonian, n_qubits, field_strength, spec.coupling, seed)
    circuit = CircuitFactory.build(ansatz_name, n_qubits, depth)
    label = f"n{n_qubits}_h{field_strength:.2f}_b{body}_s{strength:.3f}_{ansatz_name}_d{depth}_{optimizer_name}_seed{seed}"
    record = experiment.run_vqe(
        circuit,
        optimizer_name,
        spec.max_iter,
        label,
        ansatz_name,
        depth,
        body_cfg,
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
    gradient_norm = None
    if spec.compute_gradient_norm:
        gradient_norm = _compute_gradient_norm(experiment, circuit, record.optimal_params, body_cfg, spec)
    signature = build_deviation_signature(
        record=record,
        exact_summary=experiment.exact_summary,
        n_qubits=n_qubits,
        field_strength=field_strength,
        coupling=spec.coupling,
        noise_body=body,
        noise_strength=strength,
        gradient_norm=gradient_norm,
    )
    return _noise_body_row(record, signature, n_qubits=n_qubits, field_strength=field_strength, body_cfg=body_cfg)


def _summary_metrics(rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    metrics = [
        "energy_error",
        "fidelity_loss",
        "parity_sector_loss",
        "symmetry_breaking_error",
        "magnetization_x_error",
        "magnetization_z_error",
        "correlation_xx_error",
        "correlation_zz_error",
        "connected_correlation_error",
        "entanglement_entropy_error",
        "energy_variance",
        "gradient_norm",
        "critical_drift_score",
        "deformation_score",
        "exact_gap",
        "filtered_exact_gap",
        "observable_error_l2",
        "filtered_observable_error_l2",
        "physics_score",
        "execution_time",
        "transpiled_depth",
        "transpiled_two_qubit_gate_count",
    ]
    buckets: Dict[tuple, List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = (
            row["n_qubits"],
            row["field_strength"],
            row["noise_body"],
            row["noise_strength"],
            row["ansatz"],
            row["depth"],
            row["optimizer"],
        )
        buckets[key].append(row)
    summary: List[Dict[str, object]] = []
    for key, bucket in sorted(buckets.items()):
        payload = {
            "n_qubits": key[0],
            "field_strength": key[1],
            "noise_body": key[2],
            "noise_strength": key[3],
            "ansatz": key[4],
            "depth": key[5],
            "optimizer": key[6],
            "num_seeds": len(bucket),
            "valid_fraction": float(sum(1 for row in bucket if row.get("physical_valid")) / len(bucket)),
            "false_winner_fraction": None,
        }
        for metric in metrics:
            values = [float(row[metric]) for row in bucket if row.get(metric) is not None]
            payload[f"mean_{metric}"] = mean(values) if values else None
            payload[f"std_{metric}"] = pstdev(values) if len(values) > 1 else (0.0 if values else None)
        summary.append(payload)
    return summary


def _build_crossover(rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    buckets: Dict[tuple, List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = (row["n_qubits"], row["field_strength"], row["noise_body"], row["noise_strength"])
        buckets[key].append(row)
    crossover_rows: List[Dict[str, object]] = []
    for key, bucket in sorted(buckets.items()):
        energy_winner = min(bucket, key=lambda row: float(row["energy"]))
        feasible = [row for row in bucket if bool(row.get("physical_valid"))]
        candidates = feasible or bucket
        physics_winner = min(candidates, key=lambda row: float(row.get("physics_score") if row.get("physics_score") is not None else row["exact_gap"]))
        false_winner = energy_winner["label"] != physics_winner["label"]
        crossover_rows.append(
            {
                "n_qubits": key[0],
                "field_strength": key[1],
                "noise_body": key[2],
                "noise_strength": key[3],
                "physical_candidate_count": len(feasible),
                "energy_winner_label": energy_winner["label"],
                "energy_winner_ansatz": energy_winner["ansatz"],
                "energy_winner_energy": energy_winner["energy"],
                "energy_winner_symmetry_breaking_error": energy_winner.get("symmetry_breaking_error"),
                "physics_winner_label": physics_winner["label"],
                "physics_winner_ansatz": physics_winner["ansatz"],
                "physics_winner_energy": physics_winner["energy"],
                "physics_winner_filtered_exact_gap": physics_winner.get("filtered_exact_gap"),
                "physics_winner_symmetry_breaking_error": physics_winner.get("symmetry_breaking_error"),
                "false_winner_flag": false_winner,
            }
        )
    return crossover_rows


def _critical_drift_rows(summary_rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for row in summary_rows:
        rows.append(
            {
                "n_qubits": row["n_qubits"],
                "field_strength": row["field_strength"],
                "noise_body": row["noise_body"],
                "noise_strength": row["noise_strength"],
                "mean_critical_drift_score": row.get("mean_critical_drift_score"),
                "mean_deformation_score": row.get("mean_deformation_score"),
            }
        )
    return rows


def _feature_value(row: Mapping[str, object], feature: str) -> float | None:
    value = row.get(feature)
    if value is None:
        mean_key = f"mean_{feature}"
        value = row.get(mean_key)
    if value is None:
        return None
    return float(value)


def _compute_centroids(rows: Sequence[Mapping[str, object]]) -> Dict[str, Dict[str, float]]:
    buckets: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        body = str(row["noise_body"])
        for feature in BODY_MATCH_FEATURES:
            value = _feature_value(row, feature)
            if value is not None:
                buckets[body][feature].append(value)
    centroids: Dict[str, Dict[str, float]] = {}
    for body, features in buckets.items():
        centroids[body] = {feature: float(sum(values) / len(values)) for feature, values in features.items() if values}
    return centroids


def infer_noise_body(row: Mapping[str, object], reference_rows: Sequence[Mapping[str, object]]) -> str:
    centroids = _compute_centroids(reference_rows)
    best_label = ""
    best_distance = float("inf")
    for body, centroid in centroids.items():
        total = 0.0
        used = 0.0
        for feature in BODY_MATCH_FEATURES:
            lhs = _feature_value(row, feature)
            rhs = centroid.get(feature)
            if lhs is None or rhs is None:
                continue
            weight = float(BODY_MATCH_WEIGHTS.get(feature, 1.0))
            total += weight * (lhs - rhs) ** 2
            used += weight
        if used <= 0.0:
            continue
        distance = total / used
        if distance < best_distance:
            best_distance = distance
            best_label = body
    return best_label


def _load_rows(path: Path) -> List[Dict[str, object]]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text())
        if isinstance(payload, dict) and "signatures" in payload:
            return [dict(row) for row in payload["signatures"]]
        if isinstance(payload, list):
            return [dict(row) for row in payload]
        raise ValueError(f"Unsupported JSON payload in {path}")
    with path.open() as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _matching_report(input_rows: Sequence[Mapping[str, object]], reference_rows: Sequence[Mapping[str, object]]) -> Dict[str, object]:
    labels = sorted({str(row["noise_body"]) for row in reference_rows})
    confusion = {label: {other: 0 for other in labels} for label in labels}
    correct = 0
    total = 0
    for row in input_rows:
        truth = str(row["noise_body"])
        predicted = infer_noise_body(row, reference_rows)
        if truth not in confusion:
            confusion[truth] = {other: 0 for other in labels}
            labels.append(truth)
        if predicted not in confusion[truth]:
            for existing in confusion.values():
                existing.setdefault(predicted, 0)
        confusion[truth][predicted] = confusion[truth].get(predicted, 0) + 1
        correct += int(predicted == truth)
        total += 1
    return {
        "accuracy": float(correct / max(total, 1)),
        "correct": int(correct),
        "total": int(total),
        "labels": labels,
        "confusion": confusion,
    }


def _report_table(rows: Sequence[Sequence[object]]) -> str:
    if not rows:
        return ""
    widths = [max(len(str(row[idx])) for row in rows) for idx in range(len(rows[0]))]
    lines = []
    for row_idx, row in enumerate(rows):
        cells = [str(value).ljust(widths[idx]) for idx, value in enumerate(row)]
        lines.append("| " + " | ".join(cells) + " |")
        if row_idx == 0:
            lines.append("| " + " | ".join("-" * widths[idx] for idx in range(len(widths))) + " |")
    return "\n".join(lines)


def _write_matching_report(report: Mapping[str, object], out: Path) -> None:
    labels = list(report["labels"])
    confusion = report["confusion"]
    table_rows = [["true \\ predicted", *labels]]
    for truth in labels:
        table_rows.append([truth, *[confusion.get(truth, {}).get(pred, 0) for pred in labels]])
    lines = [
        "# Body matching report",
        "",
        f"- accuracy: {report['accuracy']:.3f}",
        f"- correct: {report['correct']}",
        f"- total: {report['total']}",
        "",
        _report_table(table_rows),
    ]
    out.write_text("\n".join(lines) + "\n")


def match_noise_bodies(input_path: Path, reference_path: Path | None = None, output_path: Path | None = None) -> Dict[str, object]:
    input_rows = _load_rows(input_path)
    reference_rows = input_rows if reference_path is None else _load_rows(reference_path)
    report = _matching_report(input_rows, reference_rows)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _write_matching_report(report, output_path)
    return report


def _write_gradient_report(rows: Sequence[Dict[str, object]], out: Path) -> None:
    by_body: Dict[str, List[float]] = defaultdict(list)
    for row in rows:
        if row.get("gradient_norm") is not None:
            by_body[str(row["noise_body"])].append(float(row["gradient_norm"]))
    lines = [
        "# Gradient collapse report",
        "",
        "- probe_method: parameter-shift proxy at the final optimized parameters",
        "- note: for noisy bodies this is a simulator diagnostic, not a hardware gradient oracle",
        "",
    ]
    if not by_body:
        lines.append("No gradient probes were recorded.")
    else:
        table_rows = [["noise_body", "mean_gradient_norm", "min_gradient_norm", "max_gradient_norm", "stall_fraction(<1e-2)"]]
        for body in sorted(by_body):
            values = by_body[body]
            stall = sum(1 for value in values if value < 1e-2) / max(len(values), 1)
            table_rows.append(
                [
                    body,
                    f"{mean(values):.6f}",
                    f"{min(values):.6f}",
                    f"{max(values):.6f}",
                    f"{stall:.3f}",
                ]
            )
        lines.append(_report_table(table_rows))
    out.write_text("\n".join(lines) + "\n")


def _write_body_atlas_report(
    *,
    spec: NoiseBodySweepSpec,
    rows: Sequence[Dict[str, object]],
    summary_rows: Sequence[Dict[str, object]],
    crossover_rows: Sequence[Dict[str, object]],
    matching_report: Mapping[str, object],
    out: Path,
) -> None:
    false_winner_by_body: Dict[str, List[bool]] = defaultdict(list)
    for row in crossover_rows:
        false_winner_by_body[str(row["noise_body"])].append(bool(row["false_winner_flag"]))
    lines = [
        "# Body atlas report",
        "",
        "FieldLine now treats each noise model as a structured environmental body and summarizes the deformation signature it leaves on the TFIM variational state.",
        "",
        "## Sweep",
        "",
        f"- system_sizes: {spec.system_sizes}",
        f"- field_strengths: {spec.field_strengths}",
        f"- depths: {spec.depths}",
        f"- ansatzes: {spec.ansatzes}",
        f"- optimizers: {spec.optimizers}",
        f"- bodies: {spec.bodies}",
        f"- strengths: {spec.strengths}",
        f"- matching_accuracy: {matching_report['accuracy']:.3f}",
        "",
        "## Global findings",
        "",
        f"- total_runs: {len(rows)}",
        f"- total_crossover_buckets: {len(crossover_rows)}",
        f"- false_winner_fraction: {sum(1 for row in crossover_rows if row['false_winner_flag']) / max(len(crossover_rows), 1):.3f}",
        "",
    ]
    for body in spec.bodies:
        body_rows = [row for row in summary_rows if str(row["noise_body"]) == body]
        if not body_rows:
            continue
        worst = max(body_rows, key=lambda row: float(row.get("mean_deformation_score") or 0.0))
        dominant_feature = max(
            (
                ("magnetization_x_error", float(worst.get("mean_magnetization_x_error") or 0.0)),
                ("magnetization_z_error", float(worst.get("mean_magnetization_z_error") or 0.0)),
                ("correlation_xx_error", float(worst.get("mean_correlation_xx_error") or 0.0)),
                ("correlation_zz_error", float(worst.get("mean_correlation_zz_error") or 0.0)),
                ("symmetry_breaking_error", float(worst.get("mean_symmetry_breaking_error") or 0.0)),
                ("energy_error", float(worst.get("mean_energy_error") or 0.0)),
            ),
            key=lambda item: item[1],
        )[0]
        energy_hidden = float(worst.get("mean_deformation_score") or 0.0) > float(worst.get("mean_energy_error") or 0.0)
        if body == "readout_only":
            failure_mode = "measurement-level"
        elif float(worst.get("mean_gradient_norm") or 1.0) < 1e-2 and float(worst.get("mean_energy_error") or 0.0) > 1e-2:
            failure_mode = "optimizer-level"
        else:
            failure_mode = "state-level"
        lines.extend(
            [
                f"## Body: {body}",
                "",
                f"- strongest damage point: n={worst['n_qubits']}, g={worst['field_strength']}, strength={worst['noise_strength']}, ansatz={worst['ansatz']}, depth={worst['depth']}, optimizer={worst['optimizer']}",
                f"- dominant observable shift: {dominant_feature}",
                f"- energy hid some damage: {'yes' if energy_hidden else 'no'}",
                f"- valid_fraction: {float(worst.get('valid_fraction') or 0.0):.3f}",
                f"- false_winner_fraction: {sum(1 for value in false_winner_by_body.get(body, []) if value) / max(len(false_winner_by_body.get(body, [])), 1):.3f}",
                f"- mitigation status in this sweep: {'enabled' if spec.enable_zne or spec.enable_readout_mitigation else 'disabled'}",
                f"- dominant failure mode: {failure_mode}",
                "",
            ]
        )
    out.write_text("\n".join(lines) + "\n")


class NoiseBodyStudyRunner:
    @staticmethod
    def run(spec: NoiseBodySweepSpec) -> Dict[str, object]:
        spec.validate()
        jobs = list(_iter_jobs(spec))
        LOGGER.info("Starting noise-body sweep | jobs=%s | max_workers=%s", len(jobs), spec.max_workers)
        rows: List[Dict[str, object]] = []
        if spec.max_workers == 1:
            for idx, job in enumerate(jobs, start=1):
                LOGGER.info(
                    "Noise-body job %s/%s | n=%s | g=%.3f | body=%s | strength=%.4f | ansatz=%s | depth=%s | optimizer=%s",
                    idx,
                    len(jobs),
                    job["n_qubits"],
                    float(job["field_strength"]),
                    job["body"],
                    float(job["strength"]),
                    job["ansatz_name"],
                    job["depth"],
                    job["optimizer_name"],
                )
                rows.append(_execute_job(job, spec))
        else:
            with ThreadPoolExecutor(max_workers=spec.max_workers) as executor:
                futures = {executor.submit(_execute_job, job, spec): job for job in jobs}
                for idx, future in enumerate(as_completed(futures), start=1):
                    rows.append(future.result())
                    LOGGER.info("Completed noise-body job %s/%s | label=%s", idx, len(jobs), rows[-1]["label"])
        summary_rows = _summary_metrics(rows)
        crossover_rows = _build_crossover(rows)
        false_winner_buckets: Dict[tuple, List[bool]] = defaultdict(list)
        for row in crossover_rows:
            false_winner_buckets[(row["n_qubits"], row["field_strength"], row["noise_body"], row["noise_strength"])].append(bool(row["false_winner_flag"]))
        for row in summary_rows:
            bucket = false_winner_buckets.get((row["n_qubits"], row["field_strength"], row["noise_body"], row["noise_strength"]), [])
            row["false_winner_fraction"] = float(sum(1 for value in bucket if value) / len(bucket)) if bucket else 0.0
        signatures = [{key: row[key] for key in SIGNATURE_FIELDS} for row in rows]
        critical_rows = _critical_drift_rows(summary_rows)
        matching_report = _matching_report(rows, summary_rows)
        return {
            "rows": rows,
            "summary": summary_rows,
            "crossover": crossover_rows,
            "signatures": signatures,
            "critical_drift": critical_rows,
            "matching": matching_report,
        }

    @staticmethod
    def save(prefix: Path, spec: NoiseBodySweepSpec, payload: Dict[str, object]) -> None:
        prefix.parent.mkdir(parents=True, exist_ok=True)
        rows = payload["rows"]
        summary_rows = payload["summary"]
        signatures = payload["signatures"]
        critical_rows = payload["critical_drift"]
        matching_report = payload["matching"]
        atlas_report = prefix.with_name(prefix.name + "_body_atlas_report.md")
        gradient_report = prefix.with_name(prefix.name + "_gradient_collapse_report.md")
        matching_path = prefix.with_name(prefix.name + "_body_matching_report.md")
        payload_path = prefix.with_suffix(".json")
        raw_csv = prefix.with_name(prefix.name + "_raw.csv")
        summary_csv = prefix.with_name(prefix.name + "_summary.csv")
        signature_json = prefix.with_name(prefix.name + "_deviation_signatures.json")
        critical_csv = prefix.with_name(prefix.name + "_critical_drift_map.csv")
        payload_path.write_text(json.dumps({"config": spec.to_dict(), **payload}, indent=2))
        if rows:
            with raw_csv.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
        if summary_rows:
            with summary_csv.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0].keys()))
                writer.writeheader()
                writer.writerows(summary_rows)
        signature_json.write_text(json.dumps({"config": spec.to_dict(), "signatures": signatures}, indent=2))
        if critical_rows:
            with critical_csv.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(critical_rows[0].keys()))
                writer.writeheader()
                writer.writerows(critical_rows)
        _write_body_atlas_report(spec=spec, rows=rows, summary_rows=summary_rows, crossover_rows=payload["crossover"], matching_report=matching_report, out=atlas_report)
        _write_gradient_report(rows, gradient_report)
        _write_matching_report(matching_report, matching_path)
