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

KB_KEYS = [["esc",16,16,24,24],["F1",75,16,24,24],["F2",105,16,24,24],["F3",135,16,24,24],["F4",165,16,24,24],["F5",211,16,24,24],["F6",241,16,24,24],["F7",271,16,24,24],["F8",301,16,24,24],["F9",346,16,24,24],["F10",376,16,24,24],["F11",406,16,24,24],["F12",437,16,24,24],["Prt",474,16,24,24],["Scr",505,16,24,24],["Pau",536,16,24,24],["~",16,55,24,24],["1",46,55,24,24],["2",76,55,24,24],["3",106,55,24,24],["4",136,55,24,24],["5",166,55,24,24],["6",196,55,24,24],["7",226,55,24,24],["8",256,55,24,24],["9",286,55,24,24],["0",316,55,24,24],["-",346,55,24,24],["=",376,55,24,24],["\u232b",406,55,57,24],["Ins",474,55,24,24],["Hm",505,55,24,24],["PgU",536,55,24,24],["Num",573,55,24,24],["/",604,55,24,24],["*",635,55,24,24],["-",666,55,24,24],["Tab",16,85,38,24],["Q",60,85,24,24],["W",90,85,24,24],["E",120,85,24,24],["R",150,85,24,24],["T",181,85,24,24],["Y",211,85,24,24],["U",241,85,24,24],["I",271,85,24,24],["O",301,85,24,24],["P",331,85,24,24],["[",361,85,24,24],["]",391,85,24,24],["|",422,85,40,24],["Del",474,85,24,24],["End",505,85,24,24],["PgD",536,85,24,24],["7",573,85,24,24],["8",604,85,24,24],["9",635,85,24,24],["+",666,85,24,53],["Caps",16,115,45,24],["A",67,115,24,24],["S",97,115,24,24],["D",127,115,24,24],["F",158,115,24,24],["G",188,115,24,24],["H",218,115,24,24],["J",248,115,24,24],["K",278,115,24,24],["L",308,115,24,24],[";",338,115,24,24],["'",368,115,24,24],["Enter",398,115,65,24],["4",573,115,24,24],["5",604,115,24,24],["6",635,115,24,24],["Shift",16,145,61,24],["Z",83,145,24,24],["X",113,145,24,24],["C",144,145,24,24],["V",174,145,24,24],["B",204,145,24,24],["N",234,145,24,24],["M",264,145,24,24],["<",294,145,24,24],[">",324,145,24,24],["?",354,145,24,24],["Shift",384,145,79,24],["\u25b2",505,145,24,24],["1",573,145,24,24],["2",604,145,24,24],["3",635,145,24,24],["Enter",666,145,24,53],["Ctrl",16,175,32,24],["Win",53,175,32,24],["Alt",91,175,32,24],["",129,175,180,24],["Alt",316,175,32,24],["Fn",354,175,32,24],["App",392,175,32,24],["Ctrl",430,175,32,24],["\u25c4",474,175,24,24],["\u25bc",505,175,24,24],["\u25ba",536,175,24,24],["0",573,175,54,24],[".",635,175,24,24]]

