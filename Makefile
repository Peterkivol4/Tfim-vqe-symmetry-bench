PYTHON ?= python

.PHONY: build-native audit-deps audit-surface baseline baseline-capture baseline-compare package-release verify-release test

build-native:
	$(PYTHON) tools/build_native.py

audit-deps:
	$(PYTHON) tools/audit_deps.py --json-out audit/dependency_audit.json --md-out audit/dependency_audit.md
	pip-audit -r requirements.txt
	pip-licenses --from=mixed

audit-surface:
	$(PYTHON) tools/audit_surface.py --json-out audit/surface_audit.json --md-out audit/surface_audit.md

baseline:
	PYTHONPATH=src $(PYTHON) -m fieldline_vqe.cli --mode single --n-qubits 4 --field-strength 1.0 --ansatz hardware_efficient --depth 1 --optimizer COBYLA --max-iter 2 --verification-shots 32 --output-prefix baseline_cli

baseline-capture:
	PYTHONPATH=src $(PYTHON) tools/capture_baseline.py --output-prefix results/baselines/baseline_capture

test:
	PYTHONPATH=src $(PYTHON) -m pytest -q

baseline-compare:
	$(PYTHON) tools/compare_baseline.py baseline_before.json baseline_after.json --json-out audit/baseline_compare.json --md-out audit/baseline_compare.md

package-release:
	$(PYTHON) tools/package_release.py --out-zip release/fieldline_vqe_release.zip --json-out release/release_manifest.json --md-out release/release_manifest.md

verify-release:
	$(PYTHON) tools/verify_release.py release/fieldline_vqe_release.zip --json-out release/release_verify.json --md-out release/release_verify.md
