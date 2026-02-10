"""Register tools defined under ``/tools`` using the mount adapters."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
else:
    FastMCP = Any

from tool_mounting.tool_mounts.registry import register_discovered_tools
from tool_mounting.tool_runtime import LogFn, log_stdout


def _disable_tool_name_validation() -> None:
    """Disable MCP tool name validation and warning emission."""

    def _always_valid(_name: str) -> bool:
        return True

    try:
        from mcp.shared import tool_name_validation as shared_validation

        def _always_valid_result(_name: str) -> Any:
            return shared_validation.ToolNameValidationResult(is_valid=True, warnings=[])

        shared_validation.validate_tool_name = _always_valid_result
        shared_validation.issue_tool_name_warning = lambda _name, _warnings: None
        shared_validation.validate_and_warn_tool_name = _always_valid
        logging.getLogger("mcp.shared.tool_name_validation").setLevel(logging.ERROR)
    except Exception:
        pass

    try:
        from mcp.server.fastmcp.tools import base as fastmcp_tools_base

        fastmcp_tools_base.validate_and_warn_tool_name = _always_valid
    except Exception:
        pass

    try:
        from mcp.server.lowlevel import server as lowlevel_server

        lowlevel_server.validate_and_warn_tool_name = _always_valid
    except Exception:
        pass


def register_configured_tools(
    mcp: FastMCP,
    state: dict[str, Any],
    log: LogFn = log_stdout,
) -> None:
    """Mount all TOOL.yaml-defined tools into FastMCP and runtime registry."""
    _disable_tool_name_validation()

    def _call_tool(name: str, input: dict[str, Any] | None = None) -> Any:
        """Run another registered tool and return its structured response."""
        tool = state["tool_runner_registry"].get(name)
        if tool is None:
            raise ValueError(f"unknown tool: {name}")
        return tool(input)

    register_discovered_tools(
        mcp=mcp,
        state=state,
        call_tool=_call_tool,
        log=log,
    )


__all__ = [
    "log_stdout",
    "register_configured_tools",
]
