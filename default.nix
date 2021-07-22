let pkgs = import <nixpkgs> {};
   python = pkgs.python3.withPackages(ps: (with ps; [ python-dotenv aiohttp discordpy pynacl six numpy ]) );
in
 pkgs.stdenv.mkDerivation {
      name = "clipbot";
      buildInputs = [ python ];
      unpackPhase = "true";
      installPhase = ''
        mkdir -p $out/bin
        cp "${./.}/.env" $out/bin/.env
        cp -r "${./assets}" $out/bin/assets
        cp ${./clipbot.py } $out/bin/clipbot
        chmod +x $out/bin/clipbot
      '';
}
