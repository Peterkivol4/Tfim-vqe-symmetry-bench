from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import DensityMatrix, SparsePauliOp, Statevector
from scipy.optimize import minimize

from .config import NoiseBodyConfig, NoiseDeck, SPSAConfig
from .logging_utils import get_logger
from .metrics import SymmetryGate, parity_expectation
from .observables import MeasurementPlanner, StateAnalyzer, expectation, observable_error_l2

LOGGER = get_logger(__name__)

__all__ = ["ObjectiveTrace", "OptimizerTrace", "StateExecutor", "MeasurementExecutor", "OptimizationExecutor"]


@dataclass
class ObjectiveTrace:
    history: List[float] = field(default_factory=list)
    shot_schedule: List[int] = field(default_factory=list)
    total_shot_history: List[int] = field(default_factory=list)
    last_metadata: Dict[str, object] = field(default_factory=dict)
    evaluation_count: int = 0

    def record(self, value: float, metadata: Dict[str, object], shots: Optional[int]) -> None:
        self.evaluation_count += 1
        effective_shots = int((shots or 0) * len(metadata.get("zne_noise_factors", [1])))
        payload = dict(metadata)
        payload["shots_used"] = shots
        payload["effective_total_shots"] = effective_shots
        self.last_metadata = payload
        self.history.append(float(value))
        self.shot_schedule.append(int(shots or 0))
        self.total_shot_history.append(effective_shots)

    def summary(self, *, optimizer: str, success: bool, message: str, requested_max_iter: int, effective_max_iter: int, nfev: int) -> Dict[str, object]:
        total_shots = int(sum(self.total_shot_history))
        return {
            "success": bool(success),
            "message": str(message),
            "nfev": int(nfev),
            "requested_max_iter": int(requested_max_iter),
            "effective_max_iter": int(effective_max_iter),
            "optimizer": optimizer,
            "last_metadata": dict(self.last_metadata),
            "shot_schedule": list(self.shot_schedule),
            "total_shot_history": list(self.total_shot_history),
            "total_shots_used": total_shots,
            "avg_shots_per_eval": float(total_shots / max(len(self.total_shot_history), 1)),
        }


class StateExecutor:
    def __init__(self, experiment):
        self.experiment = experiment

    def simulate_state(self, circuit: QuantumCircuit, noise_cfg: Optional[NoiseDeck | NoiseBodyConfig]) -> Statevector | DensityMatrix:
        if noise_cfg is None:
            return Statevector.from_instruction(circuit)
        sim_circuit = circuit.copy()
        sim_circuit.save_density_matrix()
        backend = self.experiment._get_backend(noise_cfg, method="density_matrix")
        compiled = transpile(sim_circuit, backend, seed_transpiler=self.experiment.seed)
        return DensityMatrix(backend.run(compiled, shots=1).result().data(0)["density_matrix"])

    def estimate_observables(self, state: Statevector | DensityMatrix) -> Dict[str, object]:
        exp = self.experiment
        return StateAnalyzer.summarize(state, exp.n_qubits, exp.hamiltonian, exp.exact_state, exp.observable_bundle)

    def symmetry_projection_summary(self, state: Statevector | DensityMatrix) -> Dict[str, object]:
        exp = self.experiment
        filtered_state, rate = StateAnalyzer.x_parity_projection(state, exp.n_qubits, sector=exp.target_x_parity_sector)
        raw = self.estimate_observables(state)
        filtered = self.estimate_observables(filtered_state)
        keys = ["magnetization_x", "magnetization_z", "correlation_xx_mean", "correlation_zz_mean"]
        raw_err = filtered_err = None
        raw_gap = filtered_gap = gap_improvement = None
        if exp.exact_summary is not None:
            raw_err = observable_error_l2(raw, exp.exact_summary, keys)
            filtered_err = observable_error_l2(filtered, exp.exact_summary, keys)
            raw_gap = abs(float(raw["energy"]) - exp.exact_energy)
            filtered_gap = abs(float(filtered["energy"]) - exp.exact_energy)
            gap_improvement = raw_gap - filtered_gap
        return {
            "raw": raw,
            "filtered": filtered,
            "postselection_rate": rate,
            "raw_observable_error_l2": raw_err,
            "filtered_observable_error_l2": filtered_err,
            "raw_exact_gap": raw_gap,
            "filtered_exact_gap": filtered_gap,
            "gap_improvement": gap_improvement,
            "target_sector": int(exp.target_x_parity_sector),
        }


