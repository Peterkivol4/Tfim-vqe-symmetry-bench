from __future__ import annotations

import os

import numpy as np
import pytest

from fieldline_vqe.ansatz import CircuitFactory
from fieldline_vqe.config import NoiseDeck, RunSpec, StudySpec, SPSAConfig
from fieldline_vqe.experiment import FieldLineExperiment
from fieldline_vqe.hamiltonian import SpinChainBuilder
from fieldline_vqe.noise import NoiseFactory
from fieldline_vqe.observables import MeasurementPlanner, ObservableFactory, StateAnalyzer
from fieldline_vqe.pipeline import run_experiment, run_study
from fieldline_vqe.study import StudyRunner

pytestmark = pytest.mark.filterwarnings(
    "ignore:Since backends now support running jobs that contain both fractional gates and dynamic circuit.*:DeprecationWarning"
)


def test_variance_weighted_allocation_prefers_high_std_group() -> None:
    groups = MeasurementPlanner.group_qwc(MeasurementPlanner.pauli_terms(SpinChainBuilder.ising_chain(4, 1.0, 1.0), prefix="cost"))
    alloc = MeasurementPlanner.allocate_shots(groups, 100, strategy="variance_weighted", empirical_variances={"ZZZZ": 1.0, "XXXX": 9.0})
    assert alloc["XXXX"] > alloc["ZZZZ"]


def test_entropy_available_for_density_matrix_projection() -> None:
    h = SpinChainBuilder.ising_chain(4, 1.0, 1.0)
    exp = FieldLineExperiment(h, 4, 1.0, 1.0, seed=1)
    ansatz = CircuitFactory.build("hardware_efficient", 4, 1)
    circuit = ansatz.assign_parameters([0.0] * ansatz.num_parameters)
    noisy_state = exp._simulate_state(circuit, NoiseDeck(gate_error=0.01, readout_error=0.02))
    summary = StateAnalyzer.summarize(noisy_state, 4, h, exp.exact_state, ObservableFactory.default_bundle(4))
    assert summary["half_chain_entropy"] is not None
    assert summary["half_chain_entropy_mode"] == "density_matrix"

def test_exact_ground_state_has_near_zero_energy_variance() -> None:
    h = SpinChainBuilder.ising_chain(4, 1.0, 1.0)
    exp = FieldLineExperiment(h, 4, 1.0, 1.0, seed=1)
    summary = StateAnalyzer.summarize(exp.exact_state, 4, h, exp.exact_state, ObservableFactory.default_bundle(4))
    assert summary["energy_variance"] is not None
    assert summary["energy_variance"] < 1e-10
    assert summary["energy_stddev"] < 1e-5


def test_connected_correlators_vanish_for_x_product_state() -> None:
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector

    h = SpinChainBuilder.ising_chain(4, 1.0, 1.0)
    circuit = QuantumCircuit(4)
    circuit.h(range(4))
    state = Statevector.from_instruction(circuit)
    summary = StateAnalyzer.summarize(state, 4, h, None, ObservableFactory.default_bundle(4))
    assert summary["magnetization_x"] == pytest.approx(1.0)
    assert all(value == pytest.approx(1.0) for value in summary["correlation_xx_profile"])
    assert all(abs(value) < 1e-10 for value in summary["connected_correlation_xx_profile"])
    assert summary["connected_correlation_xx_mean"] == pytest.approx(0.0)


def test_noise_model_includes_readout_and_extended_gates() -> None:
    model = NoiseFactory.build(NoiseDeck(gate_error=0.01, readout_error=0.03))
    basis_gates = set(model.noise_instructions)
    assert "rzz" in basis_gates or "cx" in basis_gates
    assert "measure" in basis_gates


def test_single_run_smoke(tmp_path) -> None:
    spec = RunSpec(n_qubits=4, field_strength=1.0, ansatz="hardware_efficient", depth=1, optimizer="COBYLA", max_iter=2, verification_shots=64, output_prefix=str(tmp_path / "single"), use_noise=False)
    record = run_experiment(spec, NoiseDeck(gate_error=0.01))
    assert record.energy <= 2.0
    assert (tmp_path / "single.json").exists()
    assert (tmp_path / "single.png").exists()


