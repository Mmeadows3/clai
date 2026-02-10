"""Shared runtime helpers for MCP tool mounting and execution."""

from __future__ import annotations

from typing import Any, Callable

LogFn = Callable[[str], None]
CallToolFn = Callable[[str, dict[str, Any] | None], Any]


def log_stdout(message: str) -> None:
    """Emit one flushed log line to stdout."""
    print(message, flush=True)


__all__ = [
    "CallToolFn",
    "LogFn",
    "log_stdout",
]