class MeasurementExecutor:
    def __init__(self, experiment):
        self.experiment = experiment

    def estimate_operator_with_shots(
        self,
        ansatz: QuantumCircuit,
        params: np.ndarray,
        operator: SparsePauliOp,
        noise_cfg: NoiseDeck | NoiseBodyConfig,
        total_shots: int,
        shot_allocation: str,
        preflight_shots: int,
        enable_readout_mitigation: bool,
    ) -> tuple[float, Dict[str, object]]:
        exp = self.experiment
        groups = exp._measurement_groups_for(operator)
        empirical_variances: Dict[str, float] = {}
        empirical_stddevs: Dict[str, float] = {}
        preflight_counts: Dict[str, Dict[str, int]] = {}
        preflight_alloc: Dict[str, int] = {}
        variances: Dict[str, float] = {}
        stddevs: Dict[str, float] = {}
        group_values: Dict[str, float] = {}
        template_hits = 0
        template_misses = 0

        if shot_allocation == "variance_weighted":
            preflight_budget = max(preflight_shots, len(groups))
            preflight_alloc = MeasurementPlanner.allocate_shots(groups, preflight_budget, strategy="equal")
            for group in groups:
                counts, meta = exp._sample_counts_from_template(ansatz, params, group.basis, noise_cfg, preflight_alloc[group.basis])
                template_hits += int(meta["template_cache_hit"])
                template_misses += int(not meta["template_cache_hit"])
                processed = exp._processed_distribution(counts, noise_cfg, enable_readout_mitigation)
                _, variance = MeasurementPlanner.group_value_and_variance(processed, group)
                empirical_variances[group.basis] = variance
                empirical_stddevs[group.basis] = float(np.sqrt(max(variance, 0.0)))
                preflight_counts[group.basis] = counts

        allocation = MeasurementPlanner.allocate_shots(groups, total_shots, strategy=shot_allocation, empirical_variances=empirical_variances)
        value = 0.0
        effective_shots: Dict[str, int] = {}
        additional_shots: Dict[str, int] = {}
        for group in groups:
            basis = group.basis
            counts = dict(preflight_counts.get(basis, {}))
            extra_needed = allocation[basis]
            if counts:
                extra_needed = max(allocation[basis] - int(sum(counts.values())), 0)
            if extra_needed > 0:
                extra_counts, meta = exp._sample_counts_from_template(ansatz, params, basis, noise_cfg, extra_needed)
                template_hits += int(meta["template_cache_hit"])
                template_misses += int(not meta["template_cache_hit"])
                counts = exp._merge_counts(counts, extra_counts)
            processed = exp._processed_distribution(counts, noise_cfg, enable_readout_mitigation)
            group_value, variance = MeasurementPlanner.group_value_and_variance(processed, group)
            value += group_value
            group_values[basis] = group_value
            variances[basis] = variance
            stddevs[basis] = float(np.sqrt(max(variance, 0.0)))
            effective_shots[basis] = int(sum(counts.values()))
            additional_shots[basis] = int(extra_needed)
        p01, p10 = exp._readout_pair(noise_cfg)
        group_standard_errors = {
            basis: float(np.sqrt(max(variances[basis], 0.0) / max(effective_shots.get(basis, 1), 1)))
            for basis in variances
        }
        total_variance_of_mean = float(sum(max(variances[basis], 0.0) / max(effective_shots.get(basis, 1), 1) for basis in variances))
        metadata = {
            "mode": "shot_grouped_aer_cached_templates",
            "groups": MeasurementPlanner.describe_groups(groups),
            "allocation": allocation,
            "effective_shots": effective_shots,
            "additional_shots": additional_shots,
            "group_values": group_values,
            "group_variances": variances,
            "group_stddevs": stddevs,
            "group_standard_errors": group_standard_errors,
            "total_variance_of_mean": total_variance_of_mean,
            "total_standard_error": float(np.sqrt(max(total_variance_of_mean, 0.0))),
            "preflight_variances": empirical_variances,
            "preflight_stddevs": empirical_stddevs,
            "preflight_shots": int(sum(preflight_alloc.values())) if shot_allocation == "variance_weighted" else 0,
            "template_cache_hits": template_hits,
            "template_cache_misses": template_misses,
            "template_cache_size": len(exp._measurement_template_cache),
            "transpile_cache_enabled": True,
            "readout_mitigation_enabled": bool(enable_readout_mitigation and (p01 > 0.0 or p10 > 0.0)),
            "readout_error_01": p01,
            "readout_error_10": p10,
        }
        return float(value), metadata

    def estimate_cost(
        self,
        ansatz: QuantumCircuit,
        params: np.ndarray,
        noise_cfg: Optional[NoiseDeck | NoiseBodyConfig],
        symmetry_penalty_lambda: float,
        shots: Optional[int],
        shot_allocation: str,
        preflight_shots: int,
        enable_readout_mitigation: bool,
        enable_zne: bool,
        zne_factors: List[int],
        zne_extrapolator: str,
    ) -> tuple[float, Dict[str, object]]:
        exp = self.experiment
        operator = exp._cost_operator(symmetry_penalty_lambda)
        groups = exp._measurement_groups_for(operator)
        if noise_cfg is None:
            circuit = exp._bind(ansatz, params.tolist())
            state = Statevector.from_instruction(circuit)
            value = expectation(state, operator)
            return float(value), {
                "mode": "exact_statevector",
                "groups": MeasurementPlanner.describe_groups(groups),
                "allocation": {},
                "zne_enabled": False,
                "transpile_cache_enabled": False,
                "unmitigated_cost_value": float(value),
                "unmitigated_cost_standard_error": None,
                "total_standard_error": None,
            }
        factors = zne_factors if enable_zne else [1]
        sampled_values: List[float] = []
        sampled_metadata: List[Dict[str, object]] = []
        for factor in factors:
            scaled_cfg = noise_cfg.scaled(factor)
            estimate, metadata = self.estimate_operator_with_shots(
                ansatz=ansatz,
                params=params,
                operator=operator,
                noise_cfg=scaled_cfg,
                total_shots=max(int(shots or 0), 1),
                shot_allocation=shot_allocation,
                preflight_shots=preflight_shots,
                enable_readout_mitigation=enable_readout_mitigation,
            )
            sampled_values.append(estimate)
            sampled_metadata.append(metadata)
        value = exp._zne_extrapolate(factors, sampled_values, method=zne_extrapolator) if enable_zne else sampled_values[0]
        base_meta = sampled_metadata[0] if sampled_metadata else {}
        return float(value), {
            **base_meta,
            "zne_enabled": bool(enable_zne),
            "zne_extrapolator": zne_extrapolator,
            "zne_noise_factors": list(factors),
            "zne_samples": sampled_values,
            "unmitigated_cost_value": float(sampled_values[0]) if sampled_values else None,
            "unmitigated_cost_standard_error": sampled_metadata[0].get("total_standard_error") if sampled_metadata else None,
            "cost_value": float(value),
        }

    def sample_x_parity(self, circuit: QuantumCircuit, noise_cfg: Optional[NoiseDeck | NoiseBodyConfig], shots: int, enable_readout_mitigation: bool) -> Dict[str, float]:
        exp = self.experiment
        counts = exp._sample_counts(circuit, "X" * exp.n_qubits, noise_cfg, shots)
        filtered = SymmetryGate.filter_by_x_parity(counts, sector=exp.target_x_parity_sector)
        raw = int(sum(counts.values()))
        verified = int(sum(filtered.values()))
        raw_distribution = MeasurementPlanner._clean_distribution(counts)
        mitigated_distribution = exp._processed_distribution(counts, noise_cfg, enable_readout_mitigation)
        raw_par = parity_expectation(raw_distribution)
        filt_par = parity_expectation(filtered)
        p01, p10 = exp._readout_pair(noise_cfg)
        mitigation_applied = bool(enable_readout_mitigation and (p01 > 0.0 or p10 > 0.0))
        mitigated_even_prob = MeasurementPlanner.even_parity_probability(mitigated_distribution)
        mitigated_target_prob = mitigated_even_prob if exp.target_x_parity_sector >= 0 else 1.0 - mitigated_even_prob
        raw_even_prob = MeasurementPlanner.even_parity_probability(raw_distribution)
        raw_target_prob = raw_even_prob if exp.target_x_parity_sector >= 0 else 1.0 - raw_even_prob
        mitigated_parity = parity_expectation(mitigated_distribution)
        raw_target_stderr = float(np.sqrt(max(raw_target_prob * (1.0 - raw_target_prob), 0.0) / max(raw, 1)))
        mitigated_target_stderr = float(np.sqrt(max(mitigated_target_prob * (1.0 - mitigated_target_prob), 0.0) / max(raw, 1)))
        return {
            "raw_shots": raw,
            "verified_shots": verified,
            "verification_rate": verified / max(raw, 1),
            "verification_standard_error": raw_target_stderr,
            "target_sector": int(exp.target_x_parity_sector),
            "raw_target_sector_probability": raw_target_prob,
            "raw_parity_expectation": raw_par,
            "filtered_parity_expectation": filt_par,
            "parity_shift": abs(filt_par - raw_par),
            "mitigated_parity_expectation": mitigated_parity,
            "mitigated_even_sector_probability": mitigated_even_prob,
            "mitigated_target_sector_probability": mitigated_target_prob,
            "mitigated_verification_rate": mitigated_target_prob,
            "mitigated_verification_standard_error": mitigated_target_stderr,
            "readout_mitigation_applied": mitigation_applied,
            "readout_mitigation_method": "independent-bitstring matrix inversion" if mitigation_applied else "none",
            "readout_error_01": p01,
            "readout_error_10": p10,
            "limitation": "Mitigated parity diagnostics assume an independent per-qubit readout channel and clip negative quasi-probabilities.",
        }