def test_measurement_template_cache_reuses_transpile(monkeypatch) -> None:
    import fieldline_vqe.experiment as experiment_module

    original_transpile = experiment_module.transpile
    calls = {"count": 0}

    def counting_transpile(*args, **kwargs):
        calls["count"] += 1
        return original_transpile(*args, **kwargs)

    monkeypatch.setattr(experiment_module, "transpile", counting_transpile)
    h = SpinChainBuilder.ising_chain(4, 1.0, 1.0)
    exp = FieldLineExperiment(h, 4, 1.0, 1.0, seed=1)
    ansatz = CircuitFactory.build("hardware_efficient", 4, 1)
    params = [0.0] * ansatz.num_parameters
    noise = NoiseDeck(gate_error=0.01, readout_error=0.01)
    exp._sample_counts_from_template(ansatz, np.asarray(params, dtype=float), "XXXX", noise, shots=8)
    exp._sample_counts_from_template(ansatz, np.asarray(params, dtype=float), "XXXX", noise, shots=8)
    assert calls["count"] == 1


def test_tiny_noisy_study_smoke(tmp_path) -> None:
    study = StudySpec(
        system_sizes=[4],
        field_strengths=[1.0],
        depths=[1],
        ansatzes=["hardware_efficient", "symmetry_preserving"],
        optimizers=["SPSA"],
        gate_errors=[0.01],
        seeds=[7],
        max_iter=1,
        verification_shots=32,
        output_prefix=str(tmp_path / "study"),
        base_shots=16,
        final_shots=32,
        preflight_shots=8,
        shot_allocation="variance_weighted",
    )
    payload = run_study(study, NoiseDeck(gate_error=0.01, readout_error=0.01))
    assert payload["rows"]
    assert payload["crossover"]
    assert (tmp_path / "study_raw.csv").exists()
    assert (tmp_path / "study_summary.csv").exists()
    assert (tmp_path / "study_crossover.csv").exists()


def test_tfim_hamiltonian_groups_into_x_and_zz_bases() -> None:
    groups = MeasurementPlanner.group_qwc(MeasurementPlanner.pauli_terms(SpinChainBuilder.ising_chain(4, 1.0, 1.0), prefix="cost"))
    bases = {group.basis for group in groups}
    assert bases == {"XXXX", "ZZZZ"}


def test_symmetry_preserving_ansatz_stays_in_even_x_sector() -> None:
    h = SpinChainBuilder.ising_chain(4, 1.0, 1.0)
    exp = FieldLineExperiment(h, 4, 1.0, 1.0, seed=1)
    ansatz = CircuitFactory.build("symmetry_preserving", 4, 1)
    circuit = ansatz.assign_parameters([0.0] * ansatz.num_parameters)
    state = exp._simulate_state(circuit, None)
    summary = StateAnalyzer.summarize(state, 4, h, exp.exact_state, ObservableFactory.default_bundle(4))
    assert abs(float(summary["x_parity"]) - 1.0) < 1e-9


def test_readout_mitigation_recovers_simple_one_qubit_distribution() -> None:
    mitigated = MeasurementPlanner.mitigate_readout_distribution({"0": 0.8, "1": 0.2}, 1, p01=0.2, p10=0.0)
    assert mitigated["0"] > 0.95
    assert mitigated.get("1", 0.0) < 0.05


def test_crossover_prefers_physical_candidate_when_available() -> None:
    spec = StudySpec(system_sizes=[4], field_strengths=[1.0], gate_errors=[0.01], physical_validity_tol=0.05)
    rows = [
        {
            "label": "bad_energy", "n_qubits": 4, "field_strength": 1.0, "gate_error": 0.01,
            "ansatz": "hardware_efficient", "depth": 1, "optimizer": "COBYLA",
            "energy": -10.0, "filtered_exact_gap": 0.8, "exact_gap": 0.7,
            "symmetry_breaking_error": 0.3, "filtered_observable_error_l2": 0.3,
            "physics_score": 2.0, "physical_valid": False, "x_parity": 0.4,
        },
        {
            "label": "good_physical", "n_qubits": 4, "field_strength": 1.0, "gate_error": 0.01,
            "ansatz": "symmetry_preserving", "depth": 1, "optimizer": "COBYLA",
            "energy": -9.0, "filtered_exact_gap": 0.2, "exact_gap": 0.25,
            "symmetry_breaking_error": 0.0, "filtered_observable_error_l2": 0.05,
            "physics_score": 0.2125, "physical_valid": True, "x_parity": 1.0,
        },
    ]
    crossover = StudyRunner.build_crossover(rows, spec)[0]
    assert crossover["energy_winner_label"] == "bad_energy"
    assert crossover["physics_winner_label"] == "good_physical"
    assert crossover["physical_candidate_count"] == 1


