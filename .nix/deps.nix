{ pkgs }:
{
  packages = with pkgs; [
    cspell
    nixfmt-tree
    oxfmt
  ];
}
