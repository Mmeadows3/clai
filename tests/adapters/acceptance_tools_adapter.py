"""Tools-directory adapter for high-level acceptance criteria."""

from __future__ import annotations

from pathlib import Path

import yaml


class ToolsDirectoryAdapter:
    """Counts tools from ``./tools`` using runtime-compatible filters."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    def count_supported_tools(self) -> int:
        supported_types = {"cli", "markdown", "prompt", "python"}
        count = 0
        for tool_file in (self._repo_root / "tools").rglob("TOOL.yaml"):
            if "templates" in tool_file.parts:
                continue
            spec = yaml.safe_load(tool_file.read_text(encoding="utf-8"))
            tool_type = str(spec.get("type") or "").strip().lower() if isinstance(spec, dict) else ""
            if tool_type in supported_types:
                count += 1
        return count
