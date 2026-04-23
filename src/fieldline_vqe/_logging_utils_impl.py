from __future__ import annotations

import logging
from pathlib import Path

_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

__all__ = ["configure_logging", "get_logger"]


def configure_logging(level: str = "INFO", *, console: bool = True, log_path: str | None = None) -> None:
    resolved = getattr(logging, level.upper(), logging.INFO)
    handlers: list[logging.Handler] = []
    if console:
        handlers.append(logging.StreamHandler())
    if log_path:
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))
    if not handlers:
        handlers = [logging.NullHandler()]
    logging.basicConfig(level=resolved, format=_FORMAT, force=True, handlers=handlers)
    logging.getLogger("qiskit").setLevel(max(logging.WARNING, resolved))
    logging.getLogger("matplotlib").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
