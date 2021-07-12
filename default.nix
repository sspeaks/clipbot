let pkgs = import <nixpkgs> {};
oldPkgs = import (builtins.fetchTarball {
    name = "old-numpy-version-nixpkgs";
    url = "https://github.com/nixos/nixpkgs/archive/8f7cec22975b172500ce5e83ecdcc23aea6fb262.tar.gz";
    sha256 = "sha256:1fqa0chp64hpcp17hfw9dmdh87al0dwmbm694z17pzgivnhrcqa0";
  }) {};
  scipyPkgs = import (import (builtins.fetchTarball {
    name = "old-numpy-version-nixpkgs";
    url = "https://github.com/nixos/nixpkgs/archive/a8c26cf6cdb30fcb3e7ad8293997c6ea6a073dde.tar.gz";
    sha256 = "sha256:004h9v7l5q93maffc3wx45613j4q21cayglg79sl02822c4khkz4";
  }){}).path {overlays = [ (self: super: {
      python38 = let
        packageOverrides = python-self: python-super: {
          numpy = oldPkgs.python38Packages.numpy;
        };
      in super.python38.override { inherit packageOverrides; };
    })];};
  matplotlibPkgs = import (import (builtins.fetchTarball {
    name = "old-numpy-version-nixpkgs";
    url = "https://github.com/nixos/nixpkgs/archive/dbcad7f7bba9585dfc14b019ddad676c410949a9.tar.gz";
    sha256 = "sha256:11m8pgaplxc5i9rf786drzlmp74519zc0w9sa7axrpv3mqndfv2w";
  }) {}).path {overlays = [ (self: super: {
      python38 = let
        packageOverrides = python-self: python-super: {
          numpy = oldPkgs.python38Packages.numpy;
        };
      in super.python38.override { inherit packageOverrides; };
    })];};
    metalogistic = pkgs.python38.pkgs.buildPythonPackage rec {
        pname = "metalogistic";
        version = "0.0.4";

        src = pkgs.python38.pkgs.fetchPypi {
          inherit pname version;
          sha256 = "sha256:0bp703mzfs3v0mz3qmj5j185qvn48mk0y82nmbh3pf9k5w17cv5z";
        };
        propagatedBuildInputs = [ oldPkgs.python38Packages.numpy matplotlibPkgs.python38Packages.matplotlib scipyPkgs.python38Packages.scipy ];
      };
   python = pkgs.python3.withPackages(ps: [metalogistic] ++ (with ps; [ python-dotenv aiohttp discordpy pynacl six numpy scipy matplotlib]) );
in
 pkgs.stdenv.mkDerivation {
      name = "pogbot";
      buildInputs = [ python ];
      unpackPhase = "true";
      installPhase = ''
        mkdir -p $out/bin
        cp "${./.}/.env" $out/bin/.env
        cp -r "${./assets}" $out/bin/assets
        cp ${./pogbot.py } $out/bin/pogbot
        chmod +x $out/bin/pogbot
      '';
}
