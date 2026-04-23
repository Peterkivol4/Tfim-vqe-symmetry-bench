# v22 continuation summary

## What changed

- Added explicit `__all__` and doc forwarding in every public wrapper module (`ansatz.py`, `behavior.py`, `cli.py`, `config.py`, `executors.py`, `experiment.py`, `hamiltonian.py`, `logging_utils.py`, `metrics.py`, `noise.py`, `observables.py`, `pipeline.py`, `plotting.py`, `record_builder.py`, `results.py`, `runtime.py`, `study.py`).
- Added `tools_audit_surface.py` so the package surface/debug residue audit can be regenerated instead of living only as a static markdown artifact.
- Added `Makefile` targets:
  - `audit-surface`
  - `baseline`
  - existing `build-native`, `audit-deps`, `test`
- Added regression tests for:
  - explicit wrapper export contracts
  - audit tool report generation

## What I validated

- `py_compile` on `src/` and `tests/`: passed
- `tests/test_hardening.py` and `tests/test_config.py`: 17 passed
- targeted execution regressions:
  - `test_single_run_smoke`
  - `test_tiny_noisy_study_smoke`
  - `test_runtime_transpile_uses_final_layout_for_observables`
  all passed
- generated fresh `surface_audit.json` and `surface_audit.md`

## Why this pass matters

v21 added hardening mechanisms, but the public wrapper layer was still source-level opaque and the audit process was not repeatable. This pass makes the public/export boundary explicit and turns the surface audit into an actual tool rather than a one-off document.
