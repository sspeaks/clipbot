{ pkgs, config, lib, ... }:
let
  cfg = config.services.pogbot;
  pogBotPackage = cfg.package.overrideAttrs (_: rec {
    ASSETS_PATH_FILE = cfg.assetsPathFile;
    DISCORD_TOKEN_FILE = cfg.discordTokenFile;
    GIPHY_API_KEY_FILE = cfg.giphyAPIKeyFile;
    OPEN_AI_KEY_FILE = cfg.openAIAPIKeyFile;
    postFixup = ''
      wrapProgram $out/bin/pogbot \
      --prefix PATH : ${pkgs.lib.makeBinPath [pkgs.ffmpeg]} \
      --prefix LD_LIBRARY_PATH : ${pkgs.lib.makeLibraryPath [pkgs.libopus] } \
      --set ASSETS_PATH ${ASSETS_PATH_FILE} \
      --set DISCORD_TOKEN ${DISCORD_TOKEN_FILE} \
      --set GIPHY_API_KEY ${GIPHY_API_KEY_FILE} \
      --set OPEN_AI_KEY ${OPEN_AI_KEY_FILE}
    '';
  });
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
        wantedBy = [ "multi-user.target" ];
        after = [ "network.target" ];
        path = [ pkgs.ffmpeg ];
      };
      systemd.services.pogbot.enable = true;
    };
}
