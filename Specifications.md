# LangTu LT-104 Gaming Keyboard (Linux) — Technical Specifications & Architecture

Comprehensive technical specifications, hardware protocol reverse-engineering, lighting mode behaviors, HUD telemetry architecture, clock synchronization, and LCD display pipeline for the **LangTu LT-104 (狼途 LT-104)** keyboard on Ubuntu / Linux.

---

## 1. Hardware Architecture & USB Interfaces

The LangTu LT-104 is an RGB mechanical keyboard featuring an on-board 1.14" 160×80 TFT color screen and an interactive rotary knob. It is driven by an ultra-low-power **SONiX SN32F240B** single-core 48MHz ARM Cortex-M0 microcontroller.

### USB Identifiers
- **USB Vendor ID (VID)**: `0c45` (Microdia / SONiX Technology Co., Ltd.)
- **USB Product ID (PID)**: `8009` (LT104 Gaming Keyboard)

### USB Logical Interfaces
| Interface | Kernel Driver | Endpoint(s) | Functionality |
| :--- | :--- | :--- | :--- |
| **Interface 0** | `usbhid` (`/dev/input/event*`) | `0x81` (Interrupt In) | Standard USB HID 104-key typing input (N-Key Rollover). |
| **Interface 1** | `usbhid` (`/dev/input/event*`) | `0x82` (Interrupt In) | Consumer keys, audio volume knob, media controls. |
| **Interface 2** | `hidraw` (`/dev/hidraw*`) | `0x03` (Interrupt Out), `0x84` (Interrupt In) | TFT LCD communication channel. Framebuffer streaming (RAM/Flash) and write ACK flow control. |
| **Interface 3** | Vendor Control (`USBDEVFS_CONTROL`) | `Endpoint 0` (Control Transfers) | Hardware configuration: Backlight modes, RGB color, brightness, speed, clock calibration, EEPROM commit. |

---

## 2. Lighting Modes Matrix & Exact Behaviors

The physical LT-104 keyboard microcontroller firmware contains **19 built-in hardware lighting animations** (Modes `1` through `19`), plus a dedicated hardware sleep opcode (`0x80`) for Backlight Off (Mode `20`).

### Quick Reference Matrix

| Mode ID | Name (ZH / EN) | Custom Color | Speed Slider | Brightness Slider | Keypress Reactivity |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **1** | 静态恒亮 (Static) | **Yes** | *Hidden (N/A)* | **Yes (1–4)** | Continuous solid light |
| **2** | 单点亮 (Single Light) | **Yes** | **Yes** | **Yes (1–4)** | Keypress triggers fade-out |
| **3** | 单熄灭 (Single Off) | **Yes** | **Yes** | **Yes (1–4)** | Keypress extinguishes key |
| **4** | 繁星点点 (Stars) | **Yes** | **Yes** | **Yes (1–4)** | Autonomous twinkling |
| **5** | 漫天飞雪 (Snow) | **Yes** | **Yes** | **Yes (1–4)** | Autonomous snow falling |
| **6** | 百花争艳 (Blossom) | No | **Yes** | **Yes (1–4)** | Autonomous multi-color bloom |
| **7** | 动态呼吸 (Breathing) | **Yes** | **Yes** | **Yes (1–4)** | Full-board rhythmic fade |
| **8** | 光谱循环 (Spectrum Cycle) | No | **Yes** | **Yes (1–4)** | Synchronous full-board RGB cycle |
| **9** | 彩泉涌动 (Rainbow Wave) | No | **Yes** | **Yes (1–4)** | Horizontal sweeping rainbow |
| **10** | 多彩纵横 (Cross Pattern) | No (7 Rainbow) | **Yes (0.5s @ Speed 2)** | **Yes (1–4)** | **No reaction on keypress** |
| **11** | 随波逐流 (River Stream) | No | **Yes** | **Yes (1–4)** | Serpentine organic wave |
| **12** | 峰回路转 (Rotary Wave) | No | **Yes** | **Yes (1–4)** | Angular rotary spiral sweep |
| **13** | 一触即发 (Ripple Trigger) | No | **Yes** | **Yes (1–4)** | Horizontal ripple along pressed row |
| **14** | 一石二鸟 (Dual Ripple) | No | **Yes** | **Yes (1–4)** | Bidirectional radial burst |
| **15** | 涟漪扩散 (Ripple Spread) | No | **Yes** | **Yes (1–4)** | Concentric circular ripple |
| **16** | 川流不息 (Infinite Stream) | No (Per-Key Random) | **Yes (Half-speed, 1.1s/row)** | **Yes (1–4)** | **No reaction on keypress** |
| **17** | 重峦叠嶂 (Rolling Hills) | No | **Yes** | **Yes (1–4)** | **No reaction on keypress** |
| **18** | 斜风细雨 (Gentle Rain) | No (Per-Key Random) | **Yes** | **Yes (1–4)** | **No reaction on keypress** |
| **19** | 来回穿梭 (Shuttle) | No | **Yes** | **Yes (1–4)** | **No reaction on keypress** |
| **20** | 关闭背光 (Backlight Off) | No | *Hidden (N/A)* | *Fixed 0%* | All LEDs completely off (`0x80`) |

