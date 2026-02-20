"""Discover TOOL.yaml specs and wire them directly to FastMCP runners."""

from __future__ import annotations

from typing import Any

from tool_mounting.tool_runtime import CallToolFn, LogFn
from tool_mounting.tool_specs import iter_tool_specs
from .cli import build_cli_mount
from .markdown import build_markdown_mount
from .prompt import build_prompt_mount
from .python import build_python_mount
from .types import FastMCP, MountedTool, ToolMountFn, ToolSpec

GLOBAL_TOOL_HINT = (
    "If a user prefixes text with '~', interpret that as an explicit request "
    "to use MCP tools. Treat the token after '~' as a partial tool reference, "
    "search available tool names/descriptions for the best match, then call "
    "the canonical tool name."
)


TOOL_TYPE_MOUNTS: dict[str, ToolMountFn] = {
    "cli": build_cli_mount,
    "python": build_python_mount,
    "markdown": build_markdown_mount,
    "prompt": build_prompt_mount,
}
TOOL_SPEC_ERROR_MISSING_NAME = "missing_name"
TOOL_SPEC_ERROR_MISSING_TYPE = "missing_type"
TOOL_SPEC_ERROR_UNSUPPORTED_TYPE = "unsupported_type"


def validate_tool_spec(raw_spec: dict[str, Any]) -> tuple[ToolSpec | None, str | None]:
    """Normalize one parsed spec and return an error code when invalid."""
    spec: ToolSpec = dict(raw_spec)
    name = str(spec.get("name") or "").strip()
    if not name:
        return None, TOOL_SPEC_ERROR_MISSING_NAME

    tool_type = str(spec.get("type") or "").strip().lower()
    if not tool_type:
        return None, TOOL_SPEC_ERROR_MISSING_TYPE
    if tool_type not in TOOL_TYPE_MOUNTS:
        return None, TOOL_SPEC_ERROR_UNSUPPORTED_TYPE

    spec["name"] = name
    spec["type"] = tool_type
    spec["description"] = str(spec.get("description") or "")
    return spec, None


def tool_published_name(spec: ToolSpec) -> str:
    """Return the public MCP tool name after mount-specific normalization."""
    if str(spec.get("type") or "").strip().lower() == "cli":
        mcp_name = str(spec.get("mcp_name") or "").strip()
        if mcp_name:
            return mcp_name
    return str(spec.get("name") or "").strip()


def _register_mounted_tool(
    mcp: FastMCP,
    state: dict[str, Any],
    mounted: MountedTool,
) -> None:
    """Register one mounted tool with FastMCP and the runtime tool catalog."""
    existing_meta = mounted["meta"]
    merged_meta: dict[str, Any] = {"tool_usage_hint": GLOBAL_TOOL_HINT}
    if isinstance(existing_meta, dict):
        merged_meta.update(existing_meta)

    def _tool(input: Any = None) -> dict[str, Any]:
        payload = {} if input is None else input
        return mounted["runner"](payload)

    mcp.tool(
        name=mounted["name"],
        description=mounted["description"] or None,
        meta=merged_meta,
    )(_tool)
    state["tool_runner_registry"][mounted["name"]] = mounted["runner"]


def register_discovered_tools(
    mcp: FastMCP,
    state: dict[str, Any],
    call_tool: CallToolFn,
    log: LogFn,
) -> None:
    """Discover TOOL.yaml specs and mount each supported tool type."""
    published_name_to_path: dict[str, str] = {}

    for tool_path, raw_spec in iter_tool_specs(
        state["tools_dir"],
        log=log,
        include_templates=False,
    ):
        spec, error_code = validate_tool_spec(raw_spec)
        if error_code == TOOL_SPEC_ERROR_MISSING_NAME:
            log(f"[mcp-server] tool invalid (missing_name): {tool_path}")
            continue
        if error_code == TOOL_SPEC_ERROR_MISSING_TYPE:
            name = str(raw_spec.get("name") or "").strip() or "(missing_name)"
            log(f"[mcp-server] tool {name} invalid (missing_type): {tool_path}")
            continue
        if spec is None:
            name = str(raw_spec.get("name") or "").strip() or "(missing_name)"
            tool_type = str(raw_spec.get("type") or "").strip().lower() or "(missing_type)"
            log(
                "[mcp-server] tool "
                f"{name} skipped: I don't have a mount for that tool type ({tool_type})"
            )
            continue

        published_name = tool_published_name(spec)
        existing_path = published_name_to_path.get(published_name)
        if existing_path is not None:
            log(
                "[mcp-server] tool "
                f"{published_name} skipped: duplicate published name at {tool_path} "
                f"(already defined at {existing_path})"
            )
            continue
        published_name_to_path[published_name] = str(tool_path)

        tool_type = str(spec["type"])
        mount = TOOL_TYPE_MOUNTS[tool_type]
        mounted = mount(spec, tool_path, state, call_tool, log)
        if mounted is None:
            continue
        if mounted["name"] in state["tool_runner_registry"]:
            log(
                "[mcp-server] tool "
                f"{mounted['name']} skipped: duplicate mounted name at {tool_path}"
            )
            continue
        _register_mounted_tool(
            mcp,
            state,
            mounted,
        )

__all__ = [
    "TOOL_SPEC_ERROR_MISSING_NAME",
    "TOOL_SPEC_ERROR_MISSING_TYPE",
    "TOOL_SPEC_ERROR_UNSUPPORTED_TYPE",
    "TOOL_TYPE_MOUNTS",
    "register_discovered_tools",
    "tool_published_name",
    "validate_tool_spec",
]
