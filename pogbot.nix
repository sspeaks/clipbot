{ pkgs, config, lib, ... }:
let
  cfg = config.services.pogbot;
  pogBotPackage = cfg.package.override {
    assetsPath = cfg.assetsPathFile;
    discordToken = cfg.discordTokenFile;
    giphyApiKey = cfg.giphyAPIKeyFile;
    openAiApiKey = cfg.openAIAPIKeyFile;
  };
in
{
  options = {
    services.pogbot = {
      enable = lib.mkEnableOption "pogbot";
      package = lib.mkOption {
        description = "Pogbot package";
        type = lib.types.package;
      };
      assetsPathFile = lib.mkOption {
        description = "Path of the assets to play";
        type = lib.types.str;
      };
      discordTokenFile = lib.mkOption {
        description = "Secret token for discord";
        type = lib.types.str;
      };
      giphyAPIKeyFile = lib.mkOption {
        description = "Secret token for giphy api";
        type = lib.types.str;
      };
      openAIAPIKeyFile = lib.mkOption {
        description = "Secret token for Open AI api";
        type = lib.types.str;
      };
      webPort = lib.mkOption {
        description = "Port for the clip trimmer web server";
        type = lib.types.port;
        default = 8080;
      };
      trimmerUrl = lib.mkOption {
        description = "Public base URL for clip trimmer links (e.g. https://mycatsonfire.com/pogbot)";
        type = lib.types.str;
        default = "http://localhost:8080";
      };
    };
  };
  config = lib.mkIf cfg.enable
    {
      systemd.services.pogbot = {
        description = "PogBot";
        serviceConfig = {
          ExecStart = "${pogBotPackage}/bin/pogbot";
          Restart = "always";
          RestartSec = 1;
        };
        environment = {
          POGBOT_WEB_PORT = toString cfg.webPort;
          POGBOT_TRIMMER_URL = cfg.trimmerUrl;
        };
        wantedBy = [ "multi-user.target" ];
        after = [ "network.target" ];
        path = [ pkgs.ffmpeg ];
      };
      systemd.services.pogbot.enable = true;
      networking.firewall.allowedTCPPorts = [ cfg.webPort ];
    };
}
