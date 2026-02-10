"""Markdown-backed prompt tool mount adapter."""

from __future__ import annotations

from pathlib import Path

from tool_mounting.tool_runtime import CallToolFn
from .prompt import build_text_prompt_mount
from .types import LogFn, MountedTool, ToolSpec


def build_markdown_mount(
    tool: ToolSpec,
    tool_path: Path,
    _state: dict[str, Any],
    _call_tool: CallToolFn,
    log: LogFn,
) -> MountedTool | None:
    """Build one markdown-file-backed prompt mounted tool."""
    tool_name = str(tool.get("name") or "").strip()
    source = tool.get("source")
    if not isinstance(source, str) or not source.strip():
        log(f"[mcp-server] tool {tool_name} missing source for markdown")
        return None

    source_path = tool_path.parent / source
    if not source_path.exists():
        log(f"[mcp-server] tool {tool_name} markdown source not found: {source_path}")
        return None

    prompt_text = source_path.read_text(encoding="utf-8")
    return build_text_prompt_mount(
        tool,
        prompt_text=prompt_text,
        source_path=str(source_path),
        tool_kind="markdown",
    )


__all__ = ["build_markdown_mount"]
