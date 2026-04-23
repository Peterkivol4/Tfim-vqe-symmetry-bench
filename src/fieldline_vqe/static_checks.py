from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

__all__ = ["SecretTypeViolation", "find_secret_type_violations"]

_SUSPECT = ("key", "secret", "private", "seed", "nonce")


@dataclass(frozen=True)
class SecretTypeViolation:
    path: str
    line: int
    name: str
    value_kind: str


def _literal_kind(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return "str"
    if isinstance(node, ast.Constant) and isinstance(node.value, (bytes, bytearray)):
        return "bytes"
    return None


def find_secret_type_violations(paths: Iterable[str | Path]) -> list[SecretTypeViolation]:
    findings: list[SecretTypeViolation] = []
    for item in paths:
        path = Path(item)
        files = sorted(path.rglob("*.py")) if path.is_dir() else [path]
        for file_path in files:
            try:
                tree = ast.parse(file_path.read_text(), filename=str(file_path))
            except Exception:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assign):
                    continue
                kind = _literal_kind(node.value)
                if kind is None:
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        lowered = target.id.lower()
                        if any(token in lowered for token in _SUSPECT):
                            findings.append(SecretTypeViolation(str(file_path), int(node.lineno), target.id, kind))
    return findings
