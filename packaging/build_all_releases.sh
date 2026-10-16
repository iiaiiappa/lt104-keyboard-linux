#!/bin/bash
set -e

VERSION="1.0.0"
PKG_NAME="lt104-keyboard-linux"
rm -rf dist
mkdir -p dist

echo "=== 1. Building Debian package (.deb) ==="
./packaging/build_deb.sh

echo "=== 2. Building Portable Linux Standalone Bundle (.tar.gz) ==="
TAR_DIR="packaging/build/portable/${PKG_NAME}-${VERSION}"
rm -rf packaging/build/portable
mkdir -p "$TAR_DIR"
cp -r config.py i18n.py lt104_cli.py lt104_core.py lt104_gtk.py lt104_indicator.py web_app.py lt104.sh static gnome-extension LICENSE README.md "$TAR_DIR/"

cat << 'INS' > "$TAR_DIR/install.sh"
#!/bin/bash
set -e
echo "=== Installing LangTu LT-104 Keyboard Driver ==="

if [ -d "/etc/udev/rules.d" ]; then
    echo "Installing udev rule to /etc/udev/rules.d/99-lt104.rules..."
    echo 'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0c45", ATTRS{idProduct}=="8009", MODE="0666"' | sudo tee /etc/udev/rules.d/99-lt104.rules > /dev/null
    sudo udevadm control --reload-rules 2>/dev/null || true
    sudo udevadm trigger 2>/dev/null || true
fi

TARGET_DIR="${HOME}/.local/share/applications"
mkdir -p "$TARGET_DIR"
cat << APPDESK > "$TARGET_DIR/lt104.desktop"
[Desktop Entry]
Name=LT-104 Keyboard Center
Name[zh_CN]=LT-104 键盘控制中心
Comment=RGB lighting, LCD clock sync, HUD telemetry, and GIF uploader for LangTu LT-104
Exec=python3 $(pwd)/lt104_gtk.py
Icon=input-keyboard
Terminal=false
Type=Application
Categories=Utility;Settings;HardwareSettings;
Keywords=Keyboard;RGB;LangTu;LT104;HUD;
StartupNotify=true
APPDESK
update-desktop-database "$TARGET_DIR" 2>/dev/null || true

echo "✅ Installation complete! You can run:"
echo "   python3 lt104_gtk.py      # GTK4 Desktop App"
echo "   python3 web_app.py 8989   # Web Control Panel"
echo "   python3 lt104_cli.py      # CLI utility"
INS
chmod +x "$TAR_DIR/install.sh"

tar -czf "dist/${PKG_NAME}-${VERSION}-linux-portable.tar.gz" -C "packaging/build/portable" "${PKG_NAME}-${VERSION}"

echo "=== 3. Packaging GNOME Shell Extension bundle (.zip) ==="
(cd gnome-extension && zip -r "../dist/lt104-indicator@theforwardway.com.v${VERSION}.shell-extension.zip" . -x "*.git*")

echo "=== 4. Generating SHA256 Checksums ==="
(cd dist && sha256sum -- *.deb *.tar.gz *.zip > SHA256SUMS.txt)

echo "=== Build Complete! Artifacts in dist/ ==="
ls -lh dist/