def test_target_sector_projection_supports_odd_sector() -> None:
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector

    circuit = QuantumCircuit(1)
    circuit.x(0)
    circuit.h(0)
    state = Statevector.from_instruction(circuit)
    projected, rate = StateAnalyzer.x_parity_projection(state, 1, sector=-1)
    summary = StateAnalyzer.summarize(projected, 1, ObservableFactory.global_x_parity(1), None, ObservableFactory.default_bundle(1))
    assert rate > 0.999
    assert summary["x_parity"] < -0.999


def test_noise_signature_distinguishes_asymmetric_readout() -> None:
    h = SpinChainBuilder.ising_chain(4, 1.0, 1.0)
    exp = FieldLineExperiment(h, 4, 1.0, 1.0, seed=1)
    left = NoiseDeck(gate_error=0.01, readout_error_01=0.02, readout_error_10=0.01)
    right = NoiseDeck(gate_error=0.01, readout_error_01=0.01, readout_error_10=0.02)
    assert exp._noise_signature(left) != exp._noise_signature(right)


def test_run_record_exposes_spectral_gap_and_target_sector(tmp_path) -> None:
    spec = RunSpec(n_qubits=4, field_strength=1.0, ansatz="symmetry_preserving", depth=1, optimizer="COBYLA", max_iter=1, verification_shots=32, output_prefix=str(tmp_path / "single_gap"), use_noise=False)
    record = run_experiment(spec, NoiseDeck(gate_error=0.01))
    assert record.exact_first_excited_energy is not None
    assert record.exact_spectral_gap is not None and record.exact_spectral_gap >= 0.0
    assert record.target_x_parity_sector in {-1, 1}

def test_run_record_exposes_variance_and_connected_means(tmp_path) -> None:
    spec = RunSpec(n_qubits=4, field_strength=1.0, ansatz="symmetry_preserving", depth=1, optimizer="COBYLA", max_iter=1, verification_shots=32, output_prefix=str(tmp_path / "single_diag"), use_noise=False)
    record = run_experiment(spec, NoiseDeck(gate_error=0.01))
    assert record.energy_variance is not None and record.energy_variance >= 0.0
    assert record.energy_stddev is not None and record.energy_stddev >= 0.0
    assert record.relative_energy_stddev is not None and record.relative_energy_stddev >= 0.0
    assert record.connected_correlation_xx_mean is not None
    assert record.connected_correlation_zz_mean is not None


def test_best_label_prefers_physical_valid_result() -> None:
    h = SpinChainBuilder.ising_chain(4, 1.0, 1.0)
    exp = FieldLineExperiment(h, 4, 1.0, 1.0, seed=1)
    from fieldline_vqe.results import TrialRecord

    base_kwargs = dict(
        ansatz="he", optimizer="COBYLA", depth=1, seed=1, noise_level=0.0, energy=-1.0, exact_gap=0.1, relative_gap=0.1,
        cost_value=-1.0, cost_standard_error=None, unmitigated_cost_value=-1.0, unmitigated_cost_standard_error=None, symmetry_penalty_lambda=0.0, filtered_energy=-1.0, filtered_exact_gap=0.1,
        exact_first_excited_energy=0.0, exact_spectral_gap=1.0, energy_variance=0.0, energy_stddev=0.0, relative_energy_stddev=0.0, observable_error_l2=0.1, filtered_observable_error_l2=0.1, symmetry_postselection_rate=1.0,
        sampled_postselection_rate=1.0, sampled_postselection_standard_error=0.0, mitigated_sampled_postselection_rate=1.0, mitigated_sampled_postselection_standard_error=0.0, x_parity=1.0, mitigated_x_parity=1.0, target_x_parity_sector=1,
        target_sector_probability=1.0, symmetry_breaking_error=0.0, fidelity_to_exact=1.0, half_chain_entropy=0.0, energy_history=[-1.0], iterations=1,
        circuit_depth=1, execution_time=0.0, optimal_params=[], observables={}, symmetry_summary={}, shot_allocation_strategy="equal",
        dynamic_shots_enabled=False, base_shots=None, final_shots=None, preflight_shots=None, measurement_plan={}, zne_enabled=False, zne_noise_factors=[1],
        zne_samples=[], objective_calls=None, shot_schedule=[], estimated_total_shots_used=None, avg_shots_per_eval=None,
        original_two_qubit_gate_count=0, transpiled_depth=0, transpiled_two_qubit_gate_count=0, transpiled_entangling_layer_count=0,
        physical_validity_tol=0.05, physical_validity_reason="passes_target_x_parity_tolerance", mitigation_gain=None,
        connected_correlation_xx_mean=0.0, connected_correlation_zz_mean=0.0,
    )
    exp.results = {
        "invalid": TrialRecord(label="invalid", physics_score=0.01, physical_valid=False, **base_kwargs),
        "valid": TrialRecord(label="valid", physics_score=0.2, physical_valid=True, **base_kwargs),
    }
    assert exp.best_label() == "valid"


