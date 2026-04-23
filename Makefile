PYTHON ?= python

.PHONY: build-native audit-deps audit-surface baseline baseline-capture baseline-compare package-release verify-release test

build-native:
	$(PYTHON) tools_build_native.py

audit-deps:
	$(PYTHON) tools_audit_deps.py --json-out dependency_audit.json --md-out dependency_audit.md
	pip-audit -r requirements.txt
	pip-licenses --from=mixed

audit-surface:
	$(PYTHON) tools_audit_surface.py --json-out surface_audit.json --md-out surface_audit.md

baseline:
	PYTHONPATH=src $(PYTHON) -m fieldline_vqe.cli --mode single --n-qubits 4 --field-strength 1.0 --ansatz hardware_efficient --depth 1 --optimizer COBYLA --max-iter 2 --verification-shots 32 --output-prefix baseline_cli

baseline-capture:
	PYTHONPATH=src $(PYTHON) tools_capture_baseline.py --output-prefix baseline_capture

test:
	PYTHONPATH=src $(PYTHON) -m pytest -q

baseline-compare:
	$(PYTHON) tools_compare_baseline.py baseline_before.json baseline_after.json --json-out baseline_compare.json --md-out baseline_compare.md

package-release:
	$(PYTHON) tools_package_release.py --out-zip fieldline_vqe_release.zip --json-out release_manifest.json --md-out release_manifest.md

verify-release:
	$(PYTHON) tools_verify_release.py fieldline_vqe_release.zip --json-out release_verify.json --md-out release_verify.md
