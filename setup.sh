#!/usr/bin/env bash
# ==============================================================================
# LangTu LT-104 Keyboard Driver & Persistent Remap Setup Utility
# ==============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTION="${1:-status}"

case "$ACTION" in
    install)
        echo "=== Installing LangTu LT-104 Keyboard Driver & Persistent Remap ==="

        # 1. Install udev rules
        echo "[1/5] Installing udev rules to /etc/udev/rules.d/99-lt104.rules..."
        sudo cp "$DIR/99-lt104.rules" /etc/udev/rules.d/99-lt104.rules
        sudo udevadm control --reload-rules 2>/dev/null || true
        sudo udevadm trigger 2>/dev/null || true

        # 2. Install hwdb mapping
        echo "[2/5] Installing hwdb mapping to /etc/udev/hwdb.d/99-lt104-win.hwdb..."
        sudo cp "$DIR/99-lt104-win.hwdb" /etc/udev/hwdb.d/99-lt104-win.hwdb
        sudo systemd-hwdb update 2>/dev/null || true
        sudo udevadm trigger 2>/dev/null || true

        # 3. Install binary into /usr/bin and legacy /usr/local/bin
        echo "[3/5] Installing /usr/bin/lt104-remap-keys..."
        sudo install -m 755 "$DIR/lt104_remap.py" /usr/bin/lt104-remap-keys
        sudo mkdir -p /usr/local/bin
        sudo ln -sf /usr/bin/lt104-remap-keys /usr/local/bin/lt104-remap-keys.py 2>/dev/null || true

        # 4. Install systemd service
        echo "[4/5] Enabling and starting lt104-remap.service..."
        sudo cp "$DIR/lt104-remap.service" /etc/systemd/system/lt104-remap.service
        sudo systemctl daemon-reload 2>/dev/null || true
        sudo systemctl enable --now lt104-remap.service 2>/dev/null || true

        # 5. Apply keys immediately
        echo "[5/5] Applying scancode remap to currently connected keyboards..."
        sudo /usr/bin/lt104-remap-keys || true

        echo "✅ Installation complete! Key mappings are now permanently active."
        echo "   - Left Alt + Tab   -> One horizontal row window switcher (no workspaces)"
        echo "   - Right Alt + Tab  -> Exactly identical: one horizontal row switcher"
        echo "   - Left Win + Tab   -> Switcher with workspaces"
        echo "   - Left Win (alone) -> Opens GNOME Menu / ArcMenu"
        echo "   - Menu key         -> Context Menu / Compose key"
        ;;

    uninstall)
        echo "=== Uninstalling LangTu LT-104 Key Remap & Driver ==="
        sudo systemctl stop lt104-remap.service 2>/dev/null || true
        sudo systemctl disable lt104-remap.service 2>/dev/null || true
        sudo rm -f /etc/systemd/system/lt104-remap.service
        sudo systemctl daemon-reload 2>/dev/null || true

        sudo rm -f /etc/udev/rules.d/99-lt104.rules
        sudo rm -f /etc/udev/hwdb.d/99-lt104-win.hwdb
        sudo rm -f /usr/bin/lt104-remap-keys
        sudo rm -f /usr/local/bin/lt104-remap-keys.py

        sudo systemd-hwdb update 2>/dev/null || true
        sudo udevadm control --reload-rules 2>/dev/null || true
        sudo udevadm trigger 2>/dev/null || true
        echo "✅ Uninstallation complete."
        ;;

    remap)
        echo "=== Running LT-104 Key Remapper ==="
        python3 "$DIR/lt104_remap.py" --status
        ;;

    status)
        echo "=== LangTu LT-104 Status ==="
        python3 "$DIR/lt104_cli.py" status
        echo ""
        echo "=== Key Remap Status ==="
        python3 "$DIR/lt104_remap.py" --status
        ;;

    build)
        echo "=== Building Debian Package and Release Artifacts ==="
        "$DIR/packaging/build_all_releases.sh"
        ;;

    *)
        echo "Usage: ./setup.sh {install|uninstall|remap|status|build}"
        exit 1
        ;;
esac
