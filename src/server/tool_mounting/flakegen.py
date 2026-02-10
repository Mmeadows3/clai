"""Flake generation service for composing CLI package sets from tool specs."""

from __future__ import annotations

import os
from pathlib import Path

from tool_mounting.tool_specs import iter_tool_specs


def load_cli_specs(tools_dir: Path) -> list[dict[str, str]]:
    """Load parsed specs for tools declared as ``type: cli``."""
    specs: list[dict[str, str]] = []
    for _tool_path, spec in iter_tool_specs(
        tools_dir,
        include_templates=False,
    ):
        if str(spec.get("type") or "").strip().lower() != "cli":
            continue
        specs.append(spec)
    return specs


def collect_paths(cli_specs: list[dict[str, str]]) -> list[str]:
    """Collect and deduplicate Nix package paths from CLI specs."""
    paths: list[str] = []
    seen: set[str] = set()

    def add_path(path: str) -> None:
        """Insert one path while preserving first-seen order."""
        if path not in seen:
            seen.add(path)
            paths.append(path)

    for spec in cli_specs:
        expr = spec.get("nix_expr")
        if isinstance(expr, str) and expr.strip():
            add_path(expr.strip())
        pkg = spec.get("nix_package")
        if isinstance(pkg, str) and pkg.strip():
            add_path(f"pkgs.{pkg.strip()}")
    return sorted(paths)


def render_flake(template_path: Path, system: str, paths: list[str], nixpkgs_url: str) -> str:
    """Render the flake template with selected system, inputs, and packages."""
    template = template_path.read_text(encoding="utf-8")
    rendered_paths = "\n".join(f"        {path}" for path in paths)
    return (
        template.replace("__NIXPKGS_URL__", nixpkgs_url)
        .replace("__SYSTEM__", system)
        .replace("__PATHS__", rendered_paths)
    )


def generate_flake(repo_root: Path) -> None:
    """Generate ``src/server/flake.nix`` and fail when no CLI paths are configured."""
    system = os.getenv("NIX_SYSTEM", "x86_64-linux")
    nixpkgs_url = os.getenv("NIXPKGS_URL", "github:NixOS/nixpkgs")
    tools_dir = repo_root / "tools"
    flake_path = repo_root / "server" / "flake.nix"
    template_path = repo_root / "server" / "flake.template.nix"

    cli_specs = load_cli_specs(tools_dir)
    paths = collect_paths(cli_specs)
    if not paths:
        raise SystemExit("no nix paths found in CLI tool specs")

    content = render_flake(template_path, system, paths, nixpkgs_url)
    flake_path.write_text(content, encoding="utf-8")


def main() -> None:
    """Command-line entrypoint for generating ``src/server/flake.nix``."""
    generate_flake(Path(__file__).resolve().parents[2])


if __name__ == "__main__":
    main()

