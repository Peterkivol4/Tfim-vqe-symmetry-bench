# v24 continuation summary

## What changed

- fully separated operator-facing stderr from structured logging in production mode
  - `FIELDLINE_PRODUCTION_ERRORS=1` still enables the safe CLI boundary
  - `FIELDLINE_LOG_STDERR` now controls whether logs are allowed onto stderr in that mode
  - `FIELDLINE_LOG_PATH` can capture structured logs to a file while stderr stays operator-clean
- extended `errors.py` with:
  - `production_console_logging_enabled()`
  - `production_log_path()`
- upgraded `configure_logging()` so logging can be routed to:
  - console
  - file
  - null sink
- added `tools_compare_baseline.py`
  - compares two baseline JSON payloads recursively
  - exits nonzero on mismatch
  - writes both JSON and markdown reports
- extended `tools_audit_deps.py`
  - now audits requirement-file pin quality in addition to import surface
  - reports exact pins, includes, and any non-exact requirement entries
- extended `Makefile` with:
  - `baseline-compare`

## What I validated

- `py_compile` on source, tests, and tooling: passed
- `tests/test_hardening.py` + `tests/test_config.py`: **23 passed**
- targeted execution regressions:
  - `test_single_run_smoke`
  - `test_tiny_noisy_study_smoke`
  - `test_runtime_transpile_uses_final_layout_for_observables`
  all passed
- generated fresh:
  - `dependency_audit_v24.json`
  - `dependency_audit_v24.md`
  - `baseline_compare_v24.json`
  - `baseline_compare_v24.md`
- baseline compare result on the shipped before/after payloads: **match = true**

## Why this pass matters

v23 added an operator-safe CLI boundary, but standard logging could still land on stderr unless the environment was carefully controlled. This pass makes that boundary explicit and testable, and it adds a repeatable baseline-diff tool so equivalence is no longer asserted only by hand-written audit text.
