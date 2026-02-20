"""Server adapter that translates MCP protocol details for acceptance tests."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib import request as urllib_request
from uuid import uuid4

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
class McpToolCallResult:
    status_code: int
    is_error: bool
    structured_content: dict[str, Any]
    content_text: str
    raw_payload: Any


@dataclass(frozen=True)
class RemoteExecutionProbe:
    tool_type: str
    token: str
    file_path: str


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
    """Translates DSL-level acceptance intents into MCP protocol operations."""

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

    def initialize(self, *, client_name: str) -> McpStepResult:
        return self.post_method(
            "initialize",
            params=self._initialize_params(client_name=client_name),
            use_session=False,
        )

    def notify_initialized(self) -> McpStepResult:
        return self.post_method(
            "notifications/initialized",
            params={},
            as_notification=True,
        )

    def establish_ready_session(self) -> McpStepResult:
        initialized = self.initialize(client_name="clai-acceptance-suite")
        notified = self.notify_initialized()
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

    def initialize_with_retry(
        self,
        *,
        max_attempts: int = 40,
        delay_seconds: float = 2.0,
        client_name: str = "clai-startup-probe",
    ) -> McpStepResult:
        last_error: Exception | None = None
        for _ in range(max_attempts):
            try:
                return self.initialize(client_name=client_name)
            except Exception as exc:  # pragma: no cover - network readiness edge
                last_error = exc
                time.sleep(delay_seconds)
        raise AssertionError(f"startup initialize probe failed: {last_error}")

    def ensure_ready_server_channel(self) -> McpStepResult:
        initialized = self.initialize_with_retry()
        self.assert_initialize_contract(initialized)
        ready = self.establish_ready_session()
        self.assert_ready_session_contract(ready)
        return ready

    def assert_server_survives_basic_startup_calls(self) -> None:
        """
        Acceptance boundary:
        the MCP server should survive a basic startup battery.
        """
        initialized = self.initialize_with_retry()
        self.assert_initialize_contract(initialized)

        ready = self.establish_ready_session()
        self.assert_ready_session_contract(ready)

        listed = self.post_method("tools/list")
        if listed.status_code != 200:
            raise AssertionError(f"unexpected tools/list status: {listed.status_code}")
        if not isinstance(listed.payload, dict):
            raise AssertionError("tools/list payload was not a JSON object")

        result = listed.payload.get("result")
        if not isinstance(result, dict):
            raise AssertionError("tools/list payload missing result object")
        tools = result.get("tools")
        if not isinstance(tools, list):
            raise AssertionError("tools/list payload missing tools array")

    def list_tools(self) -> list[dict[str, Any]]:
        listed = self.post_method("tools/list")
        if not isinstance(listed.payload, dict):
            return []
        tools = listed.payload.get("result", {}).get("tools", [])
        if not isinstance(tools, list):
            return []
        return [tool for tool in tools if isinstance(tool, dict)]

    def assert_available_tools_count_equals(self, expected_count: int) -> None:
        """
        Acceptance boundary:
        a request to the MCP server for available tools should return a list with
        a count equal to TOOL.yaml configs in ./tools.
        """
        actual_count = len(self.list_tools())
        if actual_count != expected_count:
            raise AssertionError(
                "available tools count mismatch: "
                f"expected={expected_count}, actual={actual_count}"
            )

    def tool_by_name(self, name: str) -> dict[str, Any] | None:
        for tool in self.list_tools():
            if str(tool.get("name") or "").strip() == name:
                return tool
        return None

    def call_tool(self, name: str, input_payload: Any = None) -> McpToolCallResult:
        called = self.post_method(
            "tools/call",
            params={"name": name, "arguments": {"input": input_payload}},
        )
        result = {}
        if isinstance(called.payload, dict):
            raw_result = called.payload.get("result")
            if isinstance(raw_result, dict):
                result = raw_result

        structured_content = result.get("structuredContent")
        if not isinstance(structured_content, dict):
            structured_content = {}

        content_text = ""
        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    content_text = item["text"]
                    break

        return McpToolCallResult(
            status_code=called.status_code,
            is_error=bool(result.get("isError")),
            structured_content=structured_content,
            content_text=content_text,
            raw_payload=called.payload,
        )

    def is_successful_tool_call(self, called: McpToolCallResult) -> bool:
        return called.status_code == 200 and not called.is_error

    def create_remote_execution_probe(self, tool_type: str) -> RemoteExecutionProbe:
        normalized = tool_type.strip().lower()
        token = uuid4().hex
        file_path = f"/tmp/clai-acceptance-probes/{normalized}-{token}.txt"
        return RemoteExecutionProbe(tool_type=normalized, token=token, file_path=file_path)

    def probe_file_exists(self, probe: RemoteExecutionProbe) -> bool:
        called = self.call_tool(
            "core.contract.cli_contract",
            {"args": ["-c", f"let p = '{probe.file_path}'; print ($p | path exists)"]},
        )
        if not self.is_successful_tool_call(called):
            raise AssertionError("failed to probe remote file state")
        return str(called.structured_content.get("stdout") or "").strip().lower() == "true"

    def read_probe_token(self, probe: RemoteExecutionProbe) -> str:
        called = self.call_tool(
            "core.contract.cli_contract",
            {
                "args": [
                    "-c",
                    (
                        f"let p = '{probe.file_path}'; "
                        "if ($p | path exists) { open $p | into string | str trim } else { '' }"
                    ),
                ]
            },
        )
        if not self.is_successful_tool_call(called):
            raise AssertionError("failed to read remote probe")
        return str(called.structured_content.get("stdout") or "").strip()

    def call_cli_execution_probe(
        self,
        tool_name: str,
        *,
        probe: RemoteExecutionProbe,
    ) -> McpToolCallResult:
        script = (
            f"let p = '{probe.file_path}'; "
            f"let token = '{probe.token}'; "
            "mkdir ($p | path dirname); "
            "$token | save --force $p; "
            "print $token"
        )
        return self.call_tool(tool_name, {"args": ["-c", script]})

    def call_python_execution_probe(
        self,
        tool_name: str,
        *,
        probe: RemoteExecutionProbe,
        value: str = "python-execution-contract",
    ) -> McpToolCallResult:
        return self.call_tool(
            tool_name,
            {
                "value": value,
                "probe_file": probe.file_path,
                "probe_token": probe.token,
            },
        )

    def parse_content_text_json_object(self, content_text: str) -> dict[str, Any]:
        payload = json.loads(content_text)
        if not isinstance(payload, dict):
            return {}
        return payload

    def assert_initialize_contract(self, initialized: McpStepResult) -> None:
        if initialized.status_code != 200:
            raise AssertionError("unexpected status for initialize")
        if not isinstance(initialized.payload, dict):
            raise AssertionError("initialize payload was not a JSON object")

        payload = initialized.payload if isinstance(initialized.payload, dict) else {}
        result = payload.get("result")
        if not isinstance(result, dict):
            raise AssertionError("initialize payload missing result object")

        result_dict = result if isinstance(result, dict) else {}
        protocol = str(result_dict.get("protocolVersion") or "")
        if protocol != self._config.protocol_version:
            raise AssertionError("initialize returned unexpected protocolVersion")

        server_info = result_dict.get("serverInfo")
        if not isinstance(server_info, dict):
            raise AssertionError("initialize payload missing serverInfo")
        server_info_dict = server_info if isinstance(server_info, dict) else {}
        if not str(server_info_dict.get("name") or "").strip():
            raise AssertionError("initialize payload missing serverInfo.name")
        if not str(server_info_dict.get("version") or "").strip():
            raise AssertionError("initialize payload missing serverInfo.version")

        capabilities = result_dict.get("capabilities")
        if not isinstance(capabilities, dict):
            raise AssertionError("initialize payload missing capabilities object")
        capabilities_dict = capabilities if isinstance(capabilities, dict) else {}
        if not isinstance(capabilities_dict.get("tools"), dict):
            raise AssertionError("initialize payload missing capabilities.tools")

    def assert_ready_session_contract(self, ready: McpStepResult) -> None:
        if not ready.session_id:
            raise AssertionError("missing MCP session id after initialization handshake")
        if ready.status_code < 200 or ready.status_code >= 300:
            raise AssertionError("unexpected status for notifications/initialized")
        if not isinstance(ready.payload, dict):
            raise AssertionError("ready-session payload missing")

        payload = ready.payload if isinstance(ready.payload, dict) else {}
        initialize_block = payload.get("initialize")
        if not isinstance(initialize_block, dict):
            raise AssertionError("ready-session payload missing initialize block")
        initialize_dict = initialize_block if isinstance(initialize_block, dict) else {}

        initialize_step = McpStepResult(
            status_code=int(initialize_dict.get("status_code") or 0),
            payload=initialize_dict.get("payload"),
            session_id=ready.session_id,
        )
        self.assert_initialize_contract(initialize_step)

    def assert_dsl_lm_contract(self, scenario: Any) -> None:
        tool_type = str(getattr(scenario, "tool_type", "")).strip().lower()
        if tool_type == "cli":
            self._assert_cli_execution_contract(scenario)
            return
        if tool_type == "python":
            self._assert_python_execution_contract(scenario)
            return
        if tool_type in {"markdown", "prompt"}:
            self._assert_prompt_like_instruction_contract(scenario)
            return
        raise AssertionError(f"unsupported LM contract tool_type: {tool_type}")

    def assert_each_tool_type_matches_expected_mcp_response(
        self,
        scenarios: list[Any],
    ) -> None:
        """
        Acceptance boundary:
        each tool type, when called via the MCP server, should behave as expected
        and match an expected MCP response.
        """
        for scenario in scenarios:
            self.assert_dsl_lm_contract(scenario)

    def _assert_lm_readable_tool_result(self, called: McpToolCallResult) -> None:
        if called.status_code != 200:
            raise AssertionError(f"unexpected tools/call status: {called.status_code}")
        if called.is_error:
            raise AssertionError(f"tools/call marked error: {called.raw_payload}")
        if not called.structured_content:
            raise AssertionError("tool result missing structuredContent payload")
        if not called.content_text.strip():
            raise AssertionError("tool result missing text content for LM consumption")

    def _assert_probe_absent_before_execution(self, probe: RemoteExecutionProbe) -> None:
        if self.probe_file_exists(probe):
            raise AssertionError(
                f"probe file unexpectedly exists before execution: {probe.file_path}"
            )

    def _assert_probe_written_after_execution(self, probe: RemoteExecutionProbe) -> None:
        actual = self.read_probe_token(probe)
        if actual != probe.token:
            raise AssertionError(f"unexpected remote probe token in {probe.file_path}")

    def _assert_cli_execution_contract(self, scenario: Any) -> None:
        tool_name = str(getattr(scenario, "tool_name", "")).strip()
        tool = self.tool_by_name(tool_name)
        if tool is None:
            raise AssertionError(f"expected registered tool: {tool_name}")

        probe = self.create_remote_execution_probe("cli")
        self._assert_probe_absent_before_execution(probe)

        called = self.call_cli_execution_probe(tool_name, probe=probe)
        self._assert_lm_readable_tool_result(called)
        if called.structured_content.get("exit_code") != 0:
            raise AssertionError(
                f"expected cli exit_code 0, got {called.structured_content.get('exit_code')!r}"
            )
        if called.structured_content.get("stdout") != probe.token:
            raise AssertionError("expected cli stdout to equal probe token")
        if str(called.structured_content.get("stderr") or "").strip():
            raise AssertionError("expected CLI stderr to be empty for contract probe")
        if probe.token not in called.content_text:
            raise AssertionError("expected LM-facing content text to include the probe token")

        self._assert_probe_written_after_execution(probe)

    def _assert_python_execution_contract(self, scenario: Any) -> None:
        tool_name = str(getattr(scenario, "tool_name", "")).strip()
        tool = self.tool_by_name(tool_name)
        if tool is None:
            raise AssertionError(f"expected registered tool: {tool_name}")

        probe = self.create_remote_execution_probe("python")
        self._assert_probe_absent_before_execution(probe)

        probe_value = str(getattr(scenario, "probe_value", None) or "python-execution-contract")
        called = self.call_python_execution_probe(
            tool_name,
            probe=probe,
            value=probe_value,
        )
        self._assert_lm_readable_tool_result(called)

        required_keys = {"tool_type", "echoed_value", "probe_written", "probe_token"}
        missing = sorted(key for key in required_keys if key not in called.structured_content)
        if missing:
            raise AssertionError(f"python contract response missing keys: {missing}")
        if called.structured_content.get("tool_type") != "python":
            raise AssertionError("python contract response missing tool_type=python")
        if called.structured_content.get("echoed_value") != probe_value:
            raise AssertionError("python contract response missing expected echoed value")
        if called.structured_content.get("probe_token") != probe.token:
            raise AssertionError("python contract response did not echo probe token")
        if called.structured_content.get("probe_written") is not True:
            raise AssertionError("python contract response did not report probe_written=true")

        self._assert_probe_written_after_execution(probe)

    def _assert_prompt_like_instruction_contract(self, scenario: Any) -> None:
        tool_name = str(getattr(scenario, "tool_name", "")).strip()
        tool_type = str(getattr(scenario, "tool_type", "")).strip().lower()
        tool = self.tool_by_name(tool_name)
        if tool is None:
            raise AssertionError(f"expected registered tool: {tool_name}")

        input_payload = getattr(scenario, "input_payload", None)
        if not isinstance(input_payload, dict):
            raise AssertionError(f"{tool_type} scenario missing input_payload object")

        markers = getattr(scenario, "required_text_markers", None)
        if markers is not None and not isinstance(markers, (list, tuple)):
            raise AssertionError(f"{tool_type} scenario required_text_markers must be a list or tuple")
        required_text_markers = [str(marker) for marker in (markers or [])]

        called = self.call_tool(tool_name, input_payload)
        self._assert_lm_readable_tool_result(called)

        if called.structured_content.get("type") != tool_type:
            raise AssertionError(f"expected prompt-like type '{tool_type}'")

        payload = called.structured_content.get("input")
        if not isinstance(payload, dict):
            raise AssertionError("prompt-like contract missing structured input payload")
        payload_dict = payload if isinstance(payload, dict) else {}
        if payload_dict != input_payload:
            raise AssertionError("prompt-like contract did not round-trip full input")

        text = str(called.structured_content.get("text", ""))
        if not text.strip():
            raise AssertionError("prompt-like contract missing non-empty text payload")

        content_payload = self.parse_content_text_json_object(called.content_text)
        if content_payload.get("text") != text:
            raise AssertionError(
                "MCP content.text JSON payload does not match structuredContent.text"
            )
        if content_payload.get("input") != payload_dict:
            raise AssertionError(
                "MCP content.text JSON payload does not match structuredContent.input"
            )
        if content_payload.get("type") != tool_type:
            raise AssertionError(
                "MCP content.text JSON payload does not match structuredContent.type"
            )

        if "Tool behavior:" not in text:
            raise AssertionError("prompt-like contract missing tool behavior guidance")
        expected_serialized_input = f"input: {json.dumps(input_payload, ensure_ascii=True)}"
        if expected_serialized_input not in text:
            raise AssertionError(
                f"{tool_type} contract text missing serialized input payload"
            )
        if "exit_code" in called.structured_content:
            raise AssertionError("prompt-like contract should not expose CLI execution fields")
        for marker in required_text_markers:
            if marker not in text:
                raise AssertionError(
                    f"prompt-like contract missing expected text marker: {marker!r}"
                )
