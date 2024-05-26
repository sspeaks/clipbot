{
  inputs = {
    nixpkgs.url = "nixpkgs/nixos-23.11";
  };
  outputs = { self, nixpkgs, ... }:
    let
      inherit (self) outputs;
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system}.pkgs;
    in
    {
      overlays.default = final: prev: {
        pogbot = import ./default.nix { pkgs = final; };
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
