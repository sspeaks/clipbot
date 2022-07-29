let pkgs = import <nixpkgs> {};
   python = pkgs.python3.withPackages(ps: (with ps; [ python-dotenv aiohttp discordpy pynacl six numpy ]) );
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
