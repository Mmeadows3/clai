"""Tools Directory adapter for high-level DSL acceptance scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

TOOL_SPEC_NAME = "TOOL.yaml"
SKIPPED_PATH_PART = "templates"
SUPPORTED_TOOL_TYPES = ("cli", "python", "markdown", "prompt")
CONTRACT_TOOL_NAMES_BY_TYPE = {
    "cli": "core.contract.cli_contract",
    "markdown": "core.contract.markdown_contract",
    "prompt": "core.contract.prompt_contract",
    "python": "core.contract.python_contract",
}
TEXT_MARKERS_BY_TYPE = {
    "markdown": ("## Purpose", "## Instructions"),
    "prompt": ("Provide deterministic prompt instructions for acceptance MCP contract tests.",),
}
DEFAULT_PYTHON_PROBE_VALUE = "python-execution-contract::Container(Server)->Rel(Invokes,PythonTool)"


@dataclass(frozen=True)
class DslLmContractScenario:
    tool_type: str
    tool_name: str
    input_payload: dict | None = None
    required_text_markers: tuple[str, ...] = ()
    probe_value: str | None = None


class ToolsDirectoryAdapter:
    """Represents the Tools Directory boundary for acceptance tests."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    def count_bootstrappable_tool_yaml_configs(self) -> int:
        """Count supported TOOL.yaml specs in ./tools."""
        return len(self.supported_tool_names_by_type())

    def supported_tool_names_by_type(self) -> dict[str, str]:
        names_by_type: dict[str, str] = {}
        for spec in self._iter_tool_specs():
            tool_type = self._tool_type(spec)
            tool_name = str(spec.get("name") or "").strip()
            if tool_type in SUPPORTED_TOOL_TYPES and tool_name:
                names_by_type[tool_name] = tool_type
        return names_by_type

    def supported_tool_type_contract_scenarios(self) -> list[DslLmContractScenario]:
        """Build one durable contract scenario per supported tool type."""
        return [self._scenario_for_type(tool_type) for tool_type in SUPPORTED_TOOL_TYPES]

    def _scenario_for_type(self, tool_type: str) -> DslLmContractScenario:
        normalized = tool_type.strip().lower()
        if normalized not in SUPPORTED_TOOL_TYPES:
            raise AssertionError(f"unsupported tool type for LM scenarios: {tool_type}")
        scenario = DslLmContractScenario(tool_type=normalized, tool_name=self._tool_name_for_type(normalized))
        if normalized == "python":
            return DslLmContractScenario(
                tool_type=scenario.tool_type,
                tool_name=scenario.tool_name,
                probe_value=DEFAULT_PYTHON_PROBE_VALUE,
            )
        if normalized in {"markdown", "prompt"}:
            return DslLmContractScenario(
                tool_type=scenario.tool_type,
                tool_name=scenario.tool_name,
                input_payload={"value": f"clai-{normalized}-contract"},
                required_text_markers=TEXT_MARKERS_BY_TYPE[normalized],
            )
        return scenario

    def _tool_name_for_type(self, tool_type: str) -> str:
        expected_name = CONTRACT_TOOL_NAMES_BY_TYPE.get(tool_type)
        if not expected_name:
            raise AssertionError(f"missing expected contract tool mapping: {tool_type}")
        actual_type = self.supported_tool_names_by_type().get(expected_name)
        if actual_type != tool_type:
            raise AssertionError(
                f"missing contract tool for type '{tool_type}': expected '{expected_name}'"
            )
        return expected_name

    def _iter_tool_specs(self) -> list[dict]:
        specs: list[dict] = []
        for tool_file in (self._repo_root / "tools").rglob(TOOL_SPEC_NAME):
            if SKIPPED_PATH_PART in tool_file.parts:
                continue
            specs.append(self._spec(tool_file))
        return specs

    def _spec(self, tool_file: Path) -> dict:
        spec = yaml.safe_load(tool_file.read_text(encoding="utf-8"))
        if not isinstance(spec, dict):
            return {}
        return spec

    def _tool_type(self, spec: dict) -> str:
        if not isinstance(spec, dict):
            return ""
        return str(spec.get("type") or "").strip().lower()
