Name:           lt104-keyboard-linux
Version:        1.0.0
Release:        1%{?dist}
Summary:        LangTu LT-104 RGB Mechanical Keyboard Linux Driver & Control Suite
License:        GPL-3.0
URL:            https://github.com/iiaiiappa/lt104-keyboard-linux
BuildArch:      noarch

Requires:       python3, python3-pillow, python3-psutil, libadwaita, gtk4

%description
A native Linux USB HID driver, GTK4 desktop application, Web control panel,
and command-line interface for the LangTu (狼途) LT-104 RGB Mechanical Keyboard (0c45:8009).

%prep
# No prep required

%build
# No build required for Python package

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT%{_bindir}
mkdir -p $RPM_BUILD_ROOT%{_datadir}/lt104
mkdir -p $RPM_BUILD_ROOT%{_datadir}/applications
mkdir -p $RPM_BUILD_ROOT%{_prefix}/lib/udev/rules.d

# Copy application files
cp -r config.py i18n.py lt104_cli.py lt104_core.py lt104_gtk.py lt104_indicator.py web_app.py static gnome-extension $RPM_BUILD_ROOT%{_datadir}/lt104/

# CLI Wrappers
cat << 'WRAP' > $RPM_BUILD_ROOT%{_bindir}/lt104
#!/bin/bash
exec /usr/bin/python3 %{_datadir}/lt104/lt104_gtk.py "$@"
WRAP
chmod 755 $RPM_BUILD_ROOT%{_bindir}/lt104

cat << 'WRAPCLI' > $RPM_BUILD_ROOT%{_bindir}/lt104-cli
#!/bin/bash
exec /usr/bin/python3 %{_datadir}/lt104/lt104_cli.py "$@"
WRAPCLI
chmod 755 $RPM_BUILD_ROOT%{_bindir}/lt104-cli

cat << 'WRAPWEB' > $RPM_BUILD_ROOT%{_bindir}/lt104-web
#!/bin/bash
exec /usr/bin/python3 %{_datadir}/lt104/web_app.py "${1:-8989}"
WRAPWEB
chmod 755 $RPM_BUILD_ROOT%{_bindir}/lt104-web

# Udev rule
echo 'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0c45", ATTRS{idProduct}=="8009", MODE="0666"' > $RPM_BUILD_ROOT%{_prefix}/lib/udev/rules.d/99-lt104.rules

# Desktop file
cat << 'DESK' > $RPM_BUILD_ROOT%{_datadir}/applications/lt104.desktop
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

%post
udevadm control --reload-rules 2>/dev/null || true
udevadm trigger 2>/dev/null || true
update-desktop-database 2>/dev/null || true

%postun
udevadm control --reload-rules 2>/dev/null || true
udevadm trigger 2>/dev/null || true
update-desktop-database 2>/dev/null || true

%files
%{_bindir}/lt104
%{_bindir}/lt104-cli
%{_bindir}/lt104-web
%{_datadir}/lt104
%{_datadir}/applications/lt104.desktop
%{_prefix}/lib/udev/rules.d/99-lt104.rules
