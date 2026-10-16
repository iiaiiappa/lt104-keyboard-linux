import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

function findCliPath() {
    let candidates = [
        '/home/iiaiiappa/PatProject/lt104-keyboard-linux/lt104_cli.py',
        '/usr/bin/lt104-cli',
        '/usr/local/bin/lt104-cli',
        '/opt/lt104-keyboard-linux/lt104_cli.py',
    ];
    for (let p of candidates) {
        if (GLib.file_test(p, GLib.FileTest.EXISTS)) {
            return p;
        }
    }
    return 'lt104-cli';
}

function findAppPath() {
    let candidates = [
        '/home/iiaiiappa/PatProject/lt104-keyboard-linux/lt104_gtk.py',
        '/usr/bin/lt104',
        '/usr/local/bin/lt104',
        '/opt/lt104-keyboard-linux/lt104_gtk.py',
    ];
    for (let p of candidates) {
        if (GLib.file_test(p, GLib.FileTest.EXISTS)) {
            return p;
        }
    }
    return 'lt104';
}

function setItemEnabledAndVisible(item, enabled) {
    if (!item) return;
    item.visible = enabled;
    item.reactive = enabled;
    item.can_focus = enabled;
    if (item.actor) {
        item.actor.visible = enabled;
        item.actor.reactive = enabled;
        item.actor.can_focus = enabled;
    }
    if (item.menu) {
        if (item.menu.actor) {
            item.menu.actor.visible = enabled;
            item.menu.actor.reactive = enabled;
        }
        if (item.menu.box) {
            item.menu.box.visible = enabled;
            item.menu.box.reactive = enabled;
        }
        if (item.menu._getMenuItems) {
            item.menu._getMenuItems().forEach(sub => {
                sub.reactive = enabled;
                sub.can_focus = enabled;
                if (sub.actor) {
                    sub.actor.reactive = enabled;
                    sub.actor.can_focus = enabled;
                }
            });
        }
    }
}

