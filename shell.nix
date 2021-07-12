let pkgs = import <nixpkgs> {};
oldPkgs = import (builtins.fetchTarball {
    name = "old-numpy-version-nixpkgs";
    url = "https://github.com/nixos/nixpkgs/archive/8f7cec22975b172500ce5e83ecdcc23aea6fb262.tar.gz";
    sha256 = "sha256:1fqa0chp64hpcp17hfw9dmdh87al0dwmbm694z17pzgivnhrcqa0";
  }) {};
    metalogistic = pkgs.python38.pkgs.buildPythonPackage rec {
        pname = "metalogistic";
        version = "0.0.4";

        src = pkgs.python38.pkgs.fetchPypi {
          inherit pname version;
          sha256 = "sha256:0bp703mzfs3v0mz3qmj5j185qvn48mk0y82nmbh3pf9k5w17cv5z";
        };

        propagatedBuildInputs = [ oldPkgs.python38Packages.numpy oldPkgs.python38Packages.matplotlib oldPkgs.python38Packages.scipy ];
    };
in
  pkgs.mkShell {
    name = "pogbot-env";
    buildInputs = with pkgs; [ python38 python38Packages.aiohttp python38Packages.discordpy python38Packages.python-dotenv python38Packages.six ffmpeg metalogistic ];
  }
