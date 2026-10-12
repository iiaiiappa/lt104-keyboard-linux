# LangTu LT-104 Keyboard Linux Driver & Control Suite

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-orange.svg)](https://kernel.org/)
[![GTK4](https://img.shields.io/badge/GUI-GTK4%20%2B%20Libadwaita-purple.svg)](https://gnome.pages.gitlab.gnome.org/libadwaita/)
[![GNOME Shell](https://img.shields.io/badge/GNOME%20Shell-45%20%7C%2046%20%7C%2047-blue.svg)](https://extensions.gnome.org/)

**A 100% native Linux driver, Web UI, Desktop GUI (GTK4/Libadwaita), CLI tool, and GNOME Shell Extension for the LangTu (狼途) LT-104 RGB Mechanical Keyboard with 160×80 TFT LCD Screen (`USB ID 0c45:8009 Microdia/SONiX`).**

Reverse-engineered from the official Windows `DeviceDriver.exe` and USB protocol dumps. Runs entirely on native Linux USB HID interfaces without Wine, virtual machines, or proprietary Windows background daemons.

---

## 🌟 Key Features

### 1. 🌈 Full RGB Backlight Control & EEPROM Storage
- **22 Lighting Modes**: Static, Single Light, Stars, Breathing, Rainbow Wave, Neon Glow, River Stream, Ripple Spread, Backlight Off, and more.
- **Custom Color Dialog & 7 Quick Presets**: Precise RGB HEX selection with color picker and quick preset buttons.
- **Hardware-Level Persistence**: Commands write directly to the keyboard's internal non-volatile EEPROM memory (`0x04 0xF0`). Lighting preferences survive computer power-offs, reboots, and unplugging without any software running.

### 2. 🕒 TFT Clock Calibration & 12-Hour Automated Scheduler
- **One-Click Precision Time Sync**: Immediately synchronizes PC system time to the keyboard's internal hardware RTC with sub-second accuracy.
- **Background Auto-Sync Service**: Automated systemd user timer (`lt104-clock-sync.timer`) periodically calibrates the keyboard clock every 12 hours.
- **Zero Backlight Interruption**: Clock packets are only 10 bytes and transfer in `< 1ms`, keeping the keyboard backlight 100% solid and flicker-free.

### 3. 📊 Real-Time Hardware Telemetry HUD
- **Live System Stats**: Displays CPU load percentage, RAM usage (GB & %), Root Disk usage (%), System Time, and Hostname on the keyboard's 160×80 LCD.
- **Direct RAM Buffer Streaming**: Writes directly to the keyboard's volatile LCD frame buffer. **Zero SPI Flash wear** and **no flash memory degradation**.
- **Adjustable Refresh Interval**: Choose from 5s, 10s, 20s (default), 30s, 60s, 120s (2 min), or 300s (5 min).
- **Single-Shot On-Demand Trigger**: Includes a `⚡ Update HUD Once` button in both Web and GTK interfaces to query and inspect hardware metrics whenever needed without continuous background cycling.

### 4. 📺 Custom LCD Image & GIF Animation Uploader
- **GIF & Static Image Support**: Converts any animated GIF, PNG, JPEG, or WebP to 160×80 RGB565 Little-Endian format.
- **Hardware Flow Control**: Respects keyboard MCU SPI write cycles with hardware ACK synchronization on Endpoint `0x84`, preventing packet drops and tearing.
- **Hardware Slot 1 Flash Storage**: Uploaded animations are committed to internal on-board storage and loop continuously even without an active PC connection.

### 5. 💾 Cross-Session Configuration Persistence
- All settings (lighting mode, color, brightness, speed, HUD refresh interval, language) are automatically remembered across sessions in `~/.config/lt104/config.json` and browser `localStorage`.
- Settings are restored automatically whenever you launch the Web Console, the Desktop App, or the GNOME Shell extension.

### 6. 🌐 Multilingual Internationalization (i18n)
Full native localization across all interfaces in 9 Ubuntu desktop languages:
- **English**, **简体中文**, **繁體中文**, **日本語**, **한국어**, **Deutsch**, **Français**, **Español**, **Русский**.

---

## 🖥️ Four Ways to Control Your Keyboard

| Interface | Description | Launch Command |
|---|---|---|
| **Web Console** | Modern dark-mode web dashboard running on port `8989` | `python3 web_app.py 8989` |
| **Desktop App** | Native GNOME GTK4 + Libadwaita application with toast notifications | `python3 lt104_gtk.py` |
| **GNOME Extension** | Top bar system tray menu for quick clock sync, presets, and HUD | `gnome-extensions enable lt104-indicator@theforwardway.com` |
| **CLI Tool** | Command-line interface for scripts, crontabs, and shortcuts | `python3 lt104_cli.py --help` |

---

## 🔧 Hardware Architecture & Technical Notes

### Device Identifiers
- **USB Vendor ID (VID)**: `0c45` (Microdia / SONiX Technology Co., Ltd.)
- **USB Product ID (PID)**: `8009` (LT104 Gaming Keyboard)
- **Interface 0 & 1**: Standard USB HID Keyboard & Consumer Keys (`/dev/input/event*`)
- **Interface 2**: LCD Interrupt / Bulk Out Endpoint (`/dev/hidraw*` via Endpoint `0x03` Out & `0x84` In)
- **Interface 3**: Vendor Control Endpoint (`USBDEVFS_CONTROL` / HID Set_Report on Endpoint 0)

### Why Does the Backlight Turn Off for 1 Second During Full HUD Updates?
The LangTu LT-104 is driven by a cost-effective single-core 48MHz ARM Cortex-M0 MCU (SONiX SN32F240B series).
1. **Matrix PWM Multiplexing**: The 104-key RGB backlight is software-multiplexed using high-frequency timer interrupts (10–20 kHz).
2. **Frame Size**: One 160×80 color TFT frame requires 25,600 pixel bytes + 256 bytes header (25,856 bytes total), transferred in seven 4,096-byte USB chunks.
3. **SPI Bus Throughput**: For each 4KB chunk, the 48MHz MCU requires ~133ms to receive USB data and write it via the serial SPI bus to the ST7735 screen (7 chunks × 133ms ≈ 1.03 seconds).
4. **Firmware Behavior**: During this 1-second SPI write loop, the MCU consumes 100% of its CPU bandwidth. The firmware suspends the software-multiplexed LED timer to prevent USB packet drops. The backlight turns off during the 1-second transfer and immediately turns back on once the frame commit (`0x04 0x02`) completes. (This behavior is identical to the official Windows driver).
5. **Mitigation**: Use the **12-Hour Clock Auto-Sync** for zero-blinking everyday typing, or set the HUD interval to **60s / 120s / 300s** or use the **⚡ Update HUD Once** button for on-demand checks.

---

## 📦 Installation & Setup

### 1. Prerequisites (Ubuntu / Debian)
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-pil python3-psutil \
                    libadwaita-1-0 gir1.2-adw-1 gir1.2-gtk-4.0
```

### 2. Configure USB Permissions (udev Rule)
Allow non-root user access to the keyboard's raw HID interface:
```bash
echo 'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0c45", ATTRS{idProduct}=="8009", MODE="0666"' | sudo tee /etc/udev/rules.d/99-lt104.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### 3. Clone Repository
```bash
git clone https://github.com/your-username/lt104-keyboard-linux.git
cd lt104-keyboard-linux
```

---

## 🛠️ Step-by-Step Installation Guide

### Option A: Install Desktop Launcher (GNOME Application Menu)
To launch the native GTK4 application directly from the GNOME application grid or search (`Super` key):

1. Create a local `.desktop` launcher:
```bash
mkdir -p ~/.local/share/applications
cat <<EOF > ~/.local/share/applications/lt104.desktop
[Desktop Entry]
Name=LT-104 Keyboard Center
Name[zh_CN]=LT-104 键盘控制中心
Comment=RGB lighting, LCD clock sync, HUD telemetry, and GIF uploader for LangTu LT-104
Exec=/usr/bin/python3 $(pwd)/lt104_gtk.py
Icon=input-keyboard
Terminal=false
Type=Application
Categories=Utility;Settings;HardwareSettings;
Keywords=Keyboard;RGB;LangTu;LT104;HUD;
StartupNotify=true
EOF
update-desktop-database ~/.local/share/applications/ 2>/dev/null || true
```

### Option B: Install the GNOME Shell Top Bar Extension
Control clock synchronization, presets, and HUD streaming straight from your GNOME top bar:

```bash
# 1. Copy the extension to your GNOME user directory
mkdir -p ~/.local/share/gnome-shell/extensions/
cp -r gnome-extension ~/.local/share/gnome-shell/extensions/lt104-indicator@theforwardway.com

# 2. Enable the extension
gnome-extensions enable lt104-indicator@theforwardway.com
```
> **Note**: If on Wayland, log out of your GNOME session and log back in. If on X11, press `Alt+F2`, enter `r`, and press Enter.

### Option C: Enable Background 12-Hour Clock Auto-Sync Service
Keep your keyboard's LCD clock accurate across reboots without having to keep any GUI window open:

```bash
# Enable and start the systemd user timer
python3 lt104_cli.py clock-schedule-enable

# Verify timer status
systemctl --user status lt104-clock-sync.timer
```

### Option D: Run Web Control Panel as a Background Systemd Service
If you want the Web UI (`http://localhost:8989`) always accessible on boot:

```bash
mkdir -p ~/.config/systemd/user
cat <<EOF > ~/.config/systemd/user/lt104-web.service
[Unit]
Description=LT-104 Keyboard Web Dashboard
After=network.target

[Service]
Type=simple
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/python3 $(pwd)/web_app.py 8989
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now lt104-web.service
```

---

## 🚀 Quick Start Guide

### Launching the Web Control Panel Directly
```bash
python3 web_app.py 8989
```
Open your browser and navigate to:
```
http://127.0.0.1:8989
```

### Launching the Desktop GTK4 App Directly
```bash
python3 lt104_gtk.py
```

---

## ⌨️ Command-Line Interface (CLI) Reference

The `lt104_cli.py` script provides quick control for automation scripts and keybindings:

```bash
# Sync clock to current PC time
python3 lt104_cli.py sync-clock

# Manage 12-hour automated clock schedule (systemd user timer)
python3 lt104_cli.py clock-schedule-status
python3 lt104_cli.py clock-schedule-enable
python3 lt104_cli.py clock-schedule-disable

# Apply lighting presets
python3 lt104_cli.py preset breathing-cyan
python3 lt104_cli.py preset static-white
python3 lt104_cli.py preset rainbow
python3 lt104_cli.py preset off

# Custom lighting configuration
python3 lt104_cli.py set-light --mode 1 --r 0 --g 229 --b 255 --brightness 4 --speed 3

# Start / Stop background System HUD daemon
python3 lt104_cli.py hud-start --interval 20.0
python3 lt104_cli.py hud-status
python3 lt104_cli.py hud-stop

# Single-shot HUD telemetry update
python3 lt104_cli.py hud-once

# Upload image or GIF animation to keyboard LCD (Slot 1)
python3 lt104_cli.py upload-image /path/to/animation.gif
```

---

## 📁 Project Structure

```
lt104-keyboard-linux/
├── config.py              # Configuration persistence (~/.config/lt104/config.json)
├── i18n.py                # 9-language translation dictionaries
├── lt104_core.py          # Low-level USB HID & LCD packet protocol driver
├── lt104_cli.py           # CLI utility for command-line & systemd execution
├── lt104_gtk.py           # Native GTK4 / Libadwaita desktop application
├── lt104_indicator.py     # System telemetry HUD daemon & single-shot renderer
├── web_app.py             # Web dashboard & HTTP API (port 8989)
├── gnome-extension/       # Packaged GNOME Shell top bar indicator extension
│   ├── extension.js
│   └── metadata.json
├── LICENSE                # GNU General Public License v3.0 (GPLv3)
└── README.md              # Project documentation
```

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**.  
See the [LICENSE](LICENSE) file for complete details.

```
Copyright (C) 2026 The Forward Way / PatProject Contributors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
```