@pytest.mark.filterwarnings("ignore:Since backends now support running jobs that contain both fractional gates and dynamic circuit.*:DeprecationWarning")
def test_runtime_transpile_uses_final_layout_for_observables() -> None:
    from qiskit import QuantumCircuit
    from qiskit.providers.fake_provider import GenericBackendV2
    from qiskit.quantum_info import SparsePauliOp
    from qiskit.transpiler import CouplingMap

    from fieldline_vqe.runtime import RuntimeFactory

    backend = GenericBackendV2(
        num_qubits=4,
        basis_gates=["rz", "sx", "x", "cx", "swap"],
        coupling_map=CouplingMap([[0, 1], [1, 2], [2, 3]]),
        seed=11,
    )
    circuit = QuantumCircuit(4)
    circuit.h(0)
    circuit.cx(0, 3)
    circuit.cx(3, 1)
    observables = {"z_on_q1": SparsePauliOp.from_list([("IIZI", 1.0)])}
    isa_circuit, isa_observables, layout_meta = RuntimeFactory.transpile_to_isa(circuit, observables, backend, optimization_level=0, seed_transpiler=11)
    expected = observables["z_on_q1"].apply_layout(isa_circuit.layout.final_index_layout())
    assert layout_meta["final_layout_present"] is True
    assert layout_meta["final_index_layout"] != [0, 1, 2, 3]
    assert isa_observables["z_on_q1"].paulis.to_labels() == expected.paulis.to_labels()


@pytest.mark.filterwarnings("ignore:Since backends now support running jobs that contain both fractional gates and dynamic circuit.*:DeprecationWarning")
def test_runtime_transpile_expands_observables_to_backend_width() -> None:
    from qiskit import QuantumCircuit
    from qiskit.providers.fake_provider import GenericBackendV2
    from qiskit.quantum_info import SparsePauliOp

    from fieldline_vqe.runtime import RuntimeFactory

    backend = GenericBackendV2(num_qubits=12, basis_gates=["rz", "sx", "x", "cx"], seed=7)
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    observable = SparsePauliOp.from_list([("ZZ", 1.0)])
    isa_circuit, isa_observables, _layout_meta = RuntimeFactory.transpile_to_isa(
        circuit,
        {"zz": observable},
        backend,
        optimization_level=1,
        seed_transpiler=7,
    )
    assert isa_circuit.num_qubits == backend.num_qubits
    assert isa_observables["zz"].num_qubits == isa_circuit.num_qubits


@pytest.mark.live_runtime
def test_live_runtime_smoke_opt_in(tmp_path) -> None:
    pytest.importorskip("qiskit_ibm_runtime")
    if os.getenv("FIELDLINE_VQE_RUN_LIVE_RUNTIME") != "1":
        pytest.skip("set FIELDLINE_VQE_RUN_LIVE_RUNTIME=1 and a runtime token env var to enable the live IBM Runtime smoke test")

    import sys
    from pathlib import Path as _Path

    sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
    from tools_live_runtime_smoke import PENDING_STATUSES, run_live_smoke

    report = run_live_smoke(
        timeout=int(os.getenv("FIELDLINE_VQE_LIVE_TIMEOUT", "240")),
        output_path=tmp_path / "live_runtime_smoke.json",
    )

    assert report["submitted_ok"] is True
    assert report["job_id"]
    assert report["comparison_ready"] is True
    assert report["isa_circuit_num_qubits"] == report["isa_observable_num_qubits"]
    assert (tmp_path / "live_runtime_smoke.json").exists()
    if report["result_available"]:
        assert report["result_energy"] is not None
        assert report["result_exact_gap"] is not None
        assert report["result_exact_gap"] >= 0.0
    else:
        assert report["job_status_final"] in PENDING_STATUSES


