#!/usr/bin/env python3
"""
CLI helper for quick LT-104 commands used by GNOME Extension and desktop shortcuts.
Usage:
  lt104_cli.py sync-clock
  lt104_cli.py set-light --mode 7 --r 0 --g 229 --b 255 --brightness 4 --speed 3
  lt104_cli.py preset [breathing-cyan|static-white|spectrum|off|rainbow]
"""
import sys
import argparse
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lt104_core import LT104Controller
from config import save_config, load_config

PRESETS = {
    "breathing-cyan": {"mode": 7, "r": 0, "g": 229, "b": 255, "brightness": 4, "speed": 3},
    "static-white":   {"mode": 1, "r": 255, "g": 255, "b": 255, "brightness": 4, "speed": 3},
    "static-cyan":    {"mode": 1, "r": 0, "g": 229, "b": 255, "brightness": 4, "speed": 3},
    "static-magenta": {"mode": 1, "r": 255, "g": 0, "b": 85, "brightness": 4, "speed": 3},
    "static-green":   {"mode": 1, "r": 0, "g": 230, "b": 118, "brightness": 4, "speed": 3},
    "spectrum":       {"mode": 8, "r": 0, "g": 229, "b": 255, "brightness": 4, "speed": 3},
    "rainbow":        {"mode": 9, "r": 0, "g": 229, "b": 255, "brightness": 4, "speed": 3},
    "stream":         {"mode": 11, "r": 0, "g": 229, "b": 255, "brightness": 4, "speed": 3},
    "off":            {"mode": 20, "r": 0, "g": 0, "b": 0, "brightness": 0, "speed": 0},
}

