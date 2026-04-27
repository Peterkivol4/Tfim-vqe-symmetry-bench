from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List
import warnings

from .constants import (
    DEFAULT_ANSATZES,
    DEFAULT_BASE_SHOTS,
    DEFAULT_BEHAVIOR_LOW_NOISE_THRESHOLD,
    DEFAULT_BEHAVIOR_MODERATE_NOISE_THRESHOLD,
    DEFAULT_BEHAVIOR_NEAR_CRITICAL_RATIO,
    DEFAULT_BEHAVIOR_OBSERVABLE_RISK_WEIGHT,
    DEFAULT_BEHAVIOR_SYMMETRY_RISK_WEIGHT,
    DEFAULT_BEHAVIOR_UNCERTAINTY_RISK_WEIGHT,
    DEFAULT_BEHAVIOR_WEAK_FIELD_RATIO,
    DEFAULT_COUPLING,
    DEFAULT_CROSSOVER_OBSERVABLE_PENALTY,
    DEFAULT_CROSSOVER_SYMMETRY_PENALTY,
    DEFAULT_DEPTH,
    DEFAULT_ENABLE_DYNAMIC_SHOTS,
    DEFAULT_ENABLE_READOUT_MITIGATION,
    DEFAULT_ENABLE_ZNE,
    DEFAULT_FIELD_STRENGTH,
    DEFAULT_FIELD_STRENGTHS,
    DEFAULT_FINAL_SHOTS,
    DEFAULT_GATE_ERRORS,
    DEFAULT_GATE_ERROR,
    DEFAULT_GATE_TIME,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_ITER,
    DEFAULT_MAX_WORKERS,
    DEFAULT_NOISE_BODIES,
    DEFAULT_NOISE_BODY,
    DEFAULT_NOISE_BODY_COHERENCE_ANGLE,
    DEFAULT_NOISE_BODY_CORRELATION,
    DEFAULT_NOISE_BODY_OUTPUT_PREFIX,
    DEFAULT_NOISE_BODY_READOUT_ERROR,
    DEFAULT_NOISE_STRENGTHS,
    DEFAULT_OPTIMIZERS,
    DEFAULT_OUTPUT_PREFIX,
    DEFAULT_PERIODIC_BOUNDARY,
    DEFAULT_PHYSICAL_VALIDITY_TOL,
    DEFAULT_PREFLIGHT_SHOTS,
    DEFAULT_READOUT_ERROR,
    DEFAULT_SEED,
    DEFAULT_SEEDS,
    DEFAULT_SHOT_ALLOCATION,
    DEFAULT_SPSA_ALPHA,
    DEFAULT_SPSA_GAMMA,
    DEFAULT_SPSA_LEARNING_RATE,
    DEFAULT_SPSA_PERTURBATION,
    DEFAULT_SPSA_STABILITY_RATIO,
    DEFAULT_STUDY_OUTPUT_PREFIX,
    DEFAULT_SYSTEM_SIZES,
    DEFAULT_SYMMETRY_PENALTY_LAMBDA,
    DEFAULT_T1,
    DEFAULT_T2,
    DEFAULT_VERIFICATION_SHOTS,
    DEFAULT_ZNE_EXTRAPOLATOR,
    DEFAULT_ZNE_FACTORS,
    DEFAULT_DEPTHS,
    NOISE_BODY_ALIASES,
    VALID_ANSATZES,
    VALID_LOG_LEVELS,
    VALID_NOISE_BODIES,
    VALID_OPTIMIZERS,
    VALID_SHOT_ALLOCATIONS,
    VALID_ZNE_EXTRAPOLATORS,
)

__all__ = [
    "SPSAConfig", "BehaviorConfig", "NoiseDeck", "NoiseBodyConfig", "RunSpec", "StudySpec", "NoiseBodySweepSpec",
    "VALID_OPTIMIZERS", "VALID_SHOT_ALLOCATIONS", "VALID_LOG_LEVELS", "VALID_ZNE_EXTRAPOLATORS", "VALID_NOISE_BODIES",
]


