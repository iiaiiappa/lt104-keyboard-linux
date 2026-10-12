import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const CLI_PATH = '/home/iiaiiappa/PatProject/lt104-keyboard-linux/lt104_cli.py';
const APP_PATH = '/home/iiaiiappa/PatProject/lt104-keyboard-linux/lt104_gtk.py';

// Internationalization dictionary for all major Ubuntu languages
const EXT_I18N = {
    "en": {
        "header": "LangTu LT-104 Control",
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
        }
    },
    "zh-CN": {
        "header": "狼途 LT-104 控制",
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
        }
    },
    "zh-TW": {
        "header": "狼途 LT-104 控制",
        "sync_clock": "立即同步電腦時鐘到鍵盤小螢幕",
        "clock_synced": "鍵盤小螢幕時鐘已精準同步！",
        "sched_clock": "排程同步小螢幕時鐘 (每 12 小時)",
        "sched_on": "已開啟排程時鐘同步 (每 12 小時自動校準)",
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
        }
    },
    "ja": {
        "header": "LangTu LT-104 操作",
        "sync_clock": "PC の時計をキーボード液晶に同期",
        "clock_synced": "キーボード液晶の時計が正確に同期されました！",
        "sched_clock": "12時間ごとの自動時計同期",
        "sched_on": "12時間ごとの時計自動同期が有効になりました",
        "sched_off": "時計自動同期が無効になりました",
        "hud_toggle": "システム HUD 開始 ({sec}秒ごと)",
        "hud_stopped": "システム HUD を停止しました。",
        "hud_started": "システム HUD を開始しました ({sec}秒ごと)！",
        "hud_interval_sub": "HUD 更新間隔",
        "presets_sub": "バックライトプリセット",
        "open_app": "コントロールパネルを開く…",
        "hud_changed": "HUD: {sec}s",
        "hud_set": "HUD: {sec}s",
        "hud_once": "⚡ 今すぐ1回更新",
        "hud_once_success": "HUD テレメトリを1回更新しました",
        "presets": {
            "breathing_cyan": "ブリージングシアン",
            "static_white": "常時点灯ホワイト",
            "static_cyan": "常時点灯シアン",
            "static_magenta": "常時点灯マゼンタ",
            "static_green": "常時点灯グリーン",
            "spectrum": "スペクトラムサイクル",
            "rainbow": "レインボーウェーブ",
            "stream": "リバーストリーム",
            "off": "バックライト消灯"
        }
    },
    "ko": {
        "header": "LangTu LT-104 제어",
        "sync_clock": "컴퓨터 시계를 키보드 화면에 동기화",
        "clock_synced": "키보드 시계가 정확하게 동기화되었습니다!",
        "sched_clock": "12시간마다 시계 자동 동기화",
        "sched_on": "12시간 시계 자동 동기화 활성화됨",
        "sched_off": "시계 자동 동기화 비활성화됨",
        "hud_toggle": "시스템 HUD 시작 ({sec}초 간격)",
        "hud_stopped": "시스템 HUD가 중지되었습니다.",
        "hud_started": "시스템 HUD가 시작되었습니다 ({sec}초 간격)!",
        "hud_interval_sub": "HUD 갱신 주기",
        "presets_sub": "백라이트 프리셋",
        "open_app": "설정 패널 열기…",
        "hud_changed": "HUD: {sec}s",
        "hud_set": "HUD: {sec}s",
        "hud_once": "⚡ 지금 1회 갱신",
        "hud_once_success": "HUD 상태가 1회 갱신되었습니다",
        "presets": {
            "breathing_cyan": "브리딩 시안",
            "static_white": "고정 화이트",
            "static_cyan": "고정 시안",
            "static_magenta": "고정 마젠타",
            "static_green": "고정 그린",
            "spectrum": "스펙트럼 사이클",
            "rainbow": "레인보우 웨이브",
            "stream": "스트림 웨이브",
            "off": "백라이트 끄기"
        }
    },
    "de": {
        "header": "LangTu LT-104 Steuerung",
        "sync_clock": "Uhrzeit mit Tastatur synchronisieren",
        "clock_synced": "Tastaturuhr erfolgreich synchronisiert!",
        "sched_clock": "Automatische Zeitsynchronisation alle 12 Stunden",
        "sched_on": "Automatische Zeitsynchronisation alle 12 Stunden aktiviert",
        "sched_off": "Automatische Zeitsynchronisation deaktiviert",
        "hud_toggle": "System-HUD starten (alle {sec}s)",
        "hud_stopped": "System-HUD angehalten.",
        "hud_started": "System-HUD gestartet (Aktualisierung alle {sec}s)!",
        "hud_interval_sub": "HUD-Aktualisierungsintervall",
        "presets_sub": "Beleuchtungsvorlagen",
        "open_app": "Einstellungen öffnen…",
        "hud_changed": "HUD: {sec}s",
        "hud_set": "HUD: {sec}s",
        "hud_once": "⚡ HUD einmal aktualisieren",
        "hud_once_success": "HUD-Telemetrie einmalig aktualisiert",
        "presets": {
            "breathing_cyan": "Atmendes Cyan",
            "static_white": "Dauerhaft Weiß",
            "static_cyan": "Dauerhaft Cyan",
            "static_magenta": "Dauerhaft Magenta",
            "static_green": "Dauerhaft Grün",
            "spectrum": "Farbspektrum",
            "rainbow": "Regenbogenwelle",
            "stream": "Fluss-Welle",
            "off": "Beleuchtung aus"
        }
    },
    "fr": {
        "header": "Contrôle LangTu LT-104",
        "sync_clock": "Synchroniser l'horloge avec le clavier",
        "clock_synced": "Horloge du clavier synchronisée avec succès !",
        "sched_clock": "Synchronisation automatique toutes les 12h",
        "sched_on": "Synchronisation automatique toutes les 12h activée",
        "sched_off": "Synchronisation automatique désactivée",
        "hud_toggle": "Démarrer le HUD (toutes les {sec}s)",
        "hud_stopped": "HUD arrêté.",
        "hud_started": "HUD démarré (mise à jour toutes les {sec}s) !",
        "hud_interval_sub": "Intervalle d'actualisation du HUD",
        "presets_sub": "Préréglages d'éclairage",
        "open_app": "Ouvrir les réglages…",
        "hud_changed": "HUD: {sec}s",
        "hud_set": "HUD: {sec}s",
        "hud_once": "⚡ Mettre à jour le HUD une fois",
        "hud_once_success": "Télémétrie HUD mise à jour avec succès",
        "presets": {
            "breathing_cyan": "Cyan respirant",
            "static_white": "Blanc fixe",
            "static_cyan": "Cyan fixe",
            "static_magenta": "Magenta fixe",
            "static_green": "Vert fixe",
            "spectrum": "Spectre cyclique",
            "rainbow": "Vague arc-en-ciel",
            "stream": "Courant d'eau",
            "off": "Éteindre"
        }
    },
    "es": {
        "header": "Control LangTu LT-104",
        "sync_clock": "Sincronizar reloj con el teclado",
        "clock_synced": "¡Reloj del teclado sincronizado correctamente!",
        "sched_clock": "Sincronización automática cada 12 horas",
        "sched_on": "Sincronización automática cada 12 horas activada",
        "sched_off": "Sincronización automática desactivada",
        "hud_toggle": "Iniciar HUD del sistema (cada {sec}s)",
        "hud_stopped": "HUD detenido.",
        "hud_started": "¡HUD iniciado (actualización cada {sec}s)!",
        "hud_interval_sub": "Intervalo de actualización del HUD",
        "presets_sub": "Preajustes de luz",
        "open_app": "Abrir panel completo…",
        "hud_changed": "HUD: {sec}s",
        "hud_set": "HUD: {sec}s",
        "hud_once": "⚡ Actualizar HUD una vez",
        "hud_once_success": "Telemetría HUD actualizada con éxito",
        "presets": {
            "breathing_cyan": "Cian respiración",
            "static_white": "Blanco estático",
            "static_cyan": "Cian estático",
            "static_magenta": "Magenta estático",
            "static_green": "Verde estático",
            "spectrum": "Ciclo de espectro",
            "rainbow": "Ola arcoíris",
            "stream": "Corriente de río",
            "off": "Apagar luces"
        }
    },
    "ru": {
        "header": "Управление LangTu LT-104",
        "sync_clock": "Синхронизировать часы с клавиатурой",
        "clock_synced": "Часы клавиатуры успешно синхронизированы!",
        "sched_clock": "Автосинхронизация часов каждые 12 часов",
        "sched_on": "Автосинхронизация часов каждые 12 часов включена",
        "sched_off": "Автосинхронизация часов отключена",
        "hud_toggle": "Включить системный HUD (каждые {sec}с)",
        "hud_stopped": "Системный HUD остановлен.",
        "hud_started": "Системный HUD запущен (обновление каждые {sec}с)!",
        "hud_interval_sub": "Интервал обновления HUD",
        "presets_sub": "Пресеты подсветки",
        "open_app": "Открыть панель настроек…",
        "hud_changed": "HUD: {sec}s",
        "hud_set": "HUD: {sec}s",
        "hud_once": "⚡ Обновить HUD один раз",
        "hud_once_success": "Телеметрия HUD успешно обновлена",
        "presets": {
            "breathing_cyan": "Дыхание (Циан)",
            "static_white": "Постоянный белый",
            "static_cyan": "Постоянный циан",
            "static_magenta": "Постоянный маджента",
            "static_green": "Постоянный зеленый",
            "spectrum": "Спектральный цикл",
            "rainbow": "Радужная волна",
            "stream": "Течение реки",
            "off": "Выключить подсветку"
        }
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
    let bundle = EXT_I18N[loc] || EXT_I18N['en'];
    let str = bundle[key] || EXT_I18N['en'][key] || key;
    for (let k in vars) {
        str = str.replace('{' + k + '}', vars[k]);
    }
    return str;
}

