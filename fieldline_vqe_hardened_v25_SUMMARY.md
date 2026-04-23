# v25 continuation summary

## What changed

- added a clean release packaging path:
  - `tools_package_release.py`
  - creates a scrubbed release bundle from the working tree
  - excludes runtime residue such as `__pycache__`, `.pytest_cache`, generated baselines, prior audit outputs, and old release zips
- added a release verification path:
  - `tools_verify_release.py`
  - verifies the packaged bundle against the in-bundle `release_manifest.json`
  - checks for forbidden residue and hash mismatches
- release bundles now include canonical manifest names inside the zip:
  - `release_manifest.json`
  - `release_manifest.md`
  even when the outer artifact names are versioned
- extended `Makefile` with:
  - `package-release`
  - `verify-release`
- added regression coverage for:
  - packager residue exclusion
  - canonical manifest inclusion
  - release verification tamper detection

## What I validated

- `py_compile` on source, tests, and tooling: passed
- `tests/test_hardening.py` + `tests/test_config.py`: **26 passed**
- targeted execution regressions:
  - `test_single_run_smoke`
  - `test_tiny_noisy_study_smoke`
  both passed
- generated and verified a real clean release bundle:
  - `fieldline_vqe_release_v25.zip`
  - `release_manifest_v25.json`
  - `release_manifest_v25.md`
  - `release_verify_v25.json`
  - `release_verify_v25.md`
- release verification result: **ok = true**

## Why this pass matters

The repo was functionally hardened already, but the shipped tree still mixed source code with local run residue, old audit outputs, and generated artifacts. This pass hardens the release boundary itself: a clean bundle can now be built reproducibly, hashed, and verified before shipment.


## Quantum deepening before the senior pass

- added energy-variance diagnostics (`energy_variance`, `energy_stddev`, `relative_energy_stddev`) so runs can distinguish low-energy states from true near-eigenstates
- added site-resolved magnetization profiles and connected nearest-neighbor XX/ZZ correlators
- surfaced the new scalar diagnostics into run records and study aggregation outputs
- added regression coverage for exact-state variance collapse, connected-correlator sanity, and record export visibility
