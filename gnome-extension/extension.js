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
    'en': {
        header: 'LangTu LT-104 Control',
        sync_clock: 'Sync Clock to Keyboard LCD',
        clock_synced: 'Clock synchronization sent!',
        sched_clock: 'Auto-Sync Clock Every 12 Hours',
        sched_on: 'Clock auto-sync enabled (every 12 hours)',
        sched_off: 'Clock auto-sync disabled',
        hud_toggle: 'Start/Stop System HUD ({sec}s)',
        hud_stopped: 'Keyboard System HUD stopped',
        hud_started: 'Keyboard System HUD started ({sec}s)',
        hud_interval_sub: 'HUD Refresh Interval',
        presets_sub: 'Backlight Presets',
        open_app: 'Open Full Control Center...',
        hud_changed: 'HUD refresh interval set to {sec}s',
        hud_set: 'Next HUD start set to {sec}s',
        hud_once: 'Update HUD Once',
        hud_once_success: 'HUD telemetry updated once successfully'
    },
    'zh-CN': {
        header: '狼途 LT-104 控制',
        sync_clock: '同步时钟到小屏幕',
        clock_synced: '已发送小屏幕时间同步指令！',
        sched_clock: '定时同步时钟 (每 12 小时)',
        sched_on: '已开启定时时钟同步 (每 12 小时)',
        sched_off: '已停用定时时钟同步',
        hud_toggle: '启动/停止系统 HUD ({sec}秒)',
        hud_stopped: '已停止键盘小屏幕系统 HUD',
        hud_started: '已开启键盘小屏幕系统 HUD（每{sec}秒更新）',
        hud_interval_sub: 'HUD 刷新间隔',
        presets_sub: '背光灯效预设',
        open_app: '打开完整设置面板…',
        hud_changed: 'HUD 刷新间隔已切换为 {sec} 秒',
        hud_set: '已设定下次启动间隔为 {sec} 秒',
        hud_once: '立即单次刷新 HUD',
        hud_once_success: 'HUD 遥测已单次刷新成功'
    },
    'zh-TW': {
        header: '狼途 LT-104 控制',
        sync_clock: '同步時鐘到小螢幕',
        clock_synced: '已發送小螢幕時間同步指令！',
        sched_clock: '排程同步時鐘 (每 12 小時)',
        sched_on: '已開啟排程時鐘同步 (每 12 小時)',
        sched_off: '已停用排程時鐘同步',
        hud_toggle: '啟動/停止系統 HUD ({sec}秒)',
        hud_stopped: '已停止鍵盤小螢幕系統 HUD',
        hud_started: '已開啟鍵盤小螢幕系統 HUD（每{sec}秒更新）',
        hud_interval_sub: 'HUD 重新整理間隔',
        presets_sub: '背光燈效預設',
        open_app: '打開完整設定面板…',
        hud_changed: 'HUD 重新整理間隔已切換為 {sec} 秒',
        hud_set: '已設定下次啟動間隔為 {sec} 秒',
        hud_once: '立即單次重新整理 HUD',
        hud_once_success: 'HUD 遙測已單次重新整理成功'
    },
    'ja': {
        header: 'LangTu LT-104 操作',
        sync_clock: 'PC の時計をキーボード液晶に同期',
        clock_synced: '時計同期コマンドを送信しました！',
        sched_clock: '12時間ごとの自動時計同期',
        sched_on: '12時間ごとの時計自動同期が有効になりました',
        sched_off: '時計自動同期が無効になりました',
        hud_toggle: 'システム HUD 開始/停止 ({sec}秒)',
        hud_stopped: 'システム HUD を停止しました',
        hud_started: 'システム HUD を開始しました ({sec}秒ごと)',
        hud_interval_sub: 'HUD 更新間隔',
        presets_sub: 'バックライトプリセット',
        open_app: 'コントロールパネルを開く…',
        hud_changed: 'HUD 更新間隔を {sec} 秒に変更しました',
        hud_set: '次回の開始間隔を {sec} 秒に設定しました',
        hud_once: 'HUD を1回だけ更新',
        hud_once_success: 'HUD の更新が完了しました'
    },
    'ko': {
        header: 'LangTu LT-104 제어',
        sync_clock: '컴퓨터 시계를 키보드 화면에 동기화',
        clock_synced: '시계 동기화 명령이 전송되었습니다!',
        sched_clock: '12시간마다 시계 자동 동기화',
        sched_on: '12시간 시계 자동 동기화 활성화됨',
        sched_off: '시계 자동 동기화 비활성화됨',
        hud_toggle: '시스템 HUD 시작/중지 ({sec}초)',
        hud_stopped: '키보드 시스템 HUD가 중지되었습니다',
        hud_started: '키보드 시스템 HUD가 시작되었습니다 ({sec}초 간격)',
        hud_interval_sub: 'HUD 갱신 주기',
        presets_sub: '백라이트 프리셋',
        open_app: '설정 패널 열기…',
        hud_changed: 'HUD 갱신 주기가 {sec}초로 변경되었습니다',
        hud_set: '다음 시작 주기가 {sec}초로 설정되었습니다',
        hud_once: 'HUD 1회 갱신',
        hud_once_success: 'HUD 텔레메트리가 성공적으로 1회 갱신되었습니다'
    },
    'de': {
        header: 'LangTu LT-104 Steuerung',
        sync_clock: 'Uhrzeit mit Tastatur synchronisieren',
        clock_synced: 'Zeitsynchronisation gesendet!',
        sched_clock: 'Automatische Zeitsynchronisation alle 12h',
        sched_on: 'Automatische Zeitsynchronisation alle 12h aktiviert',
        sched_off: 'Automatische Zeitsynchronisation deaktiviert',
        hud_toggle: 'System-HUD starten/stoppen ({sec}s)',
        hud_stopped: 'System-HUD angehalten',
        hud_started: 'System-HUD gestartet ({sec}s)',
        hud_interval_sub: 'HUD-Intervall',
        presets_sub: 'Beleuchtungsvorlagen',
        open_app: 'Einstellungen öffnen…',
        hud_changed: 'HUD-Intervall auf {sec}s geändert',
        hud_set: 'Nächstes Intervall auf {sec}s gesetzt',
        hud_once: 'HUD einmalig aktualisieren',
        hud_once_success: 'HUD-Telemetrie einmalig aktualisiert'
    },
    'fr': {
        header: 'Contrôle LangTu LT-104',
        sync_clock: 'Synchroniser l\'horloge avec le clavier',
        clock_synced: 'Commande de synchronisation envoyée !',
        sched_clock: 'Synchronisation automatique toutes les 12h',
        sched_on: 'Synchronisation auto toutes les 12h activée',
        sched_off: 'Synchronisation auto désactivée',
        hud_toggle: 'Démarrer/Arrêter le HUD ({sec}s)',
        hud_stopped: 'HUD système arrêté',
        hud_started: 'HUD système démarré ({sec}s)',
        hud_interval_sub: 'Intervalle du HUD',
        presets_sub: 'Préréglages d\'éclairage',
        open_app: 'Ouvrir les réglages…',
        hud_changed: 'Intervalle du HUD changé à {sec}s',
        hud_set: 'Prochain intervalle réglé à {sec}s',
        hud_once: 'Mettre à jour le HUD une fois',
        hud_once_success: 'Télémétrie HUD mise à jour avec succès'
    },
    'es': {
        header: 'Control LangTu LT-104',
        sync_clock: 'Sincronizar reloj con el teclado',
        clock_synced: '¡Comando de sincronización enviado!',
        sched_clock: 'Sincronización automática cada 12h',
        sched_on: 'Sincronización auto cada 12h activada',
        sched_off: 'Sincronización auto desactivada',
        hud_toggle: 'Iniciar/Detener HUD ({sec}s)',
        hud_stopped: 'HUD detenido',
        hud_started: 'HUD iniciado ({sec}s)',
        hud_interval_sub: 'Intervalo de HUD',
        presets_sub: 'Preajustes de luz',
        open_app: 'Abrir panel completo…',
        hud_changed: 'Intervalo cambiado a {sec}s',
        hud_set: 'Próximo intervalo ajustado a {sec}s',
        hud_once: 'Actualizar HUD una vez',
        hud_once_success: 'Telemetría HUD actualizada una vez'
    },
    'ru': {
        header: 'Управление LangTu LT-104',
        sync_clock: 'Синхронизировать часы с клавиатурой',
        clock_synced: 'Команда синхронизации отправлена!',
        sched_clock: 'Автосинхронизация часов каждые 12ч',
        sched_on: 'Автосинхронизация каждые 12ч включена',
        sched_off: 'Автосинхронизация отключена',
        hud_toggle: 'Запуск/Остановка HUD ({sec}с)',
        hud_stopped: 'Системный HUD остановлен',
        hud_started: 'Системный HUD запущен ({sec}с)',
        hud_interval_sub: 'Интервал HUD',
        presets_sub: 'Пресеты подсветки',
        open_app: 'Открыть панель настроек…',
        hud_changed: 'Интервал HUD изменен на {sec}с',
        hud_set: 'Интервал следующего запуска: {sec}с',
        hud_once: 'Обновить HUD один раз',
        hud_once_success: 'Телеметрия HUD успешно обновлена'
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
        str = str.replace(`{${k}}`, vars[k]);
    }
    return str;
}

