#!/bin/bash
set -e

# Requires linuxdeploy and linuxdeploy-plugin-python in PATH

APPDIR=AppDir
APP=io.github.fernandomema.minecraft-server-manager-gtk

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"

# Copy application files
cp -r main.py controllers models utils views __init__.py "$APPDIR/usr/bin/"
cp minecraft-server-manager.sh "$APPDIR/usr/bin/minecraft-server-manager"
chmod +x "$APPDIR/usr/bin/minecraft-server-manager"

# Desktop entry and icons
install -Dm644 io.github.fernandomema.minecraft-server-manager-gtk.desktop "$APPDIR/usr/share/applications/$APP.desktop"
install -Dm644 io.github.fernandomema.minecraft-server-manager-gtk.svg "$APPDIR/usr/share/icons/hicolor/scalable/apps/$APP.svg"
install -Dm644 io.github.fernandomema.minecraft-server-manager-gtk-128.png "$APPDIR/usr/share/icons/hicolor/128x128/apps/$APP.png"
install -Dm644 io.github.fernandomema.minecraft-server-manager-gtk-64.png "$APPDIR/usr/share/icons/hicolor/64x64/apps/$APP.png"
install -Dm644 io.github.fernandomema.minecraft-server-manager-gtk-48.png "$APPDIR/usr/share/icons/hicolor/48x48/apps/$APP.png"

# Build AppImage using linuxdeploy and the python plugin
linuxdeploy \
    --appdir "$APPDIR" \
    --executable "$APPDIR/usr/bin/minecraft-server-manager" \
    --desktop-file "$APPDIR/usr/share/applications/$APP.desktop" \
    --icon-file io.github.fernandomema.minecraft-server-manager-gtk.svg \
    --plugin python \
    --output appimage
