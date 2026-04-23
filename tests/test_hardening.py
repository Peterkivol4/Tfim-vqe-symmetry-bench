from __future__ import annotations

from pathlib import Path

import pytest

from fieldline_vqe.metrics import SymmetryGate, parity_expectation
from fieldline_vqe.secure_buffer import SecureBuffer
from fieldline_vqe.secrets import SecretsManager
from fieldline_vqe.static_checks import find_secret_type_violations


def test_secure_buffer_redacts_and_blocks_copy() -> None:
    buf = SecureBuffer(b"abc")
    assert repr(buf) == "[REDACTED]"
    assert bytes(buf) == b"abc"
    with pytest.raises(TypeError):
        buf.__copy__()
    buf.close()
    assert len(buf) == 0


def test_secret_scan_flags_literal_secret_assignments(tmp_path: Path) -> None:
    src = tmp_path / "sample.py"
    src.write_text("api_secret = 'x'\nnonce_blob = b'abc'\nplain = 'ok'\n")
    findings = find_secret_type_violations([src])
    names = {(item.name, item.value_kind) for item in findings}
    assert ("api_secret", "str") in names
    assert ("nonce_blob", "bytes") in names


def test_secrets_manager_secure_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIELDLINE_TOKEN", "topsecret")
    snap = SecretsManager(["FIELDLINE_TOKEN"]).load_secure()
    try:
        assert snap.present("FIELDLINE_TOKEN")
        assert bytes(snap.get("FIELDLINE_TOKEN")) == b"topsecret"
        assert "topsecret" not in repr(snap)
    finally:
        snap.close()


def test_native_metric_fallback_matches_python() -> None:
    counts = {"00": 3.0, "11": 1.0, "01": 2.0}
    expected = (3.0 + 1.0 - 2.0) / 6.0
    assert abs(parity_expectation(counts) - expected) < 1e-12
    filtered = SymmetryGate.filter_by_x_parity(counts, sector=1)
    assert filtered == {"00": 3.0, "11": 1.0}


def test_public_wrappers_expose_explicit_all() -> None:
    import importlib

    names = [
        'fieldline_vqe.ansatz', 'fieldline_vqe.behavior', 'fieldline_vqe.cli', 'fieldline_vqe.config', 'fieldline_vqe.executors',
        'fieldline_vqe.experiment', 'fieldline_vqe.hamiltonian', 'fieldline_vqe.logging_utils', 'fieldline_vqe.metrics', 'fieldline_vqe.noise',
        'fieldline_vqe.observables', 'fieldline_vqe.pipeline', 'fieldline_vqe.plotting', 'fieldline_vqe.record_builder', 'fieldline_vqe.results',
        'fieldline_vqe.runtime', 'fieldline_vqe.study',
    ]
    for name in names:
        mod = importlib.import_module(name)
        assert hasattr(mod, '__all__')
        assert isinstance(mod.__all__, (list, tuple))


def test_surface_audit_tool_writes_reports(tmp_path: Path) -> None:
    import sys
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
    from tools_audit_surface import run_audit, write_markdown

    report = run_audit()
    assert report['modules']
    assert any(mod['module'] == 'errors' for mod in report['modules'])
    out = tmp_path / 'audit.md'
    write_markdown(report, out)
    text = out.read_text()
    assert '# Surface audit' in text
    assert '## errors' in text


def test_render_operator_error_hides_unexpected_detail() -> None:
    from fieldline_vqe.errors import render_operator_error, safe_error

    assert render_operator_error(ValueError("boom detail")) == "FLQ-UNEXPECTED-001: run failed; inspect structured logs"
    assert render_operator_error(safe_error("CFG-ENV-001", "required environment configuration missing")) == "CFG-ENV-001: required environment configuration missing"


def test_dependency_audit_tool_writes_reports(tmp_path: Path) -> None:
    import sys
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
    from tools_audit_deps import run_audit, write_markdown

    report = run_audit()
    assert 'modules' in report
    assert 'third_party_seen' in report
    out = tmp_path / 'deps.md'
    write_markdown(report, out)
    text = out.read_text()
    assert '# Dependency audit' in text
    assert '## Third-party surface' in text