function runCliAsync(args) {
    try {
        let cmd = ['/usr/bin/python3', CLI_PATH, ...args];
        let proc = Gio.Subprocess.new(cmd, Gio.SubprocessFlags.NONE);
        proc.wait_async(null, null);
    } catch (e) {
        console.error(`[LT104-Indicator] Failed to run CLI: ${e}`);
    }
}

function launchApp() {
    try {
        // Strategy 1: Direct subprocess spawn (guaranteed to launch under GNOME Wayland/X11)
        let proc = Gio.Subprocess.new(
            ['/usr/bin/python3', APP_PATH],
            Gio.SubprocessFlags.NONE
        );
        proc.wait_async(null, null);
    } catch (e) {
        console.error(`[LT104-Indicator] Failed to launch GTK App via Subprocess: ${e}`);
        try {
            // Strategy 2: Fallback to desktop app info
            let app = Gio.DesktopAppInfo.new('lt104.desktop');
            if (app) {
                app.launch([], null);
            } else {
                let appInfo = Gio.AppInfo.create_from_commandline(
                    `/usr/bin/python3 ${APP_PATH}`,
                    'LT-104 Keyboard',
                    Gio.AppInfoCreateFlags.NONE
                );
                appInfo.launch([], null);
            }
        } catch (e2) {
            console.error(`[LT104-Indicator] Fallback launch failed: ${e2}`);
        }
    }
}

