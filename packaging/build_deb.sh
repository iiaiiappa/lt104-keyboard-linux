#!/bin/bash
set -e

VERSION="1.0.0"
PKG_NAME="lt104-keyboard-linux"
ARCH="all"
BUILD_DIR="packaging/build/deb/${PKG_NAME}_${VERSION}_${ARCH}"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/usr/share/lt104"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/lib/udev/rules.d"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps"

# 1. Control file
cat << CTRL > "$BUILD_DIR/DEBIAN/control"
Package: ${PKG_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Depends: python3, python3-pil, python3-psutil, libadwaita-1-0, gir1.2-adw-1, gir1.2-gtk-4.0
Maintainer: iiaiiappa <iiaiiappa@gmail.com>
Description: LangTu LT-104 RGB mechanical keyboard driver, GTK4 app, web console, and CLI.
 Native Linux USB HID driver for LangTu LT-104 mechanical keyboard (0c45:8009)
 providing RGB backlight control, clock synchronization, hardware telemetry HUD,
 and GIF/animation frame uploader.
CTRL

# 2. Postinst & Postrm
cat << 'POST' > "$BUILD_DIR/DEBIAN/postinst"
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    udevadm control --reload-rules 2>/dev/null || true
    udevadm trigger 2>/dev/null || true
    update-desktop-database 2>/dev/null || true
fi
exit 0
POST
chmod 755 "$BUILD_DIR/DEBIAN/postinst"

cat << 'POSTRM' > "$BUILD_DIR/DEBIAN/postrm"
#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    udevadm control --reload-rules 2>/dev/null || true
    udevadm trigger 2>/dev/null || true
    update-desktop-database 2>/dev/null || true
fi
exit 0
POSTRM
chmod 755 "$BUILD_DIR/DEBIAN/postrm"

# 3. Application files
cp -r config.py i18n.py lt104_cli.py lt104_core.py lt104_gtk.py lt104_indicator.py web_app.py static "$BUILD_DIR/usr/share/lt104/"
cp -r gnome-extension "$BUILD_DIR/usr/share/lt104/"

# 4. CLI / Wrapper scripts in /usr/bin
cat << 'WRAP' > "$BUILD_DIR/usr/bin/lt104"
#!/bin/bash
exec /usr/bin/python3 /usr/share/lt104/lt104_gtk.py "$@"
WRAP
chmod 755 "$BUILD_DIR/usr/bin/lt104"

cat << 'WRAPCLI' > "$BUILD_DIR/usr/bin/lt104-cli"
#!/bin/bash
exec /usr/bin/python3 /usr/share/lt104/lt104_cli.py "$@"
WRAPCLI
chmod 755 "$BUILD_DIR/usr/bin/lt104-cli"

cat << 'WRAPWEB' > "$BUILD_DIR/usr/bin/lt104-web"
#!/bin/bash
exec /usr/bin/python3 /usr/share/lt104/web_app.py "${1:-8989}"
WRAPWEB
chmod 755 "$BUILD_DIR/usr/bin/lt104-web"

# 5. Udev rule
echo 'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0c45", ATTRS{idProduct}=="8009", MODE="0666"' > "$BUILD_DIR/usr/lib/udev/rules.d/99-lt104.rules"

# 6. Desktop launcher
cat << 'DESK' > "$BUILD_DIR/usr/share/applications/lt104.desktop"
[Desktop Entry]
Name=LT-104 Keyboard Center
Name[zh_CN]=LT-104 键盘控制中心
Comment=RGB lighting, LCD clock sync, HUD telemetry, and GIF uploader for LangTu LT-104
Exec=/usr/bin/lt104
Icon=input-keyboard
Terminal=false
Type=Application
Categories=Utility;Settings;HardwareSettings;
Keywords=Keyboard;RGB;LangTu;LT104;HUD;
StartupNotify=true
DESK

# Build the .deb
mkdir -p dist
dpkg-deb --build --root-owner-group "$BUILD_DIR" "dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"
echo "✅ Successfully built dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"
