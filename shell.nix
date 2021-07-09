let pkgs = import <nixpkgs> {};
in
  pkgs.mkShell {
    name = "pogbot-env";
    buildInputs = with pkgs; [ python38 python38Packages.aiohttp python38Packages.discordpy python38Packages.python-dotenv python38Packages.six ffmpeg ];
  }