// Internationalization dictionary for all major Ubuntu languages
const EXT_I18N = {
    "en": {
        "header": "LangTu LT-104 Control",
        "mode_cable": "🔌 Mode: USB Cable (Connected)",
        "mode_bt": "📶 Mode: Bluetooth ({name})",
        "mode_dongle": "📡 Mode: 2.4G Wireless Dongle",
        "mode_disconnected": "❌ Mode: Keyboard Disconnected",
        "battery_label": "🔋 Battery: {pct}%",
        "battery_cable_power": "⚡ Power: USB Cable Powered",
        "battery_reading": "🔋 Battery: Reading…",
        "locked_banner": "🔒 Hardware controls locked (Requires USB Cable)",
        "sync_clock": "Sync Clock to Keyboard LCD",
        "clock_synced": "Keyboard LCD clock synchronized accurately!",
        "sched_clock": "Auto-Sync Clock Every 12 Hours",
        "sched_on": "Clock auto-sync enabled (every 12 hours)",
        "sched_off": "Clock auto-sync disabled",
        "hud_toggle": "Start Real-time System HUD (Every {sec}s)",
        "hud_stopped": "System HUD stopped.",
        "hud_started": "System HUD started (updating every {sec}s)!",
        "hud_interval_sub": "HUD Refresh Interval",
        "presets_sub": "Backlight Presets",
        "open_app": "Open Full Control Center...",
        "hud_changed": "HUD: {sec}s",
        "hud_set": "HUD: {sec}s",
        "hud_once": "⚡ Update HUD Once",
        "hud_once_success": "HUD telemetry updated once successfully",
        "presets": {
            "breathing_cyan": "Breathing Cyan",
            "static_white": "Static White",
            "static_cyan": "Static Cyan",
            "static_magenta": "Static Magenta",
            "static_green": "Static Green",
            "spectrum": "Spectrum Cycle",
            "rainbow": "Rainbow Wave",
            "stream": "River Stream",
            "off": "Turn Off Backlight"
        },
        "shortcuts_ref": "Shortcuts Reference",
        "open_product_page": "Open LT-104 Product Page"
    },
    "zh-CN": {
        "header": "狼途 LT-104 控制",
        "mode_cable": "🔌 连接模式: USB 有线模式 (已连通)",
        "mode_bt": "📶 连接模式: 蓝牙无线模式 ({name})",
        "mode_dongle": "📡 连接模式: 2.4G 无线接收器模式",
        "mode_disconnected": "❌ 连接模式: 键盘未连接",
        "battery_label": "🔋 键盘电量: {pct}%",
        "battery_cable_power": "⚡ 供电状态: USB 有线供电",
        "battery_reading": "🔋 键盘电量: 读取中…",
        "locked_banner": "🔒 硬件配置已锁定 (需连接 USB 数据线)",
        "sync_clock": "立即同步电脑时钟到键盘小屏幕",
        "clock_synced": "键盘小屏幕时钟已精准同步！",
        "sched_clock": "定时同步小屏幕时钟 (每 12 小时)",
        "sched_on": "已开启定时时钟同步 (每 12 小时自动校准)",
        "sched_off": "已停用定时时钟同步",
        "hud_toggle": "开启即时系统 HUD (每{sec}秒更新)",
        "hud_stopped": "系统 HUD 已停止。",
        "hud_started": "系统 HUD 已启动 (每{sec}秒更新)！",
        "hud_interval_sub": "HUD 刷新间隔",
        "presets_sub": "背光灯效预设",
        "open_app": "打开完整设置面板…",
        "hud_changed": "HUD: {sec}s",
        "hud_set": "HUD: {sec}s",
        "hud_once": "⚡ 立即单次刷新 HUD",
        "hud_once_success": "HUD 遥测已成功单次推送到屏幕",
        "presets": {
            "breathing_cyan": "呼吸青蓝",
            "static_white": "常亮纯白",
            "static_cyan": "常亮青蓝",
            "static_magenta": "常亮品红",
            "static_green": "常亮翠绿",
            "spectrum": "光谱循环",
            "rainbow": "彩泉涌动",
            "stream": "随波逐流",
            "off": "关闭背光"
        },
        "shortcuts_ref": "快捷键参考",
        "open_product_page": "打开 LT-104 产品页面"
    },
    "zh-TW": {
        "header": "狼途 LT-104 控制",
        "mode_cable": "🔌 連線模式: USB 有線模式 (已連線)",
        "mode_bt": "📶 連線模式: 藍牙無線模式 ({name})",
        "mode_dongle": "📡 連線模式: 2.4G 無線接收器模式",
        "mode_disconnected": "❌ 連線模式: 鍵盤未連線",
        "battery_label": "🔋 鍵盤電量: {pct}%",
        "battery_cable_power": "⚡ 供電狀態: USB 有線供電",
        "battery_reading": "🔋 鍵盤電量: 讀取中…",
        "locked_banner": "🔒 硬體設定已鎖定 (需連接 USB 傳輸線)",
        "sync_clock": "立即同步電腦時鐘到鍵盤小螢幕",
        "clock_synced": "鍵盤小螢幕時鐘已精準同步！",
        "sched_clock": "排程同步小螢幕時鐘 (每 12 小時)",
        "sched_on": "已開啟排程時鐘同步 (每 12 小時自動校准)",
        "sched_off": "已停用排程時鐘同步",
        "hud_toggle": "開啟即時系統 HUD (每{sec}秒更新)",
        "hud_stopped": "系統 HUD 已停止。",
        "hud_started": "系統 HUD 已啟動 (每{sec}秒更新)！",
        "hud_interval_sub": "HUD 重新整理間隔",
        "presets_sub": "背光燈效預設",
        "open_app": "打開完整設定面板…",
        "hud_changed": "HUD: {sec}s",
        "hud_set": "HUD: {sec}s",
        "hud_once": "⚡ 立即單次重新整理 HUD",
        "hud_once_success": "HUD 遙測已成功單次推送到螢幕",
        "presets": {
            "breathing_cyan": "呼吸青藍",
            "static_white": "常亮純白",
            "static_cyan": "常亮青藍",
            "static_magenta": "常亮洋紅",
            "static_green": "常亮翠綠",
            "spectrum": "光譜循環",
            "rainbow": "彩泉湧動",
            "stream": "隨波逐流",
            "off": "關閉背光"
        },
        "shortcuts_ref": "快捷鍵參考",
        "open_product_page": "開啟 LT-104 產品頁面"
    }
};