---

### Detailed Lighting Mode Behaviors

#### Mode 1: 静态恒亮 (Static)
- **Controls**: Custom RGB Color picker enabled. Brightness slider enabled (Levels 1 to 4). Speed slider hidden (static light has no velocity).
- **Behavior**: All 104 keys remain permanently illuminated in the selected custom RGB color.

#### Mode 2: 单点亮 (Single Light)
- **Controls**: Custom Color enabled. Speed slider adjusts fade-out duration. Brightness enabled.
- **Behavior**: The entire keyboard background remains dark. Pressing any key instantly lights up that key in the custom color, which then smoothly fades back to dark.

#### Mode 3: 单熄灭 (Single Off)
- **Controls**: Custom Color enabled. Speed slider adjusts recovery duration. Brightness enabled.
- **Behavior**: All keys are continuously illuminated in the custom color. Pressing any key temporarily extinguishes it, after which it smoothly fades back on.

#### Mode 4: 繁星点点 (Stars)
- **Controls**: Custom Color enabled. Speed slider adjusts twinkle frequency. Brightness enabled.
- **Behavior**: Individual keys across the keyboard autonomously fade in and out in the custom color at random intervals, resembling stars twinkling in the night sky.

#### Mode 5: 漫天飞雪 (Snow)
- **Controls**: Custom Color enabled. Speed slider adjusts fall speed. Brightness enabled.
- **Behavior**: Clusters of keys light up and travel vertically downward across the rows in the custom color, simulating falling snowflakes.

#### Mode 6: 百花争艳 (Blossom)
- **Controls**: Multi-color mode (color picker disabled). Speed and brightness adjustable.
- **Behavior**: Vibrant multi-color floral pulses bloom outward from random cluster centers across the keyboard.

#### Mode 7: 动态呼吸 (Breathing)
- **Controls**: Custom Color enabled. Speed slider adjusts breathing pulse rate. Brightness enabled.
- **Behavior**: All 104 keys breathe synchronously, smoothly dimming to completely dark and swelling back to peak brightness in the selected custom color.

#### Mode 8: 光谱循环 (Spectrum Cycle)
- **Controls**: Multi-color mode. Speed and brightness adjustable.
- **Behavior**: All keys simultaneously transition through the entire 360° RGB color spectrum in lockstep.

#### Mode 9: 彩泉涌动 (Rainbow Wave)
- **Controls**: Multi-color mode. Speed and brightness adjustable.
- **Behavior**: A continuous horizontal rainbow spectrum wave sweeps across the keyboard from left to right.

#### Mode 10: 多彩纵横 (Cross Pattern)
- **Controls**: Multi-color mode using the 7 Rainbow Colors. Speed and brightness adjustable. Pressing keys has no reaction.
- **Behavior**:
  - Operates using the 7 canonical rainbow colors: **Red**, **Orange**, **Yellow**, **Green**, **Cyan**, **Blue**, and **Purple**.
  - Alternates across the 5 horizontal rows of the keyboard (Row 0: F-keys; Row 1: Numbers; Row 2: QWERTY; Row 3: ASDF; Row 4: ZXCV & Spacebar).
  - At any given instant, **each of the 5 rows displays a different color** from the 7 rainbow colors (no two rows share the same color).
  - Each row slowly and smoothly transitions into its own next color without copying or clashing with colors from other rows.
  - **Animation Speed 2 Timing**: Each row shifts to another color every **0.5 seconds** (scaled smoothly with speed slider: `step_dur = 0.5s / speed_mult`).
  - Typing or clicking keys has zero effect on the animation.

