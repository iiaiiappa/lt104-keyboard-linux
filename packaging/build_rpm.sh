#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="1.0.0"
RELEASE="1"
PKG_NAME="lt104-keyboard-linux"
BUILD_DIR="$DIR/packaging/build/rpm"
DIST_DIR="$DIR/dist"

mkdir -p "$DIST_DIR"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"/{BUILD,RPMS,SOURCES,SPECS,SRPMS,BUILDROOT}
mkdir -p "$BUILD_DIR/rpmdb"

STAGING="$BUILD_DIR/staging"
rm -rf "$STAGING"
mkdir -p "$STAGING/usr/bin"
mkdir -p "$STAGING/usr/share/lt104"
mkdir -p "$STAGING/usr/share/applications"
mkdir -p "$STAGING/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$STAGING/usr/lib/udev/rules.d"
mkdir -p "$STAGING/usr/lib/udev/hwdb.d"
mkdir -p "$STAGING/lib/systemd/system"

# 1. Copy Application files
cp -r "$DIR"/config.py "$DIR"/i18n.py "$DIR"/lt104_cli.py "$DIR"/lt104_core.py \
      "$DIR"/lt104_remap.py "$DIR"/lt104_gtk.py "$DIR"/lt104_indicator.py \
      "$DIR"/web_app.py "$DIR"/static "$STAGING/usr/share/lt104/"
cp -r "$DIR"/gnome-extension "$STAGING/usr/share/lt104/"

# 2. Wrapper scripts in /usr/bin
cat << 'WRAP' > "$STAGING/usr/bin/lt104"
#!/bin/bash
exec /usr/bin/python3 /usr/share/lt104/lt104_gtk.py "$@"
WRAP
chmod 755 "$STAGING/usr/bin/lt104"

cat << 'WRAPCLI' > "$STAGING/usr/bin/lt104-cli"
#!/bin/bash
exec /usr/bin/python3 /usr/share/lt104/lt104_cli.py "$@"
WRAPCLI
chmod 755 "$STAGING/usr/bin/lt104-cli"

cat << 'WRAPWEB' > "$STAGING/usr/bin/lt104-web"
#!/bin/bash
exec /usr/bin/python3 /usr/share/lt104/web_app.py "${1:-8989}"
WRAPWEB
chmod 755 "$STAGING/usr/bin/lt104-web"

cat << 'WRAPREMAP' > "$STAGING/usr/bin/lt104-remap-keys"
#!/bin/bash
exec /usr/bin/python3 /usr/share/lt104/lt104_remap.py "$@"
WRAPREMAP
chmod 755 "$STAGING/usr/bin/lt104-remap-keys"

# 3. Hardware rules & systemd service
cp "$DIR/99-lt104.rules" "$STAGING/usr/lib/udev/rules.d/99-lt104.rules"
cp "$DIR/99-lt104-win.hwdb" "$STAGING/usr/lib/udev/hwdb.d/99-lt104-win.hwdb"
cp "$DIR/lt104-remap.service" "$STAGING/lib/systemd/system/lt104-remap.service"

# 4. Desktop Entry & Icon
cat << 'DESK' > "$STAGING/usr/share/applications/lt104.desktop"
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

# Extract high-res icon
if [ -f "/usr/share/icons/Yaru/256x256@2x/devices/input-keyboard.png" ]; then
    cp "/usr/share/icons/Yaru/256x256@2x/devices/input-keyboard.png" "$STAGING/usr/share/icons/hicolor/256x256/apps/lt104.png"
elif [ -f "/usr/share/icons/hicolor/256x256/apps/input-keyboard.png" ]; then
    cp "/usr/share/icons/hicolor/256x256/apps/input-keyboard.png" "$STAGING/usr/share/icons/hicolor/256x256/apps/lt104.png"
else
    # Fallback to copy from static
    cp "$DIR/static/current_hud.png" "$STAGING/usr/share/icons/hicolor/256x256/apps/lt104.png"
fi

# 5. Write RPM Spec file
cat << SPEC > "$BUILD_DIR/SPECS/${PKG_NAME}.spec"
Name:           ${PKG_NAME}
Version:        ${VERSION}
Release:        ${RELEASE}%{?dist}
Summary:        LangTu LT-104 RGB mechanical keyboard driver, GTK4 app, web console, and CLI
License:        MIT
URL:            https://github.com/iiaiiappa/lt104-keyboard-linux
BuildArch:      noarch

AutoReqProv:    no
Requires:       python3, libadwaita, gtk4

%description
Native Linux USB HID driver and persistent key remapping for LangTu LT-104
mechanical keyboard (0c45:8009 wired & 05ac:024f 2.4G wireless dongle).
Features automatic scancode remapping for Left Alt, Right Alt, Left Win, and Menu,
RGB backlight control, clock synchronization, hardware telemetry HUD,
and GIF/animation frame uploader. Compatible with Fedora, RHEL, CentOS, Rocky Linux,
AlmaLinux, and openSUSE.

%install
mkdir -p %{buildroot}
cp -a ${STAGING}/* %{buildroot}/

%post
# Compile hwdb mappings
systemd-hwdb update 2>/dev/null || true
# Reload and trigger udev rules
udevadm control --reload-rules 2>/dev/null || true
udevadm trigger 2>/dev/null || true
# Legacy symlink for compatibility
mkdir -p /usr/local/bin
ln -sf /usr/bin/lt104-remap-keys /usr/local/bin/lt104-remap-keys.py 2>/dev/null || true
# Enable and start key remap service
systemctl daemon-reload 2>/dev/null || true
systemctl enable --now lt104-remap.service 2>/dev/null || true
# Apply keys immediately
/usr/bin/lt104-remap-keys 2>/dev/null || true
update-desktop-database 2>/dev/null || true

%postun
if [ \$1 -eq 0 ]; then
    systemctl stop lt104-remap.service 2>/dev/null || true
    systemctl disable lt104-remap.service 2>/dev/null || true
    systemctl daemon-reload 2>/dev/null || true
    rm -f /usr/local/bin/lt104-remap-keys.py 2>/dev/null || true
    systemd-hwdb update 2>/dev/null || true
    udevadm control --reload-rules 2>/dev/null || true
    udevadm trigger 2>/dev/null || true
    update-desktop-database 2>/dev/null || true
fi

%files
%defattr(-,root,root,-)
/usr/bin/lt104
/usr/bin/lt104-cli
/usr/bin/lt104-web
/usr/bin/lt104-remap-keys
/usr/share/lt104
/usr/share/applications/lt104.desktop
/usr/share/icons/hicolor/256x256/apps/lt104.png
/usr/lib/udev/rules.d/99-lt104.rules
/usr/lib/udev/hwdb.d/99-lt104-win.hwdb
/lib/systemd/system/lt104-remap.service
SPEC

# 6. Execute rpmbuild
echo "Building RPM package..."
rpmbuild -bb \
    --define "_topdir $BUILD_DIR" \
    --define "_dbpath $BUILD_DIR/rpmdb" \
    "$BUILD_DIR/SPECS/${PKG_NAME}.spec"

RPM_FILE=$(find "$BUILD_DIR/RPMS" -name "*.rpm" | head -n 1)
if [ -n "$RPM_FILE" ]; then
    FINAL_RPM="$DIST_DIR/${PKG_NAME}-${VERSION}-${RELEASE}.noarch.rpm"
    cp -v "$RPM_FILE" "$FINAL_RPM"
    echo "✅ Successfully built RPM: $FINAL_RPM"
else
    echo "❌ RPM build failed: no output RPM found"
    exit 1
fi
