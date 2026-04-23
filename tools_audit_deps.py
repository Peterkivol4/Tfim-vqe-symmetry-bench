from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src' / 'fieldline_vqe'


@dataclass
class ModuleImportAudit:
    module: str
    stdlib: list[str]
    third_party: list[str]
    local: list[str]


def _req_names(path: Path) -> set[str]:
    names: set[str] = set()
    if not path.exists():
        return names
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or line.startswith('-r '):
            continue
        if '==' in line:
            line = line.split('==', 1)[0].strip()
        elif '[' in line:
            line = line.split('[', 1)[0].strip()
        if line:
            names.add(line.lower().replace('-', '_'))
    return names


def _parse_requirement_file(path: Path) -> dict[str, object]:
    if not path.exists():
        return {'file': str(path.name), 'exact_pins': [], 'non_exact_pins': [], 'includes': []}
    includes: list[str] = []
    exact: list[str] = []
    non_exact: list[str] = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('-r '):
            includes.append(line[3:].strip())
            continue
        target = exact if '==' in line and ';' not in line and ' @ ' not in line else non_exact
        target.append(line)
    return {'file': str(path.name), 'exact_pins': sorted(exact), 'non_exact_pins': sorted(non_exact), 'includes': sorted(includes)}


def _classify(mod: str | None, local_modules: set[str], stdlib: set[str]) -> tuple[str, str]:
    if not mod:
        return 'local', ''
    head = mod.split('.', 1)[0]
    if head in local_modules or head == 'fieldline_vqe':
        return 'local', head
    if head in stdlib:
        return 'stdlib', head
    return 'third_party', head


def run_audit(src: Path = SRC) -> dict[str, object]:
    local_modules = {p.stem for p in src.glob('*.py')}
    stdlib = set(sys.stdlib_module_names)
    rows: list[ModuleImportAudit] = []
    third_party_seen: set[str] = set()
    for path in sorted(src.glob('*.py')):
        tree = ast.parse(path.read_text(), filename=str(path))
        stdlib_mods: set[str] = set()
        third_party: set[str] = set()
        local: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    kind, head = _classify(alias.name, local_modules, stdlib)
                    if head:
                        {'stdlib': stdlib_mods, 'third_party': third_party, 'local': local}[kind].add(head)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    local.add(node.module or '')
                    continue
                kind, head = _classify(node.module, local_modules, stdlib)
                if head:
                    {'stdlib': stdlib_mods, 'third_party': third_party, 'local': local}[kind].add(head)
        third_party_seen |= third_party
        rows.append(ModuleImportAudit(path.stem, sorted(stdlib_mods), sorted(third_party), sorted(x for x in local if x)))
    req_runtime = _req_names(ROOT / 'requirements-runtime.txt')
    req_all = _req_names(ROOT / 'requirements.txt') | req_runtime
    missing = sorted(x for x in third_party_seen if x not in req_all)
    requirement_files = [
        _parse_requirement_file(ROOT / 'requirements.txt'),
        _parse_requirement_file(ROOT / 'requirements-runtime.txt'),
        _parse_requirement_file(ROOT / 'requirements-dev.txt'),
    ]
    non_exact = {row['file']: row['non_exact_pins'] for row in requirement_files if row['non_exact_pins']}
    return {
        'modules': [asdict(x) for x in rows],
        'third_party_seen': sorted(third_party_seen),
        'requirements_runtime': sorted(req_runtime),
        'requirements_all': sorted(req_all),
        'missing_from_requirements': missing,
        'requirement_files': requirement_files,
        'non_exact_requirement_pins': non_exact,
    }


def write_markdown(report: dict[str, object], out: Path) -> None:
    lines = ['# Dependency audit', '']
    lines.append('## Third-party surface')
    lines.append('')
    lines.append('- seen: ' + (', '.join(report['third_party_seen']) if report['third_party_seen'] else '(none)'))
    lines.append('- missing from requirements: ' + (', '.join(report['missing_from_requirements']) if report['missing_from_requirements'] else '(none)'))
    lines.append('')
    lines.append('## Requirement pin audit')
    lines.append('')
    for row in report['requirement_files']:
        lines.append(f"### {row['file']}")
        lines.append(f"- exact pins: {', '.join(row['exact_pins']) if row['exact_pins'] else '(none)'}")
        lines.append(f"- includes: {', '.join(row['includes']) if row['includes'] else '(none)'}")
        lines.append(f"- non-exact pins: {', '.join(row['non_exact_pins']) if row['non_exact_pins'] else '(none)'}")
        lines.append('')
    for row in report['modules']:
        lines.append(f"## {row['module']}")
        lines.append(f"- stdlib: {', '.join(row['stdlib']) if row['stdlib'] else '(none)'}")
        lines.append(f"- third_party: {', '.join(row['third_party']) if row['third_party'] else '(none)'}")
        lines.append(f"- local: {', '.join(row['local']) if row['local'] else '(none)'}")
        lines.append('')
    out.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description='Audit import/dependency surface for fieldline_vqe.')
    parser.add_argument('--json-out', type=Path, default=Path('dependency_audit.json'))
    parser.add_argument('--md-out', type=Path, default=Path('dependency_audit.md'))
    parser.add_argument('--src', type=Path, default=SRC)
    args = parser.parse_args()
    report = run_audit(args.src)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_markdown(report, args.md_out)


if __name__ == '__main__':
    main()
