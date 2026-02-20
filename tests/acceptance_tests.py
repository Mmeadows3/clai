"""DSL-level acceptance tests for CLAI behavior."""

from __future__ import annotations

import unittest
from pathlib import Path

from adapters.acceptance_docs_adapter import DocsDiagramAdapter
from adapters.acceptance_server_adapter import McpProtocolTranslator, McpTestConfig
from adapters.acceptance_tools_adapter import ToolsDirectoryAdapter

REPO_ROOT = Path(__file__).resolve().parents[1]


class Acceptance01SmokeChecks(unittest.TestCase):
    """Smoke checks that guard generated Solution Specification artifacts."""

    def setUp(self) -> None:
        self.docs_adapter = DocsDiagramAdapter(REPO_ROOT)

    def test_01_solution_spec_overview_is_in_sync(self) -> None:
        """Ensures the Acceptance Test Suite keeps the DSL-driven system overview synced in project docs."""
        state = self.docs_adapter.collect_diagram_sync_state()
        self.assertTrue(state.workspace_dsl_exists, "missing workspace.dsl")
        self.assertTrue(state.readme_agents_in_sync, "README.md and AGENTS.md are out of sync")
        self.assertTrue(state.marker_count_valid, "diagram markers missing or duplicated")
        self.assertTrue(state.embedded_mermaid_present, "embedded mermaid diagram missing")
        self.assertTrue(
            state.temporary_diagram_artifacts_cleaned,
            "temporary diagram artifacts were not cleaned up",
        )


class Acceptance02DslBehaviorChecks(unittest.TestCase):
    """Behavior-scoped checks for LM-to-Server MCP interactions through Adapters."""

    def setUp(self) -> None:
        self.server_adapter = McpProtocolTranslator(McpTestConfig.from_env())
        self.tools_adapter = ToolsDirectoryAdapter(REPO_ROOT)

    def test_01_server_survives_basic_startup_calls(self) -> None:
        """The MCP server should survive a basic startup battery."""
        self.server_adapter.assert_server_survives_basic_startup_calls()

    def test_02_available_tools_count_equals_tool_yaml_count(self) -> None:
        """A request for available MCP tools should match bootstrappable TOOL.yaml count in ./tools."""
        self.server_adapter.ensure_ready_server_channel()
        expected_count = self.tools_adapter.count_bootstrappable_tool_yaml_configs()
        self.server_adapter.assert_available_tools_count_equals(expected_count)

    def test_03_each_tool_type_matches_expected_mcp_response(self) -> None:
        """Each supported tool type should behave as expected and match the expected MCP response."""
        self.server_adapter.ensure_ready_server_channel()
        scenarios = self.tools_adapter.supported_tool_type_contract_scenarios()
        self.server_adapter.assert_each_tool_type_matches_expected_mcp_response(scenarios)


if __name__ == "__main__":
    unittest.main()