const LT104Indicator = GObject.registerClass(
class LT104Indicator extends PanelMenu.Button {
    _init() {
        super._init(0.0, 'LT104 Indicator');

        // Panel icon
        let icon = new St.Icon({
            icon_name: 'input-keyboard-symbolic',
            style_class: 'system-status-icon',
        });
        this.add_child(icon);

        this._buildMenu();
    }

    _buildMenu() {
        // Title
        let headerItem = new PopupMenu.PopupMenuItem(`⌨️ ${t('header')}`, {reactive: false});
        this.menu.addMenuItem(headerItem);
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Quick Clock Sync
        let syncItem = new PopupMenu.PopupMenuItem(`🕒 ${t('sync_clock')}`);
        syncItem.connect('activate', () => {
            runCliAsync(['sync-clock']);
            Main.notify('LT-104', t('clock_synced'));
        });
        this.menu.addMenuItem(syncItem);

        // 12-Hour Schedule Clock Auto-Sync
        let schedItem = new PopupMenu.PopupMenuItem(`⏱️ ${t('sched_clock')}`);
        schedItem.connect('activate', () => {
            try {
                let cmd = ['/usr/bin/python3', CLI_PATH, 'clock-schedule-status'];
                let [ok, out] = GLib.spawn_command_line_sync(cmd.join(' '));
                let statusStr = new TextDecoder().decode(out);
                if (statusStr.includes('ENABLED')) {
                    runCliAsync(['clock-schedule-disable']);
                    Main.notify('LT-104', t('sched_off'));
                } else {
                    runCliAsync(['clock-schedule-enable']);
                    Main.notify('LT-104', t('sched_on'));
                }
            } catch (e) {
                console.error(`[LT104-Indicator] Clock schedule toggle failed: ${e}`);
            }
        });
        this.menu.addMenuItem(schedItem);

        // Toggle Real-time System HUD
        let currentInterval = 20;
        let hudItem = new PopupMenu.PopupMenuItem(`📊 ${t('hud_toggle', {sec: currentInterval})}`);

        hudItem.connect('activate', () => {
            try {
                let cmd = ['/usr/bin/python3', CLI_PATH, 'hud-status'];
                let [ok, out] = GLib.spawn_command_line_sync(cmd.join(' '));
                let statusStr = new TextDecoder().decode(out);
                if (statusStr.includes('RUNNING')) {
                    runCliAsync(['hud-stop']);
                    Main.notify('LT-104', t('hud_stopped'));
                } else {
                    runCliAsync(['hud-start', '--interval', String(currentInterval)]);
                    Main.notify('LT-104', t('hud_started', {sec: currentInterval}));
                }
            } catch (e) {
                console.error(`[LT104-Indicator] HUD toggle failed: ${e}`);
            }
        });
        this.menu.addMenuItem(hudItem);

        // Update HUD Once (single-shot)
        let hudOnceItem = new PopupMenu.PopupMenuItem(`⚡ ${t('hud_once') || 'Update HUD Once'}`);
        hudOnceItem.connect('activate', () => {
            runCliAsync(['hud-once']);
            Main.notify('LT-104', t('hud_once_success') || 'HUD updated once successfully');
        });
        this.menu.addMenuItem(hudOnceItem);

        // Submenu: HUD Interval
        let hudIntervalSubMenu = new PopupMenu.PopupSubMenuMenuItem(`⏱️ ${t('hud_interval_sub')}`);
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
                hudItem.label.set_text(`📊 ${t('hud_toggle', {sec: currentInterval})}`);
                try {
                    let cmd = ['/usr/bin/python3', CLI_PATH, 'hud-status'];
                    let [ok, out] = GLib.spawn_command_line_sync(cmd.join(' '));
                    let statusStr = new TextDecoder().decode(out);
                    if (statusStr.includes('RUNNING')) {
                        runCliAsync(['hud-stop']);
                        runCliAsync(['hud-start', '--interval', String(currentInterval)]);
                        Main.notify('LT-104', t('hud_changed', {sec: currentInterval}));
                    } else {
                        Main.notify('LT-104', t('hud_set', {sec: currentInterval}));
                    }
                } catch (e) {
                    console.error(`[LT104-Indicator] HUD interval switch failed: ${e}`);
                }
            });
            hudIntervalSubMenu.menu.addMenuItem(item);
        });

        // Submenu: Light Presets
        let lightSubMenu = new PopupMenu.PopupSubMenuMenuItem(`🌈 ${t('presets_sub')}`);
        this.menu.addMenuItem(lightSubMenu);

        const presets = [
            {label: 'Breathing Cyan', id: 'breathing-cyan'},
            {label: 'Static White', id: 'static-white'},
            {label: 'Static Cyan', id: 'static-cyan'},
            {label: 'Static Magenta', id: 'static-magenta'},
            {label: 'Static Green', id: 'static-green'},
            {label: 'Spectrum Cycle', id: 'spectrum'},
            {label: 'Rainbow Wave', id: 'rainbow'},
            {label: 'River Stream', id: 'stream'},
            {label: 'Turn Off', id: 'off'},
        ];

        presets.forEach(p => {
            let item = new PopupMenu.PopupMenuItem(p.label);
            item.connect('activate', () => {
                runCliAsync(['preset', p.id]);
            });
            lightSubMenu.menu.addMenuItem(item);
        });

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Launch full GUI
        let openAppItem = new PopupMenu.PopupMenuItem(`⚙️ ${t('open_app')}`);
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
