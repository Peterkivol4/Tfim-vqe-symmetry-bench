# Surface audit

## __init__
- explicit __all__: True
- public symbols: BehaviorAnalyzer, BehaviorConfig, CircuitFactory, FieldLineExperiment, NoiseDeck, NoiseFactory, RunSpec, SPSAConfig, SpinChainBuilder, StudySpec, VALID_ANSATZES, VALID_OPTIMIZERS, SecretsManager, AnsatzFactory, BehaviorService, ExperimentService, HamiltonianFactory, NoiseModelFactory, RecordAssembler, RuntimeBridge, StudyService
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## _ansatz_impl
- explicit __all__: True
- public symbols: CircuitFactory, VALID_ANSATZES
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## _behavior_impl
- explicit __all__: True
- public symbols: BehaviorAnalyzer
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## _cli_impl
- explicit __all__: True
- public symbols: build_parser, main
- print lines: [239]
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## _config_impl
- explicit __all__: True
- public symbols: SPSAConfig, BehaviorConfig, NoiseDeck, RunSpec, StudySpec, VALID_OPTIMIZERS, VALID_SHOT_ALLOCATIONS, VALID_LOG_LEVELS, VALID_ZNE_EXTRAPOLATORS
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments:
  - RunSpec.n_qubits @ L183: `4`
  - RunSpec.ansatz @ L187: `'hardware_efficient'`
  - RunSpec.optimizer @ L189: `'COBYLA'`
  - StudySpec.max_iter @ L254: `80`

## _executors_impl
- explicit __all__: True
- public symbols: ObjectiveTrace, OptimizerTrace, StateExecutor, MeasurementExecutor, OptimizationExecutor
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## _experiment_impl
- explicit __all__: True
- public symbols: FieldLineExperiment
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments:
  - FieldLineExperiment.DEFAULT_PHYSICAL_VALIDITY_TOL @ L49: `0.05`

## _hamiltonian_impl
- explicit __all__: True
- public symbols: SpinChainBuilder
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## _logging_utils_impl
- explicit __all__: True
- public symbols: configure_logging, get_logger
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments:
  - _FORMAT @ L6: `'%(asctime)s | %(levelname)s | %(name)s | %(message)s'`