def test_cli_production_mode_emits_operator_message_only(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    import sys
    from fieldline_vqe import cli as cli_mod

    def boom(_args):
        raise ValueError("boom detail")

    monkeypatch.setenv("FIELDLINE_PRODUCTION_ERRORS", "1")
    monkeypatch.delenv("FIELDLINE_LOG_STDERR", raising=False)
    monkeypatch.delenv("FIELDLINE_LOG_PATH", raising=False)
    monkeypatch.setattr(cli_mod, "_dispatch", boom)
    monkeypatch.setattr(sys, "argv", ["fieldline-vqe"])
    with pytest.raises(SystemExit) as exc:
        cli_mod.main()
    assert exc.value.code == 2
    err = capsys.readouterr().err.strip().splitlines()
    assert err == ["FLQ-UNEXPECTED-001: run failed; inspect structured logs"]


def test_cli_production_mode_can_log_to_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys) -> None:
    import sys
    from fieldline_vqe import cli as cli_mod

    def boom(_args):
        raise ValueError("boom detail")

    out = tmp_path / "ops" / "fieldline.log"
    monkeypatch.setenv("FIELDLINE_PRODUCTION_ERRORS", "1")
    monkeypatch.setenv("FIELDLINE_LOG_PATH", str(out))
    monkeypatch.delenv("FIELDLINE_LOG_STDERR", raising=False)
    monkeypatch.setattr(cli_mod, "_dispatch", boom)
    monkeypatch.setattr(sys, "argv", ["fieldline-vqe"])
    with pytest.raises(SystemExit):
        cli_mod.main()
    assert capsys.readouterr().err.strip() == "FLQ-UNEXPECTED-001: run failed; inspect structured logs"
    text = out.read_text()
    assert "fieldline cli failed" in text
    assert "ValueError" in text


def test_dependency_audit_reports_exact_pin_status() -> None:
    import sys
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
    from tools_audit_deps import run_audit

    report = run_audit()
    assert 'requirement_files' in report
    req = {row['file']: row for row in report['requirement_files']}
    assert 'requirements.txt' in req
    assert req['requirements.txt']['exact_pins']


def test_compare_baseline_tool_detects_mismatch(tmp_path: Path) -> None:
    import sys
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
    from tools_compare_baseline import compare

    a = tmp_path / 'a.json'
    b = tmp_path / 'b.json'
    a.write_text('{"single": {"energy": -1.0}}')
    b.write_text('{"single": {"energy": -1.1}}')
    report = compare(a, b, tol=1e-6)
    assert report['match'] is False
    assert report['diff_count'] == 1
    assert report['diffs'][0]['path'] == 'single.energy'


def test_compare_baseline_tool_ignores_volatile_paths_by_default(tmp_path: Path) -> None:
    import sys
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
    from tools_compare_baseline import compare

    left = tmp_path / 'left.json'
    right = tmp_path / 'right.json'
    left.write_text('{"config": {"run_spec": {"output_prefix": "tmp"}}, "results": {"trial": {"execution_time": 1.0}}, "behavior": {"report_markdown": "a"}}')
    right.write_text('{"config": {"run_spec": {"output_prefix": "baseline"}}, "results": {"trial": {"execution_time": 2.0}}, "behavior": {"report_markdown": "b"}}')
    report = compare(left, right)
    assert report['match'] is True
    assert report['diff_count'] == 0


def test_live_runtime_smoke_tool_prefers_configured_token_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import json
    import sys
    from pathlib import Path as _Path

    sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
    from tools_live_runtime_smoke import ordered_channels, resolve_runtime_token, write_report

    monkeypatch.delenv("FIELDLINE_IBM_RUNTIME_TOKEN", raising=False)
    monkeypatch.setenv("IBM_RUNTIME_TOKEN", "primary")
    monkeypatch.setenv("QISKIT_IBM_TOKEN", "fallback")

    assert ordered_channels("ibm_cloud")[0] == "ibm_cloud"
    env_name, token = resolve_runtime_token()
    assert env_name == "IBM_RUNTIME_TOKEN"
    assert token == "primary"

    out = tmp_path / "live_report.json"
    write_report({"submitted_ok": True, "comparison_ready": True}, out)
    assert json.loads(out.read_text())["comparison_ready"] is True


