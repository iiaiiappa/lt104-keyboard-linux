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
mkdir -p "$BUILD_DIR/usr/lib/udev/hwdb.d"
mkdir -p "$BUILD_DIR/lib/systemd/system"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps"

# 1. Control file
cat << CTRL > "$BUILD_DIR/DEBIAN/control"
Package: ${PKG_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Depends: python3, python3-pil, python3-psutil, libadwaita-1-0, gir1.2-adw-1, gir1.2-gtk-4.0
Recommends: python3-evdev
Maintainer: iiaiiappa <iiaiiappa@gmail.com>
Description: LangTu LT-104 RGB mechanical keyboard driver, GTK4 app, web console, and CLI.
 Native Linux USB HID driver and persistent key remapping for LangTu LT-104
 mechanical keyboard (0c45:8009 wired & 05ac:024f 2.4G wireless dongle).
 Features automatic scancode remapping for Left Alt, Right Alt, Left Win, and Menu,
 RGB backlight control, clock synchronization, hardware telemetry HUD,
 and GIF/animation frame uploader.
CTRL

# 2. Postinst & Postrm
cat << 'POST' > "$BUILD_DIR/DEBIAN/postinst"
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    # Compile hwdb mappings
    systemd-hwdb update 2>/dev/null || true

    # Reload and trigger udev rules
    udevadm control --reload-rules 2>/dev/null || true
    udevadm trigger 2>/dev/null || true

    # Symlink legacy /usr/local/bin path to /usr/bin/lt104-remap-keys
    mkdir -p /usr/local/bin
    ln -sf /usr/bin/lt104-remap-keys /usr/local/bin/lt104-remap-keys.py 2>/dev/null || true

    # Enable and start keyboard remap system service
    systemctl daemon-reload 2>/dev/null || true
    systemctl enable lt104-remap.service 2>/dev/null || true
    systemctl start lt104-remap.service 2>/dev/null || true

    # Apply remap immediately to all currently connected keyboards
    /usr/bin/lt104-remap-keys 2>/dev/null || true

    update-desktop-database 2>/dev/null || true
fi
exit 0
POST
chmod 755 "$BUILD_DIR/DEBIAN/postinst"

cat << 'POSTRM' > "$BUILD_DIR/DEBIAN/postrm"
#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    systemctl stop lt104-remap.service 2>/dev/null || true
    systemctl disable lt104-remap.service 2>/dev/null || true
    systemctl daemon-reload 2>/dev/null || true
    rm -f /usr/local/bin/lt104-remap-keys.py 2>/dev/null || true
    systemd-hwdb update 2>/dev/null || true
    udevadm control --reload-rules 2>/dev/null || true
    udevadm trigger 2>/dev/null || true
    update-desktop-database 2>/dev/null || true
fi
exit 0
POSTRM
chmod 755 "$BUILD_DIR/DEBIAN/postrm"

# 3. Application files
cp -r config.py i18n.py lt104_cli.py lt104_core.py lt104_remap.py lt104_gtk.py lt104_indicator.py web_app.py static "$BUILD_DIR/usr/share/lt104/"
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

cat << 'WRAPREMAP' > "$BUILD_DIR/usr/bin/lt104-remap-keys"
#!/bin/bash
exec /usr/bin/python3 /usr/share/lt104/lt104_remap.py "$@"
WRAPREMAP
chmod 755 "$BUILD_DIR/usr/bin/lt104-remap-keys"

# 5. Udev rule, hwdb, and systemd service
cp 99-lt104.rules "$BUILD_DIR/usr/lib/udev/rules.d/99-lt104.rules"
cp 99-lt104-win.hwdb "$BUILD_DIR/usr/lib/udev/hwdb.d/99-lt104-win.hwdb"
cp lt104-remap.service "$BUILD_DIR/lib/systemd/system/lt104-remap.service"

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
