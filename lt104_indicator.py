#!/usr/bin/env python3
"""
LT-104 Real-time System HUD Daemon (Linux Native)
Streams CPU, RAM, Network, Clock and System telemetry to LangTu LT-104 160x80 LCD.
Updates every 3 seconds directly into keyboard RAM without writing to SPI Flash.
Typing is 100% active and responsive.
"""
import os
import sys
import time
import select
import signal
import socket
import struct
import psutil
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lt104_core import LT104Controller, find_lt104_usb, find_lt104_lcd_hidraw

W, H = 160, 80
FRAME_PIXELS = W * H * 2    # 25,600 bytes
CHUNK_SIZE = 4096
HEADER_SIZE = 256
DATA_LEN = HEADER_SIZE + FRAME_PIXELS
PAD = (CHUNK_SIZE - (DATA_LEN % CHUNK_SIZE)) % CHUNK_SIZE
TOTAL_LEN = DATA_LEN + PAD
TOTAL_CHUNKS = TOTAL_LEN // CHUNK_SIZE

# Pre-allocated single frame buffer
BUFFER_TEMPLATE = bytearray(b'\xff' * TOTAL_LEN)
BUFFER_TEMPLATE[0] = 1     # 1 frame
BUFFER_TEMPLATE[1] = 250   # 250 * 10ms = 2.5s display hold

def get_sys_stats():
    cpu_pct = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return cpu_pct, ram, disk

def render_hud_image(cpu_pct, ram, disk):
    img = Image.new('RGB', (W, H), color=(10, 15, 29))
    draw = ImageDraw.Draw(img)

    # Top Header: System Time & Status Dot
    now_str = time.strftime("%H:%M:%S")
    draw.ellipse([(4, 5), (10, 11)], fill=(34, 197, 94))  # Green live status
    draw.text((14, 2), "SYSTEM HUD", fill=(56, 189, 248))
    draw.text((105, 2), now_str, fill=(148, 163, 184))

    # Divider Line
    draw.line([(0, 15), (W, 15)], fill=(30, 41, 59), width=1)

    # 1. CPU Section (Row 18-32)
    # Label & Value
    cpu_col = (52, 211, 153) if cpu_pct < 75 else (239, 68, 68) if cpu_pct > 90 else (251, 191, 36)
    draw.text((4, 18), "CPU", fill=(241, 245, 249))
    draw.text((30, 18), f"{cpu_pct:4.1f}%", fill=cpu_col)
    # Bar container & fill
    draw.rectangle([(75, 20), (154, 28)], outline=(51, 65, 85), fill=(15, 23, 42))
    cpu_bar_w = int(77 * max(0.0, min(1.0, cpu_pct / 100.0)))
    if cpu_bar_w > 0:
        draw.rectangle([(76, 21), (76 + cpu_bar_w, 27)], fill=cpu_col)

    # 2. RAM Section (Row 34-48)
    # Label & Value
    ram_pct = ram.percent
    ram_col = (192, 132, 252) if ram_pct < 80 else (244, 63, 94)
    draw.text((4, 34), "RAM", fill=(241, 245, 249))
    draw.text((30, 34), f"{ram_pct:4.1f}%", fill=ram_col)
    # Bar container & fill
    draw.rectangle([(75, 36), (154, 44)], outline=(51, 65, 85), fill=(15, 23, 42))
    ram_bar_w = int(77 * max(0.0, min(1.0, ram_pct / 100.0)))
    if ram_bar_w > 0:
        draw.rectangle([(76, 37), (76 + ram_bar_w, 43)], fill=ram_col)

    # 3. Memory & Storage Details (Row 50-62)
    used_gb = ram.used / (1024**3)
    total_gb = ram.total / (1024**3)
    draw.text((4, 50), f"MEM {used_gb:.1f}/{total_gb:.0f}G", fill=(148, 163, 184))
    draw.text((95, 50), f"DSK {disk.percent:.0f}%", fill=(56, 189, 248))

    # 4. Bottom Footer Info (Row 64-78)
    draw.line([(0, 63), (W, 63)], fill=(30, 41, 59), width=1)
    hostname = socket.gethostname()[:14]
    draw.text((4, 66), hostname, fill=(100, 116, 139))
    draw.text((102, 66), "LT104 LIVE", fill=(34, 197, 94))

    return img

