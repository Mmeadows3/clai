# MCP tool server flake template
# Rendered by src/server/tool_mounting/flakegen.py.
{
  description = "Modular CLI package set for the local dev container";

  inputs.nixpkgs.url = "__NIXPKGS_URL__";

  outputs = { self, nixpkgs }: let
    system = "__SYSTEM__";
    pkgs = import nixpkgs { inherit system; };
  in {
    packages.${system}.cli = pkgs.buildEnv {
      name = "cli";
      paths = [
__PATHS__
      ];
    };
  };
}