function getLocaleKey() {
    let lang = GLib.getenv('LANG') || GLib.getenv('LC_ALL') || 'en';
    if (lang.includes('.')) lang = lang.split('.')[0];
    if (EXT_I18N[lang]) return lang;
    if (lang.startsWith('zh')) return (lang.includes('TW') || lang.includes('HK')) ? 'zh-TW' : 'zh-CN';
    let short = lang.split('_')[0];
    if (EXT_I18N[short]) return short;
    return 'en';
}

function t(key, vars = {}) {
    let loc = getLocaleKey();
    let bundle = EXT_I18N[loc] || EXT_I18N['en'] || {};
    let str = bundle[key] || (EXT_I18N['en'] && EXT_I18N['en'][key]) || key;
    for (let k in vars) {
        str = str.replace('{' + k + '}', vars[k]);
    }
    return str;
}

function tPreset(presetKey, fallback) {
    let loc = getLocaleKey();
    let bundle = EXT_I18N[loc] || EXT_I18N['en'] || {};
    if (bundle && bundle.presets && bundle.presets[presetKey]) {
        return bundle.presets[presetKey];
    }
    if (EXT_I18N['en'] && EXT_I18N['en'].presets && EXT_I18N['en'].presets[presetKey]) {
        return EXT_I18N['en'].presets[presetKey];
    }
    return fallback;
}

