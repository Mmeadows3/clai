"""MCP-specific execution/translation for high-level acceptance criteria."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib import request as urllib_request

DEFAULT_MCP_URL = "http://localhost:8000/mcp"
DEFAULT_PROTOCOL_VERSION = "2025-06-18"
DEFAULT_REQUEST_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


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


@dataclass(frozen=True)
class McpHttpResponse:
    status_code: int
    body: str
    headers: dict[str, str]


class McpHttpTransport:
    def __init__(self, mcp_url: str) -> None:
        self._mcp_url = mcp_url

    def post_json(
        self,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> McpHttpResponse:
        merged_headers = dict(DEFAULT_REQUEST_HEADERS)
        if headers:
            merged_headers.update(headers)
        req = urllib_request.Request(
            self._mcp_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=merged_headers,
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=10.0) as response:
            return McpHttpResponse(
                status_code=int(response.status),
                body=response.read().decode("utf-8"),
                headers={str(k): str(v) for k, v in response.headers.items()},
            )

    def parse_jsonrpc_payload(self, response: McpHttpResponse) -> Any:
        content_type = (
            response.headers.get("content-type") or response.headers.get("Content-Type") or ""
        ).lower()
        if "text/event-stream" not in content_type:
            return self._parse_json(response.body)

        json_chunks = []
        for line in response.body.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            data_value = line[len("data:") :].strip()
            if data_value:
                json_chunks.append(data_value)
        if not json_chunks:
            return None
        return self._parse_json(json_chunks[-1])

    @staticmethod
    def _parse_json(body: str) -> Any:
        stripped = body.strip()
        if not stripped:
            return None
        return json.loads(stripped)


class McpProtocolTranslator:
    """Translates stable acceptance intents into MCP protocol calls."""

    def __init__(self, config: McpTestConfig) -> None:
        self._config = config
        self._transport = McpHttpTransport(config.mcp_url)
        self._session_id: str | None = None

    def _initialize_params(self, *, client_name: str) -> dict[str, Any]:
        return {
            "protocolVersion": self._config.protocol_version,
            "capabilities": {},
            "clientInfo": {"name": client_name, "version": "1.0"},
        }

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
        if use_session and self._session_id:
            headers = {"Mcp-Session-Id": self._session_id}

        response = self._transport.post_json(
            request_payload,
            headers=headers,
        )
        payload = self._transport.parse_jsonrpc_payload(response)
        session_id = response.headers.get("Mcp-Session-Id") or response.headers.get("mcp-session-id")
        if isinstance(session_id, str) and session_id:
            self._session_id = session_id
        return McpStepResult(
            status_code=response.status_code,
            payload=payload,
            session_id=self._session_id,
        )

    def establish_ready_session(self) -> McpStepResult:
        initialized = self.post_method(
            "initialize",
            params=self._initialize_params(client_name="clai-acceptance-suite"),
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

    def list_tools(self) -> list[dict[str, Any]]:
        listed = self.post_method("tools/list")
        if not isinstance(listed.payload, dict):
            return []
        tools = listed.payload.get("result", {}).get("tools", [])
        if not isinstance(tools, list):
            return []
        return [tool for tool in tools if isinstance(tool, dict)]

    def wait_for_initialize_healthcheck(
        self,
        *,
        max_attempts: int = 40,
        delay_seconds: float = 2.0,
    ) -> McpStepResult:
        last_error: Exception | None = None
        for _ in range(max_attempts):
            try:
                return self.post_method(
                    "initialize",
                    params=self._initialize_params(client_name="clai-startupsmoke"),
                    use_session=False,
                )
            except Exception as exc:  # pragma: no cover - network readiness edge
                last_error = exc
                time.sleep(delay_seconds)
        raise AssertionError(f"startup initialize healthcheck failed: {last_error}")

    def validate_startup_healthcheck(self) -> None:
        initialized = self.wait_for_initialize_healthcheck()
        if initialized.status_code != 200:
            raise AssertionError(f"unexpected status for initialize: {initialized.status_code}")
        if not isinstance(initialized.payload, dict):
            raise AssertionError("initialize payload was not a JSON object")
        if "result" not in initialized.payload:
            raise AssertionError("initialize payload missing result")