#### Mode 11: 随波逐流 (River Stream)
- **Controls**: Multi-color mode. Speed and brightness adjustable.
- **Behavior**: Organic serpentine ribbons of light glide horizontally and diagonally through the key matrix like river currents.

#### Mode 12: 峰回路转 (Rotary Wave)
- **Controls**: Multi-color mode. Speed and brightness adjustable.
- **Behavior**: An angular spiral color wave rotates circularly around the center of the keyboard.

#### Mode 13: 一触即发 (Ripple Trigger)
- **Controls**: Reactive mode. Speed and brightness adjustable.
- **Behavior**: Pressing a key sends a high-speed light pulse expanding left and right **strictly along the same horizontal row** as the pressed key.

#### Mode 14: 一石二鸟 (Dual Ripple)
- **Controls**: Reactive mode. Speed and brightness adjustable.
- **Behavior**: Pressing a key fires symmetric bidirectional horizontal and vertical bursts outward from the pressed switch.

#### Mode 15: 涟漪扩散 (Ripple Spread)
- **Controls**: Reactive mode. Speed and brightness adjustable.
- **Behavior**: Pressing any key casts a circular concentric shockwave that expands outward across the entire 104-key matrix.

#### Mode 16: 川流不息 (Infinite Stream)
- **Controls**: Autonomous stream mode. Speed and brightness adjustable. Pressing keys has no reaction.
- **Behavior**:
  - The background is completely dark.
  - A stream object moves continuously from **left to right** across the keyboard, progressing row by row (Row 0 → Row 1 → Row 2 → Row 3 → Row 4 → Row 5, then loops back to Row 0).
  - **Calibrated Half-Speed**: The traverse time per row is calibrated to **1.10 seconds** at Speed 2 (`row_interval = 1.10s / speed_mult`), cutting the motion speed in half for a smooth, relaxed flow.
  - **5.4-Key Width with Gaussian Blur**: The stream object is **5.4 keys wide** with Gaussian blur falloff ($\sigma = 60.0\text{px}$, where $5.4 \times 41\text{px} = 221.4\text{px}$). It starts outside the left margin ($-140\text{px}$) and exits past the right margin ($+1098\text{px}$), ensuring keys fade in and out smoothly with zero popping.
  - **Per-Key Sustained Random Color**: For each key along the row, the key assigns itself an independent random color (via bit-mixer hash of key index and stream index). This color is **sustained 100% constant** throughout the entire passage of that stream (no color rotation, shifting, or flickering).
  - **Fresh Color for Subsequent Streams**: When another stream returns to that row (`stream_id + 6`), each key assigns itself a brand-new random color.

