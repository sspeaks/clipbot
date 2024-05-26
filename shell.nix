let
  pkgs = import <nixpkgs> { };
  python = pkgs.python3.withPackages (ps: (with ps; [ ffmpeg-python ]));
in
pkgs.mkShell {
  name = "dev-shell";
  packages = [ python pkgs.ffmpeg ];
}
