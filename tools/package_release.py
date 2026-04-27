from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / 'release' / 'fieldline_vqe_release.zip'
DEFAULT_STAGE = ROOT / '.release_stage'
DEFAULT_MANIFEST_JSON = ROOT / 'release' / 'release_manifest.json'
DEFAULT_MANIFEST_MD = ROOT / 'release' / 'release_manifest.md'

REQUIRED_TOP = [
    'README.md',
    'pyproject.toml',
    'requirements.txt',
    'requirements-runtime.txt',
    'requirements-dev.txt',
    'Makefile',
    'DEPENDENCIES.md',
]

EXCLUDE_DIRS = {
    '__pycache__',
    '.pytest_cache',
    '.mypy_cache',
    '.ruff_cache',
    '.release_stage',
    'audit',
    'release',
    'baseline_capture_artifacts',
    'baseline_before_seeded_artifacts',
    'baseline_after_seeded_artifacts',
}
EXCLUDE_SUFFIXES = {'.pyc', '.pyo', '.zip'}
EXCLUDE_PATTERNS = ('release_manifest*.json', 'release_manifest*.md', 'release_verify*.json', 'release_verify*.md', 'fieldline_vqe_release*.zip')

EXCLUDE_NAMES = {
    'baseline.json', 'baseline_after.json', 'baseline_before_seeded.json', 'baseline_after_seeded.json',
    'baseline_capture.json', 'continue_baseline.json', 'surface_audit.json', 'surface_audit.md',
    'dependency_audit.json', 'dependency_audit.md', 'dependency_audit_v24.json', 'dependency_audit_v24.md',
    'baseline_compare_v24.json', 'baseline_compare_v24.md', 'STEP1_AUDIT.md', 'FINAL_AUDIT.md',
    '_after_single.json', '_after_single.png', '_after_study.json', '_after_study_raw.csv', '_after_study_summary.csv',
    '_after_study_crossover.csv', '_after_study_behavior.json', '_after_study_behavior_report.md',
    '_after_study_behavior_regimes.csv', '_after_study_behavior_ansatz.csv', '_after_study_behavior_optimizers.csv',
    '_after_study_behavior_crossover.csv', '_after_study.png', 'continue_baseline_single.json', 'continue_baseline_single.png',
    'continue_baseline_study.json', 'continue_baseline_study_raw.csv', 'continue_baseline_study_summary.csv',
    'continue_baseline_study_crossover.csv', 'continue_baseline_study_behavior.json', 'continue_baseline_study_behavior_report.md',
    'continue_baseline_study_behavior_regimes.csv', 'continue_baseline_study_behavior_ansatz.csv',
    'continue_baseline_study_behavior_optimizers.csv', 'continue_baseline_study_behavior_crossover.csv',
    'continue_baseline_study.png', 'continue_baseline_zne.json', 'continue_baseline_zne.png',
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _include(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        return False
    if any(part.startswith('.') and part not in {'.gitignore'} for part in rel.parts):
        return False
    if any(part.startswith('.venv') or part.startswith('.mplconfig') for part in rel.parts):
        return False
    if any(part.startswith('tmp_') for part in rel.parts):
        return False
    if path.name in EXCLUDE_NAMES:
        return False
    if any(path.match(pattern) for pattern in EXCLUDE_PATTERNS):
        return False
    if path.suffix in EXCLUDE_SUFFIXES:
        return False
    if path.name.startswith('.') and path.name not in {'.gitignore'}:
        return False
    return path.is_file()


def staged_files(root: Path) -> list[Path]:
    picked: list[Path] = []
    for path in root.rglob('*'):
        if _include(path, root):
            picked.append(path)
    return sorted(picked)


def build_manifest(root: Path, files: list[Path]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total_bytes = 0
    for path in files:
        rel = path.relative_to(root).as_posix()
        size = path.stat().st_size
        total_bytes += size
        rows.append({
            'path': rel,
            'sha256': _sha256(path),
            'bytes': size,
        })
    missing_required = [name for name in REQUIRED_TOP if not (root / name).exists()]
    return {
        'root': str(root),
        'file_count': len(rows),
        'total_bytes': total_bytes,
        'missing_required': missing_required,
        'files': rows,
    }


def stage_release(root: Path, stage_dir: Path) -> dict[str, Any]:
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True)
    files = staged_files(root)
    manifest = build_manifest(root, files)
    for path in files:
        rel = path.relative_to(root)
        dst = stage_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
    return manifest


def write_manifest_md(report: dict[str, Any], out: Path) -> None:
    lines = ['# Release manifest', '']
    lines.append(f"- file_count: {report['file_count']}")
    lines.append(f"- total_bytes: {report['total_bytes']}")
    lines.append(f"- missing_required: {report['missing_required'] or '(none)'}")
    lines.append('')
    for row in report['files']:
        lines.append(f"- `{row['path']}` | {row['bytes']} bytes | `{row['sha256']}`")
    out.write_text('\n'.join(lines))


def zip_stage(stage_dir: Path, out_zip: Path) -> None:
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    if out_zip.exists():
        out_zip.unlink()
    with zipfile.ZipFile(out_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(stage_dir.rglob('*')):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(stage_dir).as_posix())


def main() -> None:
    parser = argparse.ArgumentParser(description='Create a clean release bundle and manifest.')
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--stage-dir', type=Path, default=DEFAULT_STAGE)
    parser.add_argument('--out-zip', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--json-out', type=Path, default=DEFAULT_MANIFEST_JSON)
    parser.add_argument('--md-out', type=Path, default=DEFAULT_MANIFEST_MD)
    args = parser.parse_args()

    report = stage_release(args.root, args.stage_dir)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_manifest_md(report, args.md_out)
    canonical_json = args.stage_dir / 'release_manifest.json'
    canonical_md = args.stage_dir / 'release_manifest.md'
    shutil.copy2(args.json_out, args.stage_dir / args.json_out.name)
    shutil.copy2(args.md_out, args.stage_dir / args.md_out.name)
    if canonical_json.name != args.json_out.name:
        shutil.copy2(args.json_out, canonical_json)
    if canonical_md.name != args.md_out.name:
        shutil.copy2(args.md_out, canonical_md)
    zip_stage(args.stage_dir, args.out_zip)
    shutil.rmtree(args.stage_dir)


if __name__ == '__main__':
    main()
