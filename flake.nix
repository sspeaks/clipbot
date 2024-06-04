{
  inputs = {
    nixpkgs.url = "nixpkgs/nixos-24.05";
  };
  outputs = { self, nixpkgs, ... }:
    let
      inherit (self) outputs;
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system}.pkgs;
      lib = pkgs.lib;
    in
    {
      overlays.default = final: prev: {

        pogbot =
          let f = import ./default.nix;
          in lib.makeOverridable f { pkgs = final; };
      };
      packages.${system}.default = pkgs.callPackage ./default.nix { };
      # legacyPackages.${system}.pogbot = outputs.packages.${system}.default;
      nixosModules = {
        pogbot = { pkgs, lib, ... }: {
          imports = [ ./pogbot.nix ];
          nixpkgs.overlays = [ self.overlays.default ];
          services.pogbot.package = lib.mkDefault pkgs.pogbot;
        };
        default = self.nixosModules.pogbot;
      };
      formatter.${system} = pkgs.nixpkgs-fmt;
    };
}
