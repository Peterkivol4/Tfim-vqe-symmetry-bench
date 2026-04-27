from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "src" / "fieldline_vqe"
DEFAULT_JSON_OUT = ROOT / "audit" / "surface_audit.json"
DEFAULT_MD_OUT = ROOT / "audit" / "surface_audit.md"

@dataclass
class ModuleAudit:
    module: str
    public_symbols: list[str]
    has_explicit_all: bool
    print_lines: list[int]
    debug_markers: list[str]
    import_star: list[str]
    internal_imports: list[str]
    hardcoded_assignments: list[dict[str, Any]]

def _module_name(path: Path) -> str:
    return path.stem

def _string(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return node.__class__.__name__

def _public_symbols(tree: ast.Module) -> tuple[list[str], bool]:
    explicit: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                        explicit = [elt.value for elt in node.value.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)]
                    return explicit, True
    inferred: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith('_'):
            inferred.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith('_'):
                    inferred.append(target.id)
    return sorted(dict.fromkeys(inferred)), False

def _is_meaningful_literal(node: ast.AST) -> bool:
    if not isinstance(node, ast.Constant):
        return False
    value = node.value
    if isinstance(value, (int, float)):
        return value not in {0, 1, -1}
    if isinstance(value, str):
        return len(value) >= 4 and not value.startswith('_')
    return False

def _collect_hardcoded(tree: ast.Module) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if _is_meaningful_literal(node.value):
                rows.append({'name': node.targets[0].id, 'value': _string(node.value), 'line': node.lineno})
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and _is_meaningful_literal(item.value):
                    rows.append({'name': f'{node.name}.{item.target.id}', 'value': _string(item.value), 'line': item.lineno})
                elif isinstance(item, ast.Assign) and len(item.targets) == 1 and isinstance(item.targets[0], ast.Name) and _is_meaningful_literal(item.value):
                    rows.append({'name': f'{node.name}.{item.targets[0].id}', 'value': _string(item.value), 'line': item.lineno})
    return rows

def _audit_module(path: Path) -> ModuleAudit:
    text = path.read_text()
    tree = ast.parse(text)
    public_symbols, has_all = _public_symbols(tree)
    print_lines: list[int] = []
    import_star: list[str] = []
    internal_imports: list[str] = []
    debug_markers: list[str] = []
    for needle in ('TODO', 'FIXME', 'HACK', 'breakpoint(', 'pdb.set_trace'):
        if needle in text:
            debug_markers.append(needle)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'print':
            print_lines.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ''
            if any(alias.name == '*' for alias in node.names):
                import_star.append(f'{mod}:{node.lineno}')
            if mod.startswith('.') and '._' in mod:
                internal_imports.append(f'{mod}:{node.lineno}')
    return ModuleAudit(module=_module_name(path), public_symbols=public_symbols, has_explicit_all=has_all, print_lines=sorted(print_lines), debug_markers=sorted(set(debug_markers)), import_star=sorted(import_star), internal_imports=sorted(internal_imports), hardcoded_assignments=_collect_hardcoded(tree))

def run_audit(package_root: Path = PKG) -> dict[str, Any]:
    modules = sorted(package_root.glob('*.py'))
    return {'package_root': str(package_root), 'modules': [asdict(_audit_module(path)) for path in modules]}

def write_markdown(report: dict[str, Any], out: Path) -> None:
    lines = ['# Surface audit', '']
    for mod in report['modules']:
        lines.append(f"## {mod['module']}")
        lines.append(f"- explicit __all__: {mod['has_explicit_all']}")
        lines.append(f"- public symbols: {', '.join(mod['public_symbols']) if mod['public_symbols'] else '(none)'}")
        lines.append(f"- print lines: {mod['print_lines'] or '(none)'}")
        lines.append(f"- debug markers: {', '.join(mod['debug_markers']) if mod['debug_markers'] else '(none)'}")
        lines.append(f"- import *: {', '.join(mod['import_star']) if mod['import_star'] else '(none)'}")
        lines.append(f"- internal imports: {', '.join(mod['internal_imports']) if mod['internal_imports'] else '(none)'}")
        if mod['hardcoded_assignments']:
            lines.append('- hardcoded assignments:')
            for row in mod['hardcoded_assignments']:
                lines.append(f"  - {row['name']} @ L{row['line']}: `{row['value']}`")
        else:
            lines.append('- hardcoded assignments: (none)')
        lines.append('')
    out.write_text('\n'.join(lines))

def main() -> None:
    parser = argparse.ArgumentParser(description='Audit fieldline_vqe package surface and debug residue.')
    parser.add_argument('--json-out', type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument('--md-out', type=Path, default=DEFAULT_MD_OUT)
    parser.add_argument('--package-root', type=Path, default=PKG)
    args = parser.parse_args()
    report = run_audit(args.package_root)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True))
    write_markdown(report, args.md_out)

if __name__ == '__main__':
    main()
