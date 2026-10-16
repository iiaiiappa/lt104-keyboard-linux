#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="1.0.0"
RELEASE="1"
PKG_NAME="lt104-keyboard-linux"
BUILD_DIR="$DIR/packaging/build/arch"
DIST_DIR="$DIR/dist"
OUTPUT_PKG="$DIST_DIR/${PKG_NAME}-${VERSION}-${RELEASE}-any.pkg.tar.zst"

mkdir -p "$DIST_DIR"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/pkg"

ROOT="$BUILD_DIR/pkg"
mkdir -p "$ROOT/usr/bin"
mkdir -p "$ROOT/usr/share/lt104"
mkdir -p "$ROOT/usr/share/applications"
mkdir -p "$ROOT/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$ROOT/usr/lib/udev/rules.d"
mkdir -p "$ROOT/usr/lib/udev/hwdb.d"
mkdir -p "$ROOT/usr/lib/systemd/system"

# 1. Copy Application files
cp -r "$DIR"/config.py "$DIR"/i18n.py "$DIR"/lt104_cli.py "$DIR"/lt104_core.py \
      "$DIR"/lt104_remap.py "$DIR"/lt104_gtk.py "$DIR"/lt104_indicator.py \
      "$DIR"/web_app.py "$DIR"/static "$ROOT/usr/share/lt104/"
cp -r "$DIR"/gnome-extension "$ROOT/usr/share/lt104/"

# 2. Wrapper scripts in /usr/bin
cat << 'WRAP' > "$ROOT/usr/bin/lt104"
#!/bin/bash
exec /usr/bin/python3 /usr/share/lt104/lt104_gtk.py "$@"
WRAP
chmod 755 "$ROOT/usr/bin/lt104"

cat << 'WRAPCLI' > "$ROOT/usr/bin/lt104-cli"
#!/bin/bash
exec /usr/bin/python3 /usr/share/lt104/lt104_cli.py "$@"
WRAPCLI
chmod 755 "$ROOT/usr/bin/lt104-cli"

cat << 'WRAPWEB' > "$ROOT/usr/bin/lt104-web"
#!/bin/bash
exec /usr/bin/python3 /usr/share/lt104/web_app.py "${1:-8989}"
WRAPWEB
chmod 755 "$ROOT/usr/bin/lt104-web"

cat << 'WRAPREMAP' > "$ROOT/usr/bin/lt104-remap-keys"
#!/bin/bash
exec /usr/bin/python3 /usr/share/lt104/lt104_remap.py "$@"
WRAPREMAP
chmod 755 "$ROOT/usr/bin/lt104-remap-keys"

# 3. Hardware rules & systemd service
cp "$DIR/99-lt104.rules" "$ROOT/usr/lib/udev/rules.d/99-lt104.rules"
cp "$DIR/99-lt104-win.hwdb" "$ROOT/usr/lib/udev/hwdb.d/99-lt104-win.hwdb"
cp "$DIR/lt104-remap.service" "$ROOT/usr/lib/systemd/system/lt104-remap.service"

# 4. Desktop Entry & Icon
cat << 'DESK' > "$ROOT/usr/share/applications/lt104.desktop"
[Desktop Entry]
Name=LT-104 Keyboard Center
Name[zh_CN]=LT-104 键盘控制中心
Comment=RGB lighting, LCD clock sync, HUD telemetry, and GIF uploader for LangTu LT-104
Exec=/usr/bin/lt104
Icon=lt104
Terminal=false
Type=Application
Categories=Utility;Settings;HardwareSettings;
Keywords=Keyboard;RGB;LangTu;LT104;HUD;
StartupNotify=true
DESK

if [ -f "/usr/share/icons/Yaru/256x256@2x/devices/input-keyboard.png" ]; then
    cp "/usr/share/icons/Yaru/256x256@2x/devices/input-keyboard.png" "$ROOT/usr/share/icons/hicolor/256x256/apps/lt104.png"
else
    cp "$DIR/static/current_hud.png" "$ROOT/usr/share/icons/hicolor/256x256/apps/lt104.png"
fi

# 5. .INSTALL script
cat << 'INSTALL' > "$ROOT/.INSTALL"
post_install() {
    systemd-hwdb update 2>/dev/null || true
    udevadm control --reload-rules 2>/dev/null || true
    udevadm trigger 2>/dev/null || true
    mkdir -p /usr/local/bin
    ln -sf /usr/bin/lt104-remap-keys /usr/local/bin/lt104-remap-keys.py 2>/dev/null || true
    systemctl daemon-reload 2>/dev/null || true
    systemctl enable --now lt104-remap.service 2>/dev/null || true
    /usr/bin/lt104-remap-keys 2>/dev/null || true
}

