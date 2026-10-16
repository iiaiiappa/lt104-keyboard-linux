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

from lt104_core import LT104Controller, LIGHT_MODES, SIDE_LIGHT_MODES, SLEEP_TIMER_MODES, MULTI_COLOR_MODES, KB_KEYS, find_lt104_usb, find_lt104_dongle, find_lt104_bluetooth, find_lt104_lcd_hidraw, get_lt104_connection_status

from config import load_config, save_config
from PIL import Image, ImageSequence

APP_ID = "com.theforwardway.lt104"
CLI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lt104_cli.py")

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
        # Calculate optimal size based on screen monitor work area
        target_w = 1240
        target_h = 1240
        display = Gdk.Display.get_default()
        if display:
            monitors = display.get_monitors()
            if monitors and monitors.get_n_items() > 0:
                geom = monitors.get_item(0).get_geometry()
                target_w = min(target_w, max(960, geom.width - 40))
                target_h = min(target_h, max(720, geom.height - 70))

        self.set_default_size(target_w, target_h)
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

        # Shortcuts Reference button (header start)
        sc_btn = Gtk.Button(label="⌨️  快捷键")
        sc_btn.set_tooltip_text("快捷键参考 / Shortcuts Reference")
        sc_btn.add_css_class("flat")
        sc_btn.connect("clicked", self._on_show_shortcuts)
        header.pack_start(sc_btn)

        # Product page button (header end, before window controls)
        product_btn = Gtk.Button(label="🛍️")
        product_btn.set_tooltip_text("LangTu LT-104 产品页面 / Product Page")
        product_btn.add_css_class("flat")
        product_btn.connect("clicked", lambda _: Gio.AppInfo.launch_default_for_uri(
            "https://langtustore.com/collections/mechanical-keyboards/products/langtu-lt-104-rgb-tri-mode-mechanical-gaming-keyboard",
            None
        ))
        header.pack_end(product_btn)

        # Scrollable main content with natural height propagation
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_propagate_natural_height(True)
        scroll.set_propagate_natural_width(True)
        toolbar_view.set_content(scroll)
        self._main_scroll = scroll

        clamp = Adw.Clamp()
        clamp.set_maximum_size(1160)
        clamp.set_margin_top(6)
        clamp.set_margin_bottom(8)
        clamp.set_margin_start(14)
        clamp.set_margin_end(14)
        scroll.set_child(clamp)


        # Main vertical container: Top Preview Card + 2-Column Setting Cards below
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        clamp.set_child(main_vbox)

        # 2-Column responsive container below the preview
        two_col_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        two_col_box.set_homogeneous(True)

        col_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        col_right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        two_col_box.append(col_left)
        two_col_box.append(col_right)

        # State and settings initialization
        init_cfg = load_config()
        self._remembered_brightness = int(init_cfg.get("remembered_brightness", init_cfg.get("brightness", 4))) or 4
        self._previous_mode_id = int(init_cfg.get("mode", 1))
        self._dim_star_keys = []
        self._next_star_change_time = 0.0
        self._hud_running = False
        self._key_flashes = [0.0] * len(KB_KEYS)
        self._pressed_key_idx = -1
        self._active_ripples = []
        self._hovered_key_idx = -1
        self._last_auto_tap_time = 0.0
        self._last_auto_ripple_time = 0.0
        self._lcd_frames = []
        self._lcd_total_duration = 0.0
        self._last_lcd_mtime = 0.0
        self._hud_surface = None
        self._last_hud_mtime = 0.0

        # Photorealistic skin surfaces
        base_dir = os.path.dirname(os.path.abspath(__file__))
        none_png = os.path.join(base_dir, "static", "keyboard_skin_none.png")
        dark_png = os.path.join(base_dir, "static", "keyboard_skin_dark.png")
        lit_png = os.path.join(base_dir, "static", "keyboard_skin_lit.png")
        self._skin_none = cairo.ImageSurface.create_from_png(none_png) if os.path.exists(none_png) else None
        self._skin_dark = cairo.ImageSurface.create_from_png(dark_png) if os.path.exists(dark_png) else None
        self._skin_lit = cairo.ImageSurface.create_from_png(lit_png) if os.path.exists(lit_png) else None
        self._load_lcd_surface()

        # ---- Top Middle: Full-width Standalone Keyboard Preview Card (200% larger) ---- #
        main_vbox.append(self._build_preview_card())

        # ---- Connection Mode Status Card (Explicit 3-Mode Indicator) ---- #
        main_vbox.append(self._build_connection_status_card())

        # ---- Below: 2-Column Setting Cards ---- #
        main_vbox.append(two_col_box)

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

        # Preview tick timer
        self._preview_timer_id = GLib.timeout_add(33, self._tick_preview)

        # Auto-fit window height dynamically to fit all controls without scrollbar
        GLib.timeout_add(100, self._auto_fit_window)

        # Initial device check once, then poll every 2 seconds
        GLib.idle_add(self._initial_refresh)
        GLib.timeout_add_seconds(2, self._refresh_status)

    def _auto_fit_window(self):
        """Always resize window to fit all controls without vertical scrollbar."""
        try:
            if hasattr(self, '_main_scroll') and self._main_scroll:
                vadjustment = self._main_scroll.get_vadjustment()
                upper = vadjustment.get_upper()
                page_size = vadjustment.get_page_size()
                curr_w = self.get_width()
                curr_h = self.get_height()
                if upper > page_size and upper > 100:
                    needed_extra = int(upper - page_size) + 16
                    display = Gdk.Display.get_default()
                    max_screen_h = 1600
                    if display:
                        monitors = display.get_monitors()
                        if monitors and monitors.get_n_items() > 0:
                            geom = monitors.get_item(0).get_geometry()
                            max_screen_h = geom.height - 70
                    target_h = min(max_screen_h, curr_h + needed_extra)
                    if target_h > curr_h:
                        self.set_default_size(curr_w, target_h)
                        self.queue_resize()
        except Exception:
            pass
        return False

    def _initial_refresh(self):
        self._refresh_status()
        return False


    # ------------------------------------------------------------------ #
    #  Card builders                                                        #
    # ------------------------------------------------------------------ #

    def _build_preview_card(self):
        """Top-middle full-width preview card with 200% larger keyboard visualizer (284px height)."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.add_css_class("card")
        card.set_margin_bottom(4)

        cfg = load_config()
        current_mode_id = int(cfg.get("mode", 1))
        initial_mode_idx = 0
        for idx, m in enumerate(LIGHT_MODES):
            if m["id"] == current_mode_id:
                initial_mode_idx = idx
                break

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

        hint_lbl = Gtk.Label(label="💡 点击按键触发灯光反馈 · 左右侧翼灯带实时同显")
        hint_lbl.add_css_class("dim-label")
        hint_lbl.set_halign(Gtk.Align.END)
        header_box.append(hint_lbl)

        card.append(header_box)

        # Drawing Area (Height: 284px — 200% larger than original 142px)
        self._preview_area = Gtk.DrawingArea()
        self._preview_area.set_content_height(284)
        self._preview_area.set_hexpand(True)
        self._preview_area.set_draw_func(self._on_draw_keyboard_preview)

        # Gesture & motion controllers
        click_gesture = Gtk.GestureClick()
        click_gesture.connect("pressed", self._on_preview_pressed)
        click_gesture.connect("released", self._on_preview_released)
        self._preview_area.add_controller(click_gesture)

        motion_ctrl = Gtk.EventControllerMotion()
        motion_ctrl.connect("motion", self._on_preview_motion)
        motion_ctrl.connect("leave", self._on_preview_leave)
        self._preview_area.add_controller(motion_ctrl)

        card.append(self._preview_area)
        return card

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
            ".conn-pill { padding: 4px 12px; border-radius: 14px; font-size: 12px; font-weight: 600; background: rgba(255, 255, 255, 0.05); color: #888888; border: 1px solid rgba(255,255,255,0.08); }",
            ".conn-pill-active-cable { background: rgba(46, 194, 126, 0.2); color: #2ec27e; border: 1px solid rgba(46, 194, 126, 0.6); }",
            ".conn-pill-active-dongle { background: rgba(246, 185, 59, 0.2); color: #f5a623; border: 1px solid rgba(246, 185, 59, 0.6); }",
            ".conn-pill-active-bluetooth { background: rgba(53, 132, 228, 0.2); color: #78aeed; border: 1px solid rgba(53, 132, 228, 0.6); }",
            ".conn-pill-inactive { opacity: 0.45; }",
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

        # ---- Side Edge Backlight Controls (侧翼双侧灯带 - 硬件快捷键控制) ---- #
        self._side_mode_row = Adw.ComboRow()
        self._side_mode_row.set_title("两侧边缘背光 (侧翼灯带 - 状态预览)")
        self._side_mode_row.set_subtitle("💡 纯硬件按键控制：请直接在键盘上按 Fn + Insert 切换模式与颜色（仅供预览，不可软件修改）")
        side_mode_strings = Gtk.StringList.new([m["name"] for m in SIDE_LIGHT_MODES])
        self._side_mode_row.set_model(side_mode_strings)
        self._side_mode_row.set_list_factory(make_wide_list_factory())
        # Enabled to allow viewing all options; selection updates local preview only without configuring hardware
        self._side_mode_row.set_sensitive(True)
        current_side_mode = int(cfg.get("side_mode", 1))
        initial_side_idx = 1
        for idx, sm in enumerate(SIDE_LIGHT_MODES):
            if sm["id"] == current_side_mode:
                initial_side_idx = idx
                break
        self._side_mode_row.set_selected(initial_side_idx)
        self._side_mode_row.connect("notify::selected", self._on_side_light_changed)
        group.add(self._side_mode_row)

        self._side_color_row = Adw.ActionRow()
        self._side_color_row.set_title("两侧边缘背光颜色预览 (Side Light Color Preview)")
        self._side_color_row.set_subtitle("当前硬件档位预设颜色（仅供预览）")
        self._side_color_btn = Gtk.ColorDialogButton()
        self._side_color_btn.set_valign(Gtk.Align.CENTER)
        self._side_color_btn.set_sensitive(False)  # Read-only non-editable
        side_dialog = Gtk.ColorDialog()
        side_dialog.set_title("侧翼灯带颜色预览")
        side_dialog.set_with_alpha(False)
        self._side_color_btn.set_dialog(side_dialog)
        side_rgba = Gdk.RGBA()
        side_rgba.parse(cfg.get("side_color", "#00e5ff"))
        self._side_color_btn.set_rgba(side_rgba)
        self._side_color_row.add_suffix(self._side_color_btn)
        # Mode 0: Off, 1: Breathing, 2: Spectrum Cycle -> NO Side Light Color Preview (hide)
        # Modes 3-10 (Preset colors) -> show preview
        self._side_color_row.set_visible(current_side_mode >= 3)
        group.add(self._side_color_row)

        # ---- Inactivity Sleep Timeout Row (无活动自动熄灭背光) ---- #
        self._sleep_timer_row = Adw.ComboRow()
        self._sleep_timer_row.set_title("背光无活动休眠时间 (自动熄灭)")
        self._sleep_timer_row.set_subtitle("无键盘活动时自动熄灭背光以节省电量并保护硬件")
        sleep_timer_strings = Gtk.StringList.new([m["name"] for m in SLEEP_TIMER_MODES])
        self._sleep_timer_row.set_model(sleep_timer_strings)
        self._sleep_timer_row.set_list_factory(make_wide_list_factory())
        current_sleep_id = int(cfg.get("sleep_timer", 3))
        initial_sleep_idx = 0
        for idx, slm in enumerate(SLEEP_TIMER_MODES):
            if slm["id"] == current_sleep_id:
                initial_sleep_idx = idx
                break
        self._sleep_timer_row.set_selected(initial_sleep_idx)
        self._sleep_timer_row.connect("notify::selected", self._on_sleep_timer_changed)
        group.add(self._sleep_timer_row)

        # Auto Apply Switch Row
        self._auto_apply_row = Adw.SwitchRow()
        self._auto_apply_row.set_title("即时生效 (调整时自动应用)")
        self._auto_apply_row.set_subtitle("开启后调整模式、颜色、亮度、速度或侧边灯立即应用，无需手动点击应用按钮")
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

        # Buttons: Row 1 (Toggle HUD) + Row 2 (Single-shot Once & Restore Anim)
        btn_box1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._hud_btn = Gtk.Button(label=f"📊  开启即时系统 HUD (每{int(initial_inv)}秒更新)")
        self._hud_btn.add_css_class("pill")
        self._hud_btn.set_hexpand(True)
        self._hud_btn.connect("clicked", self._on_toggle_hud)
        btn_box1.append(self._hud_btn)
        box.append(btn_box1)

        btn_box2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._hud_once_btn = Gtk.Button(label="⚡  立即单次刷新")
        self._hud_once_btn.add_css_class("pill")
        self._hud_once_btn.set_hexpand(True)
        self._hud_once_btn.connect("clicked", self._on_hud_once)
        btn_box2.append(self._hud_once_btn)

        self._hud_restore_btn = Gtk.Button(label="🔄  恢复动画")
        self._hud_restore_btn.add_css_class("pill")
        self._hud_restore_btn.set_hexpand(True)
        self._hud_restore_btn.connect("clicked", self._on_restore_anim)
        btn_box2.append(self._hud_restore_btn)
        box.append(btn_box2)


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
    def _build_connection_status_card(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        card.add_css_class("card")
        card.set_margin_top(2)
        card.set_margin_bottom(2)

        pad_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        pad_box.set_margin_top(10)
        pad_box.set_margin_bottom(10)
        pad_box.set_margin_start(14)
        pad_box.set_margin_end(14)
        card.append(pad_box)

        # Top row: Left (Icon + Title), Right (3-Mode Segment Pills)
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        top_row.set_hexpand(True)
        pad_box.append(top_row)

        self._conn_mode_icon = Gtk.Label(label="📡")
        self._conn_mode_icon.add_css_class("title-3")
        top_row.append(self._conn_mode_icon)

        self._conn_mode_title = Gtk.Label(label="键盘连接模式: 检测中…")
        self._conn_mode_title.add_css_class("heading")
        self._conn_mode_title.set_halign(Gtk.Align.START)
        self._conn_mode_title.set_hexpand(True)
        top_row.append(self._conn_mode_title)

        pills_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pills_box.set_halign(Gtk.Align.END)
        top_row.append(pills_box)

        self._pill_cable = Gtk.Label(label="🔌 USB Cable (有线)")
        self._pill_cable.add_css_class("conn-pill")
        pills_box.append(self._pill_cable)

        self._pill_dongle = Gtk.Label(label="📡 USB Dongle (接收器)")
        self._pill_dongle.add_css_class("conn-pill")
        pills_box.append(self._pill_dongle)

        self._pill_bluetooth = Gtk.Label(label="📶 Bluetooth (蓝牙)")
        self._pill_bluetooth.add_css_class("conn-pill")
        pills_box.append(self._pill_bluetooth)

        # Bottom row: Capability Description
        self._conn_mode_desc = Gtk.Label(label="正在检测键盘连接状态…")
        self._conn_mode_desc.set_halign(Gtk.Align.START)
        self._conn_mode_desc.add_css_class("caption")
        self._conn_mode_desc.add_css_class("dim-label")
        self._conn_mode_desc.set_wrap(True)
        pad_box.append(self._conn_mode_desc)

        self._conn_status_card = card
        return card

    # ------------------------------------------------------------------ #

    def _refresh_status(self):
        status = get_lt104_connection_status()
        mode = status["mode"]

        # Reset pill styles
        for pill in [self._pill_cable, self._pill_dongle, self._pill_bluetooth]:
            pill.remove_css_class("conn-pill-active-cable")
            pill.remove_css_class("conn-pill-active-dongle")
            pill.remove_css_class("conn-pill-active-bluetooth")
            pill.remove_css_class("conn-pill-inactive")
            pill.add_css_class("conn-pill-inactive")

        if mode == "usb_cable":
            lcd = status.get("lcd_path") or "未找到"
            self._status_label.set_text(f"🔌  LT-104 [USB 有线模式 · 全部功能已就绪]  |  LCD: {lcd}")
            self._conn_mode_icon.set_text("🔌")
            self._conn_mode_title.set_text("当前连接模式: USB 有线连接 (USB Cable Mode)")
            self._conn_mode_desc.set_text("● 已连接 SONiX 0c45:8009。全部硬件功能已就绪：RGB 灯效、时钟同步、屏幕 GIF 动画上传与系统 HUD。")
            self._pill_cable.remove_css_class("conn-pill-inactive")
            self._pill_cable.add_css_class("conn-pill-active-cable")

        elif mode == "usb_dongle":
            self._status_label.set_text("📡  LT-104 [2.4G 接收器模式 · 打字正常 · 配置需插线]")
            self._conn_mode_icon.set_text("📡")
            self._conn_mode_title.set_text("当前连接模式: 2.4G 无线接收器 (USB Dongle Mode)")
            self._conn_mode_desc.set_text("● 已插入 2.4G 接收器 (05ac:024f)。键盘打字完全正常。如需配置背光灯效、时钟校准或屏幕动画，请插上 USB 有线连接线。")
            self._pill_dongle.remove_css_class("conn-pill-inactive")
            self._pill_dongle.add_css_class("conn-pill-active-dongle")

        elif mode == "bluetooth":
            dev_name = status.get("device_name", "LT104 BT")
            self._status_label.set_text(f"📶  LT-104 [蓝牙无线模式 ({dev_name}) · 打字正常 · 配置需插线]")
            self._conn_mode_icon.set_text("📶")
            self._conn_mode_title.set_text(f"当前连接模式: 蓝牙无线连接 ({dev_name})")
            self._conn_mode_desc.set_text(f"● 已通过蓝牙无线连接 ({dev_name})。键盘打字完全正常。如需配置背光灯效、时钟校准或屏幕动画，请插上 USB 有线连接线。")
            self._pill_bluetooth.remove_css_class("conn-pill-inactive")
            self._pill_bluetooth.add_css_class("conn-pill-active-bluetooth")

        else:
            self._status_label.set_text("❌  未检测到 LT-104 键盘 (未连接)")
            self._conn_mode_icon.set_text("❌")
            self._conn_mode_title.set_text("当前连接模式: 未检测到键盘 (Not Present / Disconnected)")
            self._conn_mode_desc.set_text("● 未检测到任何 LT-104 键盘。本键盘支持 3 种连接方式：1) USB 有线数据线  2) 2.4G USB 接收器  3) 蓝牙无线配对。")

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

    def _on_show_shortcuts(self, _btn):
        """Show a scrollable Shortcuts Reference dialog with OS selector and live search."""
        dlg = Adw.Dialog()
        dlg.set_title("⌨️  快捷键参考 / Shortcuts Reference")
        dlg.set_content_width(640)
        dlg.set_content_height(720)

        toolbar = Adw.ToolbarView()
        hdr = Adw.HeaderBar()
        toolbar.add_top_bar(hdr)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_propagate_natural_height(True)
        toolbar.set_content(scroll)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        scroll.set_child(main_box)

        # 1. Search bar & OS Filter controls
        controls_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        controls_card.add_css_class("card")
        controls_card.set_margin_bottom(4)

        # Free text search
        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text("🔍 搜索快捷键、功能或按键名称 (Search key or function)...")
        controls_card.append(search_entry)

        # OS Selector row
        os_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        os_lbl = Gtk.Label(label="选择操作系统 / Select OS:")
        os_lbl.add_css_class("heading")
        os_lbl.set_xalign(0.0)
        os_row.append(os_lbl)

        os_dropdown = Gtk.DropDown.new_from_strings([
            "🐧 Ubuntu Linux (建议使用 Win 模式连接)",
            "🪟 Win System (Windows)",
            "🍎 Mac System (macOS)",
            "🌐 全部系统 (All Systems)"
        ])
        os_dropdown.set_selected(0)
        os_dropdown.set_hexpand(True)
        os_row.append(os_dropdown)
        controls_card.append(os_row)

        # Ubuntu connection hint banner
        ubuntu_banner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ubuntu_banner.add_css_class("card")
        ubuntu_banner.set_margin_top(4)
        ubuntu_banner.set_margin_bottom(4)
        hint_icon = Gtk.Label(label="💡")
        hint_txt = Gtk.Label(label="<b>提示</b>：连接至 Ubuntu Linux 时，建议将键盘硬件开关拨至 <b>Win 模式</b> 以获得最佳键位与 Fn 多媒体控制兼容性。\n(Suggestion: Switch keyboard to Win system mode when connecting to Ubuntu for optimal shortcut compatibility.)")
        hint_txt.set_use_markup(True)
        hint_txt.set_wrap(True)
        hint_txt.set_xalign(0.0)
        ubuntu_banner.append(hint_icon)
        ubuntu_banner.append(hint_txt)
        controls_card.append(ubuntu_banner)

        main_box.append(controls_card)

        # Container for shortcut groups
        groups_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.append(groups_box)

        # Empty state label
        empty_lbl = Gtk.Label(label="未找到匹配的快捷键 (No matching shortcuts found)")
        empty_lbl.add_css_class("dim-label")
        empty_lbl.set_margin_top(30)
        empty_lbl.set_margin_bottom(30)
        empty_lbl.set_visible(False)
        main_box.append(empty_lbl)

        SHORTCUTS_DATA = [
            ("ubuntu", "🐧 Ubuntu Linux — Fn + F-key (建议使用 Win 模式)", [
                ("Fn + F1",  "Settings > Displays (设置 > 显示器)"),
                ("Fn + F2",  "Calculator (计算器)"),
                ("Fn + F3",  "Same as WIN + TAB (Task Switch) (任务切换)"),
                ("Fn + F4",  "Nothing Happened (无反应)"),
                ("Fn + F5",  "Backlight Brightness − (背光亮度 −)"),
                ("Fn + F6",  "Backlight Brightness + (背光亮度 +)"),
                ("Fn + F7",  "Previous Track (上一曲)"),
                ("Fn + F8",  "Play / Pause (播放 / 暂停)"),
                ("Fn + F9",  "Next Track (下一曲)"),
                ("Fn + F10", "Mute / Unmute (静音 / 取消静音)"),
                ("Fn + F11", "Volume − (音量 −)"),
                ("Fn + F12", "Volume + (音量 +)"),
                ("Fn + WIN", "Lock WIN Key (锁定 WIN 键)"),
            ]),
            ("win", "🪟 Win System — Fn + F-key", [
                ("Fn + F1",  "Media Player (媒体播放器)"),
                ("Fn + F2",  "Calculator (计算器)"),
                ("Fn + F3",  "Win + TAB  (Task View 任务视图)"),
                ("Fn + F4",  "Win + E  (File Explorer 文件资源管理器)"),
                ("Fn + F5",  "Backlight Brightness − (背光亮度 −)"),
                ("Fn + F6",  "Backlight Brightness + (背光亮度 +)"),
                ("Fn + F7",  "Previous Track (上一曲)"),
                ("Fn + F8",  "Play / Pause (播放 / 暂停)"),
                ("Fn + F9",  "Next Track (下一曲)"),
                ("Fn + F10", "Mute / Unmute (静音 / 取消静音)"),
                ("Fn + F11", "Volume − (音量 −)"),
                ("Fn + F12", "Volume + (音量 +)"),
                ("Fn + WIN", "Lock WIN Key (锁定 WIN 键)"),
            ]),
            ("mac", "🍎 Mac System — F-key Direct", [
                ("F1",  "Screen Brightness − (屏幕亮度 −)"),
                ("F2",  "Screen Brightness + (屏幕亮度 +)"),
                ("F3",  "Split Screen (分屏显示)"),
                ("F4",  "Call up Siri (唤出 Siri)"),
                ("F5",  "Keyboard Backlight − (键盘背光 −)"),
                ("F6",  "Keyboard Backlight + (键盘背光 +)"),
                ("F7",  "Previous Track (上一曲)"),
                ("F8",  "Play / Pause (播放 / 暂停)"),
                ("F9",  "Next Track (下一曲)"),
                ("F10", "Mute / Unmute (静音 / 取消静音)"),
                ("F11", "Volume − (音量 −)"),
                ("F12", "Volume + (音量 +)"),
            ]),
            ("common", "🔑 Common Shortcuts (通用硬件快捷键)", [
                ("Fn + Esc  (hold 3s)", "Restore Factory Settings (恢复出厂设置)"),
                ("Fn + Ins",            "Side Edge Backlight — cycle mode & color (两侧边光切换模式与颜色)"),
                ("Fn + Q",              "Switch to 2.4G Connection Mode (切换 2.4G 无线模式)"),
                ("Fn + W",              "Switch to Bluetooth 1 Mode (切换蓝牙 1 模式)"),
                ("Fn + E",              "Switch to Bluetooth 2 Mode (切换蓝牙 2 模式)"),
                ("Fn + R",              "Switch to Bluetooth 3 Mode (切换蓝牙 3 模式)"),
                ("Fn + T",              "Switch to Wired Connection Mode (切换有线模式)"),
                ("Fn + Knob tap",       "Toggle main interface / volume level display (切换主界面与音量显示)"),
            ]),
        ]

        group_widgets = []
        for os_key, section_title, rows in SHORTCUTS_DATA:
            grp = Adw.PreferencesGroup()
            grp.set_title(section_title)
            row_items = []
            for key, action in rows:
                row = Adw.ActionRow()
                row.set_title(key)
                row.set_subtitle(action)
                grp.add(row)
                row_items.append((row, key.lower(), action.lower()))
            groups_box.append(grp)
            group_widgets.append((grp, os_key, row_items))

        def filter_shortcuts(*_):
            query = search_entry.get_text().strip().lower()
            selected_os_idx = os_dropdown.get_selected()
            target_os = ["ubuntu", "win", "mac", "all"][selected_os_idx]

            ubuntu_banner.set_visible(target_os in ("ubuntu", "all"))

            total_visible_rows = 0
            for grp, os_key, rows in group_widgets:
                os_match = (target_os == "all") or (os_key == target_os) or (os_key == "common")
                if not os_match:
                    grp.set_visible(False)
                    continue

                visible_in_grp = 0
                for row, key_text, action_text in rows:
                    if not query or query in key_text or query in action_text:
                        row.set_visible(True)
                        visible_in_grp += 1
                        total_visible_rows += 1
                    else:
                        row.set_visible(False)

                grp.set_visible(visible_in_grp > 0)

            empty_lbl.set_visible(total_visible_rows == 0)

        search_entry.connect("search-changed", filter_shortcuts)
        os_dropdown.connect("notify::selected", filter_shortcuts)
        filter_shortcuts()

        dlg.set_child(toolbar)
        dlg.present(self)

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
            else:
                # Coming to other mode: guarantee non-zero brightness
                if self._previous_mode_id == 20 or current_bright <= 0:
                    restore_val = self._remembered_brightness if (self._remembered_brightness and self._remembered_brightness > 0) else 4
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

    def _on_side_light_changed(self, row, param):
        side_idx = self._side_mode_row.get_selected() if hasattr(self, '_side_mode_row') else 1
        side_mode = SIDE_LIGHT_MODES[side_idx]["id"] if side_idx < len(SIDE_LIGHT_MODES) else 1
        if hasattr(self, '_side_color_row'):
            self._side_color_row.set_visible(side_mode >= 3)
        if hasattr(self, '_side_color_btn') and "color" in SIDE_LIGHT_MODES[side_idx] and side_mode >= 3:
            c_hex = SIDE_LIGHT_MODES[side_idx]["color"]
            rgba = Gdk.RGBA()
            rgba.parse(c_hex)
            self._side_color_btn.set_rgba(rgba)
        if hasattr(self, '_preview_area') and self._preview_area:
            self._preview_area.queue_draw()
        if hasattr(self, '_auto_apply_row') and self._auto_apply_row.get_active():
            self._apply_side_light_silently()

    def _on_sleep_timer_changed(self, row, param):
        sleep_idx = self._sleep_timer_row.get_selected() if hasattr(self, '_sleep_timer_row') else 0
        sleep_id = SLEEP_TIMER_MODES[sleep_idx]["id"] if sleep_idx < len(SLEEP_TIMER_MODES) else 3
        save_config({"sleep_timer": sleep_id})

        def do_sleep():
            try:
                ctl = LT104Controller()
                ctl.set_sleep_timer(sleep_id)
                ctl.close()
            except Exception:
                pass

        threading.Thread(target=do_sleep, daemon=True).start()

    def _on_side_color_changed(self, btn, param):
        if hasattr(self, '_preview_area') and self._preview_area:
            self._preview_area.queue_draw()

    def _apply_side_light_silently(self):
        pass


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
                for cand in ["0.gif", "lt104_sample.gif"]:
                    cand_path = os.path.join(base_dir, cand)
                    if os.path.exists(cand_path):
                        lcd_path = cand_path
                        break
            if os.path.exists(lcd_path):
                mtime = os.path.getmtime(lcd_path)
                if mtime != getattr(self, '_last_lcd_mtime', 0.0) or not getattr(self, '_lcd_frames', None):
                    im = Image.open(lcd_path)
                    frames = []
                    for f in ImageSequence.Iterator(im):
                        rgba = f.convert("RGBA").resize((62, 39), Image.Resampling.LANCZOS)
                        raw = bytearray(rgba.tobytes("raw", "BGRA"))
                        surf = cairo.ImageSurface.create_for_data(raw, cairo.FORMAT_ARGB32, 62, 39)
                        dur = f.info.get("duration", 80) / 1000.0
                        if dur <= 0.01:
                            dur = 0.08
                        frames.append((surf, dur, raw))
                    if frames:
                        self._lcd_frames = frames
                        self._lcd_total_duration = sum(f[1] for f in frames)
                        self._last_lcd_mtime = mtime
        except Exception:
            pass

    def _load_hud_surface(self):
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            hud_path = os.path.join(base_dir, "static", "current_hud.png")
            if os.path.exists(hud_path):
                mtime = os.path.getmtime(hud_path)
                if mtime != getattr(self, '_last_hud_mtime', 0.0) or getattr(self, '_hud_surface', None) is None:
                    im = Image.open(hud_path)
                    rgba = im.convert("RGBA").resize((62, 39), Image.Resampling.LANCZOS)
                    raw = bytearray(rgba.tobytes("raw", "BGRA"))
                    self._hud_surface = cairo.ImageSurface.create_for_data(raw, cairo.FORMAT_ARGB32, 62, 39)
                    self._hud_raw = raw
                    self._last_hud_mtime = mtime
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

    def _on_preview_pressed(self, gesture, n_press, x, y):
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
        self._pressed_key_idx = idx
        now = time.time()
        rgba = self._color_btn.get_rgba()
        base_rgb = (rgba.red, rgba.green, rgba.blue)

        mode_idx = self._mode_row.get_selected()
        mode_id = LIGHT_MODES[mode_idx]["id"] if mode_idx < len(LIGHT_MODES) else 1
        if mode_id in (2, 3, 4, 5, 10, 16, 17, 18, 19):
            # Modes 2, 3 have NO ripples. Modes 4 (Stars), 5 (Snow), 10, 16, 17, 18, 19 do not react to keypresses.
            self._preview_area.queue_draw()
            return

        if idx >= 0:
            self._key_flashes[idx] = 1.0
            k = KB_KEYS[idx]
            self._active_ripples.append({
                "x": k[1] + k[3] / 2.0,
                "y": k[2] + k[4] / 2.0,
                "row": get_key_row(k[2]),
                "t": now,
                "color": base_rgb,
                "mode": mode_id
            })
        else:
            self._active_ripples.append({
                "x": canvas_x,
                "y": canvas_y,
                "row": get_key_row(canvas_y),
                "t": now,
                "color": base_rgb,
                "mode": mode_id
            })
        self._preview_area.queue_draw()

    def _on_preview_released(self, gesture, n_press, x, y):
        self._pressed_key_idx = -1
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
            # Lights OFF by default. When pressing a key, that key's light is ON. When not pressing, light back to OFF.
            if idx == getattr(self, '_pressed_key_idx', -1):
                return base_rgb
            return (0.0, 0.0, 0.0)

        elif mode == 3:  # 单熄灭 (Single Off)
            # Lights on ALL the time. When pressing a key, the key's light is OFF. When not pressing, light is back ON.
            if idx == getattr(self, '_pressed_key_idx', -1):
                return (0.0, 0.0, 0.0)
            return base_rgb

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
            # 7 rainbow colors alternating on 5 rows in the keyboard.
            # Each row uses different colors from 7 rainbow colors.
            # Each row changes its own color slowly without using color from other rows.
            # At Animation Speed 2 -> changes to another color every 0.5s.
            # Pressing keyboard has no reaction.
            RAINBOW_7 = (
                (1.0, 0.0, 0.0),      # Red
                (1.0, 0.48, 0.0),     # Orange
                (1.0, 0.95, 0.0),     # Yellow
                (0.0, 0.88, 0.0),     # Green
                (0.0, 0.88, 1.0),     # Cyan
                (0.0, 0.22, 1.0),     # Blue
                (0.68, 0.0, 1.0),     # Purple
            )
            step_dur = 0.5 / speed_mult
            step = int(t / step_dur)
            prog = (t % step_dur) / step_dur

            # 5 rows: F-keys(0), Numbers(1), QWERTY(2), ASDF(3), ZXCV+Space(4)
            k_row = min(4, get_key_row(k[2]))

            c1 = RAINBOW_7[(step + k_row) % 7]
            c2 = RAINBOW_7[(step + 1 + k_row) % 7]
            r = (1.0 - prog) * c1[0] + prog * c2[0]
            g = (1.0 - prog) * c1[1] + prog * c2[1]
            b = (1.0 - prog) * c1[2] + prog * c2[2]
            return (r, g, b)

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
            # Speed slowed down in half: row duration doubled (1.10s base per row)
            # Stream object width: increased from 1 key to 5.4 keys in a row (sigma = 60.0px)
            # Motion: moving smoothly from left to right with Gaussian blur
            # Color: For each key, it assigns itself a random color sustained for each stream;
            #        each key uses another random color for other streams.
            row_interval = 1.10 / speed_mult
            travel_dur = 1.15 * row_interval
            sigma = 60.0  # 5.4 keys Gaussian blur width (5.4 * 41px = 221.4px)
            x_start = -140.0
            x_end = 1098.0

            k_row = get_key_row(k[2])
            s_base = int(t / row_interval)

            total_r = 0.0
            total_g = 0.0
            total_b = 0.0

            # Check nearby stream passes for this row (at most 1 is active on this row)
            for s in (s_base - 1, s_base, s_base + 1):
                if s < 0 or (s % 6) != k_row:
                    continue
                t_el = t - s * row_interval
                if 0.0 <= t_el <= travel_dur:
                    prog = t_el / travel_dur
                    swipe_x = x_start + prog * (x_end - x_start)
                    dist_x = abs(cx - swipe_x)
                    val = math.exp(-(dist_x * dist_x) / (2.0 * sigma * sigma))
                    if val > 0.005:
                        # Deterministic random hue unique to this (key, stream) combination,
                        # sustained continuously throughout the entire passage of this stream
                        h = (idx * 0x1f1f1f1f + s * 0x3d3d3d3d) & 0xffffffff
                        h = ((h >> 16) ^ h) * 0x45d9f3b & 0xffffffff
                        h = ((h >> 16) ^ h) * 0x45d9f3b & 0xffffffff
                        hue = ((h >> 16) ^ h) % 360.0

                        c = hsl_to_rgb(hue, 1.0, 0.5)
                        total_r += c[0] * val
                        total_g += c[1] * val
                        total_b += c[2] * val

            return (min(1.0, total_r), min(1.0, total_g), min(1.0, total_b))

        elif mode == 17:  # 重峦叠嶂 (Rolling Hills)
            # Background all off, 2.5-keys wide 45° slashes with Gaussian blur.
            # Slashes emerge from the 50% middle of keyboard:
            # - Left side (cx <= mid_x): forward slash (/) and inserted backslash (\) alternating, 3 keys apart, sweeping to the left without bouncing.
            # - Right side (cx >= mid_x): backslash (\) and inserted forward slash (/) alternating, 3 keys apart, sweeping to the right without bouncing.
            # No cross in the middle of keyboard, 3 keys apart between slashes.
            mid_x = 479.0
            mid_y = 141.5
            wave_speed = 220.0 * speed_mult
            slash_spacing = 164.0  # Exactly 3 unlit keys apart between slashes (4 * 41px pitch)
            spawn_interval = slash_spacing / wave_speed
            travel_duration = 550.0 / wave_speed
            sigma = 28.0  # 2.5 keys width Gaussian blur (2.5 * 41px ~ 102.5px full span at 95% width, sigma ~ 28px)

            spawn_b = mid_x - mid_y
            spawn_f = mid_x + mid_y

            max_val = 0.0
            active_hue = 0.0

            current_wave_idx = int(t / spawn_interval)
            for w in range(current_wave_idx - 6, current_wave_idx + 1):
                if w < 0:
                    continue
                wave_age = t - w * spawn_interval
                if wave_age < 0 or wave_age > travel_duration:
                    continue

                dist_travelled = wave_age * wave_speed

                # Left side (cx <= mid_x): sweeps to the left
                if cx <= mid_x:
                    if w % 2 == 0:
                        # Forward slash (/) sweeping left
                        coord_f = cx + cy
                        wave_coord = spawn_f - dist_travelled
                        dist = abs(coord_f - wave_coord)
                    else:
                        # Inserted backslash (\) between forward slashes sweeping left
                        coord_b = cx - cy
                        wave_coord = spawn_b - dist_travelled
                        dist = abs(coord_b - wave_coord)

                    val = math.exp(-(dist * dist) / (2.0 * sigma * sigma))
                    if val > 0.005 and val > max_val:
                        max_val = val
                        active_hue = ((w * 67.0) + 180.0 + 360.0) % 360.0

                # Right side (cx >= mid_x): sweeps to the right
                if cx >= mid_x:
                    if w % 2 == 0:
                        # Backslash (\) sweeping right
                        coord_b = cx - cy
                        wave_coord = spawn_b + dist_travelled
                        dist = abs(coord_b - wave_coord)
                    else:
                        # Inserted forward slash (/) between backslashes sweeping right
                        coord_f = cx + cy
                        wave_coord = spawn_f + dist_travelled
                        dist = abs(coord_f - wave_coord)

                    val = math.exp(-(dist * dist) / (2.0 * sigma * sigma))
                    if val > 0.005 and val > max_val:
                        max_val = val
                        active_hue = ((w * 67.0) + 360.0) % 360.0

            if max_val < 0.01:
                return (0.0, 0.0, 0.0)

            # Per-key random color that smoothly changes every second (scaled by speed_mult)
            sec_step = t * speed_mult
            curr_sec = int(sec_step)
            frac = sec_step - curr_sec

            def get_key_sec_rgb(k_idx, s_idx):
                h = (k_idx * 0x1f1f1f1f + s_idx * 0x3d3d3d3d) & 0xffffffff
                h = ((h >> 16) ^ h) * 0x45d9f3b & 0xffffffff
                h = ((h >> 16) ^ h) * 0x45d9f3b & 0xffffffff
                hue = ((h >> 16) ^ h) % 360.0
                return hsl_to_rgb(hue, 1.0, 0.5)

            c1 = get_key_sec_rgb(idx, curr_sec)
            c2 = get_key_sec_rgb(idx, curr_sec + 1)
            cr_k = c1[0] + (c2[0] - c1[0]) * frac
            cg_k = c1[1] + (c2[1] - c1[1]) * frac
            cb_k = c1[2] + (c2[2] - c1[2]) * frac

            return (cr_k * max_val, cg_k * max_val, cb_k * max_val)

        elif mode == 18:  # 斜风细雨 (Gentle Rain)
            # Multiple 45° backslashes (cx - cy) sweeping continuously from left to right.
            # Spacing: Exactly 5 keys apart from middle of backslash to middle of next backslash (5 * 41px = 205px).
            # Width: 1.8 keys width with Gaussian blur (sigma = 20.0px).
            # Color: For each key, it assigns itself a random color sustained for each backslash,
            #        using another random color for other backslashes.
            # Seamless fade-in and fade-out transitions; slashes flow continuously without on/off popping.
            wave_speed = 180.0 * speed_mult
            slash_spacing = 205.0  # 5 keys pitch from middle of backslash to next middle
            sigma = 20.0         # 1.8 keys Gaussian blur width
            coord_b = cx - cy
            global_phase = t * wave_speed

            # Check active adjacent slashes
            k_center = (coord_b - global_phase) / slash_spacing
            k_min = int(math.floor(k_center - 1.0))
            k_max = int(math.ceil(k_center + 1.0))

            total_r = 0.0
            total_g = 0.0
            total_b = 0.0

            for k in range(k_min, k_max + 1):
                line_pos = k * slash_spacing + global_phase
                dist = abs(coord_b - line_pos)
                val = math.exp(-(dist * dist) / (2.0 * sigma * sigma))
                if val > 0.005:
                    # Deterministic random hue unique to this (key, slash) combination,
                    # sustained continuously throughout the entire passage of this backslash
                    h = (idx * 0x1f1f1f1f + k * 0x3d3d3d3d) & 0xffffffff
                    h = ((h >> 16) ^ h) * 0x45d9f3b & 0xffffffff
                    h = ((h >> 16) ^ h) * 0x45d9f3b & 0xffffffff
                    hue = ((h >> 16) ^ h) % 360.0

                    c = hsl_to_rgb(hue, 1.0, 0.5)
                    total_r += c[0] * val
                    total_g += c[1] * val
                    total_b += c[2] * val

            if total_r < 0.005 and total_g < 0.005 and total_b < 0.005:
                return (0.0, 0.0, 0.0)
            return (
                min(1.0, total_r),
                min(1.0, total_g),
                min(1.0, total_b)
            )

        elif mode == 19:  # 来回穿梭 (Shuttle)
            # Slow flowing harmonic wave across the whole board (does not react to keypresses)
            hue = (cx * 0.45 - t * speed_mult * 35.0 + math.sin(cy * 0.04) * 40.0 + 360.0) % 360.0
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

        # 1. Background base
        cr.set_source_rgb(0.035, 0.043, 0.078)
        cr.rectangle(0, 0, 954, 297)
        cr.fill()

        # 2. Lighting Blocks behind keyboard card
        if bright_mult > 0:
            if mode_id == 1 and not self._active_ripples:
                # STATIC MODE: Uniform colored lighting behind keys
                cr.set_source_rgb(base_rgb[0] * bright_mult, base_rgb[1] * bright_mult, base_rgb[2] * bright_mult)
                for i, k in enumerate(KB_KEYS):
                    _, kx, ky, kw, kh = k
                    cr.rectangle(kx - 1, ky - 1, kw + 2, kh + 2)
                cr.fill()
            else:
                # DYNAMIC MODES: Render light blocks per key behind keyboard card
                for i, k in enumerate(KB_KEYS):
                    _, kx, ky, kw, kh = k
                    cx = kx + kw / 2.0
                    cy = ky + kh / 2.0
                    r, g, b = self._calc_key_color(mode_id, k, i, t, base_rgb, speed_mult, bright_mult)

                    if mode_id not in (2, 3, 4, 5, 10, 16, 17, 18, 19):
                        for rip in self._active_ripples:
                            age = (now - rip["t"])
                            rip_mode = rip.get("mode", mode_id)

                            if rip_mode == 13:
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
                        cr.set_source_rgb(r, g, b)
                        cr.rectangle(kx - 1, ky - 1, kw + 2, kh + 2)
                        cr.fill()

        # 3. Draw singledevice_keyboardK870T_none card ON TOP of the lighting blocks
        if self._skin_none:
            cr.set_source_surface(self._skin_none, 0, 0)
            cr.paint()
        elif self._skin_dark:
            cr.set_source_surface(self._skin_dark, 0, 0)
            cr.paint()

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
            self._load_hud_surface()
            if getattr(self, '_hud_surface', None):
                cr.set_source_surface(self._hud_surface, 808, 18)
                cr.paint()
            else:
                # Real-time HUD Mode Fallback: Live hardware telemetry & digital clock
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
            # GIF Animation Mode: Render active moving LCD GIF
            self._load_lcd_surface()
            if getattr(self, '_lcd_frames', None) and getattr(self, '_lcd_total_duration', 0.0) > 0:
                t_in_cycle = t % self._lcd_total_duration
                accum = 0.0
                active_surface = self._lcd_frames[0][0]
                for surf, dur, _ in self._lcd_frames:
                    accum += dur
                    if t_in_cycle < accum:
                        active_surface = surf
                        break
                cr.set_source_surface(active_surface, 808, 18)
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

        # 5. Left & Right Edge Ambient Light Strips (侧翼灯带)
        side_idx = self._side_mode_row.get_selected() if hasattr(self, '_side_mode_row') else 1
        side_mode = SIDE_LIGHT_MODES[side_idx]["id"] if hasattr(self, '_side_mode_row') and side_idx < len(SIDE_LIGHT_MODES) else 1
        side_rgba = self._side_color_btn.get_rgba() if hasattr(self, '_side_color_btn') else None
        side_base = (side_rgba.red, side_rgba.green, side_rgba.blue) if side_rgba else (0.0, 0.9, 1.0)

        if side_mode != 0 and bright_mult > 0:
            if side_mode == 1:       # 动态呼吸 (Rainbow sweeping top to bottom slowly)
                sweep_phase = (t * speed_mult * 0.35) % 1.0

                glow_pat = cairo.LinearGradient(0, 26, 0, 271)
                core_pat = cairo.LinearGradient(0, 30, 0, 267)
                for step in range(9):
                    frac = step / 8.0
                    hue = (((sweep_phase - frac * 0.85) % 1.0) * 360.0)
                    r, g, b = hsl_to_rgb(hue, 1.0, 0.5)
                    glow_pat.add_color_stop_rgba(frac, r * bright_mult, g * bright_mult, b * bright_mult, 0.45)
                    core_pat.add_color_stop_rgba(frac, min(1.0, r * bright_mult * 1.3), min(1.0, g * bright_mult * 1.3), min(1.0, b * bright_mult * 1.3), 0.95)

                # Outer diffuse glow (Left and Right)
                cr.set_source(glow_pat)
                draw_round_rect(cr, 1, 26, 12, 245, 6)
                cr.fill()
                draw_round_rect(cr, 941, 26, 12, 245, 6)
                cr.fill()

                # Core intense lightbar strip
                cr.set_source(core_pat)
                draw_round_rect(cr, 4, 30, 6, 237, 3)
                cr.fill()
                draw_round_rect(cr, 944, 30, 6, 237, 3)
                cr.fill()
            else:
                if side_mode == 2:     # 幻彩循环 (Spectrum Cycle)
                    hue = (t * speed_mult * 60.0) % 360.0
                    sr, sg, sb = hsl_to_rgb(hue, 1.0, 0.5)
                else:                  # 固定单色 (Modes 3-10: Red, Orange, Yellow, Green, Cyan, Blue, Magenta, White)
                    sr, sg, sb = side_base

                sr = max(0.0, min(1.0, sr * bright_mult))
                sg = max(0.0, min(1.0, sg * bright_mult))
                sb = max(0.0, min(1.0, sb * bright_mult))

                # Outer diffuse glow (Left and Right)
                cr.set_source_rgba(sr, sg, sb, 0.45)
                draw_round_rect(cr, 1, 26, 12, 245, 6)
                cr.fill()
                draw_round_rect(cr, 941, 26, 12, 245, 6)
                cr.fill()

                # Core intense lightbar strip
                cr.set_source_rgba(min(1.0, sr * 1.3), min(1.0, sg * 1.3), min(1.0, sb * 1.3), 0.92)
                draw_round_rect(cr, 4, 30, 6, 237, 3)
                cr.fill()
                draw_round_rect(cr, 944, 30, 6, 237, 3)
                cr.fill()

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
        elif brightness <= 0:
            brightness = self._remembered_brightness if (self._remembered_brightness and self._remembered_brightness > 0) else 4
            self._brightness_scale.set_value(brightness)

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
        elif brightness <= 0:
            brightness = self._remembered_brightness if (self._remembered_brightness and self._remembered_brightness > 0) else 4
            self._brightness_scale.set_value(brightness)

        side_idx = self._side_mode_row.get_selected() if hasattr(self, '_side_mode_row') else 1
        side_mode = SIDE_LIGHT_MODES[side_idx]["id"] if hasattr(self, '_side_mode_row') and side_idx < len(SIDE_LIGHT_MODES) else 1
        side_rgba = self._side_color_btn.get_rgba() if hasattr(self, '_side_color_btn') else None
        side_r = int(side_rgba.red * 255) if side_rgba else 0
        side_g = int(side_rgba.green * 255) if side_rgba else 229
        side_b = int(side_rgba.blue * 255) if side_rgba else 255

        sleep_idx = self._sleep_timer_row.get_selected() if hasattr(self, '_sleep_timer_row') else 0
        sleep_id = SLEEP_TIMER_MODES[sleep_idx]["id"] if sleep_idx < len(SLEEP_TIMER_MODES) else 3

        def do_light():
            ctl = LT104Controller()
            ctl.set_light(mode=mode_id, r=r, g=g, b=b, brightness=brightness, speed=speed)
            try:
                ctl.set_sleep_timer(sleep_id)
            except Exception:
                pass
            ctl.close()
            save_config({
                "mode": mode_id,
                "color": f"#{r:02x}{g:02x}{b:02x}",
                "r": r, "g": g, "b": b,
                "brightness": brightness,
                "speed": speed,
                "side_mode": side_mode,
                "side_color": f"#{side_r:02x}{side_g:02x}{side_b:02x}",
                "side_r": side_r, "side_g": side_g, "side_b": side_b,
                "sleep_timer": sleep_id
            })

        def done(_):
            btn.set_sensitive(True)
            btn.set_label("✨  即时应用并保存灯效")
            self._toast("✅  键盘背光及休眠设置已写入硬体！")

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
                self._hud_running = True
                self._load_hud_surface()
                self._preview_area.queue_draw()
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
                try:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    preset_path = os.path.join(base_dir, preset)
                    if os.path.exists(preset_path):
                        dst = os.path.join(base_dir, "static", "current_lcd.gif")
                        im = Image.open(preset_path)
                        cached_frames = [f.copy().convert("RGB").resize((62, 39), Image.Resampling.LANCZOS) for f in ImageSequence.Iterator(im)]
                        dur = im.info.get("duration", 80)
                        cached_frames[0].save(dst, save_all=True, append_images=cached_frames[1:], loop=0, duration=dur)
                        self._hud_running = False
                        self._last_lcd_mtime = 0.0
                        self._lcd_frames = []
                        self._load_lcd_surface()
                        self._preview_area.queue_draw()
                except Exception:
                    pass
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
            try:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                static_dir = os.path.join(base_dir, "static")
                os.makedirs(static_dir, exist_ok=True)
                dst = os.path.join(static_dir, "current_lcd.gif")
                im = Image.open(path)
                cached_frames = [f.copy().convert("RGB").resize((62, 39), Image.Resampling.LANCZOS) for f in ImageSequence.Iterator(im)]
                dur = im.info.get("duration", 80)
                cached_frames[0].save(dst, save_all=True, append_images=cached_frames[1:], loop=0, duration=dur)
                self._hud_running = False
                self._last_lcd_mtime = 0.0
                self._lcd_frames = []
                self._load_lcd_surface()
                self._preview_area.queue_draw()
            except Exception:
                pass

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
        win = self.get_active_window()
        if not win:
            windows = self.get_windows()
            if windows:
                win = windows[0]
        if not win:
            win = LT104Window(application=app)
        win.present()


def main():
    app = LT104App()
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()

