{ pkgs }: {
  deps = [
    pkgs.chromium
    pkgs.chromedriver
    pkgs.xorg.xvfb
    pkgs.python312Packages.selenium
  ];
}
