#!/usr/bin/env python3
"""
LangTu LT-104 Keyboard Scancode-to-Keycode Remapper for Linux / Ubuntu.
Ensures identical and expected key behaviors across all Linux desktop environments:
  - Physical Left Alt  (scancode 0x700e2) -> keycode 125 (Left Alt horizontal switcher)
  - Physical Left Win  (scancode 0x700e3) -> keycode 56  (Super / GNOME Menu / Overview)
  - Physical Right Alt (scancode 0x700e6) -> keycode 125 (Identical to Left Alt)
  - Physical Right Cmd (scancode 0x700e7) -> keycode 125 (Identical to Left Alt)
  - Physical Menu Key  (scancode 0x70065) -> keycode 127 (Compose / Context Menu)

Zero external dependencies: uses Linux kernel evdev ioctl (EVIOCSKEYCODE_V2)
via standard library fcntl and struct.
"""

import sys
import os
import glob
import fcntl
import struct

# Kernel Keycodes
KEY_ALT   = 125  # In Ubuntu GNOME, 125 triggers <Alt> (single horizontal row window switcher)
KEY_WIN   = 56   # In Ubuntu GNOME, 56 triggers <Super> (overview / menu / workspace switcher)
KEY_MENU  = 127  # KEY_COMPOSE (Menu / Application key)

MAPPINGS = [
    (0x700e2, KEY_ALT,  "Left Alt (0x700e2) -> Alt (125)"),
    (0x700e3, KEY_WIN,  "Left Win (0x700e3) -> Super/Win (56)"),
    (0x700e6, KEY_ALT,  "Right Alt (0x700e6) -> Alt (125)"),
    (0x700e7, KEY_ALT,  "Right Cmd (0x700e7) -> Alt (125)"),
    (0x70065, KEY_MENU, "Menu Key (0x70065) -> Compose/Menu (127)"),
]

# Linux Input Subsystem ioctl constants
# struct input_keymap_entry {
#     __u8  flags;
#     __u8  len;
#     __u16 index;
#     __u32 keycode;
#     __u8  scancode[32];
# };
EVIOCSKEYCODE_V2 = 0x40284504  # _IOW('E', 0x04, struct input_keymap_entry)
EVIOCGKEYCODE_V2 = 0x80284504  # _IOR('E', 0x04, struct input_keymap_entry)

def is_lt104_input_device(devpath):
    """Check if input device corresponds to LT-104 2.4G Dongle (05ac:024f) or Sonix (0c45:8009)."""
    devname = os.path.basename(devpath)
    syspath = f"/sys/class/input/{devname}/device/id"
    v_file = os.path.join(syspath, "vendor")
    p_file = os.path.join(syspath, "product")
    if os.path.exists(v_file) and os.path.exists(p_file):
        try:
            v = int(open(v_file).read().strip(), 16)
            p = int(open(p_file).read().strip(), 16)
            if (v == 0x05ac and p == 0x024f) or (v == 0x0c45 and p == 0x8009):
                return True
        except Exception:
            pass
    return False

def remap_event_device(devpath, verbose=False):
    """Apply scancode remap to a single /dev/input/eventX device node."""
    if not os.path.exists(devpath):
        return False

    if not is_lt104_input_device(devpath):
        return False

    try:
        fd = os.open(devpath, os.O_RDWR | os.O_NONBLOCK)
    except Exception as e:
        if verbose:
            print(f"Cannot open {devpath}: {e}")
        return False

    success_count = 0
    results = []

    for scancode, keycode, desc in MAPPINGS:
        scan_bytes = struct.pack("<I", scancode) + b"\x00" * 28
        ke_set = struct.pack("<BBHI32s", 0, 4, 0, keycode, scan_bytes)
        try:
            fcntl.ioctl(fd, EVIOCSKEYCODE_V2, ke_set)
            # Verify readback
            ke_get = struct.pack("<BBHI32s", 0, 4, 0, 0, scan_bytes)
            res = fcntl.ioctl(fd, EVIOCGKEYCODE_V2, ke_get)
            _, _, _, read_kc, _ = struct.unpack("<BBHI32s", res)
            results.append(f"  ✓ {desc} -> Verified keycode: {read_kc}")
            success_count += 1
        except OSError as e:
            # Not all event nodes (e.g. mouse/consumer controls) accept keyboard scancodes
            results.append(f"  - {desc} -> Not applicable on this node ({e.strerror})")

    os.close(fd)

    if success_count > 0:
        log_line = f"Applied LT-104 remap on {devpath}:\n" + "\n".join(results)
        if verbose:
            print(log_line)
        try:
            with open("/tmp/lt104-remap.log", "a") as f:
                f.write(log_line + "\n")
        except Exception:
            pass
        return True
    return False

def remap_all(verbose=False):
    """Scan and remap all connected LT-104 input event nodes."""
    applied = 0
    for devnode in sorted(glob.glob("/dev/input/event*")):
        if remap_event_device(devnode, verbose=verbose):
            applied += 1
    return applied

if __name__ == "__main__":
    verbose = "-v" in sys.argv or "--verbose" in sys.argv or "--status" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("-")]

    if args:
        # Specific device node passed (e.g. from udev RUN rule)
        for dev in args:
            remap_event_device(dev, verbose=verbose)
    else:
        # Scan all devices
        count = remap_all(verbose=True)
        if count == 0:
            print("No LT-104 keyboard event devices found to remap.")
        else:
            print(f"Successfully applied LT-104 key remap to {count} device interface(s).")
