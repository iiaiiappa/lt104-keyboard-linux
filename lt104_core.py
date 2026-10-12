#!/usr/bin/env python3
"""
LT-104 Gaming Keyboard Controller (Linux Native)
Direct USB HID protocol controller for LangTu LT-104 RGB & TFT LCD.
Reverse-engineered from SONiX LT104 USB HID firmware and DeviceDriver.exe.
"""
import os
import glob
import time
import select
import struct
import fcntl
import ctypes
from PIL import Image

# USBDEVFS_CONTROL ioctl — 'BBHHHI P' = 3+1+2+2+2+4+8 = 22 bytes on x86_64
USBDEVFS_CONTROL = 0xc0185500

LIGHT_MODES = [
    {"id": 1,  "name": "静态恒亮 (Static)"},
    {"id": 2,  "name": "单点亮 (Single Light)"},
    {"id": 3,  "name": "单熄灭 (Single Off)"},
    {"id": 4,  "name": "繁星点点 (Stars)"},
    {"id": 5,  "name": "漫天飞雪 (Snow)"},
    {"id": 6,  "name": "百花争艳 (Blossom)"},
    {"id": 7,  "name": "动态呼吸 (Breathing)"},
    {"id": 8,  "name": "光谱循环 (Spectrum Cycle)"},
    {"id": 9,  "name": "彩泉涌动 (Rainbow Wave)"},
    {"id": 10, "name": "多彩纵横 (Cross Pattern)"},
    {"id": 11, "name": "随波逐流 (River Stream)"},
    {"id": 12, "name": "峰回路转 (Rotary Wave)"},
    {"id": 13, "name": "一触即发 (Ripple Trigger)"},
    {"id": 14, "name": "一石二鸟 (Dual Ripple)"},
    {"id": 15, "name": "涟漪扩散 (Ripple Spread)"},
    {"id": 16, "name": "川流不息 (Infinite Stream)"},
    {"id": 17, "name": "重峦叠嶂 (Rolling Hills)"},
    {"id": 18, "name": "斜风细雨 (Gentle Rain)"},
    {"id": 19, "name": "来回穿梭 (Shuttle)"},
    {"id": 20, "name": "关闭背光 (Backlight Off)"},
    {"id": 21, "name": "万众一心 (Solid Center)"},
    {"id": 22, "name": "流光溢彩 (Neon Glow)"},
]

# Lighting modes that support custom single color (1: Static, 2: Single Light, 3: Single Off, 4: Stars, 5: Snow, 7: Breathing)
SINGLE_COLOR_MODES = (1, 2, 3, 4, 5, 7)
MULTI_COLOR_MODES = tuple(m["id"] for m in LIGHT_MODES if m["id"] not in SINGLE_COLOR_MODES)

def supports_single_color(mode):
    """Check if the given lighting mode supports custom single color."""
    return int(mode) in SINGLE_COLOR_MODES

def find_lt104_usb():
    """Find the raw USB devfs path for 0c45:8009 (SONiX LT104)."""
    for dev_path in glob.glob('/sys/bus/usb/devices/*'):
        id_vendor  = os.path.join(dev_path, 'idVendor')
        id_product = os.path.join(dev_path, 'idProduct')
        if os.path.exists(id_vendor) and os.path.exists(id_product):
            try:
                vid = open(id_vendor).read().strip().lower()
                pid = open(id_product).read().strip().lower()
                if vid == '0c45' and pid == '8009':
                    busnum = int(open(os.path.join(dev_path, 'busnum')).read().strip())
                    devnum = int(open(os.path.join(dev_path, 'devnum')).read().strip())
                    return f'/dev/bus/usb/{busnum:03d}/{devnum:03d}'
            except Exception:
                pass
    return None

def find_lt104_lcd_hidraw():
    """Find the hidraw device corresponding to Interface 2 (LCD output)."""
    for h in glob.glob('/sys/class/hidraw/*'):
        name    = os.path.basename(h)
        devlink = os.path.realpath(h + '/device')
        if '0C45:8009' in devlink or '0c45:8009' in devlink:
            if ':1.2' in devlink:
                return f'/dev/{name}'
    return None


