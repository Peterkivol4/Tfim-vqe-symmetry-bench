from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any

FORBIDDEN_PARTS = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'baseline_capture_artifacts', 'baseline_before_seeded_artifacts', 'baseline_after_seeded_artifacts'}
FORBIDDEN_SUFFIXES = {'.pyc', '.pyo'}
FORBIDDEN_NAMES = {'baseline.json', 'baseline_after.json', 'STEP1_AUDIT.md', 'FINAL_AUDIT.md', 'surface_audit.json', 'surface_audit.md'}


def _hash(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _collect_tree(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob('*') if p.is_file())


def verify_tree(root: Path) -> dict[str, Any]:
    files = _collect_tree(root)
    problems: list[str] = []
    for path in files:
        rel = path.relative_to(root)
        if any(part in FORBIDDEN_PARTS for part in rel.parts):
            problems.append(f'forbidden-dir:{rel.as_posix()}')
        if path.suffix in FORBIDDEN_SUFFIXES:
            problems.append(f'forbidden-suffix:{rel.as_posix()}')
        if path.name in FORBIDDEN_NAMES:
            problems.append(f'forbidden-name:{rel.as_posix()}')
    manifest_path = root / 'release_manifest.json'
    manifest_ok = False
    hash_mismatches: list[str] = []
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        expected = {row['path']: row['sha256'] for row in manifest.get('files', [])}
        for rel, digest in expected.items():
            fp = root / rel
            if not fp.exists():
                hash_mismatches.append(f'missing:{rel}')
                continue
            if _hash(fp) != digest:
                hash_mismatches.append(rel)
        manifest_ok = not hash_mismatches
    else:
        problems.append('missing:release_manifest.json')
    return {
        'root': str(root),
        'file_count': len(files),
        'problems': problems,
        'hash_mismatches': hash_mismatches,
        'manifest_ok': manifest_ok,
        'ok': not problems and manifest_ok,
    }


def verify(path: Path) -> dict[str, Any]:
    if path.is_dir():
        return verify_tree(path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        with zipfile.ZipFile(path) as zf:
            zf.extractall(tmp_root)
        return verify_tree(tmp_root)


def write_markdown(report: dict[str, Any], out: Path) -> None:
    lines = ['# Release verification', '']
    lines.append(f"- root: {report['root']}")
    lines.append(f"- file_count: {report['file_count']}")
    lines.append(f"- manifest_ok: {report['manifest_ok']}")
    lines.append(f"- ok: {report['ok']}")
    lines.append(f"- problems: {report['problems'] or '(none)'}")
    lines.append(f"- hash_mismatches: {report['hash_mismatches'] or '(none)'}")
    out.write_text('\n'.join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description='Verify a release bundle against its manifest.')
    parser.add_argument('path', type=Path)
    parser.add_argument('--json-out', type=Path, default=Path('release_verify.json'))
    parser.add_argument('--md-out', type=Path, default=Path('release_verify.md'))
    args = parser.parse_args()
    report = verify(args.path)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_markdown(report, args.md_out)
    raise SystemExit(0 if report['ok'] else 1)


if __name__ == '__main__':
    main()