function tPreset(presetKey, fallback) {
    let loc = getLocaleKey();
    let bundle = EXT_I18N[loc] || EXT_I18N['en'];
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
        let cmd = ['/usr/bin/python3', CLI_PATH, ...args];
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
        let proc = Gio.Subprocess.new(
            ['/usr/bin/python3', APP_PATH],
            Gio.SubprocessFlags.NONE
        );
        proc.wait_async(null, null);
    } catch (e) {
        console.error('[LT104-Indicator] Failed to launch GTK App via Subprocess: ' + e);
        try {
            let app = Gio.DesktopAppInfo.new('lt104.desktop');
            if (app) {
                app.launch([], null);
            } else {
                let appInfo = Gio.AppInfo.create_from_commandline(
                    '/usr/bin/python3 ' + APP_PATH,
                    'LT-104 Keyboard',
                    Gio.AppInfoCreateFlags.NONE
                );
                appInfo.launch([], null);
            }
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

        this._buildMenu();
    }

    _buildMenu() {
        // Title
        let headerItem = new PopupMenu.PopupMenuItem('⌨️ ' + t('header'), {reactive: false});
        this.menu.addMenuItem(headerItem);
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Quick Clock Sync
        let syncItem = new PopupMenu.PopupMenuItem('🕒 ' + t('sync_clock'));
        syncItem.connect('activate', () => {
            runCliAsync(['sync-clock'], t('clock_synced'));
        });
        this.menu.addMenuItem(syncItem);

        // 12-Hour Schedule Clock Auto-Sync
        let schedItem = new PopupMenu.PopupMenuItem('⏱️ ' + t('sched_clock'));
        schedItem.connect('activate', () => {
            try {
                let cmd = ['/usr/bin/python3', CLI_PATH, 'clock-schedule-status'];
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
        this.menu.addMenuItem(schedItem);

        // Toggle Real-time System HUD
        let currentInterval = 20;
        let hudItem = new PopupMenu.PopupMenuItem('📊 ' + t('hud_toggle', {sec: currentInterval}));

        hudItem.connect('activate', () => {
            try {
                let cmd = ['/usr/bin/python3', CLI_PATH, 'hud-status'];
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
        this.menu.addMenuItem(hudItem);

        // Update HUD Once (single-shot)
        let hudOnceItem = new PopupMenu.PopupMenuItem('⚡ ' + (t('hud_once') || 'Update HUD Once'));
        hudOnceItem.connect('activate', () => {
            runCliAsync(['hud-once'], t('hud_once_success') || 'HUD updated once successfully');
        });
        this.menu.addMenuItem(hudOnceItem);

        // Submenu: HUD Interval
        let hudIntervalSubMenu = new PopupMenu.PopupSubMenuMenuItem('⏱️ ' + t('hud_interval_sub'));
        this.menu.addMenuItem(hudIntervalSubMenu);

        const intervals = [
            {label: '5s', val: 5},
            {label: '10s', val: 10},
            {label: '20s (Default)', val: 20},
            {label: '30s', val: 30},
            {label: '60s', val: 60},
            {label: '120s (2 min - Recommended)', val: 120},
            {label: '300s (5 min - Recommended)', val: 300},
        ];

        intervals.forEach(inv => {
            let item = new PopupMenu.PopupMenuItem(inv.label);
            item.connect('activate', () => {
                currentInterval = inv.val;
                hudItem.label.set_text('📊 ' + t('hud_toggle', {sec: currentInterval}));
                try {
                    let cmd = ['/usr/bin/python3', CLI_PATH, 'hud-status'];
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
            hudIntervalSubMenu.menu.addMenuItem(item);
        });

        // Submenu: Light Presets
        let lightSubMenu = new PopupMenu.PopupSubMenuMenuItem('🌈 ' + t('presets_sub'));
        this.menu.addMenuItem(lightSubMenu);

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
                runCliAsync(['preset', p.id], '🌈 ' + localizedName);
            });
            lightSubMenu.menu.addMenuItem(item);
        });

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Launch full GUI
        let openAppItem = new PopupMenu.PopupMenuItem('⚙️ ' + t('open_app'));
        openAppItem.connect('activate', () => {
            launchApp();
        });
        this.menu.addMenuItem(openAppItem);
    }
});

export default class LT104Extension extends Extension {
    enable() {
        this._indicator = new LT104Indicator();
        Main.panel.addToStatusArea(this.uuid, this._indicator);
    }

    disable() {
        if (this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }
    }
}