def draw_round_rect(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()

def hsl_to_rgb(h, s, l):
    return colorsys.hls_to_rgb((h % 360.0) / 360.0, l, s)


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

        initial_mode_idx = max(0, min(len(LIGHT_MODES)-1, int(cfg.get("mode", 1)) - 1))

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
            if is_off:
                self._brightness_scale.set_value(0)
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
        scale_x = w / 706.0
        scale_y = h / 214.0
        scale = min(scale_x, scale_y)
        offset_x = (w - 706.0 * scale) / 2.0
        offset_y = (h - 214.0 * scale) / 2.0

        canvas_x = (x - offset_x) / scale
        canvas_y = (y - offset_y) / scale

        idx = self._find_key_at(canvas_x, canvas_y)
        now = time.time()
        rgba = self._color_btn.get_rgba()
        base_rgb = (rgba.red, rgba.green, rgba.blue)

        if idx >= 0:
            self._key_flashes[idx] = 1.0
            k = KB_KEYS[idx]
            self._active_ripples.append({
                "x": k[1] + k[3] / 2.0,
                "y": k[2] + k[4] / 2.0,
                "t": now,
                "color": base_rgb
            })
        else:
            self._active_ripples.append({
                "x": canvas_x,
                "y": canvas_y,
                "t": now,
                "color": base_rgb
            })
        self._preview_area.queue_draw()

    def _on_preview_motion(self, controller, x, y):
        w = self._preview_area.get_width()
        h = self._preview_area.get_height()
        scale_x = w / 706.0
        scale_y = h / 214.0
        scale = min(scale_x, scale_y)
        offset_x = (w - 706.0 * scale) / 2.0
        offset_y = (h - 214.0 * scale) / 2.0

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
            seed = (idx * 137.5) % 6.283
            val = max(0.0, (math.sin(t * speed_mult * 2.2 + seed) - 0.25) / 0.75)
            return (base_rgb[0] * val, base_rgb[1] * val, base_rgb[2] * val)

        elif mode == 5:  # 漫天飞雪 (Snow)
            row = round((k[2] - 16) / 30)
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
            x_wave = math.sin(cx * 0.03 - t * speed_mult * 3.0)
            y_wave = math.cos(cy * 0.05 + t * speed_mult * 2.5)
            val = max(0.15, (x_wave + y_wave) * 0.5)
            hue = (cx * 0.3 + cy * 0.5 + t * speed_mult * 60.0) % 360.0
            c = hsl_to_rgb(hue, 1.0, 0.5)
            return (c[0] * val, c[1] * val, c[2] * val)

        elif mode == 11:  # 随波逐流 (River Stream)
            hue = ((cx + cy * 1.6) * 0.38 - t * speed_mult * 80.0) % 360.0
            return hsl_to_rgb(hue, 1.0, 0.5)

        elif mode == 12:  # 峰回路转 (Rotary Wave)
            angle = math.atan2(cy - 105.0, cx - 350.0)
            hue = (angle * (180.0 / math.pi) + t * speed_mult * 90.0) % 360.0
            return hsl_to_rgb(hue, 1.0, 0.5)

        elif mode == 13:  # 一触即发 (Ripple Trigger)
            dist = math.hypot(cx - 350.0, cy - 105.0)
            ripple = math.sin(dist * 0.08 - t * speed_mult * 4.0)
            val = max(0.1, max(0.0, ripple) ** 2)
            return (base_rgb[0] * val, base_rgb[1] * val, base_rgb[2] * val)

        elif mode == 14:  # 一石二鸟 (Dual Ripple)
            d1 = math.hypot(cx - 180.0, cy - 105.0)
            d2 = math.hypot(cx - 520.0, cy - 105.0)
            r1 = math.sin(d1 * 0.07 - t * speed_mult * 4.0)
            r2 = math.sin(d2 * 0.07 - t * speed_mult * 4.0 + math.pi)
            hue = (d1 * 0.5 + d2 * 0.5 + t * speed_mult * 50.0) % 360.0
            val = max(0.1, (max(0.0, r1) + max(0.0, r2)) * 0.5)
            c = hsl_to_rgb(hue, 1.0, 0.5)
            return (c[0] * val, c[1] * val, c[2] * val)

        elif mode == 15:  # 涟漪扩散 (Ripple Spread)
            dist = math.hypot(cx - 350.0, cy - 105.0)
            hue = (dist * 1.2 - t * speed_mult * 90.0) % 360.0
            return hsl_to_rgb(hue, 1.0, 0.5)

        elif mode == 16:  # 川流不息 (Infinite Stream)
            row = round((k[2] - 16) / 30)
            dir_val = 1 if row % 2 == 0 else -1
            hue = (cx * 0.4 * dir_val - t * speed_mult * 120.0 + row * 40.0) % 360.0
            val = 0.5 + 0.5 * math.sin(cx * 0.04 * dir_val - t * speed_mult * 3.5)
            c = hsl_to_rgb(hue, 1.0, 0.5)
            return (c[0] * val, c[1] * val, c[2] * val)

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
            beam_x = (math.sin(t * speed_mult * 2.2) * 0.5 + 0.5) * 650.0 + 20.0
            dist = abs(cx - beam_x)
            val = max(0.08, math.exp(-dist * dist / 3000.0))
            hue = (t * speed_mult * 60.0) % 360.0
            c = hsl_to_rgb(hue, 1.0, 0.5)
            return (c[0] * val, c[1] * val, c[2] * val)

        elif mode == 21:  # 万众一心 (Solid Center)
            dist = math.hypot(cx - 350.0, cy - 105.0)
            pulse = math.sin(dist * 0.04 + t * speed_mult * 3.0)
            val = max(0.15, pulse * 0.5 + 0.5)
            hue = (dist * 0.5 + t * speed_mult * 30.0) % 360.0
            c = hsl_to_rgb(hue, 1.0, 0.5)
            return (c[0] * val, c[1] * val, c[2] * val)

        elif mode == 22:  # 流光溢彩 (Neon Glow)
            plasma = (math.sin(cx * 0.015 + t * speed_mult * 1.5) +
                      math.sin(cy * 0.035 + t * speed_mult * 1.2) +
                      math.sin((cx + cy) * 0.012 + t * speed_mult * 1.8))
            hue = (plasma * 60.0 + 280.0) % 360.0
            return hsl_to_rgb(hue, 1.0, 0.5)

        return base_rgb

    def _on_draw_keyboard_preview(self, area, cr, width, height):
        now = time.time()
        t = now

        scale_x = width / 706.0
        scale_y = height / 214.0
        scale = min(scale_x, scale_y)
        offset_x = (width - 706.0 * scale) / 2.0
        offset_y = (height - 214.0 * scale) / 2.0

        mode_idx = self._mode_row.get_selected()
        mode_id = LIGHT_MODES[mode_idx]["id"] if mode_idx < len(LIGHT_MODES) else 1

        rgba = self._color_btn.get_rgba()
        base_rgb = (rgba.red, rgba.green, rgba.blue)

        bright_val = int(self._brightness_scale.get_value())
        bright_mult = 0.0 if mode_id == 20 else [0.25, 0.45, 0.65, 0.85, 1.0][min(4, max(0, bright_val))]

        speed_val = int(self._speed_scale.get_value())
        speed_mult = [0.4, 0.7, 1.0, 1.6, 2.4][min(4, max(0, speed_val))]

        # Decay key flashes
        for i in range(len(self._key_flashes)):
            if self._key_flashes[i] > 0.001:
                self._key_flashes[i] *= 0.94

        # Simulated auto-tap for Single Light / Single Off modes
        if mode_id in (2, 3) and (now - self._last_auto_tap_time > 1.3):
            rand_idx = random.randint(0, len(KB_KEYS) - 1)
            self._key_flashes[rand_idx] = 1.0
            self._last_auto_tap_time = now

        # Simulated ripple for Ripple Trigger mode
        if mode_id == 13 and (now - self._last_auto_ripple_time > 2.6):
            self._active_ripples.append({
                "x": 350.0, "y": 105.0, "t": now, "color": base_rgb
            })
            self._last_auto_ripple_time = now

        # Filter active ripples
        self._active_ripples = [r for r in self._active_ripples if (now - r["t"]) < 0.9]

        cr.save()
        cr.translate(offset_x, offset_y)
        cr.scale(scale, scale)

        # 1. Keyboard Chassis
        draw_round_rect(cr, 4, 4, 698, 206, 12)
        chassis_pat = cairo.LinearGradient(4, 4, 4, 210)
        chassis_pat.add_color_stop_rgb(0, 0.075, 0.082, 0.14)
        chassis_pat.add_color_stop_rgb(1, 0.047, 0.055, 0.094)
        cr.set_source(chassis_pat)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.08)
        cr.set_line_width(1.5)
        cr.stroke()

        # 2. Plate Bezel
        draw_round_rect(cr, 10, 10, 686, 194, 8)
        cr.set_source_rgba(0, 0, 0, 0.6)
        cr.set_line_width(2)
        cr.stroke()

        # 3. Mini TFT Color LCD Screen (X=573, Y=14, W=68, H=28)
        draw_round_rect(cr, 573, 14, 68, 28, 4)
        cr.set_source_rgb(0.012, 0.031, 0.075)
        cr.fill_preserve()
        cr.set_source_rgb(0.15, 0.17, 0.24)
        cr.set_line_width(1)
        cr.stroke()

        cr.save()
        draw_round_rect(cr, 574, 15, 66, 26, 3)
        cr.clip()
        time_str = time.strftime("LT %H:%M:%S")
        cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(7.0)
        cr.set_source_rgb(0.22, 0.74, 0.97)
        cr.move_to(578, 25)
        cr.show_text(time_str)

        # Telemetry equalizer bars
        for bi in range(7):
            bar_h = 3 + abs(math.sin(t * 3.5 + bi * 0.9)) * 6.5
            bx = 578 + bi * 9
            if bi % 2 == 0:
                cr.set_source_rgb(0.06, 0.72, 0.5)
            else:
                cr.set_source_rgb(0.02, 0.71, 0.83)
            cr.rectangle(bx, 38 - bar_h, 6, bar_h)
            cr.fill()
        cr.restore()

        # 4. Rotary Knob (CX=668, CY=28, R=13)
        knob_cx, knob_cy, knob_r = 668.0, 28.0, 13.0
        knob_pat = cairo.RadialGradient(knob_cx - 3, knob_cy - 3, 2, knob_cx, knob_cy, knob_r)
        knob_pat.add_color_stop_rgb(0, 0.39, 0.44, 0.55)
        knob_pat.add_color_stop_rgb(0.7, 0.20, 0.25, 0.33)
        knob_pat.add_color_stop_rgb(1, 0.12, 0.16, 0.23)
        cr.arc(knob_cx, knob_cy, knob_r, 0, math.pi * 2)
        cr.set_source(knob_pat)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.2)
        cr.set_line_width(1)
        cr.stroke()

        knob_angle = (t * 0.8) % (math.pi * 2)
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.set_line_width(2)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(knob_cx + math.cos(knob_angle) * 5, knob_cy + math.sin(knob_angle) * 5)
        cr.line_to(knob_cx + math.cos(knob_angle) * 11, knob_cy + math.sin(knob_angle) * 11)
        cr.stroke()

        # 5. Keys Layer
        for i, k in enumerate(KB_KEYS):
            label, x, y, w, h = k
            cx = x + w / 2.0
            cy = y + h / 2.0

            r, g, b = self._calc_key_color(mode_id, k, i, t, base_rgb, speed_mult, bright_mult)

            # Ripple waves
            for rip in self._active_ripples:
                age = (now - rip["t"])
                rip_dist = math.hypot(cx - rip["x"], cy - rip["y"])
                wave_front = age * 380.0
                diff = abs(rip_dist - wave_front)
                if diff < 35.0:
                    amp = (1.0 - age / 0.9) * (1.0 - diff / 35.0)
                    r = min(1.0, r + rip["color"][0] * amp)
                    g = min(1.0, g + rip["color"][1] * amp)
                    b = min(1.0, b + rip["color"][2] * amp)

            # Underglow
            if bright_mult > 0 and (r > 0.02 or g > 0.02 or b > 0.02):
                rad = max(w, h) * 0.72
                glow_pat = cairo.RadialGradient(cx, cy, 2, cx, cy, rad)
                glow_pat.add_color_stop_rgba(0, r, g, b, 0.48 * bright_mult)
                glow_pat.add_color_stop_rgba(0.65, r, g, b, 0.16 * bright_mult)
                glow_pat.add_color_stop_rgba(1, 0, 0, 0, 0)
                cr.set_source(glow_pat)
                cr.rectangle(cx - rad, cy - rad, rad * 2, rad * 2)
                cr.fill()

            # Keycap Base
            draw_round_rect(cr, x, y, w, h, 3.5)
            cr.set_source_rgb(0.09, 0.098, 0.15)
            cr.fill_preserve()
            cr.set_source_rgba(1, 1, 1, 0.08)
            cr.set_line_width(1)
            cr.stroke()

            # Inset Dish
            draw_round_rect(cr, x + 1.5, y + 1.5, w - 3, h - 3, 2.5)
            top_pat = cairo.LinearGradient(x, y, x, y + h)
            top_pat.add_color_stop_rgb(0, 0.15, 0.16, 0.23)
            top_pat.add_color_stop_rgb(1, 0.08, 0.09, 0.14)
            cr.set_source(top_pat)
            cr.fill()

            # Legend
            if label:
                cr.save()
                cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
                font_size = 7.0 if len(label) > 3 else 8.5
                cr.set_font_size(font_size)
                ext = cr.text_extents(label)
                tx = cx - ext.width / 2.0 - ext.x_bearing
                ty = cy - ext.height / 2.0 - ext.y_bearing

                if bright_mult > 0 and (r > 0.02 or g > 0.02 or b > 0.02):
                    lr = min(1.0, r * 0.75 + 0.25 * bright_mult)
                    lg = min(1.0, g * 0.75 + 0.25 * bright_mult)
                    lb = min(1.0, b * 0.75 + 0.25 * bright_mult)
                    cr.set_source_rgb(lr, lg, lb)
                else:
                    cr.set_source_rgb(0.39, 0.45, 0.55)

                cr.move_to(tx, ty)
                cr.show_text(label)
                cr.restore()

            # Hover ring highlight
            if i == self._hovered_key_idx:
                draw_round_rect(cr, x, y, w, h, 3.5)
                cr.set_source_rgba(1, 1, 1, 0.5)
                cr.set_line_width(1.5)
                cr.stroke()

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

