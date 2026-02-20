"""MCP-specific execution/translation for high-level acceptance criteria."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import request as urllib_request

DEFAULT_MCP_URL = "http://localhost:8000/mcp"
DEFAULT_PROTOCOL_VERSION = "2025-06-18"


@dataclass(frozen=True)
class McpTestConfig:
    mcp_url: str
    protocol_version: str

    @classmethod
    def from_env(cls) -> "McpTestConfig":
        return cls(
            mcp_url=os.environ.get("MCP_SERVER_URL", DEFAULT_MCP_URL),
            protocol_version=os.environ.get("MCP_PROTOCOL_VERSION", DEFAULT_PROTOCOL_VERSION),
        )


@dataclass(frozen=True)
class McpStepResult:
    status_code: int
    payload: Any
    session_id: str | None = None


def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> tuple[int, str, dict[str, str]]:
    merged_headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if headers:
        merged_headers.update(headers)
    req = urllib_request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=merged_headers,
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=10.0) as response:
        body = response.read().decode("utf-8")
        response_headers = {str(k): str(v) for k, v in response.headers.items()}
        return int(response.status), body, response_headers


def _parse_json(body: str) -> Any:
    stripped = body.strip()
    if not stripped:
        return None
    return json.loads(stripped)


def _parse_jsonrpc_from_http(body: str, headers: dict[str, str]) -> Any:
    content_type = (headers.get("content-type") or headers.get("Content-Type") or "").lower()
    if "text/event-stream" not in content_type:
        return _parse_json(body)

    json_chunks: list[str] = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data_value = line[len("data:") :].strip()
        if data_value:
            json_chunks.append(data_value)
    if not json_chunks:
        return None
    return _parse_json(json_chunks[-1])


class McpProtocolTranslator:
    """Translates stable acceptance intents into MCP protocol calls."""

    def __init__(self, config: McpTestConfig) -> None:
        self._config = config
        self._session_id: str | None = None

    def post_method(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        use_session: bool = True,
        as_notification: bool = False,
    ) -> McpStepResult:
        request_payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        if not as_notification:
            request_payload["id"] = f"{method}-1"

        headers: dict[str, str] | None = None
        if use_session:
            headers = {"Mcp-Session-Id": self._session_id or ""}

        status, body, response_headers = _post_json(
            self._config.mcp_url,
            request_payload,
            headers=headers,
        )
        payload = _parse_jsonrpc_from_http(body, response_headers)
        session_id = response_headers.get("Mcp-Session-Id") or response_headers.get("mcp-session-id")
        if isinstance(session_id, str) and session_id:
            self._session_id = session_id
        return McpStepResult(status_code=status, payload=payload, session_id=self._session_id)

    def establish_ready_session(self) -> McpStepResult:
        initialized = self.post_method(
            "initialize",
            params={
                "protocolVersion": self._config.protocol_version,
                "capabilities": {},
                "clientInfo": {"name": "clai-acceptance-suite", "version": "1.0"},
            },
            use_session=False,
        )
        notified = self.post_method(
            "notifications/initialized",
            params={},
            as_notification=True,
        )
        return McpStepResult(
            status_code=notified.status_code,
            payload={
                "initialize": {
                    "status_code": initialized.status_code,
                    "payload": initialized.payload,
                },
                "initialized": {
                    "status_code": notified.status_code,
                    "payload": notified.payload,
                },
            },
            session_id=self._session_id,
        )
