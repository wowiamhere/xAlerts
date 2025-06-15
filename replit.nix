{ pkgs }: {
  deps = [
    pkgs.chromium
    pkgs.chromedriver
    pkgs.xorg.xorgserver
    pkgs.python312Packages.selenium
  ];
}
