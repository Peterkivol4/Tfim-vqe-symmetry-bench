from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .config import BehaviorConfig, NoiseBodySweepSpec, NoiseDeck, RunSpec, SPSAConfig, StudySpec
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
    DEFAULT_NOISE_BODY_COHERENCE_ANGLE,
    DEFAULT_NOISE_BODY_CORRELATION,
    DEFAULT_NOISE_BODY_OUTPUT_PREFIX,
    DEFAULT_NOISE_BODY_READOUT_ERROR,
    DEFAULT_NOISE_STRENGTHS,
    DEFAULT_OUTPUT_PREFIX,
    DEFAULT_PERIODIC_BOUNDARY,
    DEFAULT_PHYSICAL_VALIDITY_TOL,
    DEFAULT_PREFLIGHT_SHOTS,
    DEFAULT_READOUT_ERROR,
    DEFAULT_SEED,
    DEFAULT_SEEDS,
    DEFAULT_SPSA_ALPHA,
    DEFAULT_SPSA_GAMMA,
    DEFAULT_SPSA_LEARNING_RATE,
    DEFAULT_SPSA_PERTURBATION,
    DEFAULT_SPSA_STABILITY_RATIO,
    DEFAULT_SYSTEM_SIZES,
    DEFAULT_T1,
    DEFAULT_T2,
    DEFAULT_VERIFICATION_SHOTS,
    DEFAULT_ZNE_EXTRAPOLATOR,
    DEFAULT_ZNE_FACTORS,
    DEFAULT_DEPTHS,
)
from .errors import production_console_logging_enabled, production_errors_enabled, production_log_path, render_operator_error
from .logging_utils import configure_logging, get_logger
from .pipeline import run_experiment, run_noise_body_match, run_noise_body_sweep, run_study

__all__ = ["build_parser", "main"]

_LOG = get_logger("fieldline_vqe.cli")


def _csv_ints(text: str):
    return [int(item.strip()) for item in text.split(',') if item.strip()]


def _csv_floats(text: str):
    return [float(item.strip()) for item in text.split(',') if item.strip()]


