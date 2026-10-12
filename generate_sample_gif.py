#!/usr/bin/env python3
"""
Generate a test animated GIF specifically formatted for LT-104 TFT LCD:
Dimensions: 160 x 80 pixels
Animation: Cyberpunk HUD audio visualizer with pulsing neon ring & clock/stats counter.
"""
import math
from PIL import Image, ImageDraw, ImageFont

W, H = 160, 80
NUM_FRAMES = 36  # Smooth looping animation

frames = []

for i in range(NUM_FRAMES):
    # Base dark background
    img = Image.new("RGB", (W, H), (10, 14, 26))
    draw = ImageDraw.Draw(img)

    phase = (i / NUM_FRAMES) * 2 * math.pi

    # 1. Subtle grid lines
    for x in range(0, W, 20):
        draw.line([(x, 0), (x, H)], fill=(20, 26, 45), width=1)
    for y in range(0, H, 16):
        draw.line([(0, y), (W, y)], fill=(20, 26, 45), width=1)

    # 2. Glowing outer border
    border_pulse = int(180 + 75 * math.sin(phase))
    draw.rectangle([(1, 1), (W - 2, H - 2)], outline=(0, border_pulse, 255), width=1)

    # 3. Audio visualizer EQ spectrum bars on the right side
    num_bars = 9
    bar_w = 5
    bar_gap = 2
    start_x = 90
    for b in range(num_bars):
        # Sine wave height modulation per bar
        bar_phase = phase * 2 + b * 0.7
        h_ratio = (math.sin(bar_phase) + 1.0) / 2.0
        bar_height = int(8 + h_ratio * 44)
        bx = start_x + b * (bar_w + bar_gap)
        by = H - 10 - bar_height
        
        # Color gradient: Cyan -> Magenta
        r = int(255 * (b / num_bars))
        g = int(229 * (1.0 - (b / num_bars) * 0.7))
        b_col = 255
        draw.rectangle([(bx, by), (bx + bar_w, H - 10)], fill=(r, g, b_col))

    # 4. Animated Rotating / Pulsing Cyberpunk Ring on the left side
    cx, cy = 42, 40
    base_r = 22 + 4 * math.sin(phase)
    # Background circle
    draw.ellipse([(cx - base_r, cy - base_r), (cx + base_r, cy + base_r)], outline=(35, 45, 80), width=2)
    # Orbiting dots
    for dot in range(4):
        dot_angle = phase + dot * (math.pi / 2)
        dot_x = cx + base_r * math.cos(dot_angle)
        dot_y = cy + base_r * math.sin(dot_angle)
        draw.ellipse([(dot_x - 3, dot_y - 3), (dot_x + 3, dot_y + 3)], fill=(0, 229, 255))

    # Inner core dot
    core_pulse = int(140 + 115 * math.sin(phase * 2))
    draw.ellipse([(cx - 7, cy - 7), (cx + 7, cy + 7)], fill=(255, 0, core_pulse))

    # 5. Top header text
    draw.text((6, 5), "LT-104", fill=(0, 229, 255))
    draw.text((95, 5), f"F:{i+1:02d}", fill=(255, 214, 0))

    # 6. Bottom status text
    draw.text((6, 64), "RGB565", fill=(142, 155, 176))

    frames.append(img)

# Save as animated GIF (duration 50ms per frame = 20 FPS)
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lt104_sample.gif")
frames[0].save(
    output_path,
    save_all=True,
    append_images=frames[1:],
    duration=50,
    loop=0,
    optimize=False
)

print(f"Generated {NUM_FRAMES} frames animated GIF at: {output_path}")