function runCliAsync(args, successNotifyMsg = null) {
    try {
        let cliPath = findCliPath();
        let cmd = ['/usr/bin/python3', cliPath, ...args];
        let proc = Gio.Subprocess.new(cmd, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
        proc.communicate_utf8_async(null, null, (p, res) => {
            try {
                let [, stdout, stderr] = p.communicate_utf8_finish(res);
                if (successNotifyMsg) {
                    Main.notify('LT-104', successNotifyMsg);
                }
            } catch (e) {
                console.error('[LT104-Indicator] CLI error: ' + e);
            }
        });
    } catch (e) {
        console.error('[LT104-Indicator] Failed to run CLI: ' + e);
    }
}

function launchApp() {
    try {
        let app = Gio.DesktopAppInfo.new('lt104.desktop');
        if (app) {
            app.launch([], null);
            return;
        }
    } catch (e) {
        console.warn('[LT104-Indicator] DesktopAppInfo launch warning: ' + e);
    }

    let appPath = findAppPath();
    try {
        let proc = Gio.Subprocess.new(
            ['/usr/bin/python3', appPath],
            Gio.SubprocessFlags.NONE
        );
        proc.wait_async(null, null);
    } catch (e) {
        console.error('[LT104-Indicator] Subprocess launch failed: ' + e);
        try {
            let appInfo = Gio.AppInfo.create_from_commandline(
                '/usr/bin/python3 ' + appPath,
                'LT-104 Keyboard',
                Gio.AppInfoCreateFlags.NONE
            );
            appInfo.launch([], null);
        } catch (e2) {
            console.error('[LT104-Indicator] Fallback launch failed: ' + e2);
        }
    }
}

const LT104Indicator = GObject.registerClass(
class LT104Indicator extends PanelMenu.Button {
    _init() {
        super._init(0.0, 'LT104 Indicator');

        let icon = new St.Icon({
            icon_name: 'input-keyboard-symbolic',
            style_class: 'system-status-icon',
        });
        this.add_child(icon);

        if (this.menu && this.menu.box) {
            this.menu.box.add_style_class_name('lt104-menu-box');
            this.menu.box.set_style('min-width: 330px; max-height: 980px;');
        }
        if (this.menu && this.menu.actor) {
            this.menu.actor.add_style_class_name('lt104-menu-box');
            this.menu.actor.set_style('max-height: 980px;');
        }

        this._isCableMode = false;
        this._buildMenu();
        this._refreshStatusAsync();

        // Refresh dynamic status and hide/show controls whenever the menu is clicked open
        this._openStateId = this.menu.connect('open-state-changed', (m, open) => {
            if (open) {
                this._refreshStatusAsync();
            }
        });

        // Periodic background poll every 5s to reflect hotplugged / switched state
        this._timerId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 5, () => {
            this._refreshStatusAsync();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _buildMenu() {
        // Title
        let headerItem = new PopupMenu.PopupMenuItem('⌨️ ' + t('header'), {reactive: false});
        this.menu.addMenuItem(headerItem);

        // Connection Mode Status
        this._modeItem = new PopupMenu.PopupMenuItem(t('mode_cable'), {reactive: false});
        this._modeItem.add_style_class_name('lt104-status-mode');
        this.menu.addMenuItem(this._modeItem);

        // Bluetooth Battery % / Power state
        this._batteryItem = new PopupMenu.PopupMenuItem(t('battery_cable_power'), {reactive: false});
        this._batteryItem.add_style_class_name('lt104-status-battery');
        this.menu.addMenuItem(this._batteryItem);

        // Locked Banner (visible only when not in USB cable mode)
        this._lockedBannerItem = new PopupMenu.PopupMenuItem(t('locked_banner'), {reactive: false});
        this._lockedBannerItem.add_style_class_name('lt104-locked-banner');
        setItemEnabledAndVisible(this._lockedBannerItem, false);
        this.menu.addMenuItem(this._lockedBannerItem);

        // Separator between status and cable-only items
        this._cableSep1 = new PopupMenu.PopupSeparatorMenuItem();
        this.menu.addMenuItem(this._cableSep1);

        // --- USB CABLE ONLY ITEMS START ---

        // Quick Clock Sync
        this._syncItem = new PopupMenu.PopupMenuItem('🕒 ' + t('sync_clock'));
        this._syncItem.connect('activate', () => {
            if (!this._isCableMode) {
                Main.notify('LT-104', t('locked_banner'));
                return;
            }
            runCliAsync(['sync-clock'], t('clock_synced'));
        });
        this.menu.addMenuItem(this._syncItem);

        // 12-Hour Schedule Clock Auto-Sync
        this._schedItem = new PopupMenu.PopupMenuItem('⏱️ ' + t('sched_clock'));
        this._schedItem.connect('activate', () => {
            if (!this._isCableMode) {
                Main.notify('LT-104', t('locked_banner'));
                return;
            }
            try {
                let cliPath = findCliPath();
                let cmd = ['/usr/bin/python3', cliPath, 'clock-schedule-status'];
                let [ok, out] = GLib.spawn_command_line_sync(cmd.join(' '));
                let statusStr = new TextDecoder().decode(out);
                if (statusStr.includes('ENABLED')) {
                    runCliAsync(['clock-schedule-disable'], t('sched_off'));
                } else {
                    runCliAsync(['clock-schedule-enable'], t('sched_on'));
                }
            } catch (e) {
                console.error('[LT104-Indicator] Clock schedule toggle failed: ' + e);
            }
        });
        this.menu.addMenuItem(this._schedItem);

        // Toggle Real-time System HUD
        let currentInterval = 120;
        this._hudItem = new PopupMenu.PopupMenuItem('📊 ' + t('hud_toggle', {sec: currentInterval}));
        this._hudItem.connect('activate', () => {
            if (!this._isCableMode) {
                Main.notify('LT-104', t('locked_banner'));
                return;
            }
            try {
                let cliPath = findCliPath();
                let cmd = ['/usr/bin/python3', cliPath, 'hud-status'];
                let [ok, out] = GLib.spawn_command_line_sync(cmd.join(' '));
                let statusStr = new TextDecoder().decode(out);
                if (statusStr.includes('RUNNING')) {
                    runCliAsync(['hud-stop'], t('hud_stopped'));
                } else {
                    runCliAsync(['hud-start', '--interval', String(currentInterval)], t('hud_started', {sec: currentInterval}));
                }
            } catch (e) {
                console.error('[LT104-Indicator] HUD toggle failed: ' + e);
            }
        });
        this.menu.addMenuItem(this._hudItem);

        // Update HUD Once (single-shot)
        this._hudOnceItem = new PopupMenu.PopupMenuItem('⚡ ' + (t('hud_once') || 'Update HUD Once'));
        this._hudOnceItem.connect('activate', () => {
            if (!this._isCableMode) {
                Main.notify('LT-104', t('locked_banner'));
                return;
            }
            runCliAsync(['hud-once'], t('hud_once_success') || 'HUD updated once successfully');
        });
        this.menu.addMenuItem(this._hudOnceItem);

        // Submenu: HUD Interval
        this._hudIntervalSubMenu = new PopupMenu.PopupSubMenuMenuItem('⏱️ ' + t('hud_interval_sub'));
        this.menu.addMenuItem(this._hudIntervalSubMenu);

        const intervals = [
            {label: '5s', val: 5},
            {label: '10s', val: 10},
            {label: '20s', val: 20},
            {label: '30s', val: 30},
            {label: '60s', val: 60},
            {label: '120s (2 min - Default)', val: 120},
            {label: '300s (5 min - Power Saving)', val: 300},
        ];

        intervals.forEach(inv => {
            let item = new PopupMenu.PopupMenuItem(inv.label);
            item.connect('activate', () => {
                if (!this._isCableMode) {
                    Main.notify('LT-104', t('locked_banner'));
                    return;
                }
                currentInterval = inv.val;
                this._hudItem.label.set_text('📊 ' + t('hud_toggle', {sec: currentInterval}));
                try {
                    let cliPath = findCliPath();
                    let cmd = ['/usr/bin/python3', cliPath, 'hud-status'];
                    let [ok, out] = GLib.spawn_command_line_sync(cmd.join(' '));
                    let statusStr = new TextDecoder().decode(out);
                    if (statusStr.includes('RUNNING')) {
                        runCliAsync(['hud-stop']);
                        runCliAsync(['hud-start', '--interval', String(currentInterval)], t('hud_changed', {sec: currentInterval}));
                    } else {
                        Main.notify('LT-104', t('hud_set', {sec: currentInterval}));
                    }
                } catch (e) {
                    console.error('[LT104-Indicator] HUD interval switch failed: ' + e);
                }
            });
            this._hudIntervalSubMenu.menu.addMenuItem(item);
        });

        // Submenu: Light Presets
        this._lightSubMenu = new PopupMenu.PopupSubMenuMenuItem('🌈 ' + t('presets_sub'));
        this.menu.addMenuItem(this._lightSubMenu);

        const presets = [
            {key: 'breathing_cyan', id: 'breathing-cyan', fallback: 'Breathing Cyan'},
            {key: 'static_white', id: 'static-white', fallback: 'Static White'},
            {key: 'static_cyan', id: 'static-cyan', fallback: 'Static Cyan'},
            {key: 'static_magenta', id: 'static-magenta', fallback: 'Static Magenta'},
            {key: 'static_green', id: 'static-green', fallback: 'Static Green'},
            {key: 'spectrum', id: 'spectrum', fallback: 'Spectrum Cycle'},
            {key: 'rainbow', id: 'rainbow', fallback: 'Rainbow Wave'},
            {key: 'stream', id: 'stream', fallback: 'River Stream'},
            {key: 'off', id: 'off', fallback: 'Turn Off'},
        ];

        presets.forEach(p => {
            let localizedName = tPreset(p.key, p.fallback);
            let item = new PopupMenu.PopupMenuItem(localizedName);
            item.connect('activate', () => {
                if (!this._isCableMode) {
                    Main.notify('LT-104', t('locked_banner'));
                    return;
                }
                runCliAsync(['preset', p.id], '🌈 ' + localizedName);
            });
            this._lightSubMenu.menu.addMenuItem(item);
        });

        // Separator after cable-only items
        this._cableSep2 = new PopupMenu.PopupSeparatorMenuItem();
        this.menu.addMenuItem(this._cableSep2);

        // Group cable-only items together for toggling & disabling
        this._cableItems = [
            this._cableSep1,
            this._syncItem,
            this._schedItem,
            this._hudItem,
            this._hudOnceItem,
            this._hudIntervalSubMenu,
            this._lightSubMenu,
            this._cableSep2,
        ];

        // Safely initialize with all cable items disabled and hidden until status-json confirms USB cable mode
        this._isCableMode = false;
        this._cableItems.forEach(item => {
            setItemEnabledAndVisible(item, false);
        });

        // --- USB CABLE ONLY ITEMS END ---

        // Shortcuts Reference submenu (Always visible)
        this._scSubMenu = new PopupMenu.PopupSubMenuMenuItem('⌨️ ' + (t('shortcuts_ref') || 'Shortcuts Reference'));
        this.menu.addMenuItem(this._scSubMenu);

        const SHORTCUTS = [
            ['🐧 Ubuntu Linux', 'Suggest to use Win mode (建议使用 Win 模式)'],
            ['Fn+F1', 'Settings > Displays (设置 > 显示器)'],
            ['Fn+F2', 'Calculator (计算器)'],
            ['Fn+F3', 'Same as WIN + TAB (Task Switch 任务切换)'],
            ['Fn+F4', 'Nothing Happened (无反应)'],
            ['Fn+F5', 'Backlight Brightness − (背光亮度 −)'],
            ['Fn+F6', 'Backlight Brightness + (背光亮度 +)'],
            ['Fn+F7', 'Previous Track (上一曲)'],
            ['Fn+F8', 'Play / Pause (播放 / 暂停)'],
            ['Fn+F9', 'Next Track (下一曲)'],
            ['Fn+F10', 'Mute / Unmute (静音 / 取消静音)'],
            ['Fn+F11', 'Volume − (音量 −)'],
            ['Fn+F12', 'Volume + (音量 +)'],
            ['Fn+WIN', 'Lock WIN Key (锁定 WIN 键)'],
            ['── Common ──', ''],
            ['Fn+Esc (3s)', 'Restore Factory Settings (恢复出厂设置)'],
            ['Fn+Ins', 'Side Backlight: cycle mode & color (两侧边光切换)'],
            ['Fn+Q', '2.4G Mode (2.4G 模式)'],
            ['Fn+W/E/R', 'Bluetooth 1/2/3 (蓝牙模式)'],
            ['Fn+T', 'Wired Mode (有线模式)'],
            ['Fn+Knob', 'Toggle main / volume screen (切换主界面与音量显示)'],
        ];

        SHORTCUTS.forEach(([key, action]) => {
            if (!action) {
                this._scSubMenu.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
                return;
            }
            let labelText = (key.startsWith('🐧') ? key + ' (' + action + ')' : key + '  →  ' + action);
            let item = new PopupMenu.PopupMenuItem(labelText, {reactive: false});
            item.label.get_clutter_text().set_use_markup(false);
            this._scSubMenu.menu.addMenuItem(item);
        });

        // Product page link (Always visible)
        this._productItem = new PopupMenu.PopupMenuItem('🛍️ ' + (t('open_product_page') || 'Open LT-104 Product Page'));
        this._productItem.connect('activate', () => {
            try {
                Gio.AppInfo.launch_default_for_uri(
                    'https://langtustore.com/collections/mechanical-keyboards/products/langtu-lt-104-rgb-tri-mode-mechanical-gaming-keyboard',
                    null
                );
            } catch (e) {
                console.error('[LT104-Indicator] Failed to open product URL: ' + e);
            }
        });
        this.menu.addMenuItem(this._productItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Launch full GUI (Always visible)
        this._openAppItem = new PopupMenu.PopupMenuItem('⚙️ ' + t('open_app'));
        this._openAppItem.connect('activate', () => {
            launchApp();
        });
        this.menu.addMenuItem(this._openAppItem);
    }

    _refreshStatusAsync() {
        try {
            let cliPath = findCliPath();
            let cmd = ['/usr/bin/python3', cliPath, 'status-json'];
            let proc = Gio.Subprocess.new(cmd, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
            proc.communicate_utf8_async(null, null, (p, res) => {
                try {
                    let [, stdout, stderr] = p.communicate_utf8_finish(res);
                    if (stdout && stdout.trim()) {
                        let info = JSON.parse(stdout.trim());
                        this._updateStatus(info);
                    }
                } catch (e) {
                    console.error('[LT104-Indicator] Status JSON parse error: ' + e);
                }
            });
        } catch (e) {
            console.error('[LT104-Indicator] Failed to query status: ' + e);
        }
    }

    _updateStatus(info) {
        if (!info) return;

        let mode = info.mode || 'disconnected';
        let isCable = (mode === 'usb_cable' && info.can_configure !== false);
        this._isCableMode = isCable;

        // 1. Update Connection Mode Label
        if (isCable) {
            this._modeItem.label.set_text(t('mode_cable'));
        } else if (mode === 'bluetooth') {
            let name = info.device_name || 'LT104 BT5.1_2';
            this._modeItem.label.set_text(t('mode_bt', {name: name}));
        } else if (mode === 'usb_dongle') {
            let desc = (info.dongle_status === 'plugged_unlinked') ? ' (未配对)' : '';
            this._modeItem.label.set_text(t('mode_dongle') + desc);
        } else {
            this._modeItem.label.set_text(t('mode_disconnected'));
        }

        // 2. Update Battery % / Power State
        if (info.battery !== null && info.battery !== undefined) {
            this._batteryItem.label.set_text(t('battery_label', {pct: String(info.battery)}));
            setItemEnabledAndVisible(this._batteryItem, true);
        } else if (mode === 'bluetooth') {
            this._batteryItem.label.set_text(t('battery_reading'));
            setItemEnabledAndVisible(this._batteryItem, true);
        } else if (isCable) {
            this._batteryItem.label.set_text(t('battery_cable_power'));
            setItemEnabledAndVisible(this._batteryItem, true);
        } else {
            setItemEnabledAndVisible(this._batteryItem, false);
        }

        // 3. Toggle Locked Banner (shown when NOT in USB cable mode)
        setItemEnabledAndVisible(this._lockedBannerItem, !isCable);

        // 4. Toggle & Disable USB Cable Only Items (Clock Sync, Sched, HUD, Light Presets)
        if (this._cableItems) {
            this._cableItems.forEach(item => {
                setItemEnabledAndVisible(item, isCable);
            });
        }
    }

    destroy() {
        if (this._timerId) {
            GLib.source_remove(this._timerId);
            this._timerId = null;
        }
        if (this._openStateId) {
            this.menu.disconnect(this._openStateId);
            this._openStateId = null;
        }
        super.destroy();
    }
});

export class LT104IndicatorImpl {
    constructor(extension) {
        this._extension = extension;
        this._indicator = null;
    }

    enable() {
        this._indicator = new LT104Indicator();
        Main.panel.addToStatusArea(this._extension.uuid, this._indicator);
    }

    disable() {
        if (this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }
    }
}