@dataclass
class SPSAConfig:
    learning_rate: float = DEFAULT_SPSA_LEARNING_RATE
    perturbation: float = DEFAULT_SPSA_PERTURBATION
    alpha: float = DEFAULT_SPSA_ALPHA
    gamma: float = DEFAULT_SPSA_GAMMA
    stability_constant_ratio: float = DEFAULT_SPSA_STABILITY_RATIO

    def validate(self) -> None:
        if self.learning_rate <= 0 or self.perturbation <= 0:
            raise ValueError("invalid SPSA schedule")
        if not (0.5 < self.alpha <= 1.0):
            raise ValueError("invalid SPSA alpha")
        if not (0.0 < self.gamma <= 1.0):
            raise ValueError("invalid SPSA gamma")
        if self.gamma > (1.0 / 6.0):
            warnings.warn("SPSA gamma exceeds 1/6; schedule may be unstable", RuntimeWarning, stacklevel=2)
        if self.stability_constant_ratio < 0.0:
            raise ValueError("invalid SPSA stability constant")

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class BehaviorConfig:
    weak_field_ratio: float = DEFAULT_BEHAVIOR_WEAK_FIELD_RATIO
    near_critical_ratio: float = DEFAULT_BEHAVIOR_NEAR_CRITICAL_RATIO
    low_noise_threshold: float = DEFAULT_BEHAVIOR_LOW_NOISE_THRESHOLD
    moderate_noise_threshold: float = DEFAULT_BEHAVIOR_MODERATE_NOISE_THRESHOLD
    symmetry_risk_weight: float = DEFAULT_BEHAVIOR_SYMMETRY_RISK_WEIGHT
    observable_risk_weight: float = DEFAULT_BEHAVIOR_OBSERVABLE_RISK_WEIGHT
    uncertainty_risk_weight: float = DEFAULT_BEHAVIOR_UNCERTAINTY_RISK_WEIGHT

    def validate(self) -> None:
        if self.weak_field_ratio <= 0.0:
            raise ValueError("invalid weak-field threshold")
        if self.near_critical_ratio < self.weak_field_ratio:
            raise ValueError("invalid critical-field threshold")
        if self.low_noise_threshold < 0.0 or self.moderate_noise_threshold < self.low_noise_threshold:
            raise ValueError("invalid noise thresholds")
        for value in (self.symmetry_risk_weight, self.observable_risk_weight, self.uncertainty_risk_weight):
            if value < 0.0:
                raise ValueError("risk weights must be non-negative")

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class NoiseDeck:
    gate_error: float = DEFAULT_GATE_ERROR
    two_qubit_gate_error: float | None = None
    t1: float = DEFAULT_T1
    t2: float = DEFAULT_T2
    gate_time: float = DEFAULT_GATE_TIME
    seed: int = DEFAULT_SEED
    readout_error: float = DEFAULT_READOUT_ERROR
    readout_error_01: float | None = None
    readout_error_10: float | None = None

    def validate(self) -> None:
        if not (0.0 <= self.gate_error < 1.0):
            raise ValueError("invalid 1q gate error")
        if self.two_qubit_gate_error is not None and not (0.0 <= self.two_qubit_gate_error < 1.0):
            raise ValueError("invalid 2q gate error")
        if self.t1 <= 0 or self.t2 <= 0 or self.gate_time <= 0:
            raise ValueError("invalid relaxation parameters")
        if self.t2 > 2.0 * self.t1:
            raise ValueError("unphysical T2")
        for value in (self.readout_error, self.readout_error_01, self.readout_error_10):
            if value is not None and not (0.0 <= float(value) < 1.0):
                raise ValueError("invalid readout error")

    def readout_pair(self) -> tuple[float, float]:
        p01 = float(self.readout_error if self.readout_error_01 is None else self.readout_error_01)
        p10 = float(self.readout_error if self.readout_error_10 is None else self.readout_error_10)
        return p01, p10

    def has_readout_noise(self) -> bool:
        p01, p10 = self.readout_pair()
        return p01 > 0.0 or p10 > 0.0

    def effective_two_qubit_gate_error(self) -> float:
        if self.two_qubit_gate_error is not None:
            return float(self.two_qubit_gate_error)
        return float(min(10.0 * self.gate_error, 0.999))

    def scaled(self, factor: float) -> "NoiseDeck":
        factor = float(factor)
        if factor <= 0.0:
            raise ValueError("invalid ZNE scale factor")
        return NoiseDeck(
            gate_error=min(self.gate_error * factor, 0.999),
            two_qubit_gate_error=min(self.effective_two_qubit_gate_error() * factor, 0.999),
            t1=self.t1,
            t2=self.t2,
            gate_time=self.gate_time * factor,
            seed=self.seed,
            readout_error=self.readout_error,
            readout_error_01=self.readout_error_01,
            readout_error_10=self.readout_error_10,
        )

    def to_dict(self) -> Dict[str, float | None | str]:
        payload = asdict(self)
        payload["effective_readout_error_01"], payload["effective_readout_error_10"] = self.readout_pair()
        payload["effective_two_qubit_gate_error"] = self.effective_two_qubit_gate_error()
        payload["zne_scaling_strategy"] = "scale gate error and gate duration; keep T1/T2 fixed"
        return payload