#### Mode 17: 重峦叠嶂 (Rolling Hills)
- **Controls**: Autonomous dual-wave mode. Speed and brightness adjustable. Pressing keys has no reaction.
- **Behavior**:
  - Background is completely dark.
  - Slashes emerge strictly from the **50% middle of the keyboard**:
    - **Backslash (`\`)**: Emerges at 55% and sweeps rightward to the right edge without bouncing back.
    - **Forward slash (`/`)**: Emerges at 45% and sweeps leftward to the left edge without bouncing back.
  - **Alternating Sequence**: Once a forward slash finishes emerging from the 50% midpoint, a backslash begins emerging immediately; once that backslash finishes emerging, a forward slash begins immediately. Slashes alternate continuously.
  - **No Cross in Center**: Forward and backward slashes do not cross over each other in the middle.
  - **Spacing & Width**: Slashes are spaced **3 keys apart** (`slash_spacing = 164.0px`), are **1 key wide** with smooth exponential window falloff, and smoothly disappear at the edges without bouncing.

#### Mode 18: 斜风细雨 (Gentle Rain)
- **Controls**: Autonomous rain mode. Speed and brightness adjustable. Pressing keys has no reaction.
- **Behavior**:
  - Multiple 45° backslashes (`\`, along $cx - cy$) sweep continuously from left to right across the matrix.
  - **1.8-Key Width with Gaussian Blur**: Each backslash has a width of 1.8 keys with Gaussian blur ($\sigma = 20.0\text{px}$, full falloff across $1.8 \times 41\text{px} = 73.8\text{px}$).
  - **5-Key Pitch Spacing**: Slashes are spaced exactly **5 keys apart** from the center of one backslash to the center of the next (`slash_spacing = 205.0px`).
  - **Continuous Fade In/Out**: Keys never turn on and off abruptly. They fade in smoothly as the slash approaches and fade out smoothly as it passes.
  - **Per-Key Sustained Random Color**: Each key assigns itself an independent random color that is sustained throughout the passage of that backslash. The key uses another random color when the next backslash arrives.

#### Mode 19: 来回穿梭 (Shuttle)
- **Controls**: Multi-color wave mode. Speed and brightness adjustable. Pressing keys has no reaction.
- **Behavior**: Harmonic oscillating color ribbons oscillate back and forth horizontally across the keyboard.

#### Mode 20: 关闭背光 (Backlight Off)
- **Controls**: Fixed brightness 0, speed hidden, color picker hidden.
- **Behavior**: Sends hardware sleep opcode `pkt[0] = 0x80`. Turns off all 104 LEDs immediately. The software stores the user's previously chosen brightness so that selecting any active mode immediately restores the keyboard to its prior illumination level.

---

### Note on Phantom Modes 21 & 22 (Solid Center & Neon Glow)
- **Discovery**: In the generic Windows OEM software template, options labeled "万众一心 (Solid Center)" (ID 21) and "流光溢彩 (Neon Glow)" (ID 22) appeared in the dropdown.
- **Hardware Verification**: Physical testing on the actual LangTu LT-104 hardware confirmed that when opcode `21` (0x15) or `22` (0x16) is sent over USB, the keyboard MCU's switch statement encounters an unhandled mode and falls through to `default: break`. The physical keyboard **does not change lighting and remains on whatever previous mode was running**.
- **Resolution**: Modes 21 and 22 do not exist in the LT-104 microcontroller ROM. They have been completely removed from the software suite to ensure that every option presented to the user is 100% functional on the real hardware.

---

## 3. Real-Time System Monitoring HUD

The LT-104 features a 1.14" 160×80 full-color TFT LCD screen. The System HUD feature streams live CPU utilization, RAM usage, and animated telemetry bars directly to the display.

### How It Works
1. System metrics are sampled using `psutil` (CPU percentage, RAM percentage, system clock).
2. The telemetry frame is rendered into a 160×80 RGB565 Little-Endian buffer with dark cyan/emerald aesthetic, live bar graphs, and an equalizer visualizer.
3. The frame is streamed in seven 4,096-byte USB chunks over Interrupt Out Endpoint `0x03` (Interface 2).
4. After transferring the pixel data, the host sends the **RAM commit command** `[0x04, 0x02]` over Interface 3.
5. **Zero Flash Wear**: Pushing telemetry to screen RAM (`0x04 0x02`) updates the display without writing to on-board SPI Flash, eliminating any wear on the flash memory chips.

### The Hardware Blinking Problem & Explanation
Users frequently notice that when the HUD updates, the keyboard's 104-key RGB backlight blinks or turns off for approximately 0.5 to 1.0 second.

#### Root Cause:
1. **Microcontroller Architecture**: The keyboard uses a 48MHz single-core ARM Cortex-M0 MCU (SONiX SN32F240B).
2. **Software-Multiplexed PWM**: The 104 RGB LEDs are driven by software-multiplexed high-frequency timer interrupts (10–20 kHz) rather than dedicated hardware LED driver ASICs.
3. **SPI Bus Saturation**: One 160×80 screen frame requires 25,600 pixel bytes + 256 header bytes = 25,856 bytes. At the MCU's maximum SPI clock rate, writing 25.8KB to the ST7735 LCD driver takes ~1.0 second.
4. **Firmware Behavior**: During this 1-second transfer, the 48MHz MCU CPU utilization reaches 100%. To prevent USB buffer overruns and packet drops, the microcontroller firmware temporarily halts the software PWM LED timer. Once the frame commit completes, the PWM timer immediately resumes and the backlight turns back on.
5. **Identical in Official Software**: This behavior is an inherent hardware characteristic of the keyboard's MCU and occurs identically when using the official LangTu Windows driver.

#### Software Mitigations:
- **Adjustable Refresh Intervals**: Users can select from `5s`, `10s`, `20s`, `30s`, `60s`, `120s` (2 min - recommended default), and `300s` (5 min - power saving). Setting the interval to 2 or 5 minutes minimizes backlight interruptions while keeping system telemetry up to date.
- **Single-Shot Trigger (`⚡ Update HUD Once`)**: Allows the user to inspect hardware metrics on-demand with a single click, completely avoiding continuous background cycling.
- **Stop Restore Preset**: When the HUD is stopped, the software automatically restores the factory loop (`lt104_sample.gif`) or custom animation back to the LCD.

---

## 4. TFT Clock Calibration & Auto-Sync

The keyboard's LCD displays a digital clock with year, month, date, and 24-hour time.

### How It Works
1. The host queries local PC system time (`struct tm`).
2. A 64-byte vendor command packet is constructed and sent to Interface 3:
   ```
   Byte 0:  0x04
   Byte 1:  0x14
   Byte 2:  Year High Byte (e.g. 20)
   Byte 3:  Year Low Byte  (e.g. 26 for 2026)
   Byte 4:  Month (1-12)
   Byte 5:  Day (1-31)
   Byte 6:  Hour (0-23)
   Byte 7:  Minute (0-59)
   Byte 8:  Second (0-59)
   ...
   ```
3. The keyboard microcontroller updates its internal hardware RTC and echoes `[0x04, 0x14]` via GET_REPORT as an ACK.
4. Because the clock packet is only 64 bytes (unlike 25.8KB screen frames), clock synchronization takes less than 15 milliseconds and **causes zero backlight blinking or typing disruption**.

### Automated 12-Hour Schedule Service
- Implemented as a native Linux `systemd` user timer:
  - Unit: `~/.config/systemd/user/lt104-clock-sync.timer`
  - Service: `~/.config/systemd/user/lt104-clock-sync.service`
  - Schedule: `OnCalendar=*-*-* 00,12:00:00` (runs automatically at midnight and noon).
- Can be toggled on or off directly from the Web Console, Desktop App, GNOME Extension, or CLI (`lt104_cli.py clock-schedule-enable / disable`).

---

## 5. LCD Image & GIF Upload Pipeline

The keyboard supports committing custom static graphics or multi-frame animated GIFs to internal on-board SPI Flash (Slot 1), so they loop autonomously even when the keyboard is disconnected from the PC.

### Image Format Requirements
| Parameter | Requirement | Notes |
| :--- | :--- | :--- |
| **Dimensions** | Exactly **160 × 80 pixels** | Uploads in other dimensions are automatically scaled/cropped. |
| **Color Depth** | **16-bit RGB565 Little-Endian** | 5 bits Red, 6 bits Green, 5 bits Blue. Byte order: `[low_byte, high_byte]`. |
| **Frame Header** | 256 bytes per frame | Contains frame index, width (160), height (80), and duration metadata. |
| **Frame Data** | 25,600 bytes per frame | $160 \times 80 \times 2\text{ bytes} = 25,600\text{ bytes}$. Total frame chunk: 25,856 bytes. |
| **Frame Rate** | 10 to 30 FPS recommended | Standard frame delay: 60ms to 100ms. |
| **File Types** | Animated `.gif`, `.png`, `.jpg`, `.webp` | Converted client-side / server-side via PIL (Python Pillow). |

### Flash Upload Protocol & Hardware Handshake
1. Handshake `[0x04, 0x18]` and `[0x04, 0x11]` initialize flash write mode.
2. For each frame:
   - 256-byte header + 25,600 pixel bytes are split into seven 4,096-byte blocks.
   - Blocks are sent over Interface 2 Endpoint `0x03`.
   - After each block, the host polls Endpoint `0x84` for a hardware ACK byte (`0xAA`) confirming the 48MHz MCU has committed the block to SPI Flash before sending the next chunk.
3. Commit command `[0x04, 0x02]` and Flash Commit `[0x04, 0xF0]` finalize the upload.
4. The uploaded GIF is now stored permanently in Slot 1 and loops continuously.
