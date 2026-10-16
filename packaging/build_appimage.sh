#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="1.0.0"
APP_DIR="$DIR/packaging/build/AppDir"
DIST_DIR="$DIR/dist"
OUTPUT_FILE="$DIST_DIR/LT104-Keyboard-Center-${VERSION}-x86_64.AppImage"

mkdir -p "$DIST_DIR"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/usr/bin"
mkdir -p "$APP_DIR/usr/share/lt104"
mkdir -p "$APP_DIR/usr/share/applications"
mkdir -p "$APP_DIR/usr/share/icons/hicolor/256x256/apps"

# Copy application files
cp -r "$DIR"/config.py "$DIR"/i18n.py "$DIR"/lt104_cli.py "$DIR"/lt104_core.py \
      "$DIR"/lt104_remap.py "$DIR"/lt104_gtk.py "$DIR"/lt104_indicator.py \
      "$DIR"/web_app.py "$DIR"/static "$DIR"/gnome-extension \
      "$DIR"/99-lt104.rules "$DIR"/99-lt104-win.hwdb "$DIR"/lt104-remap.service \
      "$APP_DIR/usr/share/lt104/"

# Icons
if [ -f "/usr/share/icons/Yaru/256x256@2x/devices/input-keyboard.png" ]; then
    cp "/usr/share/icons/Yaru/256x256@2x/devices/input-keyboard.png" "$APP_DIR/usr/share/icons/hicolor/256x256/apps/lt104.png"
    cp "/usr/share/icons/Yaru/256x256@2x/devices/input-keyboard.png" "$APP_DIR/lt104.png"
else
    cp "$DIR/static/current_hud.png" "$APP_DIR/usr/share/icons/hicolor/256x256/apps/lt104.png"
    cp "$DIR/static/current_hud.png" "$APP_DIR/lt104.png"
fi

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
elif [ "$1" = "remap" ]; then
    shift
    exec python3 "${HERE}/usr/share/lt104/lt104_remap.py" "$@"
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

echo "Building AppImage package..."
TOOL="$DIR/packaging/tools/appimagetool"
if [ ! -f "$TOOL" ]; then
    mkdir -p "$DIR/packaging/tools"
    wget -qO "$TOOL" "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$TOOL"
fi

ARCH=x86_64 "$TOOL" --appimage-extract-and-run "$APP_DIR" "$OUTPUT_FILE"
chmod +x "$OUTPUT_FILE"

echo "✅ Successfully built AppImage: $OUTPUT_FILE"
