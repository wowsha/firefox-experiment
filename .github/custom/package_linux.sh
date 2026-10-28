#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$1" && pwd)"
mkdir -p "$2"
OUTPUT_DIR="$(cd "$2" && pwd)"
OBJ_DIR="$SOURCE_DIR/obj-browser"
BIN_DIR="$OBJ_DIR/dist/bin"

test -x "$BIN_DIR/firefox"
ARCHIVE="$(find "$OBJ_DIR/dist" -maxdepth 1 -type f \( -name '*.tar.bz2' -o -name '*.tar.xz' -o -name '*.tar.zst' \) -print -quit)"
if [[ -z "$ARCHIVE" ]]; then
  echo "No Firefox Linux package archive found under $OBJ_DIR/dist" >&2
  exit 1
fi

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/opt/browser" "$STAGE/usr/bin" "$STAGE/usr/share/applications" "$STAGE/DEBIAN"

tar -xf "$ARCHIVE" -C "$STAGE/opt/browser" --strip-components=1
cat > "$STAGE/usr/bin/browser" <<'LAUNCHER'
#!/bin/sh
exec /opt/browser/firefox "$@"
LAUNCHER
chmod 0755 "$STAGE/usr/bin/browser"

cat > "$STAGE/usr/share/applications/browser.desktop" <<'DESKTOP'
[Desktop Entry]
Name=Browser
Comment=Simple web browser
Exec=browser %u
Terminal=false
Type=Application
Icon=web-browser
Categories=Network;WebBrowser;
MimeType=text/html;text/xml;application/xhtml+xml;x-scheme-handler/http;x-scheme-handler/https;
DESKTOP

VERSION="$(awk -F= '/^Version=/{print $2; exit}' "$STAGE/opt/browser/application.ini" 2>/dev/null || true)"
if [[ -z "$VERSION" ]]; then VERSION="1.0.0"; fi
VERSION="$(printf '%s' "$VERSION" | tr -cd 'A-Za-z0-9.+:~_-')"
cat > "$STAGE/DEBIAN/control" <<CONTROL
Package: browser
Version: $VERSION
Section: web
Priority: optional
Architecture: amd64
Maintainer: Browser Project
Depends: libc6, libgcc-s1, libstdc++6, libgtk-3-0, libnss3, libdbus-glib-1-2, libasound2
Description: Minimal, unbranded Firefox ESR-based web browser with uBlock Origin
CONTROL

PACKAGE="$OUTPUT_DIR/Browser_"$VERSION"_amd64.deb"
dpkg-deb --build --root-owner-group "$STAGE" "$PACKAGE"
echo "Created $PACKAGE"
