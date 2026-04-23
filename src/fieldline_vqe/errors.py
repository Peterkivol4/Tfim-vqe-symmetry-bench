from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SafeErrorEnvelope:
    code: str
    operator_message: str
    detail: str | None = None


class SafeRuntimeError(RuntimeError):
    def __init__(self, envelope: SafeErrorEnvelope) -> None:
        super().__init__(f"{envelope.code}: {envelope.operator_message}")
        self.envelope = envelope


def safe_error(code: str, operator_message: str, detail: str | None = None, *, debug: bool = False) -> SafeRuntimeError:
    payload = SafeErrorEnvelope(code=code, operator_message=operator_message, detail=detail if debug else None)
    return SafeRuntimeError(payload)


def _truthy_env(name: str) -> bool:
    raw = os.getenv(name, "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def production_errors_enabled() -> bool:
    return _truthy_env("FIELDLINE_PRODUCTION_ERRORS")


def production_console_logging_enabled() -> bool:
    if _truthy_env("FIELDLINE_LOG_STDERR"):
        return True
    raw = os.getenv("FIELDLINE_LOG_STDERR", "")
    if raw.strip().lower() in {"0", "false", "no", "off"}:
        return False
    return not production_errors_enabled()


def production_log_path() -> str | None:
    raw = os.getenv("FIELDLINE_LOG_PATH", "").strip()
    return raw or None


def render_operator_error(exc: BaseException, *, fallback_code: str = "FLQ-UNEXPECTED-001", fallback_message: str = "run failed; inspect structured logs") -> str:
    if isinstance(exc, SafeRuntimeError):
        return f"{exc.envelope.code}: {exc.envelope.operator_message}"
    return f"{fallback_code}: {fallback_message}"


__all__ = [
    "SafeErrorEnvelope", "SafeRuntimeError", "safe_error", "production_errors_enabled", "production_console_logging_enabled",
    "production_log_path", "render_operator_error",
]
