from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional, Tuple

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.converters import circuit_to_dag
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit_aer import AerSimulator
from scipy.linalg import eigh
from scipy.optimize import curve_fit
from scipy.sparse.linalg import eigsh

from .config import NoiseBodyConfig, NoiseDeck, SPSAConfig
from .constants import (
    BUDGET_FALLBACK,
    DEFAULT_PHYSICS_OBSERVABLE_WEIGHT,
    DEFAULT_PHYSICS_SYMMETRY_WEIGHT,
    DEFAULT_RUNTIME_OPTIMIZATION_LEVEL,
    EXACT_DIAGONALIZATION_MAX_QUBITS,
    NUMERIC_EPS,
    ZNE_CURVE_FIT_MAX_EVALS,
    ZNE_EXPONENTIAL_INITIAL_RATE,
)
from .executors import MeasurementExecutor, OptimizationExecutor, StateExecutor
from .logging_utils import get_logger
from .metrics import parity_expectation
from .noise import NoiseFactory, TWO_QUBIT_NOISE_GATES
from .observables import MeasurementGroup, MeasurementPlanner, ObservableFactory, StateAnalyzer
from .plotting import PlotBook
from .record_builder import RecordBuilder
from .results import TrialRecord
from .runtime import RuntimeFactory
from .interfaces import ExperimentService

LOGGER = get_logger(__name__)

__all__ = ["FieldLineExperiment"]


