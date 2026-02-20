"""Docs/diagram sync adapter for high-level acceptance criteria."""

from __future__ import annotations

from pathlib import Path

DIAGRAM_BLOCK_START = "<!-- BEGIN:STRUCTURIZR_MAIN_OVERVIEW -->"
DIAGRAM_BLOCK_END = "<!-- END:STRUCTURIZR_MAIN_OVERVIEW -->"


class DocsDiagramAdapter:
    """Validates generated diagram embedding and cleanup invariants."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    def validate_diagram_sync_smoke(self) -> None:
        readme = self._repo_root / "README.md"
        agents = self._repo_root / "AGENTS.md"
        dsl = self._repo_root / "workspace.dsl"
        generated_docs = self._repo_root / ".generated-docs"
        mermaid_dir = self._repo_root / "mermaid"

        if not dsl.exists():
            raise AssertionError("missing workspace.dsl")

        readme_text = readme.read_text(encoding="utf-8")
        agents_text = agents.read_text(encoding="utf-8")
        if readme_text != agents_text:
            raise AssertionError("README.md and AGENTS.md are out of sync")

        if readme_text.count(DIAGRAM_BLOCK_START) != 1 or readme_text.count(DIAGRAM_BLOCK_END) != 1:
            raise AssertionError("diagram markers missing or duplicated")

        block = self._extract_diagram_block(readme_text)
        if "```mermaid" not in block or "graph " not in block:
            raise AssertionError("embedded mermaid diagram missing")

        if generated_docs.exists() or mermaid_dir.exists():
            raise AssertionError("temporary diagram artifacts were not cleaned up")

    def _extract_diagram_block(self, readme_text: str) -> str:
        block_start = readme_text.find(DIAGRAM_BLOCK_START)
        block_end = readme_text.find(DIAGRAM_BLOCK_END, block_start)
        if block_start == -1 or block_end == -1:
            raise AssertionError("diagram markers missing")
        return readme_text[block_start:block_end]
