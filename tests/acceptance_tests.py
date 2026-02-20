"""High-level acceptance tests for MCP Server behavior. Assumes a running MCP Server."""

from __future__ import annotations

import unittest
from pathlib import Path

from adapters.acceptance_docs_adapter import DocsDiagramAdapter
from adapters.acceptance_server_adapter import McpProtocolTranslator, McpTestConfig
from adapters.acceptance_tools_adapter import ToolsDirectoryAdapter

REPO_ROOT = Path(__file__).resolve().parents[1]


def build_server_adapter() -> McpProtocolTranslator:
    return McpProtocolTranslator(McpTestConfig.from_env())


class Acceptance01SmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.docs_adapter = DocsDiagramAdapter(REPO_ROOT)

    def test_01_docs_diagram_sync_smoke(self) -> None:
        self.docs_adapter.validate_diagram_sync_smoke()


class Acceptance02ToolChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.server_adapter = build_server_adapter()
        self.tools_adapter = ToolsDirectoryAdapter(REPO_ROOT)
        self.server_adapter.validate_startup_healthcheck()
        self.server_adapter.establish_ready_session()

    def test_01_tool_count(self) -> None:
        tools = self.server_adapter.list_tools()
        expected_count = self.tools_adapter.count_supported_tools()

        self.assertEqual(len(tools), expected_count)


if __name__ == "__main__":
    unittest.main()