class FieldLineExperiment(ExperimentService):
    DEFAULT_PHYSICS_SYMMETRY_WEIGHT = DEFAULT_PHYSICS_SYMMETRY_WEIGHT
    DEFAULT_PHYSICS_OBSERVABLE_WEIGHT = DEFAULT_PHYSICS_OBSERVABLE_WEIGHT
    DEFAULT_PHYSICAL_VALIDITY_TOL = 0.05

    def __init__(self, hamiltonian: SparsePauliOp, n_qubits: int, field_strength: float, coupling: float, seed: int = 42):
        self.hamiltonian = hamiltonian
        self.n_qubits = n_qubits
        self.field_strength = field_strength
        self.coupling = coupling
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.symmetry_operator = ObservableFactory.global_x_parity(n_qubits)
        self.exact_energy, self.exact_state, self.exact_first_excited_energy, self.exact_spectral_gap = self._solve_exactly()
        self.observable_bundle = ObservableFactory.default_bundle(n_qubits)
        self.exact_summary = StateAnalyzer.summarize(self.exact_state, n_qubits, hamiltonian, self.exact_state, self.observable_bundle) if self.exact_state is not None else None
        exact_parity = None if self.exact_summary is None else self.exact_summary.get("x_parity")
        self.target_x_parity_sector = 1 if exact_parity is None or float(exact_parity) >= 0.0 else -1
        self.results: Dict[str, TrialRecord] = {}
        self._noise_model_cache: Dict[tuple, object] = {}
        self._backend_cache: Dict[tuple, AerSimulator] = {}
        self._group_cache: Dict[tuple, List[MeasurementGroup]] = {}
        self._measurement_template_cache: Dict[tuple, dict] = {}
        self._cache_lock = RLock()
        self._cache_stats: Dict[str, int] = {
            "measurement_template_hits": 0,
            "measurement_template_misses": 0,
            "noise_model_hits": 0,
            "noise_model_misses": 0,
            "backend_hits": 0,
            "backend_misses": 0,
        }
        self.state_executor = StateExecutor(self)
        self.measurement_executor = MeasurementExecutor(self)
        self.optimization_executor = OptimizationExecutor(self)

    def _solve_exactly(self) -> Tuple[float, Statevector | None, float | None, float | None]:
        if self.n_qubits <= EXACT_DIAGONALIZATION_MAX_QUBITS:
            matrix = self.hamiltonian.to_matrix()
            vals, vecs = eigh(matrix)
            idx = int(np.argmin(vals))
            ground = float(np.real(vals[idx]))
            excited = float(np.real(vals[min(idx + 1, len(vals) - 1)])) if len(vals) > 1 else None
            gap = None if excited is None else float(max(excited - ground, 0.0))
            return ground, Statevector(vecs[:, idx]), excited, gap
        sparse_matrix = self.hamiltonian.to_matrix(sparse=True).tocsr()
        vals, _ = eigsh(sparse_matrix, k=2, which="SA")
        vals = np.sort(np.real(vals))
        ground = float(vals[0])
        excited = float(vals[1]) if len(vals) > 1 else None
        gap = None if excited is None else float(max(excited - ground, 0.0))
        return ground, None, excited, gap

    @staticmethod
    def _ordered_param_map(ansatz: QuantumCircuit, values: List[float]) -> Dict[object, float]:
        ordered = sorted(ansatz.parameters, key=lambda p: p.name)
        return dict(zip(ordered, values))

    def _bind(self, ansatz: QuantumCircuit, params: List[float]) -> QuantumCircuit:
        return ansatz.assign_parameters(self._ordered_param_map(ansatz, params))

    @staticmethod
    def _noise_signature(noise_cfg: Optional[NoiseDeck | NoiseBodyConfig]) -> tuple:
        if noise_cfg is None:
            return ("ideal",)
        if isinstance(noise_cfg, NoiseBodyConfig):
            p01, p10 = noise_cfg.readout_pair()
            return (
                "noise_body",
                noise_cfg.body,
                round(float(noise_cfg.strength), 12),
                round(float(noise_cfg.correlation), 12),
                round(float(noise_cfg.effective_coherence_angle()), 12),
                round(float(noise_cfg.temporal_drift), 12),
                round(float(p01), 12),
                round(float(p10), 12),
            )
        p01, p10 = noise_cfg.readout_pair()
        return (
            "noisy",
            round(float(noise_cfg.gate_error), 12),
            round(float(noise_cfg.effective_two_qubit_gate_error()), 12),
            round(float(noise_cfg.t1), 12),
            round(float(noise_cfg.t2), 12),
            round(float(noise_cfg.gate_time), 12),
            round(float(p01), 12),
            round(float(p10), 12),
        )

    @staticmethod
    def _ansatz_signature(ansatz: QuantumCircuit) -> tuple:
        return (
            ansatz.name,
            ansatz.num_qubits,
            ansatz.num_parameters,
            tuple(parameter.name for parameter in sorted(ansatz.parameters, key=lambda p: p.name)),
            tuple(sorted((name, int(count)) for name, count in ansatz.count_ops().items())),
        )

    @staticmethod
    def _operator_signature(operator: SparsePauliOp) -> tuple:
        return tuple((label, round(float(np.real(coeff)), 12)) for label, coeff in zip(operator.paulis.to_labels(), operator.coeffs))

    def _get_noise_model(self, noise_cfg: Optional[NoiseDeck | NoiseBodyConfig]):
        signature = self._noise_signature(noise_cfg)
        with self._cache_lock:
            if signature in self._noise_model_cache:
                self._cache_stats["noise_model_hits"] += 1
                return self._noise_model_cache[signature]
            self._cache_stats["noise_model_misses"] += 1
            model = None if noise_cfg is None else NoiseFactory.build(noise_cfg)
            self._noise_model_cache[signature] = model
            return model

    def _get_backend(self, noise_cfg: Optional[NoiseDeck | NoiseBodyConfig], method: Optional[str] = None) -> AerSimulator:
        signature = (self._noise_signature(noise_cfg), method or "default")
        with self._cache_lock:
            if signature in self._backend_cache:
                self._cache_stats["backend_hits"] += 1
                return self._backend_cache[signature]
        model = self._get_noise_model(noise_cfg)
        backend = AerSimulator(noise_model=model, seed_simulator=self.seed) if method is None else AerSimulator(method=method, noise_model=model, seed_simulator=self.seed)
        with self._cache_lock:
            self._cache_stats["backend_misses"] += 1
            self._backend_cache[signature] = backend
        return backend

    def _measurement_groups_for(self, operator: SparsePauliOp) -> List[MeasurementGroup]:
        signature = self._operator_signature(operator)
        with self._cache_lock:
            if signature not in self._group_cache:
                self._group_cache[signature] = MeasurementPlanner.group_qwc(MeasurementPlanner.pauli_terms(operator, prefix="cost"))
            return self._group_cache[signature]

    @staticmethod
    def _readout_pair(noise_cfg: Optional[NoiseDeck]) -> tuple[float, float]:
        return (0.0, 0.0) if noise_cfg is None else noise_cfg.readout_pair()

    def _processed_distribution(self, counts: Dict[str, int] | Dict[str, float], noise_cfg: Optional[NoiseDeck], enable_readout_mitigation: bool) -> Dict[str, float]:
        distribution = {bitstring.replace(" ", ""): float(value) for bitstring, value in counts.items()}
        if not enable_readout_mitigation:
            return MeasurementPlanner._clean_distribution(distribution)
        p01, p10 = self._readout_pair(noise_cfg)
        if p01 <= 0.0 and p10 <= 0.0:
            return MeasurementPlanner._clean_distribution(distribution)
        return MeasurementPlanner.mitigate_readout_distribution(distribution, self.n_qubits, p01, p10)

    @staticmethod
    def _merge_counts(left: Dict[str, int], right: Dict[str, int]) -> Dict[str, int]:
        merged = dict(left)
        for key, value in right.items():
            merged[key] = merged.get(key, 0) + int(value)
        return merged

    def _measurement_template_key(self, ansatz: QuantumCircuit, basis: str, noise_cfg: Optional[NoiseDeck | NoiseBodyConfig]) -> tuple:
        return (self._ansatz_signature(ansatz), basis, self._noise_signature(noise_cfg))

    def _get_measurement_template(self, ansatz: QuantumCircuit, basis: str, noise_cfg: Optional[NoiseDeck | NoiseBodyConfig]) -> tuple[dict, bool]:
        key = self._measurement_template_key(ansatz, basis, noise_cfg)
        with self._cache_lock:
            if key in self._measurement_template_cache:
                self._cache_stats["measurement_template_hits"] += 1
                return self._measurement_template_cache[key], True
        backend = self._get_backend(noise_cfg)
        measured = MeasurementPlanner.measurement_circuit(ansatz, basis)
        transpiled_template = transpile(measured, backend, seed_transpiler=self.seed)
        entry = {"backend": backend, "template": transpiled_template, "template_depth": transpiled_template.depth()}
        with self._cache_lock:
            self._cache_stats["measurement_template_misses"] += 1
            self._measurement_template_cache[key] = entry
        return entry, False

    def _sample_counts_from_template(self, ansatz: QuantumCircuit, params: np.ndarray, basis: str, noise_cfg: Optional[NoiseDeck | NoiseBodyConfig], shots: int) -> tuple[Dict[str, int], Dict[str, object]]:
        entry, cache_hit = self._get_measurement_template(ansatz, basis, noise_cfg)
        parameter_map = {parameter: float(value) for parameter, value in zip(sorted(entry["template"].parameters, key=lambda p: p.name), params.tolist())}
        executable = entry["template"].assign_parameters(parameter_map, inplace=False) if parameter_map else entry["template"]
        counts = entry["backend"].run(executable, shots=shots).result().get_counts()
        return counts, {
            "template_cache_hit": cache_hit,
            "template_basis": basis,
            "template_depth": entry["template_depth"],
            "shots_executed": int(sum(counts.values())),
        }

    def _sample_counts(self, circuit: QuantumCircuit, basis: str, noise_cfg: Optional[NoiseDeck | NoiseBodyConfig], shots: int) -> Dict[str, int]:
        measured = MeasurementPlanner.measurement_circuit(circuit, basis)
        backend = self._get_backend(noise_cfg)
        compiled = transpile(measured, backend, seed_transpiler=self.seed)
        return backend.run(compiled, shots=shots).result().get_counts()

    def _simulate_state(self, circuit: QuantumCircuit, noise_cfg: Optional[NoiseDeck | NoiseBodyConfig]):
        return self.state_executor.simulate_state(circuit, noise_cfg)

    def _estimate_observables(self, state):
        return self.state_executor.estimate_observables(state)

    def _estimate_operator_with_shots(self, *args, **kwargs):
        return self.measurement_executor.estimate_operator_with_shots(*args, **kwargs)

    @staticmethod
    def _two_qubit_gate_count(circuit: QuantumCircuit) -> int:
        return int(sum(int(count) for name, count in circuit.count_ops().items() if name in set(TWO_QUBIT_NOISE_GATES)))

    @staticmethod
    def _entangling_layer_count(circuit: QuantumCircuit) -> int:
        dag = circuit_to_dag(circuit)
        return int(sum(1 for layer in dag.layers() if any(len(node.qargs) >= 2 for node in layer["graph"].op_nodes())))

    def _circuit_hardware_metrics(self, ansatz: QuantumCircuit, noise_cfg: Optional[NoiseDeck | NoiseBodyConfig]) -> Dict[str, int]:
        backend = self._get_backend(noise_cfg)
        transpiled_ansatz = transpile(ansatz, backend, seed_transpiler=self.seed)
        observables = {"energy": self.hamiltonian, "x_parity": self.symmetry_operator}
        _, _, layout_metadata = RuntimeFactory.transpile_to_isa(ansatz, observables, backend, optimization_level=DEFAULT_RUNTIME_OPTIMIZATION_LEVEL, seed_transpiler=self.seed)
        return {
            "original_two_qubit_gate_count": self._two_qubit_gate_count(ansatz),
            "transpiled_depth": int(transpiled_ansatz.depth() or 0),
            "transpiled_two_qubit_gate_count": self._two_qubit_gate_count(transpiled_ansatz),
            "transpiled_entangling_layer_count": self._entangling_layer_count(transpiled_ansatz),
            "runtime_layout_final_index": layout_metadata.get("final_index_layout"),
            "runtime_layout_initial_index": layout_metadata.get("initial_layout"),
            "runtime_layout_final_present": layout_metadata.get("final_layout_present"),
            "runtime_layout_resolved_type": layout_metadata.get("resolved_layout_type"),
        }

    def _cost_operator(self, symmetry_penalty_lambda: float) -> SparsePauliOp:
        return self.hamiltonian if symmetry_penalty_lambda <= 0 else self.hamiltonian - symmetry_penalty_lambda * self.symmetry_operator

    @staticmethod
    def _zne_extrapolate(noise_factors: List[int], values: List[float], method: str = "linear") -> float:
        if len(noise_factors) == 1:
            return float(values[0])
        x = np.asarray(noise_factors, dtype=float)
        y = np.asarray(values, dtype=float)
        method = method.lower()
        if method == "quadratic":
            degree = min(len(noise_factors) - 1, 2)
            coefficients = np.polyfit(x, y, deg=degree)
            return float(np.polyval(coefficients, 0.0))
        if method == "exponential":
            def model(xdata, offset, amplitude, rate):
                return offset + amplitude * np.exp(-rate * xdata)

            try:
                offset0 = float(y[-1])
                amplitude0 = float(y[0] - offset0)
                rate0 = ZNE_EXPONENTIAL_INITIAL_RATE
                params, _ = curve_fit(model, x, y, p0=(offset0, amplitude0, rate0), maxfev=ZNE_CURVE_FIT_MAX_EVALS)
                return float(model(np.asarray([0.0]), *params)[0])
            except Exception:
                LOGGER.warning("Exponential ZNE fit failed; falling back to linear extrapolation.")
        coefficients = np.polyfit(x, y, deg=1)
        return float(np.polyval(coefficients, 0.0))

    def _estimate_cost(self, *args, **kwargs):
        return self.measurement_executor.estimate_cost(*args, **kwargs)

    def _sample_x_parity(self, circuit: QuantumCircuit, noise_cfg: Optional[NoiseDeck], shots: int, enable_readout_mitigation: bool) -> Dict[str, float]:
        return self.measurement_executor.sample_x_parity(circuit, noise_cfg, shots, enable_readout_mitigation)

    def _symmetry_projection_summary(self, state):
        return self.state_executor.symmetry_projection_summary(state)

    @staticmethod
    def _wrap_angles(params: np.ndarray) -> np.ndarray:
        return ((params + np.pi) % (2 * np.pi)) - np.pi

    def _shots_for_call(self, call_index: int, max_iter: int, base_shots: int, final_shots: int, dynamic: bool) -> int:
        if not dynamic or max_iter <= 1:
            return final_shots
        progress = min(max(call_index - 1, 0), max_iter - 1) / max(max_iter - 1, 1)
        return int(round(base_shots + progress * (final_shots - base_shots)))

    def _optimize(self, *, ansatz: QuantumCircuit, optimizer_name: str, max_iter: int, noise_cfg: Optional[NoiseDeck], symmetry_penalty_lambda: float, shot_allocation: str, base_shots: int, final_shots: int, preflight_shots: int, enable_dynamic_shots: bool, enable_readout_mitigation: bool, enable_zne: bool, zne_factors: List[int], zne_extrapolator: str = "linear", spsa_config: Optional[SPSAConfig] = None) -> tuple[np.ndarray, List[float], Dict[str, object]]:
        return self.optimization_executor.optimize(
            ansatz=ansatz,
            optimizer_name=optimizer_name,
            max_iter=max_iter,
            noise_cfg=noise_cfg,
            symmetry_penalty_lambda=symmetry_penalty_lambda,
            shot_allocation=shot_allocation,
            base_shots=base_shots,
            final_shots=final_shots,
            preflight_shots=preflight_shots,
            enable_dynamic_shots=enable_dynamic_shots,
            enable_readout_mitigation=enable_readout_mitigation,
            enable_zne=enable_zne,
            zne_factors=zne_factors,
            zne_extrapolator=zne_extrapolator,
            spsa_config=spsa_config or SPSAConfig(),
        )

    def _assemble_measurement_plan(self, *, hardware_metrics: Dict[str, object], optimizer_summary: Dict[str, object], last_metadata: Dict[str, object], shot_allocation: str, base_shots: int, final_shots: int, preflight_shots: int, enable_dynamic_shots: bool, enable_zne: bool, noise_cfg: Optional[NoiseDeck], zne_factors: List[int], zne_extrapolator: str, mitigation_gain: float | None, final_cost_evaluation_shots: int | None = None) -> Dict[str, object]:
        zne_samples = [float(v) for v in last_metadata.get("zne_samples", [])]
        return {
            "shot_allocation_strategy": shot_allocation,
            "dynamic_shots_enabled": enable_dynamic_shots,
            "base_shots": base_shots if noise_cfg is not None else None,
            "final_shots": final_shots if noise_cfg is not None else None,
            "preflight_shots": preflight_shots if noise_cfg is not None else None,
            "zne_enabled": bool(enable_zne and noise_cfg is not None),
            "zne_noise_factors": zne_factors if noise_cfg is not None else [1],
            "zne_samples": zne_samples,
            "measurement_plan": {
                "zne_extrapolator": zne_extrapolator,
                "effective_two_qubit_gate_error": None if noise_cfg is None else noise_cfg.effective_two_qubit_gate_error(),
                "runtime_layout_final_index": hardware_metrics.get("runtime_layout_final_index"),
                "runtime_layout_initial_index": hardware_metrics.get("runtime_layout_initial_index"),
                "runtime_layout_final_present": hardware_metrics.get("runtime_layout_final_present"),
                "runtime_layout_resolved_type": hardware_metrics.get("runtime_layout_resolved_type"),
                "shot_allocation": shot_allocation,
                "groups": last_metadata.get("groups", []),
                "allocation": last_metadata.get("allocation", {}),
                "effective_shots": last_metadata.get("effective_shots", {}),
                "additional_shots": last_metadata.get("additional_shots", {}),
                "group_variances": last_metadata.get("group_variances", {}),
                "group_standard_errors": last_metadata.get("group_standard_errors", {}),
                "total_standard_error": last_metadata.get("total_standard_error"),
                "preflight_variances": last_metadata.get("preflight_variances", {}),
                "shots_used_in_last_eval": last_metadata.get("shots_used"),
                "template_cache_hits": last_metadata.get("template_cache_hits", 0),
                "template_cache_misses": last_metadata.get("template_cache_misses", 0),
                "template_cache_size": last_metadata.get("template_cache_size", len(self._measurement_template_cache)),
                "transpile_cache_enabled": bool(last_metadata.get("transpile_cache_enabled", False)),
                "readout_mitigation_enabled": bool(last_metadata.get("readout_mitigation_enabled", False)),
                "readout_error_01": last_metadata.get("readout_error_01"),
                "readout_error_10": last_metadata.get("readout_error_10"),
                "experiment_cache_totals": dict(self._cache_stats),
                "optimizer_budget": {
                    "requested_max_iter": optimizer_summary.get("requested_max_iter"),
                    "effective_max_iter": optimizer_summary.get("effective_max_iter"),
                    "nfev": optimizer_summary.get("nfev"),
                    "shot_schedule": optimizer_summary.get("shot_schedule", []),
                    "total_shot_history": optimizer_summary.get("total_shot_history", []),
                    "total_shots_used": optimizer_summary.get("total_shots_used"),
                    "avg_shots_per_eval": optimizer_summary.get("avg_shots_per_eval"),
                },
                "zne_samples": zne_samples,
                "zne_mitigation_gain": mitigation_gain,
                "final_cost_evaluation_shots": final_cost_evaluation_shots,
            },
        }

    def _final_cost_evaluation(self, *, ansatz: QuantumCircuit, optimal: np.ndarray, noise_cfg: Optional[NoiseDeck | NoiseBodyConfig], symmetry_penalty_lambda: float, shot_allocation: str, final_shots: int, preflight_shots: int, enable_readout_mitigation: bool, enable_zne: bool, zne_factors: List[int], zne_extrapolator: str) -> tuple[float, Dict[str, object], int | None]:
        shots = final_shots if noise_cfg is not None else None
        value, metadata = self._estimate_cost(
            ansatz=ansatz,
            params=np.asarray(optimal, dtype=float),
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
        return float(value), metadata, shots

    def run_vqe(self, ansatz: QuantumCircuit, optimizer_name: str, max_iter: int, label: str, ansatz_name: str, depth: int, noise_cfg: Optional[NoiseDeck | NoiseBodyConfig] = None, verification_shots: int = 4096, symmetry_penalty_lambda: float = 0.0, shot_allocation: str = "equal", base_shots: int = 512, final_shots: int = 4096, preflight_shots: int = 256, enable_dynamic_shots: bool = False, enable_readout_mitigation: bool = True, enable_zne: bool = False, zne_factors: Optional[List[int]] = None, zne_extrapolator: str = "linear", physical_validity_tol: float = DEFAULT_PHYSICAL_VALIDITY_TOL, spsa_config: Optional[SPSAConfig] = None) -> TrialRecord:
        zne_factors = list(zne_factors or [1, 3, 5])
        LOGGER.info("Running VQE | label=%s | ansatz=%s | optimizer=%s | noisy=%s", label, ansatz_name, optimizer_name.upper(), noise_cfg is not None)
        start = time.time()
        optimal, history, optimizer_summary = self._optimize(
            ansatz=ansatz,
            optimizer_name=optimizer_name,
            max_iter=max_iter,
            noise_cfg=noise_cfg,
            symmetry_penalty_lambda=symmetry_penalty_lambda,
            shot_allocation=shot_allocation,
            base_shots=base_shots,
            final_shots=final_shots,
            preflight_shots=preflight_shots,
            enable_dynamic_shots=enable_dynamic_shots,
            enable_readout_mitigation=enable_readout_mitigation,
            enable_zne=enable_zne,
            zne_factors=zne_factors,
            zne_extrapolator=zne_extrapolator,
            spsa_config=spsa_config,
        )
        elapsed = time.time() - start
        hardware_metrics = self._circuit_hardware_metrics(ansatz, noise_cfg)
        bound = self._bind(ansatz, optimal.tolist())
        state = self._simulate_state(bound, noise_cfg)
        observables = self._estimate_observables(state)
        sampled = self._sample_x_parity(bound, noise_cfg, verification_shots, enable_readout_mitigation)
        symmetry_summary = {**self._symmetry_projection_summary(state), "sampled": sampled}

        energy = float(observables["energy"])
        exact_gap = abs(energy - self.exact_energy)
        relative_gap = exact_gap / max(abs(self.exact_energy), NUMERIC_EPS)
        x_parity = observables.get("x_parity")
        symmetry_breaking_error = None if x_parity is None else float(max(0.0, 0.5 * (1.0 - float(self.target_x_parity_sector) * float(x_parity))))
        physical_valid = None if symmetry_breaking_error is None else bool(symmetry_breaking_error <= physical_validity_tol)
        if physical_valid is None:
            physical_validity_reason = None
        elif physical_valid:
            physical_validity_reason = "passes_target_x_parity_tolerance"
        else:
            physical_validity_reason = f"target_x_parity_sector_mismatch>{physical_validity_tol:.3f}"
        physics_score = None
        if symmetry_summary.get("filtered_exact_gap") is not None:
            physics_score = (
                float(symmetry_summary["filtered_exact_gap"])
                + self.DEFAULT_PHYSICS_SYMMETRY_WEIGHT * float(symmetry_breaking_error or 0.0)
                + self.DEFAULT_PHYSICS_OBSERVABLE_WEIGHT * float(symmetry_summary.get("filtered_observable_error_l2") or 0.0)
            )

        final_cost_value, final_cost_metadata, final_cost_shots = self._final_cost_evaluation(
            ansatz=ansatz,
            optimal=optimal,
            noise_cfg=noise_cfg,
            symmetry_penalty_lambda=symmetry_penalty_lambda,
            shot_allocation=shot_allocation,
            final_shots=final_shots,
            preflight_shots=preflight_shots,
            enable_readout_mitigation=enable_readout_mitigation,
            enable_zne=enable_zne,
            zne_factors=zne_factors,
            zne_extrapolator=zne_extrapolator,
        )
        zne_samples = [float(v) for v in final_cost_metadata.get("zne_samples", [])]
        mitigation_gain = None if final_cost_metadata.get("unmitigated_cost_value") is None else float(final_cost_metadata.get("unmitigated_cost_value")) - float(final_cost_value)
        measurement_bundle = self._assemble_measurement_plan(
            hardware_metrics=hardware_metrics,
            optimizer_summary=optimizer_summary,
            last_metadata=final_cost_metadata,
            shot_allocation=shot_allocation,
            base_shots=base_shots,
            final_shots=final_shots,
            preflight_shots=preflight_shots,
            enable_dynamic_shots=enable_dynamic_shots,
            enable_zne=enable_zne,
            noise_cfg=noise_cfg,
            zne_factors=zne_factors,
            zne_extrapolator=zne_extrapolator,
            mitigation_gain=mitigation_gain,
            final_cost_evaluation_shots=final_cost_shots,
        )

        energy_metrics = {
            "energy": energy,
            "exact_gap": exact_gap,
            "relative_gap": relative_gap,
            "energy_variance": observables.get("energy_variance"),
            "energy_stddev": observables.get("energy_stddev"),
            "relative_energy_stddev": observables.get("relative_energy_stddev"),
            "cost_value": float(final_cost_value),
            "cost_standard_error": final_cost_metadata.get("total_standard_error"),
            "unmitigated_cost_value": final_cost_metadata.get("unmitigated_cost_value"),
            "unmitigated_cost_standard_error": final_cost_metadata.get("unmitigated_cost_standard_error"),
            "mitigation_gain": mitigation_gain,
            "symmetry_penalty_lambda": float(symmetry_penalty_lambda),
            "filtered_energy": float(symmetry_summary["filtered"]["energy"]) if symmetry_summary["filtered"].get("energy") is not None else None,
            "filtered_exact_gap": symmetry_summary.get("filtered_exact_gap"),
            "exact_first_excited_energy": self.exact_first_excited_energy,
            "exact_spectral_gap": self.exact_spectral_gap,
        }
        physics_metrics = {
            "observable_error_l2": symmetry_summary.get("raw_observable_error_l2"),
            "filtered_observable_error_l2": symmetry_summary.get("filtered_observable_error_l2"),
            "symmetry_postselection_rate": symmetry_summary.get("postselection_rate"),
            "sampled_postselection_rate": sampled.get("verification_rate"),
            "sampled_postselection_standard_error": sampled.get("verification_standard_error"),
            "mitigated_sampled_postselection_rate": sampled.get("mitigated_verification_rate"),
            "mitigated_sampled_postselection_standard_error": sampled.get("mitigated_verification_standard_error"),
            "x_parity": x_parity,
            "mitigated_x_parity": sampled.get("mitigated_parity_expectation"),
            "target_x_parity_sector": int(self.target_x_parity_sector),
            "target_sector_probability": observables.get("x_even_sector_probability") if self.target_x_parity_sector >= 0 else observables.get("x_odd_sector_probability"),
            "symmetry_breaking_error": symmetry_breaking_error,
            "physics_score": physics_score,
            "physical_valid": physical_valid,
            "physical_validity_tol": float(physical_validity_tol),
            "physical_validity_reason": physical_validity_reason,
        }
        execution_metrics = {
            "energy_history": history,
            "iterations": len(history),
            "circuit_depth": ansatz.depth(),
            "execution_time": elapsed,
            "optimal_params": optimal.tolist(),
            "objective_calls": optimizer_summary.get("nfev"),
            "shot_schedule": list(optimizer_summary.get("shot_schedule", [])),
            "estimated_total_shots_used": optimizer_summary.get("total_shots_used") if noise_cfg is not None else None,
            "avg_shots_per_eval": optimizer_summary.get("avg_shots_per_eval") if noise_cfg is not None else None,
            "original_two_qubit_gate_count": hardware_metrics["original_two_qubit_gate_count"],
            "transpiled_depth": hardware_metrics["transpiled_depth"],
            "transpiled_two_qubit_gate_count": hardware_metrics["transpiled_two_qubit_gate_count"],
            "transpiled_entangling_layer_count": hardware_metrics["transpiled_entangling_layer_count"],
        }
        identity = {
            "ansatz": ansatz_name,
            "optimizer": optimizer_name.upper(),
            "depth": depth,
            "seed": self.seed,
            "noise_level": 0.0 if noise_cfg is None else float(noise_cfg.gate_error),
        }

        record = RecordBuilder.build_trial_record(
            label=label,
            identity=identity,
            energy_metrics=energy_metrics,
            physics_metrics=physics_metrics,
            execution_metrics=execution_metrics,
            measurement_plan=measurement_bundle,
            observables=observables,
            symmetry_summary=symmetry_summary,
            optimizer_summary=optimizer_summary,
        )
        self.results[label] = record
        LOGGER.info("Completed VQE | label=%s | energy=%.6f | exact_gap=%.6f | physical_valid=%s", label, energy, exact_gap, physical_valid)
        return record

    def save_summary(self, prefix: Path, config: Dict[str, object]) -> None:
        payload = {
            "config": config,
            "system": {"n_qubits": self.n_qubits, "field_strength": self.field_strength, "coupling": self.coupling},
            "exact_energy": self.exact_energy,
            "exact_summary": self.exact_summary,
            "results": {label: asdict(result) for label, result in self.results.items()},
            "best_label": self.best_label(),
        }
        prefix.with_suffix(".json").write_text(json.dumps(payload, indent=2))

    def save_plot(self, prefix: Path) -> None:
        PlotBook.save_single_run(prefix, self.exact_energy, self.results)

    def best_label(self) -> Optional[str]:
        if not self.results:
            return None
        labels = list(self.results)
        physical_labels = [label for label in labels if self.results[label].physical_valid]
        candidate_labels = physical_labels or labels
        return min(candidate_labels, key=lambda label: (self.results[label].physics_score if self.results[label].physics_score is not None else self.results[label].exact_gap))
