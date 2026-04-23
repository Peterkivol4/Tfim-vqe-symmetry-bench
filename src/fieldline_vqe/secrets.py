from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

from .errors import safe_error
from .secure_buffer import SecureBuffer


@dataclass(frozen=True)
class SecretSnapshot:
    values: dict[str, str]

    def present(self, name: str) -> bool:
        return name in self.values

    def get(self, name: str) -> str:
        return self.values[name]

    def __repr__(self) -> str:
        keys = ", ".join(sorted(self.values))
        return f"SecretSnapshot(keys=[{keys}])"


class SecureSecretSnapshot:
    def __init__(self, values: dict[str, SecureBuffer]) -> None:
        self._values = values

    def present(self, name: str) -> bool:
        return name in self._values

    def get(self, name: str) -> SecureBuffer:
        return self._values[name]

    def close(self) -> None:
        for value in self._values.values():
            value.close()
        self._values.clear()

    def __repr__(self) -> str:
        keys = ", ".join(sorted(self._values))
        return f"SecureSecretSnapshot(keys=[{keys}])"


class SecretsManager:
    def __init__(self, required: Iterable[str] = ()) -> None:
        self._required = tuple(required)

    def _collect(self) -> dict[str, str]:
        values: dict[str, str] = {}
        missing = []
        for name in self._required:
            value = os.getenv(name)
            if value is None or value == "":
                missing.append(name)
                continue
            values[name] = value
        if missing:
            joined = ", ".join(sorted(missing))
            raise safe_error("CFG-ENV-001", "required environment configuration missing", detail=joined)
        return values

    def load(self) -> SecretSnapshot:
        return SecretSnapshot(values=self._collect())

    def load_secure(self) -> SecureSecretSnapshot:
        return SecureSecretSnapshot({name: SecureBuffer(value.encode("utf-8")) for name, value in self._collect().items()})

    def audit_presence(self) -> dict[str, bool]:
        return {name: bool(os.getenv(name)) for name in self._required}


__all__ = ["SecretSnapshot", "SecureSecretSnapshot", "SecretsManager"]
