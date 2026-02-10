"""Parsing helpers for ``TOOL.yaml`` tool specifications."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def parse_tool_yaml(
    tool_path: Path, log: Callable[[str], None] | None = None
) -> dict[str, Any] | None:
    """Read and parse one tool spec file, returning ``None`` on parse failure."""
    try:
        import yaml
    except Exception as exc:
        if log is not None:
            log(f"[mcp-server] yaml parser unavailable for {tool_path}: {exc}")
        return None

    text = tool_path.read_text(encoding="utf-8")
    if not text.strip():
        return None
    try:
        parsed = yaml.safe_load(text)
    except Exception as exc:
        if log is not None:
            log(f"[mcp-server] tool spec parse failed: {tool_path} ({exc})")
        return None
    if not isinstance(parsed, dict):
        if log is not None:
            log(
                "[mcp-server] tool spec parse failed: "
                f"{tool_path} (top-level YAML must be an object)"
            )
        return None
    return parsed


def iter_tool_spec_paths(
    tools_dir: Path,
    *,
    include_templates: bool = False,
) -> list[Path]:
    """Discover all TOOL spec file paths in deterministic order."""
    if not tools_dir.exists():
        return []

    tool_paths = list(tools_dir.rglob("TOOL.yaml")) + list(tools_dir.rglob("TOOL.yml"))
    resolved_paths = sorted({path.resolve() for path in tool_paths})
    if include_templates:
        return resolved_paths
    return [path for path in resolved_paths if "templates" not in path.parts]


def iter_tool_specs(
    tools_dir: Path,
    log: Callable[[str], None] | None = None,
    include_templates: bool = False,
) -> list[tuple[Path, dict[str, Any]]]:
    """Discover and parse all valid ``TOOL.yaml`` / ``TOOL.yml`` specs."""
    specs: list[tuple[Path, dict[str, Any]]] = []
    for tool_path in iter_tool_spec_paths(
        tools_dir,
        include_templates=include_templates,
    ):
        spec = parse_tool_yaml(tool_path, log=log)
        if not spec:
            continue
        specs.append((tool_path, spec))
    return specs