def _csv_strings(text: str):
    return [item.strip() for item in text.split(',') if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run FieldLine VQE experiments or study sweeps.')
    parser.add_argument('--mode', choices=['single', 'study', 'noise-body-sweep', 'critical-drift-sweep', 'match-noise-body'], default='single')
    parser.add_argument('--n-qubits', type=int, default=4)
    parser.add_argument('--field-strength', type=float, default=DEFAULT_FIELD_STRENGTH)
    parser.add_argument('--coupling', type=float, default=DEFAULT_COUPLING)
    parser.add_argument('--periodic-boundary', action='store_true', default=DEFAULT_PERIODIC_BOUNDARY)
    parser.add_argument('--ansatz', type=str, default='hardware_efficient')
    parser.add_argument('--depth', type=int, default=DEFAULT_DEPTH)
    parser.add_argument('--optimizer', type=str, default='COBYLA')
    parser.add_argument('--max-iter', type=int, default=DEFAULT_MAX_ITER)
    parser.add_argument('--verification-shots', type=int, default=DEFAULT_VERIFICATION_SHOTS)
    parser.add_argument('--seed', type=int, default=DEFAULT_SEED)
    parser.add_argument('--output-prefix', '--output-stem', dest='output_prefix', type=str, default=DEFAULT_OUTPUT_PREFIX)
    parser.add_argument('--use-noise', action='store_true')
    parser.add_argument('--gate-error', type=float, default=DEFAULT_GATE_ERROR)
    parser.add_argument('--two-qubit-gate-error', type=float, default=None)
    parser.add_argument('--t1', type=float, default=DEFAULT_T1)
    parser.add_argument('--t2', type=float, default=DEFAULT_T2)
    parser.add_argument('--gate-time', type=float, default=DEFAULT_GATE_TIME)
    parser.add_argument('--readout-error', type=float, default=DEFAULT_READOUT_ERROR)
    parser.add_argument('--readout-error-01', type=float, default=None)
    parser.add_argument('--readout-error-10', type=float, default=None)
    parser.add_argument('--symmetry-penalty-lambda', type=float, default=0.0)
    parser.add_argument('--shot-allocation', choices=['equal', 'coefficient_weighted', 'variance_weighted'], default='equal')
    parser.add_argument('--preflight-shots', type=int, default=DEFAULT_PREFLIGHT_SHOTS)
    parser.add_argument('--base-shots', type=int, default=DEFAULT_BASE_SHOTS)
    parser.add_argument('--final-shots', type=int, default=DEFAULT_FINAL_SHOTS)
    parser.add_argument('--enable-dynamic-shots', action='store_true')
    parser.add_argument('--enable-zne', action='store_true')
    parser.add_argument('--disable-readout-mitigation', action='store_true')
    parser.add_argument('--physical-validity-tol', type=float, default=DEFAULT_PHYSICAL_VALIDITY_TOL)
    parser.add_argument('--zne-factors', type=_csv_ints, default=list(DEFAULT_ZNE_FACTORS))
    parser.add_argument('--zne-extrapolator', choices=['linear', 'quadratic', 'exponential'], default=DEFAULT_ZNE_EXTRAPOLATOR)
    parser.add_argument('--system-sizes', '--n-values', dest='system_sizes', type=_csv_ints, default=list(DEFAULT_SYSTEM_SIZES))
    parser.add_argument('--field-strengths', '--g-values', dest='field_strengths', type=_csv_floats, default=list(DEFAULT_FIELD_STRENGTHS))
    parser.add_argument('--depths', type=_csv_ints, default=list(DEFAULT_DEPTHS))
    parser.add_argument('--ansatzes', type=_csv_strings, default=list(DEFAULT_ANSATZES))
    parser.add_argument('--optimizers', type=_csv_strings, default=['COBYLA', 'SPSA', 'SLSQP'])
    parser.add_argument('--gate-errors', type=_csv_floats, default=list(DEFAULT_GATE_ERRORS))
    parser.add_argument('--seeds', type=_csv_ints, default=list(DEFAULT_SEEDS))
    parser.add_argument('--bodies', type=_csv_strings, default=list(DEFAULT_NOISE_BODIES))
    parser.add_argument('--strengths', type=_csv_floats, default=list(DEFAULT_NOISE_STRENGTHS))
    parser.add_argument('--body-correlation', type=float, default=DEFAULT_NOISE_BODY_CORRELATION)
    parser.add_argument('--body-coherence-angle', type=float, default=DEFAULT_NOISE_BODY_COHERENCE_ANGLE)
    parser.add_argument('--body-readout-error', type=float, default=DEFAULT_NOISE_BODY_READOUT_ERROR)
    parser.add_argument('--disable-gradient-probe', action='store_true')
    parser.add_argument('--input', type=str, default=None)
    parser.add_argument('--reference', type=str, default=None)
    parser.add_argument('--output', type=str, default=None)
    parser.add_argument('--crossover-symmetry-penalty', type=float, default=DEFAULT_CROSSOVER_SYMMETRY_PENALTY)
    parser.add_argument('--crossover-observable-penalty', type=float, default=DEFAULT_CROSSOVER_OBSERVABLE_PENALTY)
    parser.add_argument('--log-level', type=str, default=DEFAULT_LOG_LEVEL)
    parser.add_argument('--max-workers', type=int, default=DEFAULT_MAX_WORKERS)
    parser.add_argument('--spsa-learning-rate', type=float, default=DEFAULT_SPSA_LEARNING_RATE)
    parser.add_argument('--spsa-perturbation', type=float, default=DEFAULT_SPSA_PERTURBATION)
    parser.add_argument('--spsa-alpha', type=float, default=DEFAULT_SPSA_ALPHA)
    parser.add_argument('--spsa-gamma', type=float, default=DEFAULT_SPSA_GAMMA)
    parser.add_argument('--spsa-stability-constant-ratio', type=float, default=DEFAULT_SPSA_STABILITY_RATIO)
    parser.add_argument('--behavior-weak-field-ratio', type=float, default=DEFAULT_BEHAVIOR_WEAK_FIELD_RATIO)
    parser.add_argument('--behavior-near-critical-ratio', type=float, default=DEFAULT_BEHAVIOR_NEAR_CRITICAL_RATIO)
    parser.add_argument('--behavior-low-noise-threshold', type=float, default=DEFAULT_BEHAVIOR_LOW_NOISE_THRESHOLD)
    parser.add_argument('--behavior-moderate-noise-threshold', type=float, default=DEFAULT_BEHAVIOR_MODERATE_NOISE_THRESHOLD)
    parser.add_argument('--behavior-symmetry-risk-weight', type=float, default=DEFAULT_BEHAVIOR_SYMMETRY_RISK_WEIGHT)
    parser.add_argument('--behavior-observable-risk-weight', type=float, default=DEFAULT_BEHAVIOR_OBSERVABLE_RISK_WEIGHT)
    parser.add_argument('--behavior-uncertainty-risk-weight', type=float, default=DEFAULT_BEHAVIOR_UNCERTAINTY_RISK_WEIGHT)
    return parser


def _dispatch(args: argparse.Namespace) -> None:
    if args.mode == 'match-noise-body':
        if not args.input:
            raise ValueError("--input is required for match-noise-body")
        out = args.output or str(Path(DEFAULT_NOISE_BODY_OUTPUT_PREFIX).with_name(Path(DEFAULT_NOISE_BODY_OUTPUT_PREFIX).name + "_body_matching_report.md"))
        run_noise_body_match(args.input, args.reference, out)
        return
    noise = NoiseDeck(
        gate_error=args.gate_error,
        two_qubit_gate_error=args.two_qubit_gate_error,
        t1=args.t1,
        t2=args.t2,
        gate_time=args.gate_time,
        seed=args.seed,
        readout_error=args.readout_error,
        readout_error_01=args.readout_error_01,
        readout_error_10=args.readout_error_10,
    )
    spsa = SPSAConfig(
        learning_rate=args.spsa_learning_rate,
        perturbation=args.spsa_perturbation,
        alpha=args.spsa_alpha,
        gamma=args.spsa_gamma,
        stability_constant_ratio=args.spsa_stability_constant_ratio,
    )
    behavior = BehaviorConfig(
        weak_field_ratio=args.behavior_weak_field_ratio,
        near_critical_ratio=args.behavior_near_critical_ratio,
        low_noise_threshold=args.behavior_low_noise_threshold,
        moderate_noise_threshold=args.behavior_moderate_noise_threshold,
        symmetry_risk_weight=args.behavior_symmetry_risk_weight,
        observable_risk_weight=args.behavior_observable_risk_weight,
        uncertainty_risk_weight=args.behavior_uncertainty_risk_weight,
    )
    if args.mode == 'single':
        run_experiment(
            RunSpec(
                n_qubits=args.n_qubits,
                field_strength=args.field_strength,
                coupling=args.coupling,
                periodic_boundary=args.periodic_boundary,
                ansatz=args.ansatz,
                depth=args.depth,
                optimizer=args.optimizer,
                max_iter=args.max_iter,
                verification_shots=args.verification_shots,
                seed=args.seed,
                output_prefix=args.output_prefix,
                use_noise=args.use_noise,
                symmetry_penalty_lambda=args.symmetry_penalty_lambda,
                shot_allocation=args.shot_allocation,
                preflight_shots=args.preflight_shots,
                base_shots=args.base_shots,
                final_shots=args.final_shots,
                enable_dynamic_shots=args.enable_dynamic_shots,
                enable_zne=args.enable_zne,
                enable_readout_mitigation=not args.disable_readout_mitigation,
                zne_factors=args.zne_factors,
                zne_extrapolator=args.zne_extrapolator,
                physical_validity_tol=args.physical_validity_tol,
                spsa=spsa,
                log_level=args.log_level,
            ),
            noise,
        )
        return
    if args.mode in {'noise-body-sweep', 'critical-drift-sweep'}:
        run_noise_body_sweep(
            NoiseBodySweepSpec(
                system_sizes=args.system_sizes,
                field_strengths=args.field_strengths,
                depths=args.depths,
                ansatzes=args.ansatzes,
                optimizers=args.optimizers,
                bodies=args.bodies,
                strengths=args.strengths,
                seeds=args.seeds,
                coupling=args.coupling,
                periodic_boundary=args.periodic_boundary,
                max_iter=args.max_iter,
                verification_shots=args.verification_shots,
                output_prefix=args.output_prefix if args.output_prefix != DEFAULT_OUTPUT_PREFIX else DEFAULT_NOISE_BODY_OUTPUT_PREFIX,
                symmetry_penalty_lambda=args.symmetry_penalty_lambda,
                shot_allocation=args.shot_allocation,
                preflight_shots=args.preflight_shots,
                base_shots=args.base_shots,
                final_shots=args.final_shots,
                enable_dynamic_shots=args.enable_dynamic_shots,
                enable_zne=args.enable_zne,
                enable_readout_mitigation=not args.disable_readout_mitigation,
                zne_factors=args.zne_factors,
                zne_extrapolator=args.zne_extrapolator,
                physical_validity_tol=args.physical_validity_tol,
                max_workers=args.max_workers,
                body_correlation=args.body_correlation,
                body_coherence_angle=args.body_coherence_angle,
                body_readout_error=args.body_readout_error,
                compute_gradient_norm=not args.disable_gradient_probe,
                spsa=spsa,
                log_level=args.log_level,
            )
        )
        return
    run_study(
        StudySpec(
            system_sizes=args.system_sizes,
            field_strengths=args.field_strengths,
            depths=args.depths,
            ansatzes=args.ansatzes,
            optimizers=args.optimizers,
            gate_errors=args.gate_errors,
            seeds=args.seeds,
            coupling=args.coupling,
            periodic_boundary=args.periodic_boundary,
            max_iter=args.max_iter,
            verification_shots=args.verification_shots,
            output_prefix=args.output_prefix,
            symmetry_penalty_lambda=args.symmetry_penalty_lambda,
            shot_allocation=args.shot_allocation,
            preflight_shots=args.preflight_shots,
            base_shots=args.base_shots,
            final_shots=args.final_shots,
            enable_dynamic_shots=args.enable_dynamic_shots,
            enable_zne=args.enable_zne,
            enable_readout_mitigation=not args.disable_readout_mitigation,
            zne_factors=args.zne_factors,
            zne_extrapolator=args.zne_extrapolator,
            crossover_symmetry_penalty=args.crossover_symmetry_penalty,
            crossover_observable_penalty=args.crossover_observable_penalty,
            physical_validity_tol=args.physical_validity_tol,
            max_workers=args.max_workers,
            spsa=spsa,
            behavior=behavior,
            log_level=args.log_level,
        ),
        noise,
    )


def main() -> None:
    argv = sys.argv[1:]
    if argv and argv[0] in {'single', 'study', 'noise-body-sweep', 'critical-drift-sweep', 'match-noise-body'}:
        argv = ['--mode', argv[0], *argv[1:]]
    args = build_parser().parse_args(argv)
    prod = production_errors_enabled()
    configure_logging(args.log_level, console=production_console_logging_enabled(), log_path=production_log_path() if prod else None)
    try:
        _dispatch(args)
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        if not prod:
            raise
        _LOG.error("fieldline cli failed | kind=%s", exc.__class__.__name__)
        print(render_operator_error(exc), file=sys.stderr)
        raise SystemExit(2)
