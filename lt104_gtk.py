#!/usr/bin/env python3
"""
LT-104 Keyboard Control Centre — GTK4 + libadwaita native GNOME app.
Reuses lt104_core.py directly (no web server needed).
"""
import sys
import os
import threading
import tempfile
import time
import math
import colorsys
import random
import cairo

# Make sure we can import lt104_core from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Adw, Gdk, GLib, Gio, GdkPixbuf, Pango

from lt104_core import LT104Controller, LIGHT_MODES, MULTI_COLOR_MODES, find_lt104_usb, find_lt104_lcd_hidraw
from config import load_config, save_config

APP_ID = "com.theforwardway.lt104"
CLI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lt104_cli.py")

KB_KEYS = [["esc",19,16,33,33],["F1",100,16,33,33],["F2",141,16,33,33],["F3",182,16,33,33],["F4",222,16,33,33],["F5",285,16,33,33],["F6",326,16,33,33],["F7",367,16,33,33],["F8",408,16,33,33],["F9",469,16,33,33],["F10",510,16,33,33],["F11",551,16,33,33],["F12",594,16,33,33],["print",644,16,33,33],["scrl lock",686,16,33,33],["pause",729,16,33,33],["~",19,70,33,33],["1",60,70,33,33],["2",101,70,33,33],["3",142,70,33,33],["4",183,70,33,33],["5",224,70,33,33],["6",265,70,33,33],["7",306,70,33,33],["8",347,70,33,33],["9",388,70,33,33],["0",429,70,33,33],["-",469,70,33,33],["=",510,70,33,33],["backspace",551,70,78,33],["insert",644,70,33,33],["home",686,70,33,33],["page up",729,70,33,33],["numlock",779,70,33,33],["/",822,70,33,33],["*",864,70,33,33],["-",906,70,33,33],["tab",19,111,52,33],["Q",79,111,33,33],["W",120,111,33,33],["E",161,111,33,33],["R",202,111,33,33],["T",244,111,33,33],["Y",285,111,33,33],["U",326,111,33,33],["I",367,111,33,33],["O",408,111,33,33],["P",449,111,33,33],["[",490,111,33,33],["]",531,111,33,33],["\\|",573,111,55,33],["del",644,111,33,33],["end",686,111,33,33],["page down",729,111,33,33],["7",779,111,33,33],["8",822,111,33,33],["9",864,111,33,33],["+",906,111,33,73],["Caps",19,152,61,33],["A",89,152,33,33],["S",130,152,33,33],["D",171,152,33,33],["F",213,152,33,33],["G",254,152,33,33],["H",295,152,33,33],["J",336,152,33,33],["K",377,152,33,33],["L",418,152,33,33],[";",459,152,33,33],["'\"",500,152,33,33],["enter",540,152,89,33],["4",779,152,33,33],["5",822,152,33,33],["6",864,152,33,33],["shift",19,193,83,33],["Z",111,193,33,33],["X",151,193,33,33],["C",194,193,33,33],["V",235,193,33,33],["B",276,193,33,33],["N",317,193,33,33],["M",358,193,33,33],["<",399,193,33,33],[">",439,193,33,33],["?",480,193,33,33],["shift",521,193,108,33],["\u2191",686,193,33,33],["1",779,193,33,33],["2",822,193,33,33],["3",864,193,33,33],["enter",906,193,33,73],["control",19,234,44,33],["win",70,234,44,33],["alt",121,234,44,33],["space",173,234,246,33],["alt",429,234,44,33],["fn",480,234,44,33],["app",532,234,44,33],["control",584,234,44,33],["\u2190",644,234,33,33],["\u2193",686,234,33,33],["\u2192",729,234,33,33],["0",779,234,74,33],[".",864,234,33,33]]

