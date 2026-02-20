"""Docs/diagram sync adapter for high-level acceptance criteria."""

from __future__ import annotations

from pathlib import Path


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

        start = "<!-- BEGIN:STRUCTURIZR_MAIN_OVERVIEW -->"
        end = "<!-- END:STRUCTURIZR_MAIN_OVERVIEW -->"
        if readme_text.count(start) != 1 or readme_text.count(end) != 1:
            raise AssertionError("diagram markers missing or duplicated")

        block_start = readme_text.find(start)
        block_end = readme_text.find(end)
        block = readme_text[block_start:block_end]
        if "```mermaid" not in block or "graph " not in block:
            raise AssertionError("embedded mermaid diagram missing")

        if generated_docs.exists() or mermaid_dir.exists():
            raise AssertionError("temporary diagram artifacts were not cleaned up")