def test_zne_execution_exports_samples_and_mitigation_gain(tmp_path) -> None:
    spec = RunSpec(
        n_qubits=4,
        field_strength=1.0,
        ansatz="hardware_efficient",
        depth=1,
        optimizer="COBYLA",
        max_iter=2,
        verification_shots=32,
        output_prefix=str(tmp_path / "zne_single"),
        use_noise=True,
        enable_zne=True,
        zne_factors=[1, 3],
        base_shots=16,
        final_shots=16,
    )
    record = run_experiment(spec, NoiseDeck(gate_error=0.01, readout_error=0.01))
    assert record.zne_enabled is True
    assert record.unmitigated_cost_value is not None
    assert len(record.zne_samples) == 2
    assert abs(record.zne_samples[0] - record.unmitigated_cost_value) < 1e-12
    assert record.measurement_plan["zne_samples"] == record.zne_samples
    assert record.mitigation_gain is not None


def test_dynamic_shot_scaling_exports_nontrivial_schedule(tmp_path) -> None:
    spec = RunSpec(
        n_qubits=4,
        field_strength=1.0,
        ansatz="hardware_efficient",
        depth=1,
        optimizer="SPSA",
        max_iter=2,
        verification_shots=16,
        output_prefix=str(tmp_path / "dyn_single"),
        use_noise=True,
        enable_dynamic_shots=True,
        base_shots=8,
        final_shots=16,
    )
    record = run_experiment(spec, NoiseDeck(gate_error=0.01, readout_error=0.0))
    assert record.dynamic_shots_enabled is True
    assert record.shot_schedule
    assert min(record.shot_schedule) == 8
    assert max(record.shot_schedule) == 16
    assert record.estimated_total_shots_used is not None and record.estimated_total_shots_used > 0


def test_cost_operator_penalizes_wrong_x_parity_sector() -> None:
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector

    h = SpinChainBuilder.ising_chain(2, 1.0, 1.0)
    exp = FieldLineExperiment(h, 2, 1.0, 1.0, seed=1)
    qc_plus = QuantumCircuit(2)
    qc_plus.h([0, 1])
    qc_minus = QuantumCircuit(2)
    qc_minus.h([0, 1])
    qc_minus.z(0)
    state_plus = Statevector.from_instruction(qc_plus)
    state_minus = Statevector.from_instruction(qc_minus)
    parity_plus = float(state_plus.expectation_value(exp.symmetry_operator).real)
    parity_minus = float(state_minus.expectation_value(exp.symmetry_operator).real)
    assert abs(parity_plus - 1.0) < 1e-9
    assert abs(parity_minus + 1.0) < 1e-9
    lam = 2.5
    cost_op = exp._cost_operator(lam)
    h_plus = float(state_plus.expectation_value(exp.hamiltonian).real)
    h_minus = float(state_minus.expectation_value(exp.hamiltonian).real)
    c_plus = float(state_plus.expectation_value(cost_op).real)
    c_minus = float(state_minus.expectation_value(cost_op).real)
    assert abs((h_plus - c_plus) - lam) < 1e-9
    assert abs((h_minus - c_minus) + lam) < 1e-9


def test_noisy_run_exports_measurement_uncertainty(tmp_path) -> None:
    spec = RunSpec(
        n_qubits=4,
        field_strength=1.0,
        ansatz="hardware_efficient",
        depth=1,
        optimizer="SPSA",
        max_iter=1,
        verification_shots=32,
        output_prefix=str(tmp_path / "uncertainty_single"),
        use_noise=True,
        base_shots=16,
        final_shots=16,
        preflight_shots=8,
        shot_allocation="variance_weighted",
    )
    record = run_experiment(spec, NoiseDeck(gate_error=0.01, readout_error=0.01))
    assert record.cost_standard_error is not None and record.cost_standard_error >= 0.0
    assert record.unmitigated_cost_standard_error is not None and record.unmitigated_cost_standard_error >= 0.0
    assert record.sampled_postselection_standard_error is not None and record.sampled_postselection_standard_error >= 0.0
    assert record.mitigated_sampled_postselection_standard_error is not None and record.mitigated_sampled_postselection_standard_error >= 0.0
    assert record.measurement_plan["total_standard_error"] is not None
    assert isinstance(record.measurement_plan["group_standard_errors"], dict)



