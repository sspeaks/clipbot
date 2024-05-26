{ pkgs, ... }:
let
  auzre-data-tables = pkgs.python39Packages.buildPythonPackage rec {
    pname = "azure-data-tables";
    version = "12.4.0";
    src = pkgs.python39Packages.fetchPypi {
      inherit pname version;
      extension = "zip";
      sha256 = "sha256-3V/I3pHi+JCO+kxkyn9jz4OzBoqbpCYpjeO1QTnpZlw=";
    };
    propagatedBuildInputs = with pkgs.python39Packages; [
      azure-core
      msrest
    ];
    # has no tests
    doCheck = false;
    pythonImportsCheck = [ "azure.data.tables" ];
  };

  azure-storage-blob = pkgs.python39Packages.buildPythonPackage rec {
    pname = "azure-storage-blob";
    version = "12.4.0";
    src = pkgs.python39Packages.fetchPypi {
      inherit pname version;
      extension = "zip";
      sha256 = "sha256-lqCbL/I012I2Z+EALJFrW1YuWCnqYrQXUwn2WrBqA+g=";
    };
    propagatedBuildInputs = with pkgs.python39Packages; [
      azure-core
      msrest
    ];
    # has no tests
    doCheck = false;
    pythonImportsCheck = [ "azure.storage.blob" ];
  };

  discordpy = pkgs.python39Packages.buildPythonPackage rec {
    pname = "discord.py";
    version = "2.2.2";

    src = pkgs.python39Packages.fetchPypi {
      inherit pname version;
      extension = "tar.gz";
      sha256 = "sha256-uZRAVry1cRstBAiISP0ARGbPEXwVyE+nmL9VRw8oJ18=";
    };

    propagatedBuildInputs = with pkgs.python39Packages; [
      aiohttp
      pynacl
    ];

    # has no tests
    doCheck = false;

    pythonImportsCheck = [ "discord" ];
  };

  openai = pkgs.python39Packages.buildPythonPackage rec {
    pname = "openai";
    version = "0.27.1";

    src = pkgs.python39Packages.fetchPypi {
      inherit pname version;
      extension = "tar.gz";
      sha256 = "11a8eb9b609653295be6cc67febecd5189f17b22ef015462c5003d8959567fd7";
    };

    propagatedBuildInputs = with pkgs.python39Packages; [ aiohttp requests tqdm ];

    doCheck = false;

    pythonImportsCheck = [ "openai" ];
  };

  python = pkgs.python39.withPackages (ps: (with ps; [
    python-dotenv
    aiohttp
    pynacl
    six
    numpy
    azure-identity
  ]) ++ [ auzre-data-tables openai discordpy azure-storage-blob ]);

in
pkgs.stdenv.mkDerivation rec {
  name = "pogbot";
  buildInputs = [ python pkgs.ffmpeg pkgs.makeWrapper ];
  propagatedBuildInputs = with pkgs; [ libopus ];
  unpackPhase = "true";

  /*
  *  Files that store the contents of these needed values
  */
  ASSETS_PATH_FILE = "/dev/null";
  DISCORD_TOKEN_FILE = "/dev/null";
  GIPHY_API_KEY_FILE = "/dev/null";
  OPEN_AI_KEY_FILE = "/dev/null";

  installPhase = ''
    mkdir -p $out/bin
    # cp "${./.}/.env" $out/bin/.env
    ln -s "$(cat ${ASSETS_PATH_FILE})/assets" $out/bin/assets
    cp ${./pogbot.py } $out/bin/pogbot
    chmod +x $out/bin/pogbot
  '';
  postFixup = ''
    wrapProgram $out/bin/pogbot \
    --prefix PATH : ${pkgs.lib.makeBinPath [pkgs.ffmpeg]} \
    --prefix LD_LIBRARY_PATH : ${pkgs.lib.makeLibraryPath [pkgs.libopus] } \
    --set ASSETS_PATH ${ASSETS_PATH_FILE} \
    --set DISCORD_TOKEN ${DISCORD_TOKEN_FILE} \
    --set GIPHY_API_KEY ${GIPHY_API_KEY_FILE} \
    --set OPEN_AI_KEY ${OPEN_AI_KEY_FILE}
  '';
}
