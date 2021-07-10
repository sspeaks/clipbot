{ pkgs, ...} :
let 
    python = pkgs.python3.withPackages(ps: with ps; [ python-dotenv aiohttp discordpy pynacl six numpy metalogistic ] );

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