def test_release_packager_excludes_runtime_residue(tmp_path: Path) -> None:
    import sys
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
    from tools_package_release import stage_release

    root = tmp_path / 'repo'
    (root / 'src' / 'pkg').mkdir(parents=True)
    (root / 'src' / 'pkg' / '__init__.py').write_text('x = 1\n')
    (root / 'README.md').write_text('ok\n')
    (root / 'pyproject.toml').write_text('[build-system]\nrequires=[]\n')
    (root / 'requirements.txt').write_text('numpy==1.0\n')
    (root / 'requirements-runtime.txt').write_text('numpy==1.0\n')
    (root / 'requirements-dev.txt').write_text('pytest==1.0\n')
    (root / 'Makefile').write_text('test:\n\ttrue\n')
    (root / 'DEPENDENCIES.md').write_text('deps\n')
    (root / '__pycache__').mkdir()
    (root / '__pycache__' / 'junk.pyc').write_bytes(b'x')
    (root / 'baseline.json').write_text('{}')
    stage = tmp_path / 'stage'
    report = stage_release(root, stage)
    kept = {row['path'] for row in report['files']}
    assert 'baseline.json' not in kept
    assert '__pycache__/junk.pyc' not in kept
    assert 'src/pkg/__init__.py' in kept


def test_release_packager_excludes_local_temp_and_venv_residue(tmp_path: Path) -> None:
    import sys
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
    from tools_package_release import stage_release

    root = tmp_path / 'repo'
    (root / 'src' / 'pkg').mkdir(parents=True)
    (root / 'src' / 'pkg' / '__init__.py').write_text('x = 1\n')
    (root / 'README.md').write_text('ok\n')
    (root / 'pyproject.toml').write_text('[build-system]\nrequires=[]\n')
    (root / 'requirements.txt').write_text('numpy==1.0\n')
    (root / 'requirements-runtime.txt').write_text('numpy==1.0\n')
    (root / 'requirements-dev.txt').write_text('pytest==1.0\n')
    (root / 'Makefile').write_text('test:\n\ttrue\n')
    (root / 'DEPENDENCIES.md').write_text('deps\n')
    (root / '.venv' / 'bin').mkdir(parents=True)
    (root / '.venv' / 'bin' / 'python').write_text('shim\n')
    (root / '.venv_clean' / 'bin').mkdir(parents=True)
    (root / '.venv_clean' / 'bin' / 'python').write_text('shim\n')
    (root / '.mplconfig').mkdir()
    (root / '.mplconfig' / 'fontlist.json').write_text('{}\n')
    (root / '.hidden_cache').mkdir()
    (root / '.hidden_cache' / 'note.txt').write_text('cache\n')
    (root / 'tmp_runs').mkdir()
    (root / 'tmp_runs' / 'result.json').write_text('{}\n')
    (root / 'tmp_capture.json').write_text('{}\n')
    stage = tmp_path / 'stage'
    report = stage_release(root, stage)
    kept = {row['path'] for row in report['files']}
    assert '.venv/bin/python' not in kept
    assert '.venv_clean/bin/python' not in kept
    assert '.mplconfig/fontlist.json' not in kept
    assert '.hidden_cache/note.txt' not in kept
    assert 'tmp_runs/result.json' not in kept
    assert 'tmp_capture.json' not in kept
    assert 'src/pkg/__init__.py' in kept


def test_release_verify_detects_manifest_tamper(tmp_path: Path) -> None:
    import sys
    import json
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
    from tools_verify_release import verify_tree

    root = tmp_path / 'release'
    root.mkdir()
    (root / 'a.txt').write_text('alpha')
    manifest = {
        'files': [{'path': 'a.txt', 'sha256': '0' * 64, 'bytes': 5}]
    }
    (root / 'release_manifest.json').write_text(json.dumps(manifest))
    report = verify_tree(root)
    assert report['ok'] is False
    assert report['hash_mismatches'] == ['a.txt']


def test_release_packager_writes_canonical_manifest(tmp_path: Path) -> None:
    import sys
    import zipfile
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
    from tools_package_release import main as _unused
    from tools_package_release import ROOT
    import subprocess

    src = ROOT
    out_zip = tmp_path / 'bundle.zip'
    out_json = tmp_path / 'custom_manifest.json'
    out_md = tmp_path / 'custom_manifest.md'
    subprocess.run([sys.executable, str(ROOT / 'tools_package_release.py'), '--out-zip', str(out_zip), '--json-out', str(out_json), '--md-out', str(out_md)], check=True)
    with zipfile.ZipFile(out_zip) as zf:
        names = set(zf.namelist())
    assert 'release_manifest.json' in names
    assert 'release_manifest.md' in names
