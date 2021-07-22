{ pkgs, ...} :
let 
  clipbotPackage = import ./default.nix;
in
{
systemd.services.clipbot = {
                description = "ClipBot";
                serviceConfig = {
                        ExecStart = "${clipbotPackage}/bin/clipbot";
                        Restart = "always";
                        RestartSec = 1;
                };
                wantedBy = [ "multi-user-.target" ];
                after = [ "network.target" ];
                path = [ pkgs.ffmpeg ]; 
        };

systemd.services.clipbot.enable = true;
}
