# Dependency audit

## Third-party surface

- seen: matplotlib, numpy, qiskit, qiskit_aer, qiskit_algorithms, qiskit_ibm_runtime, scipy
- missing from requirements: (none)

## Requirement pin audit

### requirements.txt
- exact pins: matplotlib==3.10.8, numpy==2.3.5, qiskit-aer==0.17.2, qiskit-algorithms==0.4.0, qiskit==2.3.1, scipy==1.17.0
- includes: (none)
- non-exact pins: (none)

### requirements-runtime.txt
- exact pins: qiskit-ibm-runtime==0.46.1
- includes: (none)
- non-exact pins: (none)

### requirements-dev.txt
- exact pins: pip-audit==2.9.0, pip-licenses==5.0.0, pytest==8.4.1
- includes: requirements-runtime.txt, requirements.txt
- non-exact pins: (none)

## __init__
- stdlib: (none)
- third_party: (none)
- local: ansatz, behavior, config, constants, experiment, hamiltonian, interfaces, noise, secrets

## _ansatz_impl
- stdlib: __future__
- third_party: qiskit
- local: constants, interfaces

## _behavior_impl
- stdlib: __future__, collections, csv, json, math, pathlib, statistics, typing
- third_party: (none)
- local: config, interfaces

## _cli_impl
- stdlib: __future__, argparse, sys
- third_party: (none)
- local: config, constants, errors, logging_utils, pipeline

## _config_impl
- stdlib: __future__, dataclasses, typing, warnings
- third_party: (none)
- local: constants

## _executors_impl
- stdlib: __future__, dataclasses, typing
- third_party: numpy, qiskit, qiskit_algorithms, scipy
- local: config, logging_utils, metrics, observables

## _experiment_impl
- stdlib: __future__, dataclasses, json, pathlib, threading, time, typing
- third_party: numpy, qiskit, qiskit_aer, scipy
- local: config, constants, executors, interfaces, logging_utils, metrics, noise, observables, plotting, record_builder, results, runtime

## _hamiltonian_impl
- stdlib: __future__, typing
- third_party: numpy, qiskit
- local: constants, interfaces

## _logging_utils_impl
- stdlib: __future__, logging, pathlib
- third_party: (none)
- local: (none)

## _metrics_impl
- stdlib: __future__, typing
- third_party: (none)
- local: _native_bridge

## _native_bridge
- stdlib: __future__, ctypes, os, pathlib, platform
- third_party: (none)
- local: (none)

## _noise_impl
- stdlib: __future__
- third_party: qiskit_aer
- local: config, constants, interfaces

## _observables_impl
- stdlib: __future__, dataclasses, typing
- third_party: numpy, qiskit
- local: (none)

## _pipeline_impl
- stdlib: __future__, pathlib
- third_party: (none)
- local: ansatz, config, experiment, hamiltonian, logging_utils, study

## _plotting_impl
- stdlib: __future__, pathlib, typing
- third_party: matplotlib
- local: results

## _record_builder_impl
- stdlib: __future__, typing
- third_party: (none)
- local: interfaces, results

## _results_impl
- stdlib: __future__, dataclasses, typing
- third_party: (none)
- local: (none)

## _runtime_impl
- stdlib: __future__, typing
- third_party: qiskit, qiskit_ibm_runtime
- local: interfaces

## _study_impl
- stdlib: __future__, collections, concurrent, csv, dataclasses, json, pathlib, statistics, typing
- third_party: (none)
- local: ansatz, behavior, config, experiment, hamiltonian, interfaces, logging_utils, plotting

## ansatz
- stdlib: __future__, sys
- third_party: (none)
- local: (none)

## behavior
- stdlib: __future__, sys
- third_party: (none)
- local: (none)

## cli
- stdlib: __future__, sys
- third_party: (none)
- local: (none)

## config
- stdlib: __future__, sys
- third_party: (none)
- local: (none)

## constants
- stdlib: __future__
- third_party: (none)
- local: (none)

## errors
- stdlib: __future__, dataclasses, os
- third_party: (none)
- local: (none)

## executors
- stdlib: __future__, sys
- third_party: (none)
- local: (none)

## experiment
- stdlib: __future__, sys
- third_party: (none)
- local: (none)

## hamiltonian
- stdlib: __future__, sys
- third_party: (none)
- local: (none)

## interfaces
- stdlib: __future__, abc, typing
- third_party: qiskit
- local: config, results

## logging_utils
- stdlib: __future__, sys
- third_party: (none)
- local: (none)

## metrics
- stdlib: __future__, sys
- third_party: (none)
- local: (none)

## noise
- stdlib: __future__, sys
- third_party: (none)
- local: (none)

## observables
- stdlib: __future__, sys
- third_party: (none)
- local: (none)

## pipeline
- stdlib: __future__, sys
- third_party: (none)
- local: (none)

## plotting
- stdlib: __future__, sys
- third_party: (none)
- local: (none)

## record_builder
- stdlib: __future__, sys
- third_party: (none)
- local: (none)

## results
- stdlib: __future__, sys
- third_party: (none)
- local: (none)

## runtime
- stdlib: __future__, sys
- third_party: (none)
- local: (none)

## secrets
- stdlib: __future__, dataclasses, os, typing
- third_party: (none)
- local: errors, secure_buffer

## secure_buffer
- stdlib: __future__, ctypes, os, typing
- third_party: (none)
- local: (none)

## static_checks
- stdlib: __future__, ast, dataclasses, pathlib, typing
- third_party: (none)
- local: (none)

## study
- stdlib: __future__, sys
- third_party: (none)
- local: (none)
