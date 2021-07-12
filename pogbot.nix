{ pkgs, ...} :
let 
  pogbotPackage = import ./default.nix;
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
