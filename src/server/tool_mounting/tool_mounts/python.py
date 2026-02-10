"""Python tool mount adapter."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from tool_mounting.tool_runtime import CallToolFn
from .types import LogFn, MountedTool, ToolSpec


def build_python_mount(
    tool: ToolSpec,
    tool_path: Path,
    _state: dict[str, Any],
    call_tool: CallToolFn,
    log: LogFn,
) -> MountedTool | None:
    """Build one mounted python tool file with a run(input, tools, cwd) entrypoint."""
    tool_name = str(tool.get("name") or "").strip()
    source = tool.get("source")
    if not isinstance(source, str) or not source.strip():
        log(f"[mcp-server] tool {tool_name} missing source for python")
        return None
    source_path = tool_path.parent / source
    if not source_path.exists():
        log(f"[mcp-server] tool {tool_name} python source not found: {source_path}")
        return None

    def _load_tool_module(module_path: Path) -> Any:
        """Load one Python file as a module object."""
        module_name = f"tool_module_{abs(hash(str(module_path)))}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load tool module: {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _result_text(value: Any) -> str:
        """Extract one text value from a nested tool result payload."""
        if isinstance(value, dict):
            stdout = value.get("stdout")
            text = value.get("text")
            stderr = value.get("stderr")
            if isinstance(stdout, str):
                return stdout
            if isinstance(text, str):
                return text
            if isinstance(stderr, str):
                return stderr
        return str(value)

    def _run_python_tool(payload: dict[str, Any]) -> Any:
        """Load and execute one Python tool module's ``run`` entrypoint."""
        module = _load_tool_module(source_path)
        runner = getattr(module, "run", None)
        if not callable(runner):
            raise ValueError(f"Tool module missing run() in {source_path}")

        def _nushell_via_cli(script: str, env: dict[str, str] | None = None) -> str:
            """Execute Nushell through the regular ``cli.nu`` tool."""
            if env:
                raise ValueError("tools.nushell does not support env overrides")
            if not isinstance(script, str) or not script.strip():
                raise ValueError("script is required")
            result = call_tool("cli.nu", {"args": ["-c", script]})
            return _result_text(result)

        tools = {
            "nushell": _nushell_via_cli,
            "call_tool": call_tool,
        }
        return runner(payload, tools, source_path.parent)

    def _tool_runner(input: Any = None) -> dict[str, Any]:
        """Execute one Python tool and normalize non-dict results."""
        if input is None:
            payload: Any = {}
        elif isinstance(input, dict):
            payload = input
        elif isinstance(input, str):
            payload = {"input": input}
        else:
            raise ValueError("input must be an object or string when provided")
        result = _run_python_tool(payload)
        if not isinstance(result, dict):
            result = {"result": result}
        return result

    return {
        "name": tool_name,
        "description": str(tool.get("description") or ""),
        "inputs_desc": tool.get("inputs"),
        "outputs_desc": tool.get("outputs"),
        "meta": None,
        "runner": _tool_runner,
        "source": source,
        "source_path": str(source_path),
    }


__all__ = ["build_python_mount"]

