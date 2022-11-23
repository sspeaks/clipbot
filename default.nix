let pkgs = import <nixpkgs> {};
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
    python = pkgs.python39.withPackages(ps: (with ps; [
      python-dotenv aiohttp discordpy pynacl six numpy azure-identity
     ]) ++ [ auzre-data-tables ] );

in
 pkgs.stdenv.mkDerivation {
      name = "pogbot";
      buildInputs = [ python ];
      unpackPhase = "true";
      installPhase = ''
        mkdir -p $out/bin
        cp "${./.}/.env" $out/bin/.env
        ln -s "/home/sspeaks/pogbot/assets" $out/bin/assets
        cp ${./pogbot.py } $out/bin/pogbot
        chmod +x $out/bin/pogbot
      '';
}