def image_to_rgb565(im):
    raw = bytearray(FRAME_PIXELS)
    idx = 0
    for y in range(H):
        for x in range(W):
            pr, pg, pb = im.getpixel((x, y))
            rgb565 = ((pr >> 3) << 11) | ((pg >> 2) << 5) | (pb >> 3)
            raw[idx] = rgb565 & 0xFF
            raw[idx + 1] = (rgb565 >> 8) & 0xFF
            idx += 2
    return raw

PID_FILE = "/tmp/lt104_indicator.pid"

def run_indicator(interval=120.0, once=False):
    print(f"[LT-104 HUD] Starting Real-time System HUD (Interval: {interval}s)...")
    running = True
    wake_event = False

    def sig_handler(sig, frame):
        nonlocal running
        print("\n[LT-104 HUD] Shutting down cleanly...")
        running = False

    def usr1_handler(sig, frame):
        nonlocal wake_event
        wake_event = True

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGUSR1, usr1_handler)

    if not once:
        try:
            with open(PID_FILE, "w") as f:
                f.write(str(os.getpid()))
        except OSError:
            pass

    # Initialize CPU measurement
    psutil.cpu_percent(interval=None)

    ctl = None
    while running:
        try:
            if not ctl:
                ctl = LT104Controller()
                print(f"[LT-104 HUD] Connected to LT-104 at {ctl.usb_path} (LCD: {ctl.lcd_path})")

            # Collect stats & render
            cpu_pct, ram, disk = get_sys_stats()
            im = render_hud_image(cpu_pct, ram, disk)
            raw = image_to_rgb565(im)

            # Save latest rendered HUD frame for simulated keyboard UI screen
            try:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                static_dir = os.path.join(base_dir, "static")
                os.makedirs(static_dir, exist_ok=True)
                hud_path = os.path.join(static_dir, "current_hud.png")
                im.resize((62, 39), Image.Resampling.LANCZOS).save(hud_path)
            except Exception:
                pass

            # Assemble buffer
            buffer = bytearray(BUFFER_TEMPLATE)
            buffer[HEADER_SIZE : HEADER_SIZE + FRAME_PIXELS] = raw

            # Start Streaming Command (Omit 0x18 to prevent backlight flickers/off during HUD updates)
            p = bytearray(64)
            p[0] = 0x04
            p[1] = 0x72
            p[2] = 0x01  # Slot 1
            p[8] = TOTAL_CHUNKS & 0xFF
            p[9] = (TOTAL_CHUNKS >> 8) & 0xFF
            ctl._set_feature(p)
            ctl._get_feature()

            # Stream chunks to Interface 2 HID with hardware ACK flow control
            for i in range(TOTAL_CHUNKS):
                chunk = buffer[i * CHUNK_SIZE : (i + 1) * CHUNK_SIZE]
                os.write(ctl.lcd_fd, chunk)
                r, _, _ = select.select([ctl.lcd_fd], [], [], 0.4)
                if r:
                    try: os.read(ctl.lcd_fd, 64)
                    except: pass
                else:
                    time.sleep(0.135)

            # Apply in RAM (No SPI flash wear, no typing freeze)
            ctl._send_with_ack(0x04, 0x02)

            if once:
                print("[LT-104 HUD] Single frame rendered and pushed successfully.")
                break

            # Release USB descriptors during interval sleep so clock sync and lighting never hit EBUSY
            if ctl:
                try: ctl.close()
                except: pass
                ctl = None

        except (OSError, RuntimeError) as e:
            print(f"[LT-104 HUD] Connection error: {e}. Reconnecting in 3s...")
            if ctl:
                try: ctl.close()
                except: pass
                ctl = None
            time.sleep(3.0)
            continue
        except Exception as e:
            print(f"[LT-104 HUD] Unexpected error: {e}")
            break

        # Sleep interval
        t_start = time.time()
        while running and not wake_event and (time.time() - t_start < interval):
            time.sleep(0.2)
        wake_event = False

    if ctl:
        try: ctl.close()
        except: pass

    if not once and os.path.exists(PID_FILE):
        try:
            if open(PID_FILE).read().strip() == str(os.getpid()):
                os.unlink(PID_FILE)
        except OSError:
            pass

    print("[LT-104 HUD] Daemon stopped.")

if __name__ == '__main__':
    interval = 120.0
    once = '--once' in sys.argv
    if '--interval' in sys.argv:
        try:
            idx = sys.argv.index('--interval')
            interval = float(sys.argv[idx + 1])
        except (IndexError, ValueError):
            pass
    run_indicator(interval=interval, once=once)
