#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="1.0.0"
PKG_NAME="lt104-keyboard-linux"

rm -rf "$DIR/dist"
mkdir -p "$DIR/dist"

echo "=== 1. Building Debian package (.deb) ==="
"$DIR/packaging/build_deb.sh"

echo "=== 2. Building Red Hat / Fedora package (.rpm) ==="
"$DIR/packaging/build_rpm.sh"

echo "=== 3. Building Universal Linux AppImage (.AppImage) ==="
"$DIR/packaging/build_appimage.sh"

echo "=== 4. Building Arch Linux Package (.pkg.tar.zst) and PKGBUILD ==="
"$DIR/packaging/build_arch.sh"

echo "=== 5. Building Portable Linux Standalone Bundle (.tar.gz) ==="
TAR_DIR="$DIR/packaging/build/portable/${PKG_NAME}-${VERSION}"
rm -rf "$DIR/packaging/build/portable"
mkdir -p "$TAR_DIR"
cp -r "$DIR"/config.py "$DIR"/i18n.py "$DIR"/lt104_cli.py "$DIR"/lt104_core.py \
      "$DIR"/lt104_remap.py "$DIR"/lt104_gtk.py "$DIR"/lt104_indicator.py \
      "$DIR"/web_app.py "$DIR"/lt104.sh "$DIR"/static "$DIR"/gnome-extension \
      "$DIR"/99-lt104.rules "$DIR"/99-lt104-win.hwdb "$DIR"/lt104-remap.service \
      "$DIR"/LICENSE "$DIR"/README.md "$TAR_DIR/"

cat << 'INS' > "$TAR_DIR/install.sh"
#!/bin/bash
set -e
echo "=== Installing LangTu LT-104 Keyboard Driver & Key Remappings ==="

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Install Udev Rules
if [ -d "/etc/udev/rules.d" ]; then
    echo "Installing udev rule to /etc/udev/rules.d/99-lt104.rules..."
    sudo cp "$DIR/99-lt104.rules" /etc/udev/rules.d/99-lt104.rules
    sudo udevadm control --reload-rules 2>/dev/null || true
    sudo udevadm trigger 2>/dev/null || true
fi

# 2. Install Hardware Database (hwdb)
if [ -d "/etc/udev/hwdb.d" ]; then
    echo "Installing hwdb mapping to /etc/udev/hwdb.d/99-lt104-win.hwdb..."
    sudo cp "$DIR/99-lt104-win.hwdb" /etc/udev/hwdb.d/99-lt104-win.hwdb
    sudo systemd-hwdb update 2>/dev/null || true
    sudo udevadm trigger 2>/dev/null || true
fi

# 3. Install CLI binaries & remap script
sudo install -m 755 "$DIR/lt104_remap.py" /usr/bin/lt104-remap-keys
sudo ln -sf /usr/bin/lt104-remap-keys /usr/local/bin/lt104-remap-keys.py 2>/dev/null || true

# 4. Install systemd service
if [ -d "/etc/systemd/system" ]; then
    echo "Installing systemd remap service..."
    sudo cp "$DIR/lt104-remap.service" /etc/systemd/system/lt104-remap.service
    sudo systemctl daemon-reload 2>/dev/null || true
    sudo systemctl enable --now lt104-remap.service 2>/dev/null || true
fi

# 5. Immediately apply remap to currently connected keyboards
echo "Applying key remap to currently connected keyboards..."
sudo /usr/bin/lt104-remap-keys || true

# 6. Desktop application launcher
TARGET_DIR="${HOME}/.local/share/applications"
mkdir -p "$TARGET_DIR"
cat << APPDESK > "$TARGET_DIR/lt104.desktop"
[Desktop Entry]
Name=LT-104 Keyboard Center
Name[zh_CN]=LT-104 键盘控制中心
Comment=RGB lighting, LCD clock sync, HUD telemetry, and GIF uploader for LangTu LT-104
Exec=python3 ${DIR}/lt104_gtk.py
Icon=input-keyboard
Terminal=false
Type=Application
Categories=Utility;Settings;HardwareSettings;
Keywords=Keyboard;RGB;LangTu;LT104;HUD;
StartupNotify=true
APPDESK
update-desktop-database "$TARGET_DIR" 2>/dev/null || true

echo "✅ Installation complete! Key mappings and hardware rules are active."
echo "   Left Alt + Tab   -> Single horizontal row window switcher"
echo "   Right Alt + Tab  -> Single horizontal row window switcher (identical)"
echo "   Left Win + Tab   -> Workspaces switcher"
echo "   Left Win (alone) -> GNOME Menu / ArcMenu"
echo "   Menu key         -> Context Menu / Compose"
echo ""
echo "You can launch:"
echo "   python3 lt104_gtk.py      # GTK4 Desktop App"
echo "   python3 web_app.py 8989   # Web Control Panel"
echo "   lt104-cli status          # Check keyboard status"
INS
chmod +x "$TAR_DIR/install.sh"

tar -czf "$DIR/dist/${PKG_NAME}-${VERSION}-linux-portable.tar.gz" -C "$DIR/packaging/build/portable" "${PKG_NAME}-${VERSION}"

echo "=== 6. Packaging GNOME Shell Extension bundle (.zip) ==="
(cd "$DIR/gnome-extension" && zip -r "../dist/lt104-indicator@theforwardway.com.v${VERSION}.shell-extension.zip" . -x "*.git*")

echo "=== 7. Generating SHA256 Checksums ==="
(cd "$DIR/dist" && sha256sum -- *.deb *.rpm *.AppImage *.pkg.tar.zst *.tar.gz *.zip PKGBUILD > SHA256SUMS.txt)

echo "=== Build Complete! All Release Artifacts in dist/ ==="
ls -lh "$DIR/dist/"
