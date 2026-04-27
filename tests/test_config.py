import pytest

from fieldline_vqe.config import NoiseBodyConfig, NoiseBodySweepSpec, NoiseDeck, RunSpec, StudySpec


def test_run_spec_normalizes_optimizer_and_ansatz() -> None:
    spec = RunSpec(optimizer="cobyla", ansatz="Symmetry_Preserving")
    spec.validate()
    assert spec.optimizer == "COBYLA"
    assert spec.ansatz == "symmetry_preserving"


def test_study_spec_normalizes_lists() -> None:
    spec = StudySpec(ansatzes=["hardware_efficient", "problem_inspired"], optimizers=["cobyla", "spsa"])
    spec.validate()
    assert spec.optimizers == ["COBYLA", "SPSA"]
    assert spec.ansatzes == ["hardware_efficient", "problem_inspired"]


def test_noise_deck_rejects_invalid_gate_error() -> None:
    deck = NoiseDeck(gate_error=1.2)
    try:
        deck.validate()
        raise AssertionError("Expected ValueError for invalid gate_error")
    except ValueError:
        pass


def test_shot_allocation_validation() -> None:
    spec = RunSpec(shot_allocation="variance_weighted", base_shots=128, final_shots=512)
    spec.validate()
    assert spec.shot_allocation == "variance_weighted"


def test_study_penalties_validate() -> None:
    spec = StudySpec(symmetry_penalty_lambda=0.1, crossover_symmetry_penalty=2.0, crossover_observable_penalty=0.25)
    spec.validate()
    assert spec.symmetry_penalty_lambda == 0.1



def test_spsa_and_behavior_config_validate() -> None:
    spec = StudySpec(max_workers=2)
    spec.validate()
    assert spec.spsa.learning_rate > 0
    assert spec.behavior.near_critical_ratio >= spec.behavior.weak_field_ratio
import warnings

from fieldline_vqe.config import SPSAConfig


def test_noise_deck_rejects_unphysical_t2() -> None:
    deck = NoiseDeck(t1=10.0, t2=25.0)
    try:
        deck.validate()
        raise AssertionError("Expected ValueError for unphysical T2 > 2*T1")
    except ValueError:
        pass


def test_noise_deck_scaled_amplifies_gate_duration_and_two_qubit_channel() -> None:
    deck = NoiseDeck(gate_error=0.01, two_qubit_gate_error=0.05, gate_time=0.2)
    scaled = deck.scaled(3)
    assert abs(scaled.gate_error - 0.03) < 1e-12
    assert abs(float(scaled.two_qubit_gate_error) - 0.15) < 1e-12
    assert abs(scaled.gate_time - 0.6) < 1e-12


def test_spsa_alpha_floor_and_gamma_warning() -> None:
    try:
        SPSAConfig(alpha=0.4).validate()
        raise AssertionError("Expected ValueError for alpha <= 0.5")
    except ValueError:
        pass
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        SPSAConfig(gamma=0.2).validate()
    assert any("gamma exceeds 1/6" in str(item.message) for item in caught)


def test_runspec_accepts_bfgs_optimizer() -> None:
    spec = RunSpec(optimizer="BFGS")
    spec.validate()
    assert spec.optimizer == "BFGS"


def test_noise_deck_scaled_rejects_nonpositive_factor() -> None:
    with pytest.raises(ValueError):
        NoiseDeck().scaled(0.0)


def test_noise_body_config_accepts_known_bodies() -> None:
    cfg = NoiseBodyConfig(body="dephasing", strength=0.01)
    cfg.validate()
    assert cfg.body == "local_dephasing"


def test_noise_body_config_rejects_invalid_body() -> None:
    with pytest.raises(ValueError):
        NoiseBodyConfig(body="dephasng", strength=0.01).validate()


def test_noise_body_strength_nonnegative() -> None:
    with pytest.raises(ValueError):
        NoiseBodyConfig(body="amplitude_damping", strength=-0.01).validate()


def test_noise_body_correlation_range() -> None:
    with pytest.raises(ValueError):
        NoiseBodyConfig(body="correlated_zz_noise", strength=0.01, correlation=1.5).validate()


def test_noise_body_sweep_spec_normalizes_body_names() -> None:
    spec = NoiseBodySweepSpec(bodies=["dephasing", "coherent_drift"], strengths=[0.0, 0.01])
    spec.validate()
    assert spec.bodies == ["local_dephasing", "coherent_z_drift"]
