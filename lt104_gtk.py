#!/usr/bin/env python3
"""
LT-104 Keyboard Control Centre — GTK4 + libadwaita native GNOME app.
Reuses lt104_core.py directly (no web server needed).
"""
import sys
import os
import threading
import tempfile

# Make sure we can import lt104_core from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Adw, Gdk, GLib, Gio, GdkPixbuf

from lt104_core import LT104Controller, LIGHT_MODES, find_lt104_usb, find_lt104_lcd_hidraw
from config import load_config, save_config

APP_ID = "com.theforwardway.lt104"
CLI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lt104_cli.py")


# --------------------------------------------------------------------------- #
#  Helpers                                                                      #
# --------------------------------------------------------------------------- #

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

        # Mode selector
        self._mode_row = Adw.ComboRow()
        self._mode_row.set_title("灯光模式")
        mode_strings = Gtk.StringList.new([m["name"] for m in LIGHT_MODES])
        self._mode_row.set_model(mode_strings)
        initial_mode_idx = max(0, min(len(LIGHT_MODES)-1, int(cfg.get("mode", 1)) - 1))
        self._mode_row.set_selected(initial_mode_idx)
        self._mode_row.connect("notify::selected", self._on_mode_changed)
        group.add(self._mode_row)

        # Colour button row
        color_row = Adw.ActionRow()
        color_row.set_title("自订颜色")
        color_row.set_subtitle("点击色块选择")
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
        color_row.add_suffix(self._color_btn)
        group.add(color_row)

        # Colour presets
        presets_row = Adw.ActionRow()
        presets_row.set_title("快速颜色")
        preset_box = Gtk.Box(spacing=8)
        preset_box.set_valign(Gtk.Align.CENTER)
        preset_colors = [
            ("#ff0055", "品红"), ("#00e5ff", "青蓝"), ("#00e676", "翠绿"),
            ("#ffd600", "亮黄"), ("#d500f9", "紫色"), ("#ff3d00", "橙红"),
            ("#ffffff", "纯白"),
        ]
        css = Gtk.CssProvider()
        css_rules = []
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

        presets_row.add_suffix(preset_box)
        group.add(presets_row)

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
        group.add(speed_row)

        # Apply button
        apply_btn = Gtk.Button(label="✨  即时应用并保存灯效")
        apply_btn.add_css_class("suggested-action")
        apply_btn.add_css_class("pill")
        apply_btn.set_margin_top(8)
        apply_btn.connect("clicked", self._on_apply_light)
        group.add(apply_btn)

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
            "20 秒 (默认推荐)",
            "30 秒 (省电)",
            "60 秒 (超慢)",
            "120 秒 (2分钟)",
            "300 秒 (5分钟)"
        ])
        self._interval_row.set_model(model)
        cfg = load_config()
        initial_inv = float(cfg.get("hud_interval", 20.0))
        sel_idx = 3  # Index 3 is 20s default
        for idx, inv in enumerate(self._interval_intervals):
            if abs(inv - initial_inv) < 0.1:
                sel_idx = idx
                break
        self._interval_row.set_selected(sel_idx)
        self._interval_row.connect("notify::selected", self._on_interval_changed)
        group.add(self._interval_row)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(4)

        # Buttons Row: Toggle & Once
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._hud_btn = Gtk.Button(label="📊  开启即时系统 HUD (每20秒更新)")
        self._hud_btn.add_css_class("pill")
        self._hud_btn.set_hexpand(True)
        self._hud_btn.connect("clicked", self._on_toggle_hud)
        btn_box.append(self._hud_btn)

        self._hud_once_btn = Gtk.Button(label="⚡  立即单次刷新")
        self._hud_once_btn.add_css_class("pill")
        self._hud_once_btn.connect("clicked", self._on_hud_once)
        btn_box.append(self._hud_once_btn)
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
            sec = self._interval_intervals[idx] if idx < len(self._interval_intervals) else 20
            if running:
                self._hud_btn.set_label(f"⏹️  停止系统 HUD (运行中，每{sec}秒更新)")
                self._hud_btn.remove_css_class("suggested-action")
                self._hud_btn.add_css_class("destructive-action")
            else:
                self._hud_btn.set_label(f"📊  开启即时系统 HUD (每{sec}秒更新)")
                self._hud_btn.remove_css_class("destructive-action")
                self._hud_btn.add_css_class("suggested-action")
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

    def _on_mode_changed(self, row, param):
        mode_idx = self._mode_row.get_selected()
        if mode_idx < len(LIGHT_MODES) and LIGHT_MODES[mode_idx]["id"] == 20:
            self._brightness_scale.set_value(0)

    def _on_preset_clicked(self, btn, hex_c):
        rgba = Gdk.RGBA()
        rgba.parse(hex_c)
        self._color_btn.set_rgba(rgba)

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

