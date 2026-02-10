"""Shared type contracts for tool mount adapters."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from tool_mounting.tool_runtime import CallToolFn, LogFn

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
else:
    FastMCP = Any

ToolSpec = dict[str, Any]
MountedTool = dict[str, Any]


ToolMountFn = Callable[
    [ToolSpec, Path, dict[str, Any], CallToolFn, LogFn], MountedTool | None
]


__all__ = [
    "FastMCP",
    "LogFn",
    "MountedTool",
    "ToolMountFn",
    "ToolSpec",
]