post_upgrade() {
    post_install
}

post_remove() {
    systemctl stop lt104-remap.service 2>/dev/null || true
    systemctl disable lt104-remap.service 2>/dev/null || true
    systemctl daemon-reload 2>/dev/null || true
    rm -f /usr/local/bin/lt104-remap-keys.py 2>/dev/null || true
    systemd-hwdb update 2>/dev/null || true
    udevadm control --reload-rules 2>/dev/null || true
    udevadm trigger 2>/dev/null || true
}
INSTALL

# Calculate size in bytes
INSTALLED_SIZE=$(du -sb "$ROOT/usr" | awk '{print $1}')
BUILD_DATE=$(date +%s)

# 6. .PKGINFO
cat << PKGINFO > "$ROOT/.PKGINFO"
pkgname = ${PKG_NAME}
pkgver = ${VERSION}-${RELEASE}
pkgdesc = Native Linux USB HID driver, GTK4 app, HUD telemetry, and persistent key remapping for LangTu LT-104
url = https://github.com/iiaiiappa/lt104-keyboard-linux
builddate = ${BUILD_DATE}
packager = iiaiiappa <iiaiiappa@theforwardway.com>
size = ${INSTALLED_SIZE}
arch = any
license = MIT
depend = python
depend = python-gobject
depend = libadwaita
depend = gtk4
PKGINFO

# 7. Package with tar and zstd
echo "Packaging Arch Linux .pkg.tar.zst..."
(
    cd "$ROOT"
    tar --numeric-owner --owner=0 --group=0 -cf - .PKGINFO .INSTALL usr | zstd -c -T0 --ultra -20 > "$OUTPUT_PKG"
)

# 8. Also generate standard PKGBUILD in dist/
cat << 'PKGBUILD' > "$DIST_DIR/PKGBUILD"
# Maintainer: iiaiiappa <iiaiiappa@theforwardway.com>
pkgname=lt104-keyboard-linux
pkgver=1.0.0
pkgrel=1
pkgdesc="Native Linux USB HID driver, GTK4 app, HUD telemetry, and persistent key remapping for LangTu LT-104"
arch=('any')
url="https://github.com/iiaiiappa/lt104-keyboard-linux"
license=('MIT')
depends=('python' 'python-gobject' 'libadwaita' 'gtk4')
source=("https://github.com/iiaiiappa/lt104-keyboard-linux/archive/v${pkgver}.tar.gz")
sha256sums=('SKIP')

package() {
    cd "${srcdir}/${pkgname}-${pkgver}"
    mkdir -p "${pkgdir}/usr/bin"
    mkdir -p "${pkgdir}/usr/share/lt104"
    mkdir -p "${pkgdir}/usr/share/applications"
    mkdir -p "${pkgdir}/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "${pkgdir}/usr/lib/udev/rules.d"
    mkdir -p "${pkgdir}/usr/lib/udev/hwdb.d"
    mkdir -p "${pkgdir}/usr/lib/systemd/system"

    cp -r config.py i18n.py lt104_cli.py lt104_core.py lt104_remap.py \
          lt104_gtk.py lt104_indicator.py web_app.py static gnome-extension "${pkgdir}/usr/share/lt104/"

    install -Dm755 <(echo -e '#!/bin/bash\nexec /usr/bin/python3 /usr/share/lt104/lt104_gtk.py "$@"') "${pkgdir}/usr/bin/lt104"
    install -Dm755 <(echo -e '#!/bin/bash\nexec /usr/bin/python3 /usr/share/lt104/lt104_cli.py "$@"') "${pkgdir}/usr/bin/lt104-cli"
    install -Dm755 <(echo -e '#!/bin/bash\nexec /usr/bin/python3 /usr/share/lt104/web_app.py "${1:-8989}"') "${pkgdir}/usr/bin/lt104-web"
    install -Dm755 <(echo -e '#!/bin/bash\nexec /usr/bin/python3 /usr/share/lt104/lt104_remap.py "$@"') "${pkgdir}/usr/bin/lt104-remap-keys"

    install -Dm644 99-lt104.rules "${pkgdir}/usr/lib/udev/rules.d/99-lt104.rules"
    install -Dm644 99-lt104-win.hwdb "${pkgdir}/usr/lib/udev/hwdb.d/99-lt104-win.hwdb"
    install -Dm644 lt104-remap.service "${pkgdir}/usr/lib/systemd/system/lt104-remap.service"
}
PKGBUILD

echo "✅ Successfully built Arch package: $OUTPUT_PKG"
echo "✅ Generated standard AUR PKGBUILD: $DIST_DIR/PKGBUILD"
