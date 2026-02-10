"""FastMCP server bootstrap and serving entrypoints."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import anyio
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.fastmcp import FastMCP

from tool_mounting.tool_registration import log_stdout, register_configured_tools
from tool_mounting.tool_specs import iter_tool_spec_paths

SERVER_NAME = "clai"
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000
MCP_PATH = "/mcp"
TRANSPORT = "streamable-http"
DEFAULT_MCP_SERVER_URL = "http://clai:8000/mcp"
AppState = dict[str, Any]


def build_state(repo_root: Path | None = None) -> AppState:
    """Build application state with resolved repository and tool paths."""
    resolved_root = repo_root or Path(__file__).resolve().parents[1]
    return {
        "repo_root": resolved_root,
        "tools_dir": resolved_root / "tools",
        "tool_runner_registry": {},
    }


def build_registered_mcp_server(state: AppState) -> FastMCP:
    """Build a FastMCP server instance with configured tools registered."""
    mcp = FastMCP(
        SERVER_NAME,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="ERROR",
        streamable_http_path=MCP_PATH,
    )
    register_configured_tools(mcp, state, log=log_stdout)
    return mcp


def serve_mcp_server() -> None:
    """Serve FastMCP without running bootstrap validation."""
    state = build_state()
    mcp = build_registered_mcp_server(state)
    mcp.run(transport=TRANSPORT)


def _extract_tools(list_tools_result: Any) -> list[tuple[str, str]]:
    items = getattr(list_tools_result, "tools", None)
    if not isinstance(items, list):
        if isinstance(list_tools_result, dict):
            items = list_tools_result.get("tools")
        elif hasattr(list_tools_result, "model_dump"):
            dumped = list_tools_result.model_dump()
            items = dumped.get("tools") if isinstance(dumped, dict) else None
    if not isinstance(items, list):
        items = []

    rendered: list[tuple[str, str]] = []
    for item in items:
        name = str(
            getattr(item, "name", "") if not isinstance(item, dict) else item.get("name") or ""
        )
        name = " ".join(name.split())
        if not name:
            continue
        description = str(
            getattr(item, "description", "")
            if not isinstance(item, dict)
            else item.get("description") or ""
        )
        description = " ".join(description.split()) or "-"
        rendered.append((name, description))
    rendered.sort(key=lambda row: row[0])
    return rendered


def _render_tool_list(tools: list[tuple[str, str]], failed_count: int = 0) -> None:
    print("=== MCP Tool Availability ===")
    print(
        "[healthcheck] "
        f"mcp_tools_discovered: PASS count={len(tools)} failed={max(0, failed_count)}"
    )
    for name, description in tools:
        print(
            "[tool] "
            f"name={_single_line(name)} "
            f"description={_single_line(description)}"
        )


def _single_line(value: Any) -> str:
    """Render one compact single-line value for log-friendly diagnostics."""
    return " ".join(str(value).split())


def _resolve_mcp_server_url(default_url: str = DEFAULT_MCP_SERVER_URL) -> str:
    """Resolve MCP server URL from environment with a supplied default."""
    return os.environ.get("MCP_SERVER_URL", default_url)


def _log_nested_validation_failure(exc: Exception) -> None:
    """Emit consistent failure logs for nested bootstrap validation."""
    print("[validation] FAIL nested_tool_calls_invoked", flush=True)
    print(
        f"[healthcheck] error={exc.__class__.__name__}: {' '.join(str(exc).split())}",
        flush=True,
    )


async def _run_bootstrap_validation_once(
    mcp_server_url: str,
    state: AppState | None = None,
) -> None:
    app_state = state or build_state()
    async with streamable_http_client(mcp_server_url) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            nested_result = await session.call_tool(
                "core.healthcheck.test_nested_tool_calls", {}
            )
            tools_result = await session.list_tools()

            nested_payload: Any = nested_result
            model_dump = getattr(nested_result, "model_dump", None)
            if callable(model_dump):
                nested_payload = model_dump()

            tools = _extract_tools(tools_result)
            declared_specs = len(
                iter_tool_spec_paths(app_state["tools_dir"], include_templates=False)
            )
            failed_count = max(0, declared_specs - len(tools))

            print("=== FastMCP Bootstrap Health ===")
            print(f"[healthcheck] mcp_session_initialize: PASS url={mcp_server_url}")
            print(
                f"[healthcheck] nested_tool_call_result: {_single_line(nested_payload)}"
            )
            _render_tool_list(tools, failed_count=failed_count)


def run_bootstrap_validation_once() -> int:
    """Run one bootstrap validation pass against an already-running FastMCP server."""
    mcp_server_url = _resolve_mcp_server_url(DEFAULT_MCP_SERVER_URL)
    try:
        anyio.run(_run_bootstrap_validation_once, mcp_server_url, build_state())
    except Exception as exc:
        _log_nested_validation_failure(exc)
        return 1

    print("[validation] PASS nested_tool_calls_invoked", flush=True)
    return 0


async def _serve_with_bootstrap_validation(mcp_server_url: str) -> None:
    """Start FastMCP, run one bootstrap validation pass, then keep serving."""
    import uvicorn

    state = build_state()
    mcp = build_registered_mcp_server(state)
    started = anyio.Event()

    class _StartupNotifyingServer(uvicorn.Server):
        async def startup(self, sockets=None) -> None:  # type: ignore[override]
            await super().startup(sockets=sockets)
            started.set()

    config = uvicorn.Config(
        mcp.streamable_http_app(),
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="error",
    )
    server = _StartupNotifyingServer(config)

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(server.serve)
        await started.wait()
        await _run_bootstrap_validation_once(mcp_server_url, state=state)
        print("[validation] PASS nested_tool_calls_invoked", flush=True)
        await anyio.sleep_forever()


def serve_mcp_with_bootstrap_validation() -> int:
    """Run FastMCP and validate nested tool calls once after startup."""
    mcp_server_url = _resolve_mcp_server_url(DEFAULT_MCP_SERVER_URL)
    try:
        anyio.run(_serve_with_bootstrap_validation, mcp_server_url)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        _log_nested_validation_failure(exc)
        return 1
    return 0


def main() -> int:
    """Command-line entrypoint for serving FastMCP tools."""
    serve_mcp_server()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