def main():
    parser = argparse.ArgumentParser(description="LT-104 CLI Control")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # sync-clock
    subparsers.add_parser("sync-clock")

    # set-light
    p_light = subparsers.add_parser("set-light")
    p_light.add_argument("--mode", type=int, default=1)
    p_light.add_argument("--r", type=int, default=0)
    p_light.add_argument("--g", type=int, default=255)
    p_light.add_argument("--b", type=int, default=255)
    p_light.add_argument("--brightness", type=int, default=4)
    p_light.add_argument("--speed", type=int, default=3)

    # preset
    p_preset = subparsers.add_parser("preset")
    p_preset.add_argument("name", choices=list(PRESETS.keys()))

    # upload-image
    p_upload = subparsers.add_parser("upload-image")
    p_upload.add_argument("image_path", help="Path to GIF or image file")
    p_upload.add_argument("--slot", type=int, default=1, help="Slot ID (default: 1)")

    # hud-start, hud-stop, hud-status
    p_hud_start = subparsers.add_parser("hud-start")
    p_hud_start.add_argument("--interval", type=float, default=20.0)
    subparsers.add_parser("hud-stop")
    subparsers.add_parser("hud-status")
    subparsers.add_parser("hud-once")

    # clock-schedule commands
    subparsers.add_parser("clock-schedule-status")
    subparsers.add_parser("clock-schedule-enable")
    subparsers.add_parser("clock-schedule-disable")

    args = parser.parse_args()

    import subprocess
    import signal

    PID_FILE = "/tmp/lt104_indicator.pid"

    if args.cmd == "hud-start":
        # Check if already running
        if os.path.exists(PID_FILE):
            try:
                pid = int(open(PID_FILE).read().strip())
                os.kill(pid, 0)
                print(f"OK: HUD already running (PID {pid})")
                return
            except (OSError, ValueError):
                pass
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lt104_indicator.py")
        proc = subprocess.Popen([sys.executable, script, "--interval", str(args.interval)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(PID_FILE, "w") as f:
            f.write(str(proc.pid))
        save_config({"hud_interval": args.interval})
        print(f"OK: HUD started (PID {proc.pid})")
        return

    elif args.cmd == "hud-stop":
        stopped = False
        if os.path.exists(PID_FILE):
            try:
                pid = int(open(PID_FILE).read().strip())
                os.kill(pid, signal.SIGTERM)
                stopped = True
            except OSError:
                pass
            try: os.unlink(PID_FILE)
            except OSError: pass
        # Fallback: check pgrep for lt104_indicator.py
        try:
            out = subprocess.check_output(["pgrep", "-f", "lt104_indicator.py"]).decode()
            for line in out.splitlines():
                p = int(line.strip())
                if p != os.getpid():
                    os.kill(p, signal.SIGTERM)
                    stopped = True
        except Exception:
            pass
        print("OK: HUD stopped" if stopped else "OK: HUD was not running")
        return

    elif args.cmd == "hud-status":
        running = False
        pid = None
        if os.path.exists(PID_FILE):
            try:
                pid = int(open(PID_FILE).read().strip())
                os.kill(pid, 0)
                running = True
            except OSError:
                pass
        if not running:
            try:
                out = subprocess.check_output(["pgrep", "-f", "lt104_indicator.py"]).decode()
                pids = [int(p.strip()) for p in out.splitlines() if int(p.strip()) != os.getpid()]
                if pids:
                    running = True
                    pid = pids[0]
            except Exception:
                pass
        print(f"RUNNING:{pid}" if running else "STOPPED")
        return

    elif args.cmd == "hud-once":
        running_pid = None
        if os.path.exists(PID_FILE):
            try:
                p = int(open(PID_FILE).read().strip())
                os.kill(p, 0)
                running_pid = p
            except (OSError, ValueError):
                pass
        if not running_pid:
            try:
                out = subprocess.check_output(["pgrep", "-f", "lt104_indicator.py"]).decode()
                pids = [int(p.strip()) for p in out.splitlines() if int(p.strip()) != os.getpid()]
                if pids:
                    running_pid = pids[0]
            except Exception:
                pass

        if running_pid:
            try:
                os.kill(running_pid, signal.SIGUSR1)
                print(f"OK: Immediate HUD update triggered on daemon (PID {running_pid})")
                return
            except OSError:
                pass

        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lt104_indicator.py")
        res = subprocess.run([sys.executable, script, "--once"])
        if res.returncode != 0:
            sys.exit(res.returncode)
        return

    elif args.cmd == "clock-schedule-status":
        timer_path = os.path.expanduser("~/.config/systemd/user/timers.target.wants/lt104-clock-sync.timer")
        enabled = os.path.exists(timer_path)
        print("ENABLED" if enabled else "DISABLED")
        return

    elif args.cmd == "clock-schedule-enable":
        unit_dir = os.path.expanduser("~/.config/systemd/user")
        os.makedirs(unit_dir, exist_ok=True)
        service_file = os.path.join(unit_dir, "lt104-clock-sync.service")
        timer_file = os.path.join(unit_dir, "lt104-clock-sync.timer")
        script_path = os.path.abspath(__file__)
        with open(service_file, "w") as f:
            f.write(f"[Unit]\nDescription=LT-104 Keyboard Clock Auto-Sync Service\nAfter=default.target\n\n[Service]\nType=oneshot\nExecStart={sys.executable} {script_path} sync-clock\n")
        with open(timer_file, "w") as f:
            f.write("[Unit]\nDescription=LT-104 Keyboard Clock Sync Timer (Every 12 Hours)\n\n[Timer]\nOnBootSec=1min\nOnUnitActiveSec=12h\nPersistent=true\n\n[Install]\nWantedBy=timers.target\n")
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "--user", "enable", "--now", "lt104-clock-sync.timer"], check=False)
        print("OK: Clock schedule enabled (every 12 hours)")
        return

    elif args.cmd == "clock-schedule-disable":
        subprocess.run(["systemctl", "--user", "disable", "--now", "lt104-clock-sync.timer"], check=False)
        print("OK: Clock schedule disabled")
        return

    ctl = LT104Controller()
    try:
        if args.cmd == "sync-clock":
            ctl.sync_clock()
            print("OK: Clock synced")
        elif args.cmd == "set-light":
            ctl.set_light(mode=args.mode, r=args.r, g=args.g, b=args.b,
                          brightness=args.brightness, speed=args.speed)
            save_config({
                "mode": args.mode,
                "color": f"#{args.r:02x}{args.g:02x}{args.b:02x}",
                "r": args.r, "g": args.g, "b": args.b,
                "brightness": args.brightness,
                "speed": args.speed
            })
            print("OK: Light set")
        elif args.cmd == "preset":
            cfg = PRESETS[args.name]
            ctl.set_light(**cfg)
            save_config({
                "mode": cfg["mode"],
                "color": f"#{cfg['r']:02x}{cfg['g']:02x}{cfg['b']:02x}",
                "r": cfg["r"], "g": cfg["g"], "b": cfg["b"],
                "brightness": cfg["brightness"],
                "speed": cfg["speed"]
            })
            print(f"OK: Preset applied ({args.name})")
        elif args.cmd == "upload-image":
            def on_progress(p):
                print(f"\rProgress: {p}%", end="", flush=True)
            frames = ctl.upload_lcd_image(args.image_path, slot=args.slot, progress_cb=on_progress)
            print(f"\nOK: Uploaded {frames} frames to LCD")
    finally:
        ctl.close()

if __name__ == "__main__":
    main()