@dataclass
class NoiseBodyConfig:
    body: str = DEFAULT_NOISE_BODY
    strength: float = 0.0
    correlation: float = DEFAULT_NOISE_BODY_CORRELATION
    coherence_angle: float = DEFAULT_NOISE_BODY_COHERENCE_ANGLE
    temporal_drift: float = 0.0
    readout_error: float = DEFAULT_NOISE_BODY_READOUT_ERROR
    seed: int = DEFAULT_SEED
    t1: float = DEFAULT_T1
    t2: float = DEFAULT_T2
    gate_time: float = DEFAULT_GATE_TIME

    def validate(self) -> None:
        self.body = NOISE_BODY_ALIASES.get(self.body.lower(), self.body.lower())
        if self.body not in VALID_NOISE_BODIES:
            raise ValueError("unsupported noise body")
        if self.strength < 0.0:
            raise ValueError("noise-body strength must be non-negative")
        if not (-1.0 <= float(self.correlation) <= 1.0):
            raise ValueError("noise-body correlation must lie in [-1, 1]")
        if self.temporal_drift < 0.0:
            raise ValueError("temporal drift must be non-negative")
        if not (0.0 <= float(self.readout_error) < 1.0):
            raise ValueError("invalid noise-body readout error")
        if self.t1 <= 0 or self.t2 <= 0 or self.gate_time <= 0:
            raise ValueError("invalid relaxation parameters")
        if self.t2 > 2.0 * self.t1:
            raise ValueError("unphysical T2")

    @property
    def gate_error(self) -> float:
        return float(self.strength)

    def readout_pair(self) -> tuple[float, float]:
        if self.body == "readout_only":
            return float(max(self.readout_error, self.strength)), float(max(self.readout_error, self.strength))
        return float(self.readout_error), float(self.readout_error)

    def has_readout_noise(self) -> bool:
        p01, p10 = self.readout_pair()
        return p01 > 0.0 or p10 > 0.0

    def effective_two_qubit_gate_error(self) -> float:
        if self.body in {"correlated_zz_noise", "hardware"}:
            return float(min(max(self.strength * (1.0 + max(self.correlation, 0.0)), 0.0), 0.999))
        return float(min(max(self.strength, 0.0), 0.999))

    def effective_coherence_angle(self) -> float:
        base = float(self.coherence_angle if abs(self.coherence_angle) > 0.0 else self.strength)
        if self.body == "correlated_zz_noise":
            base *= 1.0 + float(max(self.correlation, 0.0))
        return base

    def scaled(self, factor: float) -> "NoiseBodyConfig":
        factor = float(factor)
        if factor <= 0.0:
            raise ValueError("invalid noise-body scale factor")
        readout = self.readout_error * factor if self.body == "readout_only" else self.readout_error
        return NoiseBodyConfig(
            body=self.body,
            strength=self.strength * factor,
            correlation=self.correlation,
            coherence_angle=self.coherence_angle * factor if self.body in {"coherent_x_drift", "coherent_z_drift", "correlated_zz_noise"} else self.coherence_angle,
            temporal_drift=self.temporal_drift * factor,
            readout_error=min(readout, 0.999),
            seed=self.seed,
            t1=self.t1,
            t2=self.t2,
            gate_time=self.gate_time * max(factor, 1.0),
        )

    def to_dict(self) -> Dict[str, float | int | str]:
        payload = asdict(self)
        payload["effective_two_qubit_gate_error"] = self.effective_two_qubit_gate_error()
        payload["effective_coherence_angle"] = self.effective_coherence_angle()
        payload["effective_readout_error_01"], payload["effective_readout_error_10"] = self.readout_pair()
        return payload