## _metrics_impl
- explicit __all__: True
- public symbols: parity_expectation, SymmetryGate
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## _native_bridge
- explicit __all__: True
- public symbols: native_available, weighted_parity, sector_mask
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## _noise_impl
- explicit __all__: True
- public symbols: NoiseFactory, ONE_QUBIT_NOISE_GATES, TWO_QUBIT_NOISE_GATES
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## _observables_impl
- explicit __all__: True
- public symbols: ObservableBundle, MeasurementTerm, MeasurementGroup, ObservableFactory, MeasurementPlanner, StateAnalyzer, expectation, energy_variance, observable_error_l2
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## _pipeline_impl
- explicit __all__: True
- public symbols: run_experiment, run_study
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## _plotting_impl
- explicit __all__: True
- public symbols: PlotBook
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## _record_builder_impl
- explicit __all__: True
- public symbols: RecordBuilder
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## _results_impl
- explicit __all__: True
- public symbols: TrialRecord
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## _runtime_impl
- explicit __all__: True
- public symbols: RuntimeFactory
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## _study_impl
- explicit __all__: True
- public symbols: row_from_record, StudyRunner
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## ansatz
- explicit __all__: True
- public symbols: (none)
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## behavior
- explicit __all__: True
- public symbols: (none)
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## cli
- explicit __all__: True
- public symbols: (none)
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## config
- explicit __all__: True
- public symbols: (none)
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## constants
- explicit __all__: True
- public symbols: VALID_ANSATZES, VALID_OPTIMIZERS, VALID_SHOT_ALLOCATIONS, VALID_LOG_LEVELS, VALID_ZNE_EXTRAPOLATORS, ONE_QUBIT_NOISE_GATES, TWO_QUBIT_NOISE_GATES, DEFAULT_SPSA_LEARNING_RATE, DEFAULT_SPSA_PERTURBATION, DEFAULT_SPSA_ALPHA, DEFAULT_SPSA_GAMMA, DEFAULT_SPSA_STABILITY_RATIO, DEFAULT_BEHAVIOR_WEAK_FIELD_RATIO, DEFAULT_BEHAVIOR_NEAR_CRITICAL_RATIO, DEFAULT_BEHAVIOR_LOW_NOISE_THRESHOLD, DEFAULT_BEHAVIOR_MODERATE_NOISE_THRESHOLD, DEFAULT_BEHAVIOR_SYMMETRY_RISK_WEIGHT, DEFAULT_BEHAVIOR_OBSERVABLE_RISK_WEIGHT, DEFAULT_BEHAVIOR_UNCERTAINTY_RISK_WEIGHT, DEFAULT_GATE_ERROR, DEFAULT_T1, DEFAULT_T2, DEFAULT_GATE_TIME, DEFAULT_SEED, DEFAULT_READOUT_ERROR, DEFAULT_COUPLING, DEFAULT_FIELD_STRENGTH, DEFAULT_PERIODIC_BOUNDARY, DEFAULT_DEPTH, DEFAULT_MAX_ITER, DEFAULT_VERIFICATION_SHOTS, DEFAULT_PREFLIGHT_SHOTS, DEFAULT_BASE_SHOTS, DEFAULT_FINAL_SHOTS, DEFAULT_ENABLE_DYNAMIC_SHOTS, DEFAULT_ENABLE_ZNE, DEFAULT_ENABLE_READOUT_MITIGATION, DEFAULT_ZNE_FACTORS, DEFAULT_ZNE_EXTRAPOLATOR, DEFAULT_PHYSICAL_VALIDITY_TOL, DEFAULT_LOG_LEVEL, DEFAULT_OUTPUT_PREFIX, DEFAULT_STUDY_OUTPUT_PREFIX, DEFAULT_MAX_WORKERS, DEFAULT_SYMMETRY_PENALTY_LAMBDA, DEFAULT_CROSSOVER_SYMMETRY_PENALTY, DEFAULT_CROSSOVER_OBSERVABLE_PENALTY, DEFAULT_SHOT_ALLOCATION, DEFAULT_SYSTEM_SIZES, DEFAULT_FIELD_STRENGTHS, DEFAULT_DEPTHS, DEFAULT_ANSATZES, DEFAULT_OPTIMIZERS, DEFAULT_GATE_ERRORS, DEFAULT_SEEDS, DEFAULT_PHYSICS_SYMMETRY_WEIGHT, DEFAULT_PHYSICS_OBSERVABLE_WEIGHT, EXACT_DIAGONALIZATION_MAX_QUBITS, DEFAULT_RUNTIME_OPTIMIZATION_LEVEL, ZNE_EXPONENTIAL_INITIAL_RATE, ZNE_CURVE_FIT_MAX_EVALS, NUMERIC_EPS, BUDGET_FALLBACK
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments:
  - DEFAULT_SPSA_LEARNING_RATE @ L12: `0.2`
  - DEFAULT_SPSA_PERTURBATION @ L13: `0.15`
  - DEFAULT_SPSA_ALPHA @ L14: `0.602`
  - DEFAULT_SPSA_GAMMA @ L15: `0.101`
  - DEFAULT_SPSA_STABILITY_RATIO @ L16: `0.1`
  - DEFAULT_BEHAVIOR_WEAK_FIELD_RATIO @ L18: `0.75`
  - DEFAULT_BEHAVIOR_NEAR_CRITICAL_RATIO @ L19: `1.25`
  - DEFAULT_BEHAVIOR_LOW_NOISE_THRESHOLD @ L20: `0.005`
  - DEFAULT_BEHAVIOR_MODERATE_NOISE_THRESHOLD @ L21: `0.01`
  - DEFAULT_BEHAVIOR_SYMMETRY_RISK_WEIGHT @ L22: `2.0`
  - DEFAULT_BEHAVIOR_OBSERVABLE_RISK_WEIGHT @ L23: `0.25`
  - DEFAULT_BEHAVIOR_UNCERTAINTY_RISK_WEIGHT @ L24: `0.5`
  - DEFAULT_GATE_ERROR @ L26: `0.01`
  - DEFAULT_T1 @ L27: `50.0`
  - DEFAULT_T2 @ L28: `70.0`
  - DEFAULT_GATE_TIME @ L29: `0.1`
  - DEFAULT_SEED @ L30: `42`
  - DEFAULT_DEPTH @ L35: `2`
  - DEFAULT_MAX_ITER @ L36: `100`
  - DEFAULT_VERIFICATION_SHOTS @ L37: `4096`
  - DEFAULT_PREFLIGHT_SHOTS @ L38: `256`
  - DEFAULT_BASE_SHOTS @ L39: `512`
  - DEFAULT_FINAL_SHOTS @ L40: `4096`
  - DEFAULT_ZNE_EXTRAPOLATOR @ L45: `'linear'`
  - DEFAULT_PHYSICAL_VALIDITY_TOL @ L46: `0.05`
  - DEFAULT_LOG_LEVEL @ L47: `'INFO'`
  - DEFAULT_OUTPUT_PREFIX @ L48: `'fieldline_vqe'`
  - DEFAULT_STUDY_OUTPUT_PREFIX @ L49: `'fieldline_study'`
  - DEFAULT_CROSSOVER_SYMMETRY_PENALTY @ L52: `2.0`
  - DEFAULT_CROSSOVER_OBSERVABLE_PENALTY @ L53: `0.25`
  - DEFAULT_SHOT_ALLOCATION @ L54: `'equal'`
  - DEFAULT_PHYSICS_SYMMETRY_WEIGHT @ L64: `2.0`
  - DEFAULT_PHYSICS_OBSERVABLE_WEIGHT @ L65: `0.25`
  - EXACT_DIAGONALIZATION_MAX_QUBITS @ L66: `10`
  - ZNE_EXPONENTIAL_INITIAL_RATE @ L68: `0.5`
  - ZNE_CURVE_FIT_MAX_EVALS @ L69: `10000`
  - NUMERIC_EPS @ L70: `1e-12`
  - BUDGET_FALLBACK @ L71: `1e+18`

