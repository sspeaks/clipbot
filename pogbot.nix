{ pkgs, ...} :
let 
    inherit (pkgs.lib) fix extends attrValues;
    pythonPackagesGenerated = import ./python-packages.nix {
      inherit pkgs;
      inherit (pkgs) fetchurl fetchgit fetchhg;
    };
    basePythonPackages = self: pkgs.python37Packages;
    myPackages = (fix (extends pythonPackagesGenerated basePythonPackages));
    python = pkgs.python37.withPackages(ps: with myPackages; attrValues myPackages );

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
