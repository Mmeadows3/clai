"""Docs/diagram sync adapter for high-level acceptance criteria."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DIAGRAM_BLOCK_START = "<!-- BEGIN:STRUCTURIZR_MAIN_OVERVIEW -->"
DIAGRAM_BLOCK_END = "<!-- END:STRUCTURIZR_MAIN_OVERVIEW -->"


@dataclass(frozen=True)
class DocsDiagramSyncState:
    workspace_dsl_exists: bool
    readme_agents_in_sync: bool
    marker_count_valid: bool
    embedded_mermaid_present: bool
    temporary_diagram_artifacts_cleaned: bool


class DocsDiagramAdapter:
    """Collects generated diagram embedding and cleanup invariants."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    def collect_diagram_sync_state(self) -> DocsDiagramSyncState:
        readme = self._repo_root / "README.md"
        agents = self._repo_root / "AGENTS.md"
        dsl = self._repo_root / "workspace.dsl"
        generated_docs = self._repo_root / ".generated-docs"
        mermaid_dir = self._repo_root / "mermaid"

        readme_text = readme.read_text(encoding="utf-8") if readme.exists() else ""
        agents_text = agents.read_text(encoding="utf-8") if agents.exists() else ""

        marker_count_valid = (
            readme_text.count(DIAGRAM_BLOCK_START) == 1 and readme_text.count(DIAGRAM_BLOCK_END) == 1
        )
        block = self._diagram_block(readme_text) if marker_count_valid else ""
        embedded_mermaid_present = "```mermaid" in block and "graph " in block

        return DocsDiagramSyncState(
            workspace_dsl_exists=dsl.exists(),
            readme_agents_in_sync=readme.exists() and agents.exists() and readme_text == agents_text,
            marker_count_valid=marker_count_valid,
            embedded_mermaid_present=embedded_mermaid_present,
            temporary_diagram_artifacts_cleaned=not generated_docs.exists() and not mermaid_dir.exists(),
        )

    def _diagram_block(self, readme_text: str) -> str:
        block_start = readme_text.find(DIAGRAM_BLOCK_START)
        block_end = readme_text.find(DIAGRAM_BLOCK_END, block_start)
        if block_start == -1 or block_end == -1:
            return ""
        return readme_text[block_start:block_end]
