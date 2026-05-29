{
  description = "Repository maintenance tooling for coding-profile";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { nixpkgs, ... }:
    let
      systems = [
        "aarch64-darwin"
        "aarch64-linux"
        "x86_64-darwin"
        "x86_64-linux"
      ];

      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f system);
      perSystem =
        system:
        let
          pkgs = import nixpkgs { inherit system; };
          deps = import ./deps.nix { inherit pkgs; };
          tools = pkgs.symlinkJoin {
            name = "coding-profile-tools";
            paths = deps.packages;
          };
        in
        {
          inherit deps pkgs tools;
        };
    in
    {
      packages = forAllSystems (
        system:
        let
          env = perSystem system;
        in
        {
          default = env.tools;
          tools = env.tools;
        }
      );

      devShells = forAllSystems (
        system:
        let
          env = perSystem system;
        in
        {
          default = env.pkgs.mkShellNoCC {
            packages = env.deps.packages;
          };
        }
      );
    };
}
