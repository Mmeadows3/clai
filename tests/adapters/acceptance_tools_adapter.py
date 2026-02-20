"""Tools-directory adapter for high-level acceptance criteria."""

from __future__ import annotations

from pathlib import Path

import yaml

TOOL_SPEC_NAME = "TOOL.yaml"
SKIPPED_PATH_PART = "templates"
SUPPORTED_TOOL_TYPES = frozenset({"cli", "markdown", "prompt", "python"})


class ToolsDirectoryAdapter:
    """Counts tools from ``./tools`` using runtime-compatible filters."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    def count_supported_tools(self) -> int:
        count = 0
        for tool_file in (self._repo_root / "tools").rglob(TOOL_SPEC_NAME):
            if SKIPPED_PATH_PART in tool_file.parts:
                continue
            if self._tool_type(tool_file) in SUPPORTED_TOOL_TYPES:
                count += 1
        return count

    def _tool_type(self, tool_file: Path) -> str:
        spec = yaml.safe_load(tool_file.read_text(encoding="utf-8"))
        if not isinstance(spec, dict):
            return ""
        return str(spec.get("type") or "").strip().lower()
