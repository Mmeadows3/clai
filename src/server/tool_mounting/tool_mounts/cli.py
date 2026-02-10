"""CLI tool mount adapter."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any
import shlex

from tool_mounting.tool_runtime import CallToolFn
from .types import LogFn, MountedTool, ToolSpec

CLI_TOOL_PRE_PROMPT = (
    "This is an MCP tool for running CLI commands. Use the man pages tool and "
    "tldr tool to find an accurate command that fits the prompt."
)


def build_cli_mount(
    tool: ToolSpec,
    tool_path: Path,
    _state: dict[str, Any],
    _call_tool: CallToolFn,
    log: LogFn,
) -> MountedTool | None:
    """Build one mounted CLI tool from a catalog entry."""
    tool_name = str(tool.get("name") or "").strip()
    command = str(tool.get("command") or "").strip()
    if not command:
        log(f"[mcp-server] tool {tool_name} missing command for cli")
        return None

    mcp_name = str(tool.get("mcp_name") or tool_name or f"cli.{command}").strip()
    description = str(
        tool.get("description")
        or f"Run `{command}` from the Nix CLI environment."
    )
    inputs_desc = tool.get("inputs") or {
        "args": "Optional list of CLI arguments.",
        "stdin": "Optional stdin string passed to the process.",
        "cwd": "Optional working directory.",
    }
    outputs_desc = tool.get("outputs") or {
        "stdout": "Process stdout text.",
        "stderr": "Process stderr text.",
        "exit_code": "Process exit code.",
    }

    def _run_cli(
        args: list[str] | None = None, stdin: str | None = None, cwd: str | None = None
    ) -> dict[str, Any]:
        """Execute the configured CLI command and return process output fields."""
        cmd = [command]
        if args:
            cmd.extend(args)

        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            cwd=cwd,
            input=stdin,
        )
        stdout = (result.stdout or "").rstrip()
        stderr = (result.stderr or "").rstrip()
        if result.returncode != 0:
            log(f"[healthcheck] process failed: cmd={cmd[0]} exit={result.returncode}")
        return {"stdout": stdout, "stderr": stderr, "exit_code": result.returncode}

    def _tool_runner(input: Any = None) -> dict[str, Any]:
        """Internal dict-based adapter used by generic registration and nested calls."""
        if input is None:
            payload: dict[str, Any] = {}
        elif isinstance(input, str):
            payload = {"args": shlex.split(input)}
        elif isinstance(input, dict):
            payload = input
        else:
            raise ValueError("input must be an object or string when provided")

        raw_args = payload.get("args")
        if raw_args is None:
            args = None
        elif (
            isinstance(raw_args, list)
            and all(isinstance(item, str) for item in raw_args)
        ):
            args = raw_args
        else:
            raise ValueError("input.args must be a list of strings when provided")

        stdin = payload.get("stdin")
        if stdin is not None and not isinstance(stdin, str):
            raise ValueError("input.stdin must be a string when provided")

        cwd = payload.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            raise ValueError("input.cwd must be a string when provided")

        return _run_cli(args=args, stdin=stdin, cwd=cwd)

    return {
        "name": mcp_name,
        "description": description,
        "inputs_desc": inputs_desc,
        "outputs_desc": outputs_desc,
        "meta": {"tool_pre_prompt": CLI_TOOL_PRE_PROMPT},
        "runner": _tool_runner,
        "source": {"command": command},
        "source_path": str(tool_path),
    }


__all__ = ["CLI_TOOL_PRE_PROMPT", "build_cli_mount"]