def test_tiny_study_writes_behavior_artifacts(tmp_path) -> None:
    study = StudySpec(
        system_sizes=[4],
        field_strengths=[0.5, 1.0],
        depths=[1],
        ansatzes=["hardware_efficient", "symmetry_preserving"],
        optimizers=["SPSA"],
        gate_errors=[0.0, 0.01],
        seeds=[7],
        max_iter=1,
        verification_shots=16,
        output_prefix=str(tmp_path / "study_behavior"),
        base_shots=8,
        final_shots=16,
        preflight_shots=4,
        shot_allocation="variance_weighted",
    )
    payload = run_study(study, NoiseDeck(gate_error=0.01, readout_error=0.01))
    behavior = payload["behavior"]
    assert behavior["regime_profiles"]
    assert behavior["ansatz_profiles"]
    assert behavior["optimizer_profiles"]
    assert behavior["crossover_profiles"]
    assert (tmp_path / "study_behavior_behavior.json").exists()
    assert (tmp_path / "study_behavior_behavior_report.md").exists()
    assert (tmp_path / "study_behavior_behavior_regimes.csv").exists()
    assert (tmp_path / "study_behavior_behavior_ansatz.csv").exists()
    assert (tmp_path / "study_behavior_behavior_optimizers.csv").exists()
    assert (tmp_path / "study_behavior_behavior_crossover.csv").exists()


def test_behavior_analysis_enriches_crossover_with_regimes_and_sigma() -> None:
    from fieldline_vqe.behavior import BehaviorAnalyzer

    rows = [
        {
            "label": "raw_a", "n_qubits": 4, "field_strength": 1.0, "gate_error": 0.01, "ansatz": "hardware_efficient", "optimizer": "COBYLA", "depth": 1,
            "energy": -10.0, "cost_value": -9.8, "cost_standard_error": 0.1, "measurement_total_standard_error": 0.1, "filtered_exact_gap": 0.4, "exact_gap": 0.3,
            "filtered_observable_error_l2": 0.2, "observable_error_l2": 0.2, "symmetry_breaking_error": 0.2, "physical_valid": False, "fidelity_to_exact": 0.75,
            "estimated_total_shots_used": 200, "transpiled_two_qubit_gate_count": 8, "transpiled_depth": 20, "zne_mitigation_gain": 0.0,
        },
        {
            "label": "phys_b", "n_qubits": 4, "field_strength": 1.0, "gate_error": 0.01, "ansatz": "symmetry_preserving", "optimizer": "SPSA", "depth": 1,
            "energy": -9.6, "cost_value": -9.6, "cost_standard_error": 0.1, "measurement_total_standard_error": 0.1, "filtered_exact_gap": 0.1, "exact_gap": 0.15,
            "filtered_observable_error_l2": 0.05, "observable_error_l2": 0.05, "symmetry_breaking_error": 0.0, "physical_valid": True, "fidelity_to_exact": 0.95,
            "estimated_total_shots_used": 240, "transpiled_two_qubit_gate_count": 10, "transpiled_depth": 24, "zne_mitigation_gain": 0.02,
        },
        {
            "label": "budget_c", "n_qubits": 4, "field_strength": 1.0, "gate_error": 0.01, "ansatz": "hardware_efficient", "optimizer": "SPSA", "depth": 1,
            "energy": -9.55, "cost_value": -9.55, "cost_standard_error": 0.08, "measurement_total_standard_error": 0.08, "filtered_exact_gap": 0.12, "exact_gap": 0.18,
            "filtered_observable_error_l2": 0.06, "observable_error_l2": 0.06, "symmetry_breaking_error": 0.0, "physical_valid": True, "fidelity_to_exact": 0.94,
            "estimated_total_shots_used": 120, "transpiled_two_qubit_gate_count": 4, "transpiled_depth": 12, "zne_mitigation_gain": 0.01,
        },
    ]
    crossover = [{
        "n_qubits": 4, "field_strength": 1.0, "gate_error": 0.01, "energy_winner_label": "raw_a", "energy_winner_ansatz": "hardware_efficient",
        "physics_winner_label": "phys_b", "physics_winner_ansatz": "symmetry_preserving", "budget_winner_label": "budget_c", "budget_winner_ansatz": "hardware_efficient", "false_winner_flag": True,
    }]
    analysis = BehaviorAnalyzer.build(rows, [], crossover, coupling=1.0)
    enriched = analysis["crossover_profiles"][0]
    assert enriched["regime_label"] == "near_critical"
    assert enriched["noise_regime"] == "moderate_noise"
    assert enriched["energy_vs_physics_cost_sigma"] is not None
    assert analysis["ansatz_profiles"]
    assert analysis["optimizer_profiles"]
    assert "Detailed Behavior Study" in analysis["report_markdown"]


