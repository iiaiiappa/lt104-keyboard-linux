#!/bin/bash
set -e

VERSION="1.0.0"
APP_DIR="packaging/build/AppDir"

rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/usr/bin"
mkdir -p "$APP_DIR/usr/share/lt104"
mkdir -p "$APP_DIR/usr/share/applications"
mkdir -p "$APP_DIR/usr/share/icons/hicolor/256x256/apps"

# Copy files
cp -r config.py i18n.py lt104_cli.py lt104_core.py lt104_gtk.py lt104_indicator.py web_app.py static gnome-extension "$APP_DIR/usr/share/lt104/"
cp static/keyboard_skin_lit.png "$APP_DIR/usr/share/icons/hicolor/256x256/apps/lt104.png"
cp static/keyboard_skin_lit.png "$APP_DIR/lt104.png"

# AppRun script
cat << 'APPRUN' > "$APP_DIR/AppRun"
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PYTHONPATH="${HERE}/usr/share/lt104:${PYTHONPATH}"
export PATH="${HERE}/usr/bin:${PATH}"

if [ "$1" = "web" ]; then
    exec python3 "${HERE}/usr/share/lt104/web_app.py" "${2:-8989}"
elif [ "$1" = "cli" ]; then
    shift
    exec python3 "${HERE}/usr/share/lt104/lt104_cli.py" "$@"
else
    exec python3 "${HERE}/usr/share/lt104/lt104_gtk.py" "$@"
fi
APPRUN
chmod 755 "$APP_DIR/AppRun"

# Desktop entry
cat << 'DESK' > "$APP_DIR/lt104.desktop"
[Desktop Entry]
Name=LT-104 Keyboard Center
Name[zh_CN]=LT-104 键盘控制中心
Comment=RGB lighting, LCD clock sync, HUD telemetry, and GIF uploader for LangTu LT-104
Exec=AppRun
Icon=lt104
Terminal=false
Type=Application
Categories=Utility;Settings;HardwareSettings;
Keywords=Keyboard;RGB;LangTu;LT104;HUD;
StartupNotify=true
DESK
cp "$APP_DIR/lt104.desktop" "$APP_DIR/usr/share/applications/lt104.desktop"

echo "✅ AppDir prepared at $APP_DIR"