class OptimizationExecutor:
    def __init__(self, experiment):
        self.experiment = experiment

    def _parameter_shift_gradient(self, objective, theta: np.ndarray) -> np.ndarray:
        exp = self.experiment
        shift = np.pi / 2.0
        gradient = np.zeros_like(theta, dtype=float)
        for index in range(len(theta)):
            plus = np.asarray(theta, dtype=float).copy()
            minus = np.asarray(theta, dtype=float).copy()
            plus[index] += shift
            minus[index] -= shift
            gradient[index] = 0.5 * (objective(exp._wrap_angles(plus)) - objective(exp._wrap_angles(minus)))
        return gradient

    def _optimize_internal_spsa(self, objective, initial: np.ndarray, max_iter: int, spsa_config: SPSAConfig, trace: ObjectiveTrace) -> tuple[np.ndarray, Dict[str, object]]:
        exp = self.experiment
        theta = np.asarray(initial, dtype=float)
        stability = max_iter * float(spsa_config.stability_constant_ratio)
        for iteration in range(max_iter):
            ck = float(spsa_config.perturbation) / ((iteration + 1.0) ** float(spsa_config.gamma))
            ak = float(spsa_config.learning_rate) / ((iteration + 1.0 + stability) ** float(spsa_config.alpha))
            delta = exp.rng.choice([-1.0, 1.0], size=theta.shape)
            plus = exp._wrap_angles(theta + ck * delta)
            minus = exp._wrap_angles(theta - ck * delta)
            y_plus = objective(plus)
            y_minus = objective(minus)
            gradient = (y_plus - y_minus) / (2.0 * ck * delta)
            theta = exp._wrap_angles(theta - ak * gradient)
        summary = trace.summary(
            optimizer="SPSA",
            success=True,
            message="Completed internal SPSA fallback loop.",
            requested_max_iter=max_iter,
            effective_max_iter=max_iter,
            nfev=len(trace.history),
        )
        return theta, summary

    def optimize(
        self,
        ansatz: QuantumCircuit,
        optimizer_name: str,
        max_iter: int,
        noise_cfg: Optional[NoiseDeck | NoiseBodyConfig],
        symmetry_penalty_lambda: float,
        shot_allocation: str,
        base_shots: int,
        final_shots: int,
        preflight_shots: int,
        enable_dynamic_shots: bool,
        enable_readout_mitigation: bool,
        enable_zne: bool,
        zne_factors: List[int],
        zne_extrapolator: str,
        spsa_config: SPSAConfig,
    ) -> tuple[np.ndarray, List[float], Dict[str, object]]:
        exp = self.experiment
        trace = ObjectiveTrace()

        def objective(params: np.ndarray) -> float:
            shots = exp._shots_for_call(trace.evaluation_count + 1, max_iter, base_shots, final_shots, enable_dynamic_shots) if noise_cfg is not None else None
            value, metadata = exp._estimate_cost(
                ansatz=ansatz,
                params=np.asarray(params, dtype=float),
                noise_cfg=noise_cfg,
                symmetry_penalty_lambda=symmetry_penalty_lambda,
                shots=shots,
                shot_allocation=shot_allocation,
                preflight_shots=preflight_shots,
                enable_readout_mitigation=enable_readout_mitigation,
                enable_zne=enable_zne,
                zne_factors=zne_factors,
                zne_extrapolator=zne_extrapolator,
            )
            trace.record(float(value), metadata, shots)
            LOGGER.debug("Objective eval %s | optimizer=%s | value=%.6f | shots=%s", trace.evaluation_count, optimizer_name, float(value), shots)
            return float(value)

        initial = exp.rng.uniform(-np.pi, np.pi, size=ansatz.num_parameters)
        method = optimizer_name.upper()
        LOGGER.info("Starting optimization | optimizer=%s | max_iter=%s | params=%s | noisy=%s", method, max_iter, ansatz.num_parameters, noise_cfg is not None)
        if method in {"COBYLA", "SLSQP"}:
            effective_budget = max_iter if method != "COBYLA" else max(max_iter, ansatz.num_parameters + 2)
            result = minimize(objective, initial, method=method, options={"maxiter": effective_budget})
            params = np.asarray(result.x, dtype=float)
            summary = trace.summary(
                optimizer=method,
                success=bool(result.success),
                message=str(result.message),
                requested_max_iter=max_iter,
                effective_max_iter=effective_budget,
                nfev=max(int(getattr(result, "nfev", 0)), len(trace.history)),
            )
            return params, trace.history, summary
        if method == "BFGS":
            if noise_cfg is not None:
                raise ValueError("BFGS is restricted to noiseless/statevector execution; use SPSA or SLSQP for noisy runs.")
            result = minimize(
                objective,
                initial,
                method="BFGS",
                jac=lambda params: self._parameter_shift_gradient(objective, np.asarray(params, dtype=float)),
                options={"maxiter": max_iter},
            )
            params = np.asarray(result.x, dtype=float)
            summary = trace.summary(
                optimizer=method,
                success=bool(result.success),
                message=str(result.message),
                requested_max_iter=max_iter,
                effective_max_iter=max_iter,
                nfev=max(int(getattr(result, "nfev", 0)), len(trace.history)),
            )
            return params, trace.history, summary
        if method == "SPSA":
            try:
                from qiskit_algorithms.optimizers import SPSA as QiskitSPSA
                from qiskit_algorithms.utils import algorithm_globals

                algorithm_globals.random_seed = exp.seed
                optimizer = QiskitSPSA(
                    maxiter=max_iter,
                    learning_rate=float(spsa_config.learning_rate),
                    perturbation=float(spsa_config.perturbation),
                    blocking=False,
                    last_avg=1,
                    resamplings=1,
                )
                result = optimizer.minimize(objective, x0=initial)
                params = np.asarray(result.x, dtype=float)
                summary = trace.summary(
                    optimizer=method,
                    success=True,
                    message="Completed qiskit_algorithms SPSA loop.",
                    requested_max_iter=max_iter,
                    effective_max_iter=max_iter,
                    nfev=max(int(getattr(result, "nfev", 0)), len(trace.history)),
                )
                return params, trace.history, summary
            except Exception as exc:  # pragma: no cover - fallback path
                LOGGER.warning("Falling back to internal SPSA implementation: %s", exc)
                theta, summary = self._optimize_internal_spsa(objective, initial, max_iter, spsa_config, trace)
                return theta, trace.history, summary
        raise ValueError(f"Unsupported optimizer: {optimizer_name}")