def test_noise_model_covers_counted_two_qubit_gates() -> None:
    from fieldline_vqe.noise import NoiseFactory, TWO_QUBIT_NOISE_GATES

    noise_model = NoiseFactory.build(NoiseDeck(gate_error=0.01, two_qubit_gate_error=0.05))
    assert set(TWO_QUBIT_NOISE_GATES).issubset(set(noise_model.noise_instructions))


def test_shots_for_single_iteration_uses_final_budget() -> None:
    h = SpinChainBuilder.ising_chain(4, 1.0, 1.0)
    exp = FieldLineExperiment(h, 4, 1.0, 1.0, seed=1)
    assert exp._shots_for_call(call_index=1, max_iter=1, base_shots=8, final_shots=32, dynamic=True) == 32


def test_internal_spsa_fallback_avoids_redundant_per_iteration_probe() -> None:
    h = SpinChainBuilder.ising_chain(4, 1.0, 1.0)
    exp = FieldLineExperiment(h, 4, 1.0, 1.0, seed=1)
    ansatz = CircuitFactory.build("hardware_efficient", 4, 1)
    params, history, summary = exp._optimize(
        ansatz=ansatz,
        optimizer_name="SPSA",
        max_iter=2,
        noise_cfg=None,
        symmetry_penalty_lambda=0.0,
        shot_allocation="equal",
        base_shots=8,
        final_shots=8,
        preflight_shots=4,
        enable_dynamic_shots=False,
        enable_readout_mitigation=True,
        enable_zne=False,
        zne_factors=[1],
    )
    assert params.shape[0] == ansatz.num_parameters
    assert len(history) == 5
    assert summary["nfev"] == 5


def test_qiskit_spsa_resets_algorithm_seed_for_reproducibility() -> None:
    h = SpinChainBuilder.ising_chain(4, 1.0, 1.0)
    ansatz = CircuitFactory.build("hardware_efficient", 4, 1)

    def run_once():
        exp = FieldLineExperiment(h, 4, 1.0, 1.0, seed=17)
        params, history, summary = exp._optimize(
            ansatz=ansatz,
            optimizer_name="SPSA",
            max_iter=1,
            noise_cfg=None,
            symmetry_penalty_lambda=0.0,
            shot_allocation="equal",
            base_shots=8,
            final_shots=8,
            preflight_shots=4,
            enable_dynamic_shots=False,
            enable_readout_mitigation=True,
            enable_zne=False,
            zne_factors=[1],
        )
        return params, history, summary

    params_a, history_a, summary_a = run_once()
    params_b, history_b, summary_b = run_once()

    assert np.allclose(params_a, params_b)
    assert history_a == pytest.approx(history_b)
    assert summary_a["nfev"] == summary_b["nfev"]


def test_density_matrix_half_chain_entropy_is_available_under_noise() -> None:
    h = SpinChainBuilder.ising_chain(2, 1.0, 1.0)
    exp = FieldLineExperiment(h, 2, 1.0, 1.0, seed=1)
    ansatz = CircuitFactory.build("hardware_efficient", 2, 1)
    circuit = ansatz.assign_parameters([0.0] * ansatz.num_parameters)
    state = exp._simulate_state(circuit, NoiseDeck(gate_error=0.01, readout_error=0.0))
    summary = StateAnalyzer.summarize(state, 2, h, exp.exact_state, ObservableFactory.default_bundle(2))
    assert summary["half_chain_entropy"] is not None
    assert summary["half_chain_entropy_mode"] == "density_matrix"


def test_periodic_boundary_adds_wraparound_zz_term() -> None:
    open_chain = SpinChainBuilder.ising_chain(4, 1.0, 0.0, periodic=False)
    periodic_chain = SpinChainBuilder.ising_chain(4, 1.0, 0.0, periodic=True)
    assert len(open_chain.paulis) == 3
    assert len(periodic_chain.paulis) == 4
    labels = set(periodic_chain.paulis.to_labels())
    assert "ZIIZ" in labels


