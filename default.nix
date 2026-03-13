{ pkgs
, assetsPath ? "/dev/null"
, discordToken ? "/dev/null"
, giphyApiKey ? "/dev/null"
, openAiApiKey ? "/dev/null"
, ...
}:
let
  setuptools = pkgs.python312Packages.setuptools;
  auzre-data-tables = pkgs.python312Packages.buildPythonPackage rec {
    #  To build with setuptools as before, set `pyproject = true` and `build-system = [ setuptools ]`.`
    pname = "azure-data-tables";
    version = "12.4.0";
    src = pkgs.python312Packages.fetchPypi {
      inherit pname version;
      extension = "zip";
      sha256 = "sha256-3V/I3pHi+JCO+kxkyn9jz4OzBoqbpCYpjeO1QTnpZlw=";
    };
    propagatedBuildInputs = with pkgs.python312Packages; [
      azure-core
      msrest
    ];
    pyproject = true;
    build-system = [ setuptools ];
    # has no tests
    doCheck = false;
    pythonImportsCheck = [ "azure.data.tables" ];
  };

  azure-storage-blob = pkgs.python312Packages.buildPythonPackage rec {
    pname = "azure-storage-blob";
    version = "12.4.0";
    src = pkgs.python312Packages.fetchPypi {
      inherit pname version;
      extension = "zip";
      sha256 = "sha256-lqCbL/I012I2Z+EALJFrW1YuWCnqYrQXUwn2WrBqA+g=";
    };
    propagatedBuildInputs = with pkgs.python312Packages; [
      azure-core
      msrest
      cryptography
    ];
    pyproject = true;
    build-system = [ setuptools ];
    # has no tests
    doCheck = false;
    pythonImportsCheck = [ "azure.storage.blob" ];
  };

  discordpy = pkgs.python312Packages.buildPythonPackage rec {
    pname = "discord_py";
    version = "2.6.0";

    src = pkgs.python312Packages.fetchPypi {
      inherit pname version;
      extension = "tar.gz";
      sha256 = "8aa0f017524734653e6ddddb7878e1cdf8c3868bd7d1a386c36cd8373e5fba02";
    };

    propagatedBuildInputs = with pkgs.python312Packages; [
      aiohttp
      pynacl
    ];
    pyproject = true;
    build-system = [ setuptools ];

    # has no tests
    doCheck = false;

    pythonImportsCheck = [ "discord" ];
  };

  discord-ext-voice-recv = pkgs.python312Packages.buildPythonPackage rec {
    pname = "discord_ext_voice_recv";
    version = "0.5.2a179";

    src = pkgs.python312Packages.fetchPypi {
      inherit pname version;
      extension = "tar.gz";
      sha256 = "6cb8f5ff60c3885020e5ebd879323dc97ebb0745788f3778a14ef31810f848a8";
    };

    propagatedBuildInputs = [ discordpy ] ++ (with pkgs.python312Packages; [ pynacl ]);
    pyproject = true;
    build-system = [ setuptools ];

    doCheck = false;

    pythonImportsCheck = [ "discord.ext.voice_recv" ];
  };

  openai = pkgs.python312Packages.buildPythonPackage rec {
    pname = "openai";
    version = "0.27.1";

    src = pkgs.python312Packages.fetchPypi {
      inherit pname version;
      extension = "tar.gz";
      sha256 = "11a8eb9b609653295be6cc67febecd5189f17b22ef015462c5003d8959567fd7";
    };

    propagatedBuildInputs = with pkgs.python312Packages; [ aiohttp requests tqdm ];
    pyproject = true;
    build-system = [ setuptools ];

    doCheck = false;

    pythonImportsCheck = [ "openai" ];
  };

  python = pkgs.python312.withPackages (ps: (with ps; [
    python-dotenv
    aiohttp
    pynacl
    six
    numpy
    azure-identity
  ]) ++ [ auzre-data-tables openai discordpy discord-ext-voice-recv azure-storage-blob ]);

in
pkgs.stdenv.mkDerivation rec {
  name = "pogbot";
  buildInputs = [ python pkgs.ffmpeg pkgs.makeWrapper ];
  propagatedBuildInputs = with pkgs; [ libopus ];
  unpackPhase = "true";

  /*
  *  Files that store the contents of these needed values
  */
  ASSETS_PATH_FILE = assetsPath;
  DISCORD_TOKEN_FILE = discordToken;
  GIPHY_API_KEY_FILE = giphyApiKey;
  OPEN_AI_KEY_FILE = openAiApiKey;

  installPhase = ''
    mkdir -p $out/bin $out/lib
    ln -s "$(cat ${ASSETS_PATH_FILE})/assets" $out/bin/assets
    cp -r ${./pogbot} $out/lib/pogbot
    cat > $out/bin/pogbot <<EOF
#!/usr/bin/env python
import runpy, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
runpy.run_module('pogbot', run_name='__main__')
EOF
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
