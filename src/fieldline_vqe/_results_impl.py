from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

__all__ = ["TrialRecord", "DeviationSignature"]


@dataclass
class DeviationSignature:
    n: int
    g: float
    depth: int
    ansatz: str
    optimizer: str
    noise_body: str
    noise_strength: float
    energy_error: float
    fidelity_loss: float | None
    parity_sector_loss: float
    symmetry_breaking_error: float
    magnetization_x_error: float
    magnetization_z_error: float
    correlation_xx_error: float
    correlation_zz_error: float
    connected_correlation_error: float
    entanglement_entropy_error: float | None
    energy_variance: float
    gradient_norm: float | None
    critical_drift_score: float | None


@dataclass
class TrialRecord:
    label: str
    ansatz: str
    optimizer: str
    depth: int
    seed: int
    noise_level: float
    energy: float
    exact_gap: float
    relative_gap: float
    cost_value: float
    cost_standard_error: float | None
    unmitigated_cost_value: float | None
    unmitigated_cost_standard_error: float | None
    mitigation_gain: float | None
    symmetry_penalty_lambda: float
    filtered_energy: float | None
    filtered_exact_gap: float | None
    exact_first_excited_energy: float | None
    exact_spectral_gap: float | None
    energy_variance: float | None
    energy_stddev: float | None
    relative_energy_stddev: float | None
    observable_error_l2: float | None
    filtered_observable_error_l2: float | None
    symmetry_postselection_rate: float | None
    sampled_postselection_rate: float | None
    sampled_postselection_standard_error: float | None
    mitigated_sampled_postselection_rate: float | None
    mitigated_sampled_postselection_standard_error: float | None
    x_parity: float | None
    mitigated_x_parity: float | None
    target_x_parity_sector: int | None
    target_sector_probability: float | None
    symmetry_breaking_error: float | None
    physics_score: float | None
    physical_valid: bool | None
    physical_validity_tol: float | None
    physical_validity_reason: str | None
    fidelity_to_exact: float | None
    half_chain_entropy: float | None
    connected_correlation_xx_mean: float | None
    connected_correlation_zz_mean: float | None
    energy_history: List[float]
    iterations: int
    circuit_depth: int
    execution_time: float
    optimal_params: List[float]
    observables: Dict[str, Any]
    symmetry_summary: Dict[str, Any]
    shot_allocation_strategy: str
    dynamic_shots_enabled: bool
    base_shots: int | None
    final_shots: int | None
    preflight_shots: int | None
    measurement_plan: Dict[str, Any]
    zne_enabled: bool
    zne_noise_factors: List[int]
    zne_samples: List[float]
    objective_calls: int | None
    shot_schedule: List[int]
    estimated_total_shots_used: int | None
    avg_shots_per_eval: float | None
    original_two_qubit_gate_count: int
    transpiled_depth: int
    transpiled_two_qubit_gate_count: int
    transpiled_entangling_layer_count: int