@dataclass
class RunSpec:
    n_qubits: int = 4
    field_strength: float = DEFAULT_FIELD_STRENGTH
    coupling: float = DEFAULT_COUPLING
    periodic_boundary: bool = DEFAULT_PERIODIC_BOUNDARY
    ansatz: str = "hardware_efficient"
    depth: int = DEFAULT_DEPTH
    optimizer: str = "COBYLA"
    max_iter: int = DEFAULT_MAX_ITER
    verification_shots: int = DEFAULT_VERIFICATION_SHOTS
    seed: int = DEFAULT_SEED
    output_prefix: str = DEFAULT_OUTPUT_PREFIX
    use_noise: bool = False
    symmetry_penalty_lambda: float = DEFAULT_SYMMETRY_PENALTY_LAMBDA
    shot_allocation: str = DEFAULT_SHOT_ALLOCATION
    preflight_shots: int = DEFAULT_PREFLIGHT_SHOTS
    base_shots: int = DEFAULT_BASE_SHOTS
    final_shots: int = DEFAULT_FINAL_SHOTS
    enable_dynamic_shots: bool = DEFAULT_ENABLE_DYNAMIC_SHOTS
    enable_zne: bool = DEFAULT_ENABLE_ZNE
    enable_readout_mitigation: bool = DEFAULT_ENABLE_READOUT_MITIGATION
    zne_factors: List[int] = field(default_factory=lambda: list(DEFAULT_ZNE_FACTORS))
    zne_extrapolator: str = DEFAULT_ZNE_EXTRAPOLATOR
    physical_validity_tol: float = DEFAULT_PHYSICAL_VALIDITY_TOL
    spsa: SPSAConfig = field(default_factory=SPSAConfig)
    log_level: str = DEFAULT_LOG_LEVEL

    def validate(self) -> None:
        if self.n_qubits <= 1 or self.depth <= 0 or self.max_iter <= 0 or self.verification_shots <= 0:
            raise ValueError("invalid run dimensions")
        if self.symmetry_penalty_lambda < 0:
            raise ValueError("invalid symmetry penalty")
        if self.preflight_shots <= 0 or self.base_shots <= 0 or self.final_shots <= 0:
            raise ValueError("invalid shot schedule")
        if self.base_shots > self.final_shots:
            raise ValueError("invalid shot schedule")
        if not self.zne_factors or any(f < 1 for f in self.zne_factors):
            raise ValueError("invalid ZNE factors")
        if self.physical_validity_tol < 0:
            raise ValueError("invalid physical validity tolerance")
        self.optimizer = self.optimizer.upper()
        self.ansatz = self.ansatz.lower()
        self.shot_allocation = self.shot_allocation.lower()
        self.log_level = self.log_level.upper()
        self.zne_extrapolator = self.zne_extrapolator.lower()
        if self.optimizer not in VALID_OPTIMIZERS:
            raise ValueError("unsupported optimizer")
        if self.ansatz not in VALID_ANSATZES:
            raise ValueError("unsupported ansatz")
        if self.shot_allocation not in VALID_SHOT_ALLOCATIONS:
            raise ValueError("unsupported shot allocation")
        if self.log_level not in VALID_LOG_LEVELS:
            raise ValueError("unsupported log level")
        if self.zne_extrapolator not in VALID_ZNE_EXTRAPOLATORS:
            raise ValueError("unsupported ZNE extrapolator")
        self.spsa.validate()

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class StudySpec:
    system_sizes: List[int] = field(default_factory=lambda: list(DEFAULT_SYSTEM_SIZES))
    field_strengths: List[float] = field(default_factory=lambda: list(DEFAULT_FIELD_STRENGTHS))
    depths: List[int] = field(default_factory=lambda: list(DEFAULT_DEPTHS))
    ansatzes: List[str] = field(default_factory=lambda: list(DEFAULT_ANSATZES))
    optimizers: List[str] = field(default_factory=lambda: list(DEFAULT_OPTIMIZERS))
    gate_errors: List[float] = field(default_factory=lambda: list(DEFAULT_GATE_ERRORS))
    seeds: List[int] = field(default_factory=lambda: list(DEFAULT_SEEDS))
    coupling: float = DEFAULT_COUPLING
    periodic_boundary: bool = DEFAULT_PERIODIC_BOUNDARY
    max_iter: int = 80
    verification_shots: int = DEFAULT_VERIFICATION_SHOTS
    output_prefix: str = DEFAULT_STUDY_OUTPUT_PREFIX
    symmetry_penalty_lambda: float = DEFAULT_SYMMETRY_PENALTY_LAMBDA
    shot_allocation: str = DEFAULT_SHOT_ALLOCATION
    preflight_shots: int = DEFAULT_PREFLIGHT_SHOTS
    base_shots: int = DEFAULT_BASE_SHOTS
    final_shots: int = DEFAULT_FINAL_SHOTS
    enable_dynamic_shots: bool = DEFAULT_ENABLE_DYNAMIC_SHOTS
    enable_zne: bool = DEFAULT_ENABLE_ZNE
    enable_readout_mitigation: bool = DEFAULT_ENABLE_READOUT_MITIGATION
    zne_factors: List[int] = field(default_factory=lambda: list(DEFAULT_ZNE_FACTORS))
    zne_extrapolator: str = DEFAULT_ZNE_EXTRAPOLATOR
    crossover_symmetry_penalty: float = DEFAULT_CROSSOVER_SYMMETRY_PENALTY
    crossover_observable_penalty: float = DEFAULT_CROSSOVER_OBSERVABLE_PENALTY
    physical_validity_tol: float = DEFAULT_PHYSICAL_VALIDITY_TOL
    max_workers: int = DEFAULT_MAX_WORKERS
    spsa: SPSAConfig = field(default_factory=SPSAConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    log_level: str = DEFAULT_LOG_LEVEL

    def validate(self) -> None:
        self.ansatzes = [v.lower() for v in self.ansatzes]
        self.optimizers = [v.upper() for v in self.optimizers]
        self.shot_allocation = self.shot_allocation.lower()
        self.log_level = self.log_level.upper()
        self.zne_extrapolator = self.zne_extrapolator.lower()
        if set(self.ansatzes) - VALID_ANSATZES:
            raise ValueError("unsupported study ansatz")
        if set(self.optimizers) - VALID_OPTIMIZERS:
            raise ValueError("unsupported study optimizer")
        if self.shot_allocation not in VALID_SHOT_ALLOCATIONS:
            raise ValueError("unsupported shot allocation")
        if self.log_level not in VALID_LOG_LEVELS:
            raise ValueError("unsupported log level")
        if self.zne_extrapolator not in VALID_ZNE_EXTRAPOLATORS:
            raise ValueError("unsupported ZNE extrapolator")
        if not self.system_sizes or not self.field_strengths or not self.depths or not self.gate_errors:
            raise ValueError("empty study sweep")
        if self.symmetry_penalty_lambda < 0 or self.crossover_symmetry_penalty < 0 or self.crossover_observable_penalty < 0:
            raise ValueError("invalid study penalty")
        if self.preflight_shots <= 0 or self.base_shots <= 0 or self.final_shots <= 0:
            raise ValueError("invalid shot schedule")
        if self.base_shots > self.final_shots:
            raise ValueError("invalid shot schedule")
        if not self.zne_factors or any(f < 1 for f in self.zne_factors):
            raise ValueError("invalid ZNE factors")
        if self.physical_validity_tol < 0:
            raise ValueError("invalid physical validity tolerance")
        if self.max_workers <= 0:
            raise ValueError("invalid worker count")
        self.spsa.validate()
        self.behavior.validate()

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class NoiseBodySweepSpec:
    system_sizes: List[int] = field(default_factory=lambda: list(DEFAULT_SYSTEM_SIZES))
    field_strengths: List[float] = field(default_factory=lambda: list(DEFAULT_FIELD_STRENGTHS))
    depths: List[int] = field(default_factory=lambda: list(DEFAULT_DEPTHS))
    ansatzes: List[str] = field(default_factory=lambda: list(DEFAULT_ANSATZES))
    optimizers: List[str] = field(default_factory=lambda: list(DEFAULT_OPTIMIZERS))
    bodies: List[str] = field(default_factory=lambda: list(DEFAULT_NOISE_BODIES))
    strengths: List[float] = field(default_factory=lambda: list(DEFAULT_NOISE_STRENGTHS))
    seeds: List[int] = field(default_factory=lambda: list(DEFAULT_SEEDS))
    coupling: float = DEFAULT_COUPLING
    periodic_boundary: bool = DEFAULT_PERIODIC_BOUNDARY
    max_iter: int = DEFAULT_MAX_ITER
    verification_shots: int = DEFAULT_VERIFICATION_SHOTS
    output_prefix: str = DEFAULT_NOISE_BODY_OUTPUT_PREFIX
    symmetry_penalty_lambda: float = DEFAULT_SYMMETRY_PENALTY_LAMBDA
    shot_allocation: str = DEFAULT_SHOT_ALLOCATION
    preflight_shots: int = DEFAULT_PREFLIGHT_SHOTS
    base_shots: int = DEFAULT_BASE_SHOTS
    final_shots: int = DEFAULT_FINAL_SHOTS
    enable_dynamic_shots: bool = DEFAULT_ENABLE_DYNAMIC_SHOTS
    enable_zne: bool = False
    enable_readout_mitigation: bool = DEFAULT_ENABLE_READOUT_MITIGATION
    zne_factors: List[int] = field(default_factory=lambda: list(DEFAULT_ZNE_FACTORS))
    zne_extrapolator: str = DEFAULT_ZNE_EXTRAPOLATOR
    physical_validity_tol: float = DEFAULT_PHYSICAL_VALIDITY_TOL
    max_workers: int = DEFAULT_MAX_WORKERS
    body_correlation: float = DEFAULT_NOISE_BODY_CORRELATION
    body_coherence_angle: float = DEFAULT_NOISE_BODY_COHERENCE_ANGLE
    body_readout_error: float = DEFAULT_NOISE_BODY_READOUT_ERROR
    compute_gradient_norm: bool = True
    spsa: SPSAConfig = field(default_factory=SPSAConfig)
    log_level: str = DEFAULT_LOG_LEVEL

    def validate(self) -> None:
        self.ansatzes = [v.lower() for v in self.ansatzes]
        self.optimizers = [v.upper() for v in self.optimizers]
        self.bodies = [NOISE_BODY_ALIASES.get(v.lower(), v.lower()) for v in self.bodies]
        self.shot_allocation = self.shot_allocation.lower()
        self.log_level = self.log_level.upper()
        self.zne_extrapolator = self.zne_extrapolator.lower()
        if set(self.ansatzes) - VALID_ANSATZES:
            raise ValueError("unsupported noise-body ansatz")
        if set(self.optimizers) - VALID_OPTIMIZERS:
            raise ValueError("unsupported noise-body optimizer")
        if set(self.bodies) - VALID_NOISE_BODIES:
            raise ValueError("unsupported noise body in sweep")
        if self.shot_allocation not in VALID_SHOT_ALLOCATIONS:
            raise ValueError("unsupported shot allocation")
        if self.log_level not in VALID_LOG_LEVELS:
            raise ValueError("unsupported log level")
        if self.zne_extrapolator not in VALID_ZNE_EXTRAPOLATORS:
            raise ValueError("unsupported ZNE extrapolator")
        if not self.system_sizes or not self.field_strengths or not self.depths or not self.bodies or not self.strengths:
            raise ValueError("empty noise-body sweep")
        if any(value < 0.0 for value in self.strengths):
            raise ValueError("noise-body strengths must be non-negative")
        if not (-1.0 <= float(self.body_correlation) <= 1.0):
            raise ValueError("noise-body correlation must lie in [-1, 1]")
        if not (0.0 <= float(self.body_readout_error) < 1.0):
            raise ValueError("invalid noise-body readout error")
        if self.preflight_shots <= 0 or self.base_shots <= 0 or self.final_shots <= 0:
            raise ValueError("invalid shot schedule")
        if self.base_shots > self.final_shots:
            raise ValueError("invalid shot schedule")
        if not self.zne_factors or any(f < 1 for f in self.zne_factors):
            raise ValueError("invalid ZNE factors")
        if self.physical_validity_tol < 0:
            raise ValueError("invalid physical validity tolerance")
        if self.max_workers <= 0:
            raise ValueError("invalid worker count")
        self.spsa.validate()

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)
