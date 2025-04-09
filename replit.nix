{pkgs}: {
  deps = [
    pkgs.rustc
    pkgs.libiconv
    pkgs.cargo
    pkgs.bash
    pkgs.geos
    pkgs.openldap
    pkgs.cyrus_sasl
    pkgs.postgresql
    pkgs.openssl
  ];
}
