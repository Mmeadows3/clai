"""FastMCP server bootstrap and serving entrypoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from mcp.server.fastmcp import FastMCP

from tool_mounting.tool_registration import log_stdout, register_configured_tools

SERVER_NAME = "clai"
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000
MCP_PATH = "/mcp"
TRANSPORT = "streamable-http"
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
    """Serve FastMCP with configured tools."""
    state = build_state()
    mcp = build_registered_mcp_server(state)
    mcp.run(transport=TRANSPORT)


def main() -> int:
    """Command-line entrypoint for serving FastMCP tools."""
    serve_mcp_server()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
