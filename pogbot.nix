{ pkgs, ...} :
let 
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

        propagatedBuildInputs = with oldPkgs.python38Packages; [ numpy matplotlib scipy ];
    };

    python = pkgs.python3.withPackages(ps: [metalogistic] ++ (with ps; [ python-dotenv aiohttp discordpy pynacl six ]) );

    pogbotPackage = pkgs.stdenv.mkDerivation {
      name = "pogbot";
      buildInputs = [ python ];
      unpackPhase = "true";
      installPhase = ''
        mkdir -p $out/bin
        cp ${./pogbot.py} $out/bin/pogbot
        chmod +x $out/bin/pogbot
      '';

    };
in
{
systemd.services.pogbot = {
                description = "PogBot";
                serviceConfig = {
                        ExecStart = "${pogbotPackage}/bin/pogbot";
                        Restart = "always";
                };
                wantedBy = [ "multi-user-.target" ];
                after = [ "network.target" ];
                path = [ pkgs.ffmpeg ]; 
        };

systemd.services.pogbot.enable = true;
}
