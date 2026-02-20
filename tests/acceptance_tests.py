"""High-level acceptance tests for MCP Server behavior. Assumes a running MCP Server."""

from __future__ import annotations

import unittest
from pathlib import Path

from adapters.acceptance_docs_adapter import DocsDiagramAdapter
from adapters.acceptance_server_adapter import McpProtocolTranslator, McpTestConfig
from adapters.acceptance_tools_adapter import ToolsDirectoryAdapter

REPO_ROOT = Path(__file__).resolve().parents[1]


class Acceptance01SmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.docs_adapter = DocsDiagramAdapter(REPO_ROOT)
        self.server_adapter = McpProtocolTranslator(McpTestConfig.from_env())

    def test_01_docs_diagram_sync_smoke(self) -> None:
        self.docs_adapter.validate_diagram_sync_smoke()

    def test_02_startup_initialize_healthcheck(self) -> None:
        initialized = self.server_adapter.wait_for_initialize_healthcheck()
        self.assertEqual(initialized.status_code, 200)
        self.assertIsInstance(initialized.payload, dict)
        self.assertIn("result", initialized.payload)


class Acceptance02ToolChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.server_adapter = McpProtocolTranslator(McpTestConfig.from_env())
        self.tools_adapter = ToolsDirectoryAdapter(REPO_ROOT)
        self.server_adapter.wait_for_initialize_healthcheck()
        self.server_adapter.establish_ready_session()

    def test_01_tool_count(self) -> None:
        listed = self.server_adapter.post_method("tools/list")

        tools = (
            listed.payload.get("result", {}).get("tools", [])
            if isinstance(listed.payload, dict)
            else []
        )

        expected_count = self.tools_adapter.count_supported_tools()

        self.assertEqual(len(tools), expected_count)


if __name__ == "__main__":
    unittest.main()