class LT104Controller:
    def __init__(self, usb_path=None, lcd_path=None):
        self.usb_path = usb_path or find_lt104_usb()
        if not self.usb_path:
            raise RuntimeError("未检测到 狼途 LT-104 键盘 (VID 0C45, PID 8009)。请确认 USB 连线已插好！")
        self.fd = None
        for attempt in range(5):
            try:
                self.fd = os.open(self.usb_path, os.O_RDWR)
                break
            except OSError as e:
                if e.errno in (16, 11) and attempt < 4:
                    time.sleep(0.05 * (attempt + 1))
                    continue
                raise
        self.lcd_path = lcd_path or find_lt104_lcd_hidraw()
        self.lcd_fd = None
        if self.lcd_path and os.path.exists(self.lcd_path):
            try:
                self.lcd_fd = os.open(self.lcd_path, os.O_RDWR)
            except Exception:
                pass

    def close(self):
        if self.fd:
            try: os.close(self.fd)
            except: pass
            self.fd = None
        if self.lcd_fd:
            try: os.close(self.lcd_fd)
            except: pass
            self.lcd_fd = None

    # ------------------------------------------------------------------ #
    #  Low-level USB HID control transfers (Interface 3)                  #
    # ------------------------------------------------------------------ #

    def _set_feature(self, data, retries=10):
        """
        Send a 64-byte HID Feature Report (SET_REPORT) via USB control transfer
        to Interface 3 (vendor control channel).
        """
        pkt = bytearray(64)
        for i in range(min(len(data), 64)):
            pkt[i] = data[i]
        buf  = ctypes.create_string_buffer(bytes(pkt))
        ctrl = struct.pack('BBHHHI P',
            0x21,                   # bmRequestType: Host→Device, Class, Interface
            0x09,                   # bRequest: HID SET_REPORT
            (0x03 << 8) | 0x00,    # wValue: Feature Report (0x03), Report ID 0
            0x0003,                 # wIndex: Interface 3
            64,                     # wLength
            1500,                   # timeout ms
            ctypes.addressof(buf),
        )
        for attempt in range(retries):
            try:
                fcntl.ioctl(self.fd, USBDEVFS_CONTROL, ctrl)
                return True
            except OSError as e:
                if e.errno in (16, 11) and attempt < retries - 1:  # EBUSY (16), EAGAIN (11)
                    time.sleep(0.05 * (attempt + 1))
                    continue
                raise

    def _get_feature(self, retries=10):
        """
        Read a 64-byte HID Feature Report (GET_REPORT) via USB control transfer
        from Interface 3.
        Returns raw bytes, or None on failure.
        """
        buf  = ctypes.create_string_buffer(64)
        ctrl = struct.pack('BBHHHI P',
            0xa1,                   # bmRequestType: Device→Host, Class, Interface
            0x01,                   # bRequest: HID GET_REPORT
            (0x03 << 8) | 0x00,    # wValue: Feature Report (0x03), Report ID 0
            0x0003,                 # wIndex: Interface 3
            64,                     # wLength
            1500,                   # timeout ms
            ctypes.addressof(buf),
        )
        for attempt in range(retries):
            try:
                fcntl.ioctl(self.fd, USBDEVFS_CONTROL, ctrl)
                return bytes(buf.raw)
            except OSError as e:
                if e.errno in (16, 11) and attempt < retries - 1:
                    time.sleep(0.05 * (attempt + 1))
                    continue
                return None
            except Exception:
                return None
        return None

    def _send_with_ack(self, b0, b1, extra=None, timeout_ms=150):
        """
        Send a command packet [b0, b1, ...extra...] and poll GET_REPORT until
        the device echoes [b0, b1] in bytes [0:2] of the response.

        Matches the Windows DeviceDriver.exe logic at 0x456490:
          - SET_REPORT → poll GET_REPORT up to ~N iterations (2ms each)
          - Accepts when resp[0]==b0 and resp[1]==b1
          - Retries if resp contains 0xFF (busy)
          - 0x55 in resp[-2] = ACK flag (we just check the echo instead)
        """
        pkt = bytearray(64)
        pkt[0] = b0
        pkt[1] = b1
        if extra:
            for k, v in extra.items():
                pkt[k] = v

        self._set_feature(pkt)

        iterations = max(1, timeout_ms // 5)
        for _ in range(iterations):
            time.sleep(0.005)
            resp = self._get_feature()
            if resp is None:
                continue
            # Device echoes the opcode bytes back when done
            if resp[0] == b0 and resp[1] == b1:
                return True
            # 0xFF means device is busy — keep polling
            if resp[0] == 0xFF:
                continue
        # Timeout: return True anyway (don't abort the sequence)
        return True

    # ------------------------------------------------------------------ #
    #  RGB Lighting                                                         #
    # ------------------------------------------------------------------ #

    def set_light(self, mode=1, r=0, g=255, b=255, brightness=4, speed=3, direction=1):
        """
        Configure RGB backlight mode and colour.

        Sequence (from DeviceDriver.exe disassembly):
          1. [0x04, 0x18]             → ACK  (setup/handshake)
          2. [0x04, 0x13, ..., 0x01]  → ACK  (begin light config, byte[8]=0x01)
          3. payload [mode, r, g, b, colortype, …brightness, speed, dir, …0x55, 0xAA]  (no ACK)
          4. [0x04, 0x02]             → ACK  (apply)
          5. [0x04, 0xF0]             → ACK  (save to EEPROM)

        Args:
            mode:       1-22  (see LIGHT_MODES)
            r, g, b:    0-255 colour
            brightness: 0-4
            speed:      0-4
            direction:  0 or 1
        """
        self._send_with_ack(0x04, 0x18)
        self._send_with_ack(0x04, 0x13, extra={8: 0x01})

        # Payload packet (no ACK expected)
        pkt = bytearray(64)
        if int(mode) == 20 or int(brightness) == 0:
            # Mode 20 / Backlight Off: Windows driver uses hardware sleep opcode 0x80 (at 0x42d907)
            pkt[0]  = 0x80            # 0x80 = Hardware Backlight Off opcode
            pkt[1]  = 0x00            # R
            pkt[2]  = 0x00            # G
            pkt[3]  = 0x00            # B
            pkt[4]  = 0x00
            pkt[8]  = 0x00            # colortype = 0 (mono / off)
            pkt[9]  = 0x05            # speed
            pkt[10] = 0x05            # direction
            pkt[11] = 0x00            # brightness = 0
            pkt[14] = 0xAA
            pkt[15] = 0x55
        else:
            pkt[0]  = int(mode)       & 0xFF
            pkt[1]  = int(r)          & 0xFF
            pkt[2]  = int(g)          & 0xFF
            pkt[3]  = int(b)          & 0xFF
            pkt[4]  = 0x00
            # colortype: 0 = custom single color, 1 = multi-color spectrum cycle
            pkt[8]  = 0x00 if int(mode) in SINGLE_COLOR_MODES else 0x01
            pkt[9]  = int(speed)      & 0xFF
            pkt[10] = int(direction)  & 0xFF
            pkt[11] = int(brightness) & 0xFF
            pkt[14] = 0xAA
            pkt[15] = 0x55
        self._set_feature(pkt)
        time.sleep(0.020)

        self._send_with_ack(0x04, 0x02)   # apply
        self._send_with_ack(0x04, 0xF0)   # save to EEPROM
        return True

    # ------------------------------------------------------------------ #
    #  Clock Sync                                                          #
    # ------------------------------------------------------------------ #

    def sync_clock(self):
        """
        Sync keyboard TFT LCD clock with local system time.

        Sequence (opcode 0x28 confirmed from disassembly at 0x437160):
          1. [0x04, 0x18]                      → ACK
          2. [0x04, 0x28, ..., byte[8]=0x01]   → ACK  (begin clock config)
          3. payload: [0x00, 0x01, 0x5a, yr, mo, day, hr, min, sec, ..., 0x55, 0xAA]  (no ACK)
          4. [0x04, 0x02]                      → ACK  (apply)
        """
        now = time.localtime()

        self._send_with_ack(0x04, 0x18)
        self._send_with_ack(0x04, 0x28, extra={8: 0x01})

        # Clock payload
        pkt = bytearray(64)
        pkt[0]  = 0x00               # reserved
        pkt[1]  = 0x01               # clock display style (24h=0x01)
        pkt[2]  = 0x5A               # magic byte (from firmware)
        pkt[3]  = now.tm_year % 100  # year (2-digit)
        pkt[4]  = now.tm_mon         # month 1-12
        pkt[5]  = now.tm_mday        # day
        pkt[6]  = now.tm_hour        # hour (24h)
        pkt[7]  = now.tm_min         # minute
        pkt[8]  = now.tm_sec         # second
        pkt[62] = 0x55
        pkt[63] = 0xAA
        self._set_feature(pkt)
        time.sleep(0.020)

        self._send_with_ack(0x04, 0x02)   # apply
        return True

    # ------------------------------------------------------------------ #
    #  LCD Image / GIF Upload                                              #
    # ------------------------------------------------------------------ #

    def upload_lcd_image(self, image_path, slot=1, progress_cb=None):
        """
        Convert a GIF or static image to 160x80 RGB565 and stream it to the
        keyboard LCD via Interface 2 (/dev/hidrawXX).

        Verified Protocol (matching official LangTu DeviceDriver.exe & Windows pcapng):
          1. Handshake: [0x04, 0x18] -> ACK
          2. Start:     [0x04, 0x72, slot, 0, 0, 0, 0, 0, chunks_lo, chunks_hi, ...] -> ACK
          3. Stream:    Write 4096-byte chunks to /dev/hidrawXX:
             - Header: Exactly 256 bytes (0x100):
                 buffer[0] = num_frames (clamped to 255)
                 buffer[1 .. num_frames] = delays in 10ms units (e.g. 20 = 200ms)
                 buffer[num_frames + 1 .. 255] = 0xFF padding
             - Frames: Contiguous 25,600 bytes per frame (160x80 RGB565 Little-Endian).
                 Frame 0 starts at offset 256.
                 Frame i starts at offset: 256 + i * 25,600.
                 NO intermediate chunk padding between frames!
             - Tail: Padded with 0xFF only at the end to multiple of 4096 bytes.
          4. Apply:     [0x04, 0x02] -> ACK
        """
        if not self.lcd_fd:
            raise RuntimeError(
                "未找到键盘屏幕的输出端口 /dev/hidraw (Interface 2)，"
                "请确认 udev 规则与 USB 连线！"
            )

        W, H         = 160, 80
        FRAME_PIXELS = W * H * 2    # 25,600 bytes
        CHUNK_SIZE   = 4096
        HEADER_SIZE  = 256

        # ---- Extract frames & convert to RGB565 Little-Endian ---- #
        im     = Image.open(image_path)
        frames = []
        delays = []

        try:
            while True:
                duration = im.info.get('duration', 200)
                # Official LangTu driver sets default duration to 20 (200ms)
                if duration <= 40:
                    delay_val = 20
                else:
                    delay_val = max(1, min(255, duration // 10))
                delays.append(delay_val)

                frame = im.copy().convert('RGB').resize((W, H), Image.Resampling.LANCZOS)
                raw   = bytearray(FRAME_PIXELS)
                idx   = 0
                for y in range(H):
                    for x in range(W):
                        pr, pg, pb = frame.getpixel((x, y))
                        rgb565       = ((pr >> 3) << 11) | ((pg >> 2) << 5) | (pb >> 3)
                        raw[idx]     = rgb565 & 0xFF
                        raw[idx + 1] = (rgb565 >> 8) & 0xFF
                        idx += 2
                frames.append(bytes(raw))
                if len(frames) >= 255:
                    break
                im.seek(im.tell() + 1)
        except EOFError:
            pass

        if not frames:
            raise ValueError("未能从图像提取到有效帧")

        num_frames = len(frames)

        # Monolithic buffer matching DeviceDriver.exe exactly
        data_len = HEADER_SIZE + num_frames * FRAME_PIXELS
        pad = (CHUNK_SIZE - (data_len % CHUNK_SIZE)) % CHUNK_SIZE
        total_len = data_len + pad
        total_chunks = total_len // CHUNK_SIZE

        buffer = bytearray(b'\xff' * total_len)
        buffer[0] = num_frames & 0xFF
        for i, d in enumerate(delays):
            buffer[1 + i] = d & 0xFF

        offset = HEADER_SIZE
        for f in frames:
            buffer[offset : offset + FRAME_PIXELS] = f
            offset += FRAME_PIXELS

        # 1. Handshake
        self._send_with_ack(0x04, 0x18)

        # 2. Start command
        p = bytearray(64)
        p[0] = 0x04
        p[1] = 0x72
        p[2] = slot & 0xFF                 # Slot ID (1 for Custom Animation 1)
        p[8] = total_chunks & 0xFF         # total chunks (lo)
        p[9] = (total_chunks >> 8) & 0xFF  # total chunks (hi)
        self._set_feature(p)

        resp = self._get_feature()
        if resp:
            print(f'[LCD] 0x72 ACK: {resp[:12].hex()}')

        # 3. Stream all chunks with hardware ACK flow-control
        # Device signals readiness via 64-byte report on ep 0x84 (01 5a 02 ...)
        # typically taking ~135ms to flash each 4096-byte chunk into internal memory.
        for i in range(total_chunks):
            chunk = buffer[i * CHUNK_SIZE : (i + 1) * CHUNK_SIZE]
            os.write(self.lcd_fd, chunk)

            # Wait for hardware ACK from device (01 5a 02 ...)
            r, _, _ = select.select([self.lcd_fd], [], [], 0.5)
            if r:
                try:
                    ack = os.read(self.lcd_fd, 64)
                    # Device confirmed chunk write (01 5a 02)
                except Exception:
                    pass
                # Give MCU DMA controller 10ms to settle and commit buffer
                time.sleep(0.010)
            else:
                # Fallback: safety sleep matching hardware write cycle
                time.sleep(0.145)

            if progress_cb and (i % 5 == 0 or i + 1 == total_chunks):
                progress_cb(int((i + 1) / total_chunks * 100))

        # 4. Apply
        self._send_with_ack(0x04, 0x02)

        if progress_cb:
            progress_cb(100)
        return num_frames