## errors
- explicit __all__: True
- public symbols: SafeErrorEnvelope, SafeRuntimeError, safe_error, production_errors_enabled, production_console_logging_enabled, production_log_path, render_operator_error
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## executors
- explicit __all__: True
- public symbols: (none)
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## experiment
- explicit __all__: True
- public symbols: (none)
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## hamiltonian
- explicit __all__: True
- public symbols: (none)
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## interfaces
- explicit __all__: True
- public symbols: AnsatzFactory, HamiltonianFactory, NoiseModelFactory, RuntimeBridge, RecordAssembler, ExperimentService, BehaviorService, StudyService, PipelineRunner
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## logging_utils
- explicit __all__: True
- public symbols: (none)
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## metrics
- explicit __all__: True
- public symbols: (none)
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## noise
- explicit __all__: True
- public symbols: (none)
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## observables
- explicit __all__: True
- public symbols: (none)
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## pipeline
- explicit __all__: True
- public symbols: (none)
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## plotting
- explicit __all__: True
- public symbols: (none)
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## record_builder
- explicit __all__: True
- public symbols: (none)
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## results
- explicit __all__: True
- public symbols: (none)
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## runtime
- explicit __all__: True
- public symbols: (none)
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## secrets
- explicit __all__: True
- public symbols: SecretSnapshot, SecureSecretSnapshot, SecretsManager
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## secure_buffer
- explicit __all__: True
- public symbols: SecureBuffer
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## static_checks
- explicit __all__: True
- public symbols: SecretTypeViolation, find_secret_type_violations
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)

## study
- explicit __all__: True
- public symbols: (none)
- print lines: (none)
- debug markers: (none)
- import *: (none)
- internal imports: (none)
- hardcoded assignments: (none)
