{ pkgs, ...} :
let python = pkgs.python3.withPackages(ps: with ps; [ discordpy python-dotenv aiohttp ] );
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
        };

  systemd.services.pogbot.enable = true;
}
