"""High-level acceptance tests for MCP Server behavior. Assumes a running MCP Server."""

from __future__ import annotations

import unittest
from pathlib import Path

from acceptance_server_adapter import McpProtocolTranslator, McpTestConfig
from acceptance_tools_adapter import ToolsDirectoryAdapter


class AcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server_adapter = McpProtocolTranslator(McpTestConfig.from_env())
        self.tools_adapter = ToolsDirectoryAdapter(Path(__file__).resolve().parents[1])
        self.ready_session = self.server_adapter.establish_ready_session()

    """Server tools/list count should match tools directory count."""
    def test_tool_count(self) -> None:

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
