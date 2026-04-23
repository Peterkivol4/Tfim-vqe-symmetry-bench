from __future__ import annotations

from pathlib import Path

from .ansatz import CircuitFactory
from .config import NoiseDeck, RunSpec, StudySpec
from .experiment import FieldLineExperiment
from .hamiltonian import SpinChainBuilder
from .logging_utils import configure_logging, get_logger
from .study import StudyRunner

LOGGER = get_logger(__name__)

__all__ = ["run_experiment", "run_study"]


def run_experiment(run_spec: RunSpec, noise_deck: NoiseDeck):
    run_spec.validate()
    noise_deck.validate()
    configure_logging(run_spec.log_level)
    hamiltonian = SpinChainBuilder.ising_chain(run_spec.n_qubits, coupling=run_spec.coupling, field_strength=run_spec.field_strength, periodic=run_spec.periodic_boundary)
    experiment = FieldLineExperiment(hamiltonian, run_spec.n_qubits, run_spec.field_strength, run_spec.coupling, run_spec.seed)
    noise_cfg = noise_deck if run_spec.use_noise else None
    ansatz = CircuitFactory.build(run_spec.ansatz, run_spec.n_qubits, run_spec.depth)
    LOGGER.info("System: %s-qubit transverse-field Ising chain", run_spec.n_qubits)
    LOGGER.info("Field strength: %.3f | coupling: %.3f", run_spec.field_strength, run_spec.coupling)
    LOGGER.info("Ansatz: %s | depth: %s | optimizer: %s", run_spec.ansatz, run_spec.depth, run_spec.optimizer)
    LOGGER.info("Exact ground energy: %.6f", experiment.exact_energy)
    label = f"{run_spec.ansatz}_d{run_spec.depth}_{run_spec.optimizer}_{'noisy' if run_spec.use_noise else 'ideal'}"
    record = experiment.run_vqe(
        ansatz,
        run_spec.optimizer,
        run_spec.max_iter,
        label,
        run_spec.ansatz,
        run_spec.depth,
        noise_cfg,
        run_spec.verification_shots,
        symmetry_penalty_lambda=run_spec.symmetry_penalty_lambda,
        shot_allocation=run_spec.shot_allocation,
        base_shots=run_spec.base_shots,
        final_shots=run_spec.final_shots,
        preflight_shots=run_spec.preflight_shots,
        enable_dynamic_shots=run_spec.enable_dynamic_shots,
        enable_readout_mitigation=run_spec.enable_readout_mitigation,
        enable_zne=run_spec.enable_zne,
        zne_factors=run_spec.zne_factors,
        zne_extrapolator=run_spec.zne_extrapolator,
        physical_validity_tol=run_spec.physical_validity_tol,
        spsa_config=run_spec.spsa,
    )
    prefix = Path(run_spec.output_prefix)
    experiment.save_summary(prefix, {"run_spec": run_spec.to_dict(), "noise_deck": noise_deck.to_dict()})
    experiment.save_plot(prefix)
    LOGGER.info("Saved plot: %s", prefix.with_suffix('.png'))
    LOGGER.info("Saved summary: %s", prefix.with_suffix('.json'))
    return record


def run_study(study_spec: StudySpec, noise_template: NoiseDeck):
    study_spec.validate()
    noise_template.validate()
    configure_logging(study_spec.log_level)
    payload = StudyRunner.run(study_spec, noise_template)
    prefix = Path(study_spec.output_prefix)
    StudyRunner.save(prefix, study_spec, payload)
    LOGGER.info("Saved raw sweep: %s", prefix.with_name(prefix.name + '_raw.csv'))
    LOGGER.info("Saved summary CSV: %s", prefix.with_name(prefix.name + '_summary.csv'))
    LOGGER.info("Saved crossover: %s", prefix.with_name(prefix.name + '_crossover.csv'))
    LOGGER.info("Saved study plot: %s", prefix.with_suffix('.png'))
    LOGGER.info("Saved study JSON: %s", prefix.with_suffix('.json'))
    LOGGER.info("Saved behavior: %s", prefix.with_name(prefix.name + '_behavior.json'))
    LOGGER.info("Saved behavior report: %s", prefix.with_name(prefix.name + '_behavior_report.md'))
    return payload