def test_default_zne_extrapolator_is_linear() -> None:
    values = [1.0, 3.0, 9.0]
    result = FieldLineExperiment._zne_extrapolate([1, 3, 5], values)
    expected = float(np.polyval(np.polyfit(np.asarray([1, 3, 5], dtype=float), np.asarray(values, dtype=float), deg=1), 0.0))
    assert abs(result - expected) < 1e-12


def test_noise_scaling_preserves_t1_t2_and_scales_gate_time() -> None:
    cfg = NoiseDeck(gate_error=0.01, two_qubit_gate_error=0.05, t1=50.0, t2=70.0, gate_time=0.1)
    scaled = cfg.scaled(3.0)
    assert scaled.gate_error == pytest.approx(0.03)
    assert scaled.effective_two_qubit_gate_error() == pytest.approx(0.15)
    assert scaled.t1 == pytest.approx(cfg.t1)
    assert scaled.t2 == pytest.approx(cfg.t2)
    assert scaled.gate_time == pytest.approx(0.3)


def test_t2_constraint_is_enforced() -> None:
    with pytest.raises(ValueError, match="T2"):
        NoiseDeck(t1=10.0, t2=25.0).validate()


def test_dynamic_shots_single_eval_uses_final_budget() -> None:
    h = SpinChainBuilder.ising_chain(4, 1.0, 1.0)
    exp = FieldLineExperiment(h, 4, 1.0, 1.0, seed=1)
    assert exp._shots_for_call(call_index=1, max_iter=1, base_shots=16, final_shots=64, dynamic=True) == 64


def test_internal_spsa_fallback_avoids_redundant_third_probe() -> None:
    from fieldline_vqe.executors import ObjectiveTrace, OptimizationExecutor

    h = SpinChainBuilder.ising_chain(4, 1.0, 1.0)
    exp = FieldLineExperiment(h, 4, 1.0, 1.0, seed=1)
    executor = OptimizationExecutor(exp)
    trace = ObjectiveTrace()

    def objective(params):
        value = float(np.sum(np.square(params)))
        trace.record(value, {"zne_noise_factors": [1]}, None)
        return value

    theta, summary = executor._optimize_internal_spsa(objective, np.array([0.2, -0.3]), 3, SPSAConfig(), trace)
    assert theta.shape == (2,)
    assert summary["nfev"] == 6
    assert len(trace.history) == 6


def test_qwc_grouping_keeps_terms_pairwise_compatible() -> None:
    from fieldline_vqe.observables import MeasurementPlanner, MeasurementTerm

    terms = [
        MeasurementTerm("t0", "XXII", 1.0),
        MeasurementTerm("t1", "XIXI", 1.0),
        MeasurementTerm("t2", "ZZII", 1.0),
        MeasurementTerm("t3", "ZIZI", 1.0),
        MeasurementTerm("t4", "IYYI", 1.0),
    ]
    groups = MeasurementPlanner.group_qwc(terms)
    for group in groups:
        for left_idx, left in enumerate(group.terms):
            for right in group.terms[left_idx + 1:]:
                assert MeasurementPlanner._compatible_with_basis(left.label, right.label)


def test_bfgs_optimizer_runs_in_noiseless_mode(tmp_path) -> None:
    spec = RunSpec(n_qubits=4, field_strength=1.0, ansatz="hardware_efficient", depth=1, optimizer="BFGS", max_iter=1, verification_shots=32, output_prefix=str(tmp_path / "bfgs"), use_noise=False)
    record = run_experiment(spec, NoiseDeck(gate_error=0.01))
    assert record.optimizer == "BFGS"
    assert (tmp_path / "bfgs.json").exists()


def test_final_cost_metadata_is_recomputed_at_optimum(tmp_path) -> None:
    spec = RunSpec(n_qubits=4, field_strength=1.0, ansatz="hardware_efficient", depth=1, optimizer="SPSA", max_iter=1, verification_shots=16, output_prefix=str(tmp_path / "finalcost"), use_noise=True, base_shots=8, final_shots=16, preflight_shots=4, enable_dynamic_shots=True)
    record = run_experiment(spec, NoiseDeck(gate_error=0.01, readout_error=0.01))
    assert record.measurement_plan.get("final_cost_evaluation_shots") == 16
    assert record.cost_value is not None
