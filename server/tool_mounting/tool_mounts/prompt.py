"""Prompt tool mount adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tool_mounting.tool_runtime import CallToolFn
from .types import LogFn, MountedTool, ToolSpec

PROMPT_TOOL_RESPONSE_HINT = (
    "Tool behavior: this tool does not execute the task. "
    "It only returns instructions for you (the calling LM) to follow using other tools."
)

PROMPT_TOOL_META_HINT = (
    "Prompt/markdown tool: treat `text` as execution instructions, not a final answer."
)


def build_text_prompt_mount(
    tool: ToolSpec,
    *,
    prompt_text: str,
    source_path: str,
    tool_kind: str,
) -> MountedTool:
    """Build one prompt-like mounted tool backed by text content."""
    tool_name = str(tool.get("name") or "").strip()

    def _tool_runner(input: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return prompt source text with the supplied structured input."""
        payload = input or {}
        prompt = (
            f"{PROMPT_TOOL_RESPONSE_HINT}\n\n"
            f"{prompt_text}\n\n---\ninput: {json.dumps(payload, ensure_ascii=True)}"
        )
        return {"text": prompt, "input": payload, "type": tool_kind}

    return {
        "name": tool_name,
        "description": str(tool.get("description") or ""),
        "inputs_desc": tool.get("inputs"),
        "outputs_desc": tool.get("outputs"),
        "meta": {"prompt_tool_hint": PROMPT_TOOL_META_HINT},
        "runner": _tool_runner,
        "source": tool.get("source"),
        "source_path": source_path,
    }


def build_prompt_mount(
    tool: ToolSpec,
    tool_path: Path,
    _state: dict[str, Any],
    _call_tool: CallToolFn,
    log: LogFn,
) -> MountedTool | None:
    """Build one inline prompt mounted tool."""
    tool_name = str(tool.get("name") or "").strip()
    source = tool.get("source")
    if not isinstance(source, str) or not source.strip():
        log(f"[mcp-server] tool {tool_name} missing source for prompt")
        return None
    return build_text_prompt_mount(
        tool,
        prompt_text=source,
        source_path=str(tool_path),
        tool_kind="prompt",
    )


__all__ = ["build_prompt_mount", "build_text_prompt_mount"]