def draw_round_rect(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()

def hsl_to_rgb(h, s, l):
    return colorsys.hls_to_rgb((h % 360.0) / 360.0, l, s)

def get_key_row(ky):
    if ky < 45: return 0
    if ky < 90: return 1
    if ky < 130: return 2
    if ky < 172: return 3
    if ky < 213: return 4
    return 5


# --------------------------------------------------------------------------- #
#  Helpers                                                                      #
# --------------------------------------------------------------------------- #

def make_wide_list_factory():
    """Create a SignalListItemFactory that displays full text without ellipsis (...)"""
    factory = Gtk.SignalListItemFactory()
    def setup(f, item):
        lbl = Gtk.Label(xalign=0)
        lbl.set_ellipsize(Pango.EllipsizeMode.NONE)
        lbl.set_margin_start(12)
        lbl.set_margin_end(16)
        lbl.set_margin_top(6)
        lbl.set_margin_bottom(6)
        item.set_child(lbl)
    def bind(f, item):
        obj = item.get_item()
        if obj and hasattr(obj, 'get_string'):
            item.get_child().set_text(obj.get_string())
    factory.connect("setup", setup)
    factory.connect("bind", bind)
    return factory

def hex_to_rgb(hex_str):
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def run_in_thread(fn, *args, on_done=None, on_error=None):
    """Run fn(*args) in a background thread; call on_done/on_error on the main loop."""
    def worker():
        try:
            result = fn(*args)
            if on_done:
                GLib.idle_add(on_done, result)
        except Exception as exc:
            if on_error:
                GLib.idle_add(on_error, str(exc))
    threading.Thread(target=worker, daemon=True).start()


# --------------------------------------------------------------------------- #
#  Main Window                                                                  #
# --------------------------------------------------------------------------- #

class LT104Window(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("LT-104 键盘控制中心")
        self.set_default_size(960, 680)
        self.set_resizable(True)

        # ---- Root layout ---- #
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)
        toolbar_view.add_top_bar(header)

        # Status pill in header
        self._status_label = Gtk.Label(label="⌨️  检测中…")
        self._status_label.add_css_class("caption")
        header.set_title_widget(self._status_label)

        # Scrollable main content
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        toolbar_view.set_content(scroll)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(960)
        clamp.set_margin_top(8)
        clamp.set_margin_bottom(12)
        clamp.set_margin_start(14)
        clamp.set_margin_end(14)
        scroll.set_child(clamp)

        # 2-Column responsive container so all cards and buttons fit simultaneously
        two_col_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        two_col_box.set_homogeneous(True)
        clamp.set_child(two_col_box)

        col_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        col_right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        two_col_box.append(col_left)
        two_col_box.append(col_right)

        # ---- Left Column: RGB Card & Clock Sync Card ---- #
        col_left.append(self._build_rgb_card())
        col_left.append(self._build_clock_card())

        # ---- Right Column: Real-time HUD Card & LCD Uploader Card ---- #
        col_right.append(self._build_hud_card())
        col_right.append(self._build_lcd_card())

        # ---- Toast overlay lives at window level ---- #
        self._toast_overlay = Adw.ToastOverlay()
        self.set_content(self._toast_overlay)
        self._toast_overlay.set_child(toolbar_view)

        # Initial device check once, then poll every 2 seconds
        GLib.idle_add(self._initial_refresh)
        GLib.timeout_add_seconds(2, self._refresh_status)

        # Keyboard visualizer preview state
        self._key_flashes = [0.0] * len(KB_KEYS)
        self._active_ripples = []
        self._hovered_key_idx = -1
        self._last_auto_tap_time = 0.0
        self._last_auto_ripple_time = 0.0
        self._preview_timer_id = GLib.timeout_add(33, self._tick_preview)

        # Photorealistic skin surfaces
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dark_png = os.path.join(base_dir, "static", "keyboard_skin_dark.png")
        lit_png = os.path.join(base_dir, "static", "keyboard_skin_lit.png")
        self._skin_dark = cairo.ImageSurface.create_from_png(dark_png) if os.path.exists(dark_png) else None
        self._skin_lit = cairo.ImageSurface.create_from_png(lit_png) if os.path.exists(lit_png) else None
        self._lcd_surface = None
        self._last_lcd_mtime = 0.0
        self._hud_running = False
        init_cfg = load_config()
        self._remembered_brightness = int(init_cfg.get("remembered_brightness", init_cfg.get("brightness", 4))) or 4
        self._previous_mode_id = int(init_cfg.get("mode", 1))
        self._dim_star_keys = []
        self._next_star_change_time = 0.0
        self._load_lcd_surface()

    def _initial_refresh(self):
        self._refresh_status()
        return False

    # ------------------------------------------------------------------ #
    #  Card builders                                                        #
    # ------------------------------------------------------------------ #

    def _build_rgb_card(self):
        group = Adw.PreferencesGroup()
        group.set_title("🌈  RGB 灯效与背光")
        group.set_description("立即应用并永久写入键盘 EEPROM")

        cfg = load_config()

        current_mode_id = int(cfg.get("mode", 1))
        initial_mode_idx = 0
        for idx, m in enumerate(LIGHT_MODES):
            if m["id"] == current_mode_id:
                initial_mode_idx = idx
                break

        # Keyboard visualizer preview container
        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        preview_box.set_margin_bottom(12)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_margin_start(4)
        header_box.set_margin_end(4)

        dot = Gtk.Label(label="●")
        dot.add_css_class("accent")
        header_box.append(dot)

        title_lbl = Gtk.Label(label="即时键盘灯效动画预览")
        title_lbl.add_css_class("heading")
        header_box.append(title_lbl)

        self._preview_mode_badge = Gtk.Label(label=LIGHT_MODES[initial_mode_idx]["name"])
        self._preview_mode_badge.add_css_class("pill")
        header_box.append(self._preview_mode_badge)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header_box.append(spacer)

        hint_lbl = Gtk.Label(label="💡 点击按键触发灯光反馈")
        hint_lbl.add_css_class("dim-label")
        hint_lbl.set_halign(Gtk.Align.END)
        header_box.append(hint_lbl)

        preview_box.append(header_box)

        # Drawing Area
        self._preview_area = Gtk.DrawingArea()
        self._preview_area.set_content_height(142)
        self._preview_area.set_hexpand(True)
        self._preview_area.set_draw_func(self._on_draw_keyboard_preview)

        # Gesture & motion controllers
        click_gesture = Gtk.GestureClick()
        click_gesture.connect("pressed", self._on_preview_clicked)
        self._preview_area.add_controller(click_gesture)

        motion_ctrl = Gtk.EventControllerMotion()
        motion_ctrl.connect("motion", self._on_preview_motion)
        motion_ctrl.connect("leave", self._on_preview_leave)
        self._preview_area.add_controller(motion_ctrl)

        preview_box.append(self._preview_area)
        group.add(preview_box)

        # Mode selector
        self._mode_row = Adw.ComboRow()
        self._mode_row.set_title("灯光模式")
        mode_strings = Gtk.StringList.new([m["name"] for m in LIGHT_MODES])
        self._mode_row.set_model(mode_strings)
        self._mode_row.set_list_factory(make_wide_list_factory())
        self._mode_row.set_selected(initial_mode_idx)
        self._mode_row.connect("notify::selected", self._on_mode_changed)
        group.add(self._mode_row)

        # Colour button row
        self._color_row = Adw.ActionRow()
        self._color_row.set_title("自订颜色")
        self._color_row.set_subtitle("点击色块选择")
        self._color_btn = Gtk.ColorDialogButton()
        self._color_btn.set_valign(Gtk.Align.CENTER)
        dialog = Gtk.ColorDialog()
        dialog.set_title("选择键盘背光颜色")
        dialog.set_with_alpha(False)
        self._color_btn.set_dialog(dialog)
        # Set saved or default color
        rgba = Gdk.RGBA()
        rgba.parse(cfg.get("color", "#00e5ff"))
        self._color_btn.set_rgba(rgba)
        self._color_row.add_suffix(self._color_btn)
        group.add(self._color_row)

        # Colour presets
        self._presets_row = Adw.ActionRow()
        self._presets_row.set_title("快速颜色")
        preset_box = Gtk.Box(spacing=8)
        preset_box.set_valign(Gtk.Align.CENTER)
        preset_colors = [
            ("#ff0055", "品红"), ("#00e5ff", "青蓝"), ("#00e676", "翠绿"),
            ("#ffd600", "亮黄"), ("#d500f9", "紫色"), ("#ff3d00", "橙红"),
            ("#ffffff", "纯白"),
        ]
        css = Gtk.CssProvider()
        css_rules = [
            "popover, popover.menu { min-width: 340px; }",
            "popover listview { min-width: 320px; }",
            "popover listview row { min-width: 320px; }",
        ]
        for idx, (hex_c, name) in enumerate(preset_colors):
            btn = Gtk.Button()
            btn.set_tooltip_text(name)
            btn.set_size_request(28, 28)
            btn.add_css_class(f"preset-btn-{idx}")
            css_rules.append(f".preset-btn-{idx} {{ background: {hex_c}; border-radius: 50%; min-width: 28px; min-height: 28px; padding: 0; }}")
            btn.connect("clicked", self._on_preset_clicked, hex_c)
            preset_box.append(btn)

        css.load_from_string("\n".join(css_rules))
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(display, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self._presets_row.add_suffix(preset_box)
        group.add(self._presets_row)

        # Brightness
        bright_row = Adw.ActionRow()
        bright_row.set_title("亮度")
        bright_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        bright_box.set_valign(Gtk.Align.CENTER)
        bright_box.set_size_request(200, -1)
        self._brightness_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 4, 1)
        self._brightness_scale.set_value(int(cfg.get("brightness", 4)))
        self._brightness_scale.set_draw_value(True)
        self._brightness_scale.set_hexpand(True)
        bright_box.append(self._brightness_scale)
        bright_row.add_suffix(bright_box)
        self._bright_row = bright_row
        group.add(bright_row)

        # Speed
        speed_row = Adw.ActionRow()
        speed_row.set_title("动态速度")
        speed_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        speed_box.set_valign(Gtk.Align.CENTER)
        speed_box.set_size_request(200, -1)
        self._speed_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 4, 1)
        self._speed_scale.set_value(int(cfg.get("speed", 3)))
        self._speed_scale.set_draw_value(True)
        self._speed_scale.set_hexpand(True)
        speed_box.append(self._speed_scale)
        speed_row.add_suffix(speed_box)
        self._speed_row = speed_row
        group.add(speed_row)

        # Auto Apply Switch Row
        self._auto_apply_row = Adw.SwitchRow()
        self._auto_apply_row.set_title("即时生效 (调整时自动应用)")
        self._auto_apply_row.set_subtitle("开启后调整模式、颜色、亮度或速度立即应用，无需手动点击应用按钮")
        auto_apply_val = cfg.get("light_auto_apply", True)
        self._auto_apply_row.set_active(bool(auto_apply_val))
        self._auto_apply_row.connect("notify::active", self._on_auto_apply_toggled)
        group.add(self._auto_apply_row)

        # Apply button
        self._apply_btn = Gtk.Button(label="✨  即时应用并保存灯效")
        self._apply_btn.add_css_class("suggested-action")
        self._apply_btn.add_css_class("pill")
        self._apply_btn.set_margin_top(8)
        self._apply_btn.connect("clicked", self._on_apply_light)
        self._apply_btn.set_visible(not bool(auto_apply_val))
        group.add(self._apply_btn)

        self._color_btn.connect("notify::rgba", self._on_color_changed)
        self._brightness_scale.connect("value-changed", self._on_brightness_changed)
        self._speed_scale.connect("value-changed", self._on_speed_changed)

        self._on_mode_changed(self._mode_row, None)
        return group

    def _build_clock_card(self):
        group = Adw.PreferencesGroup()
        group.set_title("🕒  TFT 时钟校准与定时同步")
        group.set_description("即时同步系统时间到键盘屏幕，或启用后台 12 小时自动校准服务")

        # 12-Hour Schedule Auto-Sync Row
        self._sched_row = Adw.SwitchRow()
        self._sched_row.set_title("定时同步小屏幕时钟 (每 12 小时)")
        self._sched_row.set_subtitle("基于系统服务在后台自动校准键盘时间")
        timer_path = os.path.expanduser("~/.config/systemd/user/timers.target.wants/lt104-clock-sync.timer")
        self._sched_row.set_active(os.path.exists(timer_path))
        self._sched_row.connect("notify::active", self._on_schedule_toggled)
        group.add(self._sched_row)

        # Clock sync action button
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(4)
        self._clock_btn = Gtk.Button(label="🕒  立即同步电脑时钟到键盘小屏幕")
        self._clock_btn.add_css_class("pill")
        self._clock_btn.connect("clicked", self._on_sync_clock)
        box.append(self._clock_btn)
        group.add(box)

        return group

    def _build_hud_card(self):
        group = Adw.PreferencesGroup()
        group.set_title("📊  系统监控 HUD (CPU / 内存 / 磁盘)")
        group.set_description("在键盘 LCD 上实时轮播电脑硬件遥测，直接写 RAM，零 Flash 磨损")

        # Interval selector row
        self._interval_intervals = [2, 5, 10, 20, 30, 60, 120, 300]
        self._interval_row = Adw.ComboRow()
        self._interval_row.set_title("HUD 刷新间隔")
        self._interval_row.set_subtitle("设定 CPU / 内存 / 时钟 轮播更新频率")
        model = Gtk.StringList.new([
            "2 秒 (高频)",
            "5 秒 (快速)",
            "10 秒 (适中)",
            "20 秒",
            "30 秒 (省电)",
            "60 秒 (超慢)",
            "120 秒 (2分钟 - 默认)",
            "300 秒 (5分钟 - 省电)"
        ])
        self._interval_row.set_model(model)
        self._interval_row.set_list_factory(make_wide_list_factory())
        cfg = load_config()
        initial_inv = float(cfg.get("hud_interval", 120.0))
        sel_idx = 6  # Index 6 is 120s default
        for idx, inv in enumerate(self._interval_intervals):
            if abs(inv - initial_inv) < 0.1:
                sel_idx = idx
                break
        self._interval_row.set_selected(sel_idx)
        self._interval_row.connect("notify::selected", self._on_interval_changed)
        group.add(self._interval_row)

        # Stop HUD Restore Preset Row
        self._restore_presets = ["lt104_sample.gif", "0_perfect36.gif", "none"]
        self._restore_row = Adw.ComboRow()
        self._restore_row.set_title("停止 HUD 恢复动画")
        self._restore_row.set_subtitle("停止监控后恢复出厂或预设动画，避免画面停留在最后静态遥测")
        restore_model = Gtk.StringList.new([
            "lt104_sample.gif (出厂小循环预设 - 默认)",
            "0_perfect36.gif (动态预设动画)",
            "不恢复 (保持最后画面)"
        ])
        self._restore_row.set_model(restore_model)
        self._restore_row.set_list_factory(make_wide_list_factory())
        current_restore = cfg.get("hud_restore_preset", "lt104_sample.gif")
        restore_idx = 0
        if current_restore in self._restore_presets:
            restore_idx = self._restore_presets.index(current_restore)
        self._restore_row.set_selected(restore_idx)
        self._restore_row.connect("notify::selected", self._on_restore_changed)
        group.add(self._restore_row)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(4)

        # Buttons Row: Toggle & Once
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._hud_btn = Gtk.Button(label=f"📊  开启即时系统 HUD (每{int(initial_inv)}秒更新)")
        self._hud_btn.add_css_class("pill")
        self._hud_btn.set_hexpand(True)
        self._hud_btn.connect("clicked", self._on_toggle_hud)
        btn_box.append(self._hud_btn)

        self._hud_once_btn = Gtk.Button(label="⚡  立即单次刷新")
        self._hud_once_btn.add_css_class("pill")
        self._hud_once_btn.connect("clicked", self._on_hud_once)
        btn_box.append(self._hud_once_btn)

        self._hud_restore_btn = Gtk.Button(label="🔄  恢复动画")
        self._hud_restore_btn.add_css_class("pill")
        self._hud_restore_btn.connect("clicked", self._on_restore_anim)
        btn_box.append(self._hud_restore_btn)
        box.append(btn_box)

        # HUD status note
        self._hud_note = Gtk.Label(label="直接写 RAM 缓存，零 Flash 磨损，打字 100% 流畅")
        self._hud_note.add_css_class("caption")
        self._hud_note.add_css_class("dim-label")
        box.append(self._hud_note)

        # Hardware technical note banner
        self._hw_note = Gtk.Label(
            label="💡 说明：键盘内置 48MHz 单核 MCU，每次向屏幕传输 28KB 画面时占用全部 SPI 总线带宽，会短暂停顿软件 PWM 调光约 0.5 秒。推荐将刷新间隔设为 2 至 5 分钟，或使用「⚡ 立即单次刷新」。"
        )
        self._hw_note.set_wrap(True)
        self._hw_note.set_xalign(0.0)
        self._hw_note.add_css_class("caption")
        self._hw_note.set_margin_top(4)
        box.append(self._hw_note)

        group.add(box)
        return group

    def _build_lcd_card(self):
        group = Adw.PreferencesGroup()
        group.set_title("📺  LCD 图片 / GIF 上传")
        group.set_description("自动缩放为 160 × 80 像素 RGB565，支持多帧 GIF 动画")

        # File chooser row
        file_row = Adw.ActionRow()
        file_row.set_title("选择图片")
        self._file_label = Gtk.Label(label="未选择文件")
        self._file_label.add_css_class("dim-label")
        self._file_label.add_css_class("caption")
        self._file_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        file_row.add_suffix(self._file_label)
        choose_btn = Gtk.Button(label="📂  浏览…")
        choose_btn.set_valign(Gtk.Align.CENTER)
        choose_btn.connect("clicked", self._on_choose_file)
        file_row.add_suffix(choose_btn)
        group.add(file_row)

        # Progress bar row
        prog_row = Adw.ActionRow()
        prog_row.set_title("上传进度")
        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_hexpand(True)
        self._progress_bar.set_valign(Gtk.Align.CENTER)
        self._progress_bar.set_fraction(0)
        prog_row.add_suffix(self._progress_bar)
        group.add(prog_row)

        upload_btn = Gtk.Button(label="🚀  上传到键盘屏幕")
        upload_btn.add_css_class("pill")
        upload_btn.set_margin_top(4)
        upload_btn.connect("clicked", self._on_upload_lcd)
        group.add(upload_btn)

        self._selected_file = None
        self._lcd_group = group
        return group

    # ------------------------------------------------------------------ #
    #  Status                                                               #
    # ------------------------------------------------------------------ #

    def _refresh_status(self):
        usb = find_lt104_usb()
        lcd = find_lt104_lcd_hidraw()
        if usb:
            self._status_label.set_text(f"⌨️  LT-104 已连接  |  LCD: {lcd or '未找到'}")
        else:
            self._status_label.set_text("❌  未检测到 LT-104 键盘")

        self._check_hud_status()
        return True  # repeat via GLib.timeout_add_seconds

    def _check_hud_status(self):
        try:
            running = False
            pid_file = "/tmp/lt104_indicator.pid"
            if os.path.exists(pid_file):
                try:
                    with open(pid_file) as f:
                        pid = int(f.read().strip())
                    os.kill(pid, 0)
                    cmd_path = f"/proc/{pid}/cmdline"
                    if os.path.exists(cmd_path):
                        with open(cmd_path, "rb") as f:
                            cmd = f.read().replace(b"\x00", b" ")
                        if b"lt104_indicator.py" in cmd:
                            running = True
                except (OSError, ValueError):
                    pass

            self._hud_running = running
            idx = self._interval_row.get_selected()
            sec = self._interval_intervals[idx] if idx < len(self._interval_intervals) else 120
            if running:
                self._hud_btn.set_label(f"⏹️  停止系统 HUD (运行中，每{sec}秒更新)")
                self._hud_btn.remove_css_class("suggested-action")
                self._hud_btn.add_css_class("destructive-action")
            else:
                self._hud_btn.set_label(f"📊  开启即时系统 HUD (每{sec}秒更新)")
                self._hud_btn.remove_css_class("destructive-action")
                self._hud_btn.add_css_class("suggested-action")

            if hasattr(self, '_lcd_group'):
                self._lcd_group.set_visible(not running)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  Callbacks                                                            #
    # ------------------------------------------------------------------ #

    def _on_interval_changed(self, row, param):
        idx = self._interval_row.get_selected()
        sec = self._interval_intervals[idx] if idx < len(self._interval_intervals) else 20
        save_config({"hud_interval": sec})
        self._check_hud_status()

    def _on_restore_changed(self, row, param):
        idx = self._restore_row.get_selected()
        preset = self._restore_presets[idx] if idx < len(self._restore_presets) else "lt104_sample.gif"
        save_config({"hud_restore_preset": preset})

    def _on_mode_changed(self, row, param):
        mode_idx = self._mode_row.get_selected()
        if mode_idx < len(LIGHT_MODES):
            mode_id = LIGHT_MODES[mode_idx]["id"]
            if hasattr(self, '_preview_mode_badge'):
                self._preview_mode_badge.set_text(LIGHT_MODES[mode_idx]["name"])
            if hasattr(self, '_preview_area') and self._preview_area:
                self._preview_area.queue_draw()
            is_single = mode_id not in MULTI_COLOR_MODES
            if hasattr(self, '_color_row'):
                self._color_row.set_visible(is_single)
            if hasattr(self, '_presets_row'):
                self._presets_row.set_visible(is_single)
            is_off = (mode_id == 20)
            is_static = (mode_id == 1)
            if hasattr(self, '_bright_row'):
                self._bright_row.set_visible(not is_off)
            if hasattr(self, '_speed_row'):
                self._speed_row.set_visible(not is_off and not is_static)

            current_bright = int(self._brightness_scale.get_value())
            if is_off:
                # Going to Backlight Off: remember previous brightness
                if self._previous_mode_id != 20 and current_bright > 0:
                    self._remembered_brightness = current_bright
                    save_config({"remembered_brightness": self._remembered_brightness})
                self._brightness_scale.set_value(0)
            elif self._previous_mode_id == 20:
                # Coming from Backlight Off to other mode: restore remembered brightness
                restore_val = self._remembered_brightness if self._remembered_brightness > 0 else 4
                self._brightness_scale.set_value(restore_val)

            self._previous_mode_id = mode_id
            if hasattr(self, '_auto_apply_row') and self._auto_apply_row.get_active():
                self._apply_light_silently()

    def _on_auto_apply_toggled(self, row, param):
        active = row.get_active()
        save_config({"light_auto_apply": active})
        if hasattr(self, '_apply_btn'):
            self._apply_btn.set_visible(not active)
        if active:
            self._apply_light_silently()

    def _on_color_changed(self, btn, param):
        if hasattr(self, '_preview_area') and self._preview_area:
            self._preview_area.queue_draw()
        if hasattr(self, '_auto_apply_row') and self._auto_apply_row.get_active():
            self._apply_light_silently()

    def _on_brightness_changed(self, scale):
        mode_idx = self._mode_row.get_selected()
        mode_id = LIGHT_MODES[mode_idx]["id"] if mode_idx < len(LIGHT_MODES) else 1
        val = int(scale.get_value())
        if mode_id != 20 and val > 0:
            self._remembered_brightness = val
            save_config({"remembered_brightness": val})
        if hasattr(self, '_preview_area') and self._preview_area:
            self._preview_area.queue_draw()
        if hasattr(self, '_auto_apply_row') and self._auto_apply_row.get_active():
            self._apply_light_silently()

    def _on_speed_changed(self, scale):
        if hasattr(self, '_preview_area') and self._preview_area:
            self._preview_area.queue_draw()
        if hasattr(self, '_auto_apply_row') and self._auto_apply_row.get_active():
            self._apply_light_silently()

    def _on_preset_clicked(self, btn, hex_c):
        rgba = Gdk.RGBA()
        rgba.parse(hex_c)
        self._color_btn.set_rgba(rgba)
        if hasattr(self, '_preview_area') and self._preview_area:
            self._preview_area.queue_draw()
        mode_idx = self._mode_row.get_selected()
        if mode_idx < len(LIGHT_MODES) and LIGHT_MODES[mode_idx]["id"] in MULTI_COLOR_MODES:
            self._mode_row.set_selected(0)
        elif hasattr(self, '_auto_apply_row') and self._auto_apply_row.get_active():
            self._apply_light_silently()

    # ------------------------------------------------------------------ #
    #  Keyboard Visualizer Preview Engine (Cairo 30fps)                 #
    # ------------------------------------------------------------------ #

    def _load_lcd_surface(self):
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            lcd_path = os.path.join(base_dir, "static", "current_lcd.gif")
            if not os.path.exists(lcd_path):
                lcd_path = os.path.join(base_dir, "lt104_sample.gif")
            if os.path.exists(lcd_path):
                mtime = os.path.getmtime(lcd_path)
                if mtime != self._last_lcd_mtime or self._lcd_surface is None:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(lcd_path, 62, 39, False)
                    # Convert pixbuf to Cairo ImageSurface
                    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 62, 39)
                    cr = cairo.Context(surf)
                    Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
                    cr.paint()
                    self._lcd_surface = surf
                    self._last_lcd_mtime = mtime
        except Exception:
            pass

    def _tick_preview(self):
        if hasattr(self, '_preview_area') and self._preview_area and self.get_visible():
            self._preview_area.queue_draw()
        return True

    def _find_key_at(self, cx, cy):
        for i, k in enumerate(KB_KEYS):
            _, kx, ky, kw, kh = k
            if kx <= cx <= kx + kw and ky <= cy <= ky + kh:
                return i
        return -1

    def _on_preview_clicked(self, gesture, n_press, x, y):
        w = self._preview_area.get_width()
        h = self._preview_area.get_height()
        scale_x = w / 954.0
        scale_y = h / 297.0
        scale = min(scale_x, scale_y)
        offset_x = (w - 954.0 * scale) / 2.0
        offset_y = (h - 297.0 * scale) / 2.0

        canvas_x = (x - offset_x) / scale
        canvas_y = (y - offset_y) / scale

        idx = self._find_key_at(canvas_x, canvas_y)
        now = time.time()
        rgba = self._color_btn.get_rgba()
        base_rgb = (rgba.red, rgba.green, rgba.blue)

        if idx >= 0:
            self._key_flashes[idx] = 1.0
            k = KB_KEYS[idx]
            mode_idx = self._mode_row.get_selected()
            mode_id = LIGHT_MODES[mode_idx]["id"] if mode_idx < len(LIGHT_MODES) else 1
            self._active_ripples.append({
                "x": k[1] + k[3] / 2.0,
                "y": k[2] + k[4] / 2.0,
                "row": get_key_row(k[2]),
                "t": now,
                "color": base_rgb,
                "mode": mode_id
            })
        else:
            mode_idx = self._mode_row.get_selected()
            mode_id = LIGHT_MODES[mode_idx]["id"] if mode_idx < len(LIGHT_MODES) else 1
            self._active_ripples.append({
                "x": canvas_x,
                "y": canvas_y,
                "row": get_key_row(canvas_y),
                "t": now,
                "color": base_rgb,
                "mode": mode_id
            })
        self._preview_area.queue_draw()

    def _on_preview_motion(self, controller, x, y):
        w = self._preview_area.get_width()
        h = self._preview_area.get_height()
        scale_x = w / 954.0
        scale_y = h / 297.0
        scale = min(scale_x, scale_y)
        offset_x = (w - 954.0 * scale) / 2.0
        offset_y = (h - 297.0 * scale) / 2.0

        canvas_x = (x - offset_x) / scale
        canvas_y = (y - offset_y) / scale

        old_idx = self._hovered_key_idx
        self._hovered_key_idx = self._find_key_at(canvas_x, canvas_y)
        if old_idx != self._hovered_key_idx:
            self._preview_area.queue_draw()

    def _on_preview_leave(self, controller):
        self._hovered_key_idx = -1
        self._preview_area.queue_draw()

    def _calc_key_color(self, mode, k, idx, t, base_rgb, speed_mult, bright_mult):
        if mode == 20 or bright_mult <= 0:
            return (0.0, 0.0, 0.0)

        cx = k[1] + k[3] / 2.0
        cy = k[2] + k[4] / 2.0

        if mode == 1:
            return base_rgb

        elif mode == 2:  # 单点亮 (Single Light)
            f = max(0.04, self._key_flashes[idx])
            return (base_rgb[0] * f, base_rgb[1] * f, base_rgb[2] * f)

        elif mode == 3:  # 单熄灭 (Single Off)
            f = max(0.05, 1.0 - self._key_flashes[idx])
            return (base_rgb[0] * f, base_rgb[1] * f, base_rgb[2] * f)

        elif mode == 4:  # 繁星点点 (Stars)
            # All keys lit with static color, randomly turn off 2-3 keys
            if idx in getattr(self, '_dim_star_keys', []):
                return (0.0, 0.0, 0.0)
            return base_rgb

        elif mode == 5:  # 漫天飞雪 (Snow)
            row = get_key_row(k[2])
            phase = (t * speed_mult * 3.5 - row * 0.9 + (idx % 5) * 0.4) % 6.283
            val = max(0.0, math.sin(phase)) ** 3
            return (base_rgb[0] * val, base_rgb[1] * val, base_rgb[2] * val)

        elif mode == 6:  # 百花争艳 (Blossom)
            cluster = math.sin(cx * 0.015 + t * speed_mult * 1.5) + math.cos(cy * 0.03 + t * speed_mult * 1.2)
            hue = (cluster * 90.0 + t * speed_mult * 40.0) % 360.0
            return hsl_to_rgb(hue, 1.0, 0.5)

        elif mode == 7:  # 动态呼吸 (Breathing)
            factor = 0.12 + 0.88 * (0.5 + 0.5 * math.sin(t * speed_mult * 2.5))
            return (base_rgb[0] * factor, base_rgb[1] * factor, base_rgb[2] * factor)

        elif mode == 8:  # 光谱循环 (Spectrum Cycle)
            hue = (t * speed_mult * 50.0) % 360.0
            return hsl_to_rgb(hue, 1.0, 0.5)

        elif mode == 9:  # 彩泉涌动 (Rainbow Wave)
            hue = (cx * 0.5 - t * speed_mult * 90.0) % 360.0
            return hsl_to_rgb(hue, 1.0, 0.5)

        elif mode == 10:  # 多彩纵横 (Cross Pattern)
            col_beam = (math.sin(t * speed_mult * 2.5) * 0.5 + 0.5) * 920.0 + 20.0
            row_beam = (math.cos(t * speed_mult * 2.2) * 0.5 + 0.5) * 250.0 + 20.0
            dist_x = abs(cx - col_beam)
            dist_y = abs(cy - row_beam)
            val_x = math.exp(-dist_x * dist_x / 2200.0)
            val_y = math.exp(-dist_y * dist_y / 1600.0)
            val = max(0.08, max(val_x, val_y))
            hue = (cx * 0.3 + cy * 0.6 + t * speed_mult * 60.0) % 360.0
            c = hsl_to_rgb(hue, 1.0, 0.5)
            return (c[0] * val, c[1] * val, c[2] * val)

        elif mode == 11:  # 随波逐流 (River Stream)
            hue = ((cx + cy * 1.6) * 0.38 - t * speed_mult * 80.0) % 360.0
            return hsl_to_rgb(hue, 1.0, 0.5)

        elif mode == 12:  # 峰回路转 (Rotary Wave)
            angle = math.atan2(cy - 145.0, cx - 475.0)
            hue = (angle * (180.0 / math.pi) + t * speed_mult * 90.0) % 360.0
            return hsl_to_rgb(hue, 1.0, 0.5)

        elif mode in (13, 14, 15):  # Ripple modes: driven by active ripples
            return (0.0, 0.0, 0.0)

        elif mode == 16:  # 川流不息 (Infinite Stream)
            row_dur = 0.55 / speed_mult
            total_cycle = 6.0 * row_dur
            cycle_time = t % total_cycle
            active_row = int(cycle_time / row_dur)
            row_prog = (cycle_time % row_dur) / row_dur
            swipe_x = row_prog * 960.0
            k_row = get_key_row(k[2])
            if k_row == active_row:
                dist_x = abs(cx - swipe_x)
                val = max(0.04, math.exp(-dist_x * dist_x / 2500.0))
                hue = (swipe_x * 0.4 + active_row * 50.0 + t * 90.0) % 360.0
                c = hsl_to_rgb(hue, 1.0, 0.5)
                return (c[0] * val, c[1] * val, c[2] * val)
            return (0.0, 0.0, 0.0)

        elif mode == 17:  # 重峦叠嶂 (Rolling Hills)
            wave = math.sin(cx * 0.02 + t * speed_mult * 2.5) * math.cos(cy * 0.04 + t * speed_mult * 2.0)
            val = 0.3 + 0.7 * (wave * 0.5 + 0.5)
            hue = (cx * 0.3 + t * speed_mult * 40.0) % 360.0
            c = hsl_to_rgb(hue, 1.0, 0.5)
            return (c[0] * val, c[1] * val, c[2] * val)

        elif mode == 18:  # 斜风细雨 (Gentle Rain)
            slant = cx * 0.8 + cy * 1.4
            drop = math.sin(slant * 0.06 - t * speed_mult * 5.0 + (idx % 7) * 1.1)
            val = max(0.1, max(0.0, drop) ** 4)
            hue = (slant * 0.2 + 180.0) % 360.0
            c = hsl_to_rgb(hue, 0.85, 0.5)
            return (c[0] * val, c[1] * val, c[2] * val)

        elif mode == 19:  # 来回穿梭 (Shuttle)
            shuttle_cycle = 2.2 / speed_mult
            p = (t % shuttle_cycle) / shuttle_cycle
            pos = (p * 2.0) if (p < 0.5) else (2.0 - p * 2.0)
            beam_x = 25.0 + pos * 900.0
            dist_x = abs(cx - beam_x)
            val = max(0.04, math.exp(-dist_x * dist_x / 1600.0))
            hue = (beam_x * 0.4 + t * speed_mult * 90.0) % 360.0
            c = hsl_to_rgb(hue, 1.0, 0.5)
            return (c[0] * val, c[1] * val, c[2] * val)

        elif mode == 21:  # 万众一心 (Solid Center)
            hue = (cx * 0.38 + cy * 0.25) % 360.0
            return hsl_to_rgb(hue, 1.0, 0.5)

        elif mode == 22:  # 流光溢彩 (Neon Glow)
            plasma = (math.sin(cx * 0.015 + t * speed_mult * 1.5) +
                      math.sin(cy * 0.035 + t * speed_mult * 1.2) +
                      math.sin((cx + cy) * 0.012 + t * speed_mult * 1.8))
            hue = (plasma * 60.0 + t * speed_mult * 40.0 + 280.0) % 360.0
            return hsl_to_rgb(hue, 1.0, 0.5)

        return base_rgb

    def _on_draw_keyboard_preview(self, area, cr, width, height):
        now = time.time()
        t = now

        scale_x = width / 954.0
        scale_y = height / 297.0
        scale = min(scale_x, scale_y)
        offset_x = (width - 954.0 * scale) / 2.0
        offset_y = (height - 297.0 * scale) / 2.0

        mode_idx = self._mode_row.get_selected()
        mode_id = LIGHT_MODES[mode_idx]["id"] if mode_idx < len(LIGHT_MODES) else 1

        rgba = self._color_btn.get_rgba()
        base_rgb = (rgba.red, rgba.green, rgba.blue)

        bright_val = int(self._brightness_scale.get_value())
        bright_mult = 0.0 if mode_id == 20 else [0.25, 0.45, 0.65, 0.85, 1.0][min(4, max(0, bright_val))]

        speed_val = int(self._speed_scale.get_value())
        speed_mult = [0.4, 0.7, 1.0, 1.6, 2.4][min(4, max(0, speed_val))]

        # Mode 4 Stars: randomly turn off 2 to 3 keys for 0.5s when animation speed is 1
        if mode_id == 4 and now >= getattr(self, '_next_star_change_time', 0.0):
            count = random.randint(2, 3)
            self._dim_star_keys = [random.randint(0, len(KB_KEYS) - 1) for _ in range(count)]
            self._next_star_change_time = now + (0.5 / speed_mult)

        # Decay key flashes
        for i in range(len(self._key_flashes)):
            if self._key_flashes[i] > 0.001:
                self._key_flashes[i] *= 0.94

        # Simulated auto-tap for Single Light / Single Off modes
        if mode_id in (2, 3) and (now - self._last_auto_tap_time > 1.3):
            rand_idx = random.randint(0, len(KB_KEYS) - 1)
            self._key_flashes[rand_idx] = 1.0
            self._last_auto_tap_time = now

        # Simulated ripple for Ripple Trigger / Dual Ripple / Ripple Spread modes
        if mode_id in (13, 14, 15) and (now - self._last_auto_ripple_time > 2.4):
            rand_key = random.choice(KB_KEYS)
            self._active_ripples.append({
                "x": rand_key[1] + rand_key[3] / 2.0,
                "y": rand_key[2] + rand_key[4] / 2.0,
                "row": get_key_row(rand_key[2]),
                "t": now,
                "color": base_rgb,
                "mode": mode_id
            })
            self._last_auto_ripple_time = now

        # Filter active ripples
        self._active_ripples = [r for r in self._active_ripples if (now - r["t"]) < 1.1]

        cr.save()
        cr.translate(offset_x, offset_y)
        cr.scale(scale, scale)

        # 1. Keyboard Chassis Base
        if self._skin_dark:
            cr.set_source_surface(self._skin_dark, 0, 0)
            cr.paint()
        else:
            cr.set_source_rgb(0.067, 0.075, 0.122)
            cr.rectangle(0, 0, 954, 297)
            cr.fill()

        # 2. Lit Keycaps Overlay
        if self._skin_lit and bright_mult > 0:
            cr.save()
            # Clip to keys areas
            cr.rectangle(15, 12, 755, 50)
            cr.rectangle(15, 62, 930, 215)
            cr.clip()

            tinted_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 954, 297)
            tinted_cr = cairo.Context(tinted_surf)

            if mode_id == 1 and not self._active_ripples:
                # STATIC MODE: All keys uniform exact brightness
                tinted_cr.set_source_surface(self._skin_lit, 0, 0)
                tinted_cr.paint()
                tinted_cr.set_operator(cairo.OPERATOR_MULTIPLY)
                tinted_cr.set_source_rgb(base_rgb[0] * bright_mult, base_rgb[1] * bright_mult, base_rgb[2] * bright_mult)
                tinted_cr.paint()
            else:
                # Dynamic light map per key
                color_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 954, 297)
                color_cr = cairo.Context(color_surf)

                for i, k in enumerate(KB_KEYS):
                    _, kx, ky, kw, kh = k
                    cx = kx + kw / 2.0
                    cy = ky + kh / 2.0
                    r, g, b = self._calc_key_color(mode_id, k, i, t, base_rgb, speed_mult, bright_mult)

                    for rip in self._active_ripples:
                        age = (now - rip["t"])
                        rip_mode = rip.get("mode", mode_id)

                        if rip_mode == 13:
                            # Ripple Trigger: spreads left and right on same row ONLY
                            k_row = get_key_row(k[2])
                            if k_row == rip.get("row", -1):
                                dx = abs(cx - rip["x"])
                                wave_front = age * 540.0
                                diff = abs(dx - wave_front)
                                if diff < 36.0:
                                    amp = max(0.0, (1.0 - age / 0.85) * (1.0 - diff / 36.0))
                                    r = min(1.0, r + rip["color"][0] * amp)
                                    g = min(1.0, g + rip["color"][1] * amp)
                                    b = min(1.0, b + rip["color"][2] * amp)
                        elif rip_mode == 14:
                            # Dual Ripple: colorful keys separate towards left and right
                            dx = abs(cx - rip["x"])
                            wave_front = age * 500.0
                            diff = abs(dx - wave_front)
                            if diff < 42.0:
                                amp = max(0.0, (1.0 - age / 0.95) * (1.0 - diff / 42.0))
                                hue = (dx * 0.9 + age * 180.0 + k[2] * 0.3) % 360.0
                                c = hsl_to_rgb(hue, 1.0, 0.5)
                                r = min(1.0, r + c[0] * amp)
                                g = min(1.0, g + c[1] * amp)
                                b = min(1.0, b + c[2] * amp)
                        elif rip_mode == 15:
                            # Ripple Spread: concentric rings width ~3 keys
                            dist = math.hypot(cx - rip["x"], cy - rip["y"])
                            wave_front = age * 420.0
                            diff = abs(dist - wave_front)
                            if diff < 48.0:
                                amp = max(0.0, (1.0 - age / 1.1) * (1.0 - diff / 48.0))
                                hue = (dist * 1.2 - age * 140.0 + math.atan2(cy - rip["y"], cx - rip["x"]) * 180.0 / math.pi) % 360.0
                                c = hsl_to_rgb(hue, 1.0, 0.5)
                                r = min(1.0, r + c[0] * amp)
                                g = min(1.0, g + c[1] * amp)
                                b = min(1.0, b + c[2] * amp)
                        else:
                            rip_dist = math.hypot(cx - rip["x"], cy - rip["y"])
                            wave_front = age * 480.0
                            diff = abs(rip_dist - wave_front)
                            if diff < 45.0:
                                amp = max(0.0, (1.0 - age / 0.9) * (1.0 - diff / 45.0))
                                r = min(1.0, r + rip["color"][0] * amp)
                                g = min(1.0, g + rip["color"][1] * amp)
                                b = min(1.0, b + rip["color"][2] * amp)

                    r = max(0.0, min(1.0, r * bright_mult))
                    g = max(0.0, min(1.0, g * bright_mult))
                    b = max(0.0, min(1.0, b * bright_mult))

                    if r > 0.005 or g > 0.005 or b > 0.005:
                        color_cr.set_source_rgb(r, g, b)
                        color_cr.rectangle(kx - 3, ky - 3, kw + 6, kh + 6)
                        color_cr.fill()

                tinted_cr.set_source_surface(self._skin_lit, 0, 0)
                tinted_cr.paint()
                tinted_cr.set_operator(cairo.OPERATOR_MULTIPLY)
                tinted_cr.set_source_surface(color_surf, 0, 0)
                tinted_cr.paint()

            cr.set_source_surface(tinted_surf, 0, 0)
            cr.paint()
            cr.restore()

        # 3. Hover Ring Highlight
        if 0 <= self._hovered_key_idx < len(KB_KEYS):
            _, hx, hy, hw, hh = KB_KEYS[self._hovered_key_idx]
            cr.save()
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.65)
            cr.set_line_width(1.5)
            cr.rectangle(hx, hy, hw, hh)
            cr.stroke()
            cr.restore()

        # 4. Reactive LCD Screen (X=808, Y=18, W=62, H=39)
        cr.save()
        cr.rectangle(808, 18, 62, 39)
        cr.clip()

        if getattr(self, '_hud_running', False):
            # Real-time HUD Mode: Live hardware telemetry & digital clock
            cr.set_source_rgb(0.012, 0.031, 0.075)
            cr.paint()

            cr.set_source_rgb(0.22, 0.74, 0.97)
            cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(8.0)
            time_str = time.strftime("%H:%M:%S")
            cr.move_to(814, 27)
            cr.show_text(time_str)

            cr.set_source_rgb(0.12, 0.16, 0.23)
            cr.set_line_width(1.0)
            cr.move_to(810, 29)
            cr.line_to(868, 29)
            cr.stroke()

            # CPU
            cr.set_source_rgb(0.58, 0.64, 0.72)
            cr.set_font_size(7.0)
            cr.move_to(811, 37)
            cr.show_text("C")
            cr.set_source_rgb(0.06, 0.72, 0.5)
            cr.rectangle(820, 32, 12, 5)
            cr.fill()
            cr.move_to(846, 37)
            cr.show_text("18%")

            # RAM
            cr.set_source_rgb(0.58, 0.64, 0.72)
            cr.move_to(811, 46)
            cr.show_text("R")
            cr.set_source_rgb(0.02, 0.71, 0.83)
            cr.rectangle(820, 41, 18, 5)
            cr.fill()
            cr.move_to(846, 46)
            cr.show_text("51%")

            # Equalizer
            for bi in range(7):
                bx = 811 + bi * 8
                cr.set_source_rgb(0.06, 0.72, 0.5 if bi % 2 == 0 else 0.83)
                bar_h = 2 + abs(math.sin(t * 3.5 + bi * 0.9)) * 5
                cr.rectangle(bx, 56 - bar_h, 6, bar_h)
                cr.fill()
        else:
            # GIF Animation Mode: Render active custom/preset LCD GIF
            self._load_lcd_surface()
            if self._lcd_surface:
                cr.set_source_surface(self._lcd_surface, 808, 18)
                cr.paint()
            else:
                cr.set_source_rgb(0.012, 0.031, 0.075)
                cr.paint()
                cr.set_source_rgb(0.22, 0.74, 0.97)
                cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
                cr.set_font_size(7.5)
                cr.move_to(818, 40)
                cr.show_text("LT-104")

        cr.restore()
        cr.restore()

    def _apply_light_silently(self):
        mode_idx  = self._mode_row.get_selected()
        mode_id   = LIGHT_MODES[mode_idx]["id"]
        rgba      = self._color_btn.get_rgba()
        r, g, b   = int(rgba.red * 255), int(rgba.green * 255), int(rgba.blue * 255)
        brightness = int(self._brightness_scale.get_value())
        speed      = int(self._speed_scale.get_value())

        if mode_id == 20:
            brightness = 0

        def do_light():
            try:
                ctl = LT104Controller()
                ctl.set_light(mode=mode_id, r=r, g=g, b=b, brightness=brightness, speed=speed)
                ctl.close()
                save_config({
                    "mode": mode_id,
                    "color": f"#{r:02x}{g:02x}{b:02x}",
                    "r": r, "g": g, "b": b,
                    "brightness": brightness,
                    "speed": speed
                })
            except Exception:
                pass

        run_in_thread(do_light)

    def _on_apply_light(self, btn):
        btn.set_sensitive(False)
        btn.set_label("⏳  应用中…")

        mode_idx  = self._mode_row.get_selected()
        mode_id   = LIGHT_MODES[mode_idx]["id"]
        rgba      = self._color_btn.get_rgba()
        r, g, b   = int(rgba.red * 255), int(rgba.green * 255), int(rgba.blue * 255)
        brightness = int(self._brightness_scale.get_value())
        speed      = int(self._speed_scale.get_value())

        if mode_id == 20:
            brightness = 0
            self._brightness_scale.set_value(0)

        def do_light():
            ctl = LT104Controller()
            ctl.set_light(mode=mode_id, r=r, g=g, b=b, brightness=brightness, speed=speed)
            ctl.close()
            save_config({
                "mode": mode_id,
                "color": f"#{r:02x}{g:02x}{b:02x}",
                "r": r, "g": g, "b": b,
                "brightness": brightness,
                "speed": speed
            })

        def done(_):
            btn.set_sensitive(True)
            btn.set_label("✨  即时应用并保存灯效")
            self._toast("✅  键盘背光已更新并写入硬体！")

        def err(msg):
            btn.set_sensitive(True)
            btn.set_label("✨  即时应用并保存灯效")
            self._error_dialog("灯效应用失败", msg)

        run_in_thread(do_light, on_done=done, on_error=err)

    def _on_sync_clock(self, btn):
        btn.set_sensitive(False)
        btn.set_label("⏳  同步中…")

        def do_clock():
            ctl = LT104Controller()
            ctl.sync_clock()
            ctl.close()

        def done(_):
            btn.set_sensitive(True)
            btn.set_label("🕒  同步电脑时钟到键盘小屏幕")
            self._toast("🕒  键盘小屏幕时钟已精准同步！")

        def err(msg):
            btn.set_sensitive(True)
            btn.set_label("🕒  同步电脑时钟到键盘小屏幕")
            self._error_dialog("时钟同步失败", msg)

        run_in_thread(do_clock, on_done=done, on_error=err)

    def _on_schedule_toggled(self, row, param):
        import subprocess
        active = row.get_active()
        cmd = "clock-schedule-enable" if active else "clock-schedule-disable"
        subprocess.run([sys.executable, CLI_PATH, cmd])
        if active:
            self._toast("⏱️  已开启定时时钟同步 (每 12 小时自动校准)")
        else:
            self._toast("⏹️  已停用定时时钟同步")

    def _on_toggle_hud(self, btn):
        btn.set_sensitive(False)
        import subprocess

        idx = self._interval_row.get_selected()
        sec = self._interval_intervals[idx] if idx < len(self._interval_intervals) else 20

        def do_toggle():
            res = subprocess.run([sys.executable, CLI_PATH, "hud-status"],
                                 capture_output=True, text=True)
            if "RUNNING" in res.stdout:
                subprocess.run([sys.executable, CLI_PATH, "hud-stop"])
                return False, sec
            else:
                subprocess.run([sys.executable, CLI_PATH, "hud-start", "--interval", str(sec)])
                return True, sec

        def done(result):
            is_running, interval_val = result
            btn.set_sensitive(True)
            self._check_hud_status()
            if is_running:
                self._toast(f"🚀  系统 HUD 已启动 (每{interval_val}秒更新)！")
            else:
                self._toast("⏹️  系统 HUD 已停止。")

        def err(msg):
            btn.set_sensitive(True)
            self._check_hud_status()
            self._error_dialog("HUD 切换失败", msg)

        run_in_thread(do_toggle, on_done=done, on_error=err)

    def _on_hud_once(self, btn):
        btn.set_sensitive(False)
        import subprocess

        def do_once():
            res = subprocess.run([sys.executable, CLI_PATH, "hud-once"],
                                 capture_output=True, text=True)
            return res.returncode == 0

        def done(ok):
            btn.set_sensitive(True)
            if ok:
                self._toast("⚡  系统 HUD 遥测已单次推送至屏幕！")
            else:
                self._toast("❌  推送失败，请检查键盘连接。")

        def err(msg):
            btn.set_sensitive(True)
            self._error_dialog("单次推送失败", msg)

        run_in_thread(do_once, on_done=done, on_error=err)

    def _on_restore_anim(self, btn):
        btn.set_sensitive(False)
        import subprocess

        idx = self._restore_row.get_selected()
        preset = self._restore_presets[idx] if idx < len(self._restore_presets) else "lt104_sample.gif"

        def do_restore():
            cmd = [sys.executable, CLI_PATH, "hud-restore"]
            if preset:
                cmd.extend(["--preset", preset])
            res = subprocess.run(cmd, capture_output=True, text=True)
            return res.returncode == 0

        def done(ok):
            btn.set_sensitive(True)
            if ok:
                self._toast(f"🔄  预设动画 ({preset}) 已成功恢复至屏幕！")
            else:
                self._toast("❌  恢复动画失败，请检查键盘连接。")

        def err(msg):
            btn.set_sensitive(True)
            self._error_dialog("恢复动画失败", msg)

        run_in_thread(do_restore, on_done=done, on_error=err)

    def _on_choose_file(self, btn):
        dialog = Gtk.FileDialog()
        dialog.set_title("选择图片或 GIF")
        filter_ = Gtk.FileFilter()
        filter_.set_name("图片文件 (GIF, PNG, JPEG, WebP)")
        for pat in ["*.gif", "*.GIF", "*.png", "*.PNG", "*.jpg", "*.jpeg", "*.webp"]:
            filter_.add_pattern(pat)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_)
        dialog.set_filters(filters)
        dialog.open(self, None, self._on_file_chosen)

    def _on_file_chosen(self, dialog, result):
        try:
            f = dialog.open_finish(result)
            self._selected_file = f.get_path()
            self._file_label.set_text(os.path.basename(self._selected_file))
        except Exception:
            pass

    def _on_upload_lcd(self, btn):
        if not self._selected_file:
            self._toast("❗  请先选择一张图片或 GIF！")
            return
        btn.set_sensitive(False)
        btn.set_label("⏳  上传中…")
        self._progress_bar.set_fraction(0)

        path = self._selected_file

        def progress(pct):
            GLib.idle_add(self._progress_bar.set_fraction, pct / 100.0)

        def do_upload():
            ctl = LT104Controller()
            frames = ctl.upload_lcd_image(path, progress_cb=progress)
            ctl.close()
            return frames

        def done(frames):
            btn.set_sensitive(True)
            btn.set_label("🚀  上传到键盘屏幕")
            self._progress_bar.set_fraction(1.0)
            self._toast(f"📺  上传成功！已加载 {frames} 帧动画。")

        def err(msg):
            btn.set_sensitive(True)
            btn.set_label("🚀  上传到键盘屏幕")
            self._error_dialog("LCD 图片上传失败", msg)

        run_in_thread(do_upload, on_done=done, on_error=err)

    # ------------------------------------------------------------------ #
    #  Utility                                                              #
    # ------------------------------------------------------------------ #

    def _toast(self, message):
        toast = Adw.Toast(title=message)
        toast.set_timeout(3)
        self._toast_overlay.add_toast(toast)

    def _error_dialog(self, title, body):
        dialog = Adw.AlertDialog(heading=title, body=body)
        dialog.add_response("ok", "确定")
        dialog.present(self)


# --------------------------------------------------------------------------- #
#  Application                                                                  #
# --------------------------------------------------------------------------- #

class LT104App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        win = LT104Window(application=app)
        win.present()


def main():
    app = LT104App()
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()

