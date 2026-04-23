from __future__ import annotations

import argparse
import re
import json
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

DEFAULT_IGNORE_PATTERNS = (
    'config.run_spec.output_prefix',
    'config.output_prefix',
    'results.*.execution_time',
    'rows.#.execution_time',
    'aggregate.#.mean_execution_time',
    'aggregate.#.std_execution_time',
    'behavior.report_markdown',
    'report_markdown',
)


def _normalized_path(path: str) -> str:
    return re.sub(r'\[\d+\]', '.#', path)


def _ignored(path: str, ignore_patterns: tuple[str, ...]) -> bool:
    normalized = _normalized_path(path)
    return any(fnmatch(normalized, pattern) for pattern in ignore_patterns)


def _walk(prefix: str, left: Any, right: Any, *, tol: float, ignore_patterns: tuple[str, ...], out: list[dict[str, Any]]) -> None:
    if prefix and _ignored(prefix, ignore_patterns):
        return
    if isinstance(left, dict) and isinstance(right, dict):
        keys = sorted(set(left) | set(right))
        for key in keys:
            if key not in left or key not in right:
                path = f'{prefix}.{key}' if prefix else key
                if not _ignored(path, ignore_patterns):
                    out.append({'path': path, 'kind': 'missing', 'left': key in left, 'right': key in right})
                continue
            _walk(f'{prefix}.{key}' if prefix else key, left[key], right[key], tol=tol, ignore_patterns=ignore_patterns, out=out)
        return
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            out.append({'path': prefix, 'kind': 'length', 'left': len(left), 'right': len(right)})
            return
        for idx, (a, b) in enumerate(zip(left, right)):
            _walk(f'{prefix}[{idx}]', a, b, tol=tol, ignore_patterns=ignore_patterns, out=out)
        return
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        if abs(float(left) - float(right)) > tol:
            out.append({'path': prefix, 'kind': 'numeric', 'left': left, 'right': right, 'delta': abs(float(left) - float(right))})
        return
    if left != right:
        out.append({'path': prefix, 'kind': 'value', 'left': left, 'right': right})


def compare(left_path: Path, right_path: Path, *, tol: float = 1e-12, ignore_patterns: tuple[str, ...] = DEFAULT_IGNORE_PATTERNS) -> dict[str, Any]:
    left = json.loads(left_path.read_text())
    right = json.loads(right_path.read_text())
    diffs: list[dict[str, Any]] = []
    _walk('', left, right, tol=tol, ignore_patterns=ignore_patterns, out=diffs)
    return {
        'left': str(left_path),
        'right': str(right_path),
        'tolerance': tol,
        'ignore_patterns': list(ignore_patterns),
        'match': not diffs,
        'diff_count': len(diffs),
        'diffs': diffs,
    }


def write_markdown(report: dict[str, Any], out: Path) -> None:
    lines = ['# Baseline comparison', '']
    lines.append(f"- left: {report['left']}")
    lines.append(f"- right: {report['right']}")
    lines.append(f"- tolerance: {report['tolerance']}")
    lines.append(f"- match: {report['match']}")
    lines.append(f"- diff_count: {report['diff_count']}")
    lines.append('')
    for row in report['diffs'][:200]:
        lines.append(f"- {row['path']} | {row['kind']} | left={row.get('left')} | right={row.get('right')}")
    out.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description='Compare two baseline JSON payloads.')
    parser.add_argument('left', type=Path)
    parser.add_argument('right', type=Path)
    parser.add_argument('--tolerance', type=float, default=1e-12)
    parser.add_argument('--ignore-pattern', dest='ignore_patterns', action='append', default=None)
    parser.add_argument('--json-out', type=Path, default=Path('baseline_compare.json'))
    parser.add_argument('--md-out', type=Path, default=Path('baseline_compare.md'))
    args = parser.parse_args()
    ignore_patterns = tuple(args.ignore_patterns) if args.ignore_patterns else DEFAULT_IGNORE_PATTERNS
    report = compare(args.left, args.right, tol=args.tolerance, ignore_patterns=ignore_patterns)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_markdown(report, args.md_out)
    raise SystemExit(0 if report['match'] else 1)


if __name__ == '__main__':
    main()
