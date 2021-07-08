{ pkgs, ...} :
let 
    pythonPackagesGenerated = import ./python-packages.nix {
      inherit pkgs;
      inherit (pkgs) fetchurl fetchgit fetchhg;
    };
    python = pkgs.python3.withPackages(ps: with ps; [ pythonPackagesGenerated ps ] );

in
{
systemd.services.pogbot = {
                description = "PogBot";
                serviceConfig = {
                        ExecStart = "${python}/bin/python /home/sspeaks/pogbot/pogbot.py";
                        Restart = "always";
                };
                wantedBy = [ "multi-user-.target" ];
                after = [ "network.target" ];
                path = [ pkgs.ffmpeg ]; 
        };

  systemd.services.pogbot.enable = true;
}
