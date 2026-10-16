import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
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

function setItemVisible(item, visible) {
    if (!item) return;
    item.visible = visible;
    if (item.actor) {
        item.actor.visible = visible;
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
        },
        "shortcuts_ref": "快捷鍵參考",
        "open_product_page": "開啟 LT-104 產品頁面"
    },
    "ja": {
        "header": "LangTu LT-104 操作",
        "mode_cable": "🔌 接続モード: USB 有線 (接続済み)",
        "mode_bt": "📶 接続モード: Bluetooth ({name})",
        "mode_dongle": "📡 接続モード: 2.4G ドングル",
        "mode_disconnected": "❌ 接続モード: キーボード未接続",
        "battery_label": "🔋 バッテリー残量: {pct}%",
        "battery_cable_power": "⚡ 給電: USB 有線給電",
        "battery_reading": "🔋 バッテリー残量: 読込中…",
        "locked_banner": "🔒 設定ロック中 (USB ケーブル接続が必要)",
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
        "mode_cable": "🔌 연결 모드: USB 유선 (연결됨)",
        "mode_bt": "📶 연결 모드: 블루투스 ({name})",
        "mode_dongle": "📡 연결 모드: 2.4G 무선 동글",
        "mode_disconnected": "❌ 연결 모드: 키보드 연결 안 됨",
        "battery_label": "🔋 배터리 잔량: {pct}%",
        "battery_cable_power": "⚡ 전원: USB 유선 전원",
        "battery_reading": "🔋 배터리 잔량: 읽는 중…",
        "locked_banner": "🔒 설정 잠김 (USB 케이블 연결 필요)",
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
        "mode_cable": "🔌 Modus: USB-Kabel (Verbunden)",
        "mode_bt": "📶 Modus: Bluetooth ({name})",
        "mode_dongle": "📡 Modus: 2.4G Funkadapter",
        "mode_disconnected": "❌ Modus: Tastatur getrennt",
        "battery_label": "🔋 Akkustand: {pct}%",
        "battery_cable_power": "⚡ Strom: Über USB-Kabel versorgt",
        "battery_reading": "🔋 Akkustand: Wird gelesen…",
        "locked_banner": "🔒 Hardware-Einstellungen gesperrt (USB-Kabel erforderlich)",
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
        "mode_cable": "🔌 Mode: Câble USB (Connecté)",
        "mode_bt": "📶 Mode: Bluetooth ({name})",
        "mode_dongle": "📡 Mode: Sans fil 2.4G",
        "mode_disconnected": "❌ Mode: Clavier déconnecté",
        "battery_label": "🔋 Batterie: {pct}%",
        "battery_cable_power": "⚡ Alimentation: Câble USB",
        "battery_reading": "🔋 Batterie: Lecture…",
        "locked_banner": "🔒 Paramètres verrouillés (Câble USB requis)",
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
        "mode_cable": "🔌 Modo: Cable USB (Conectado)",
        "mode_bt": "📶 Modo: Bluetooth ({name})",
        "mode_dongle": "📡 Modo: Receptor 2.4G",
        "mode_disconnected": "❌ Modo: Teclado desconectado",
        "battery_label": "🔋 Batería: {pct}%",
        "battery_cable_power": "⚡ Alimentación: Cable USB",
        "battery_reading": "🔋 Batería: Leyendo…",
        "locked_banner": "🔒 Ajustes bloqueados (Requiere cable USB)",
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
        "mode_cable": "🔌 Режим: USB-кабель (Подключено)",
        "mode_bt": "📶 Режим: Bluetooth ({name})",
        "mode_dongle": "📡 Режим: 2.4G адаптер",
        "mode_disconnected": "❌ Режим: Клавиатура не подключена",
        "battery_label": "🔋 Заряд батареи: {pct}%",
        "battery_cable_power": "⚡ Питание: От USB-кабеля",
        "battery_reading": "🔋 Заряд батареи: Чтение…",
        "locked_banner": "🔒 Настройки заблокированы (Требуется USB-кабель)",
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

        this._buildMenu();
        this._refreshStatusAsync();

        // Refresh dynamic status and hide/show controls whenever the menu is clicked open
        this._openStateId = this.menu.connect('open-state-changed', (m, open) => {
            if (open) {
                this._refreshStatusAsync();
            }
        });

        // Periodic background poll every 6s to reflect hotplugged / switched state
        this._timerId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 6, () => {
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
        setItemVisible(this._lockedBannerItem, false);
        this.menu.addMenuItem(this._lockedBannerItem);

        // Separator between status and cable-only items
        this._cableSep1 = new PopupMenu.PopupSeparatorMenuItem();
        this.menu.addMenuItem(this._cableSep1);

        // --- USB CABLE ONLY ITEMS START ---

        // Quick Clock Sync
        this._syncItem = new PopupMenu.PopupMenuItem('🕒 ' + t('sync_clock'));
        this._syncItem.connect('activate', () => {
            runCliAsync(['sync-clock'], t('clock_synced'));
        });
        this.menu.addMenuItem(this._syncItem);

        // 12-Hour Schedule Clock Auto-Sync
        this._schedItem = new PopupMenu.PopupMenuItem('⏱️ ' + t('sched_clock'));
        this._schedItem.connect('activate', () => {
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
                runCliAsync(['preset', p.id], '🌈 ' + localizedName);
            });
            this._lightSubMenu.menu.addMenuItem(item);
        });

        // Separator after cable-only items
        this._cableSep2 = new PopupMenu.PopupSeparatorMenuItem();
        this.menu.addMenuItem(this._cableSep2);

        // Group cable-only items together for toggling
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
            ['── Win System ──', ''],
            ['Fn+F1', t('sc_win_f1') || 'Media Player (媒体播放器)'],
            ['Fn+F2', t('sc_win_f2') || 'Calculator (计算器)'],
            ['Fn+F3', t('sc_win_f3') || 'Win+TAB (Task View 任务视图)'],
            ['Fn+F4', t('sc_win_f4') || 'Win+E (File Explorer 资源管理器)'],
            ['Fn+F5', t('sc_win_f5') || 'Backlight Brightness −'],
            ['Fn+F6', t('sc_win_f6') || 'Backlight Brightness +'],
            ['Fn+F7', t('sc_win_f7') || 'Previous Track'],
            ['Fn+F8', t('sc_win_f8') || 'Play/Pause'],
            ['Fn+F9', t('sc_win_f9') || 'Next Track'],
            ['Fn+F10', t('sc_win_f10') || 'Mute/Unmute'],
            ['Fn+F11', t('sc_win_f11') || 'Volume −'],
            ['Fn+F12', t('sc_win_f12') || 'Volume +'],
            ['Fn+WIN', t('sc_win_winlock') || 'Lock WIN Key'],
            ['── Common ──', ''],
            ['Fn+Esc (3s)', t('sc_factory') || 'Restore Factory Settings (恢复出厂设置)'],
            ['Fn+Ins', t('sc_side_light') || 'Side Backlight: cycle mode & color (两侧边光切换)'],
            ['Fn+Q', t('sc_24g') || '2.4G Mode (2.4G 模式)'],
            ['Fn+W/E/R', t('sc_bt') || 'Bluetooth 1/2/3 (蓝牙模式)'],
            ['Fn+T', t('sc_wired') || 'Wired Mode (有线模式)'],
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
        let isCable = (mode === 'usb_cable');

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
            setItemVisible(this._batteryItem, true);
        } else if (mode === 'bluetooth') {
            this._batteryItem.label.set_text(t('battery_reading'));
            setItemVisible(this._batteryItem, true);
        } else if (isCable) {
            this._batteryItem.label.set_text(t('battery_cable_power'));
            setItemVisible(this._batteryItem, true);
        } else {
            setItemVisible(this._batteryItem, false);
        }

        // 3. Toggle Locked Banner (shown when NOT in USB cable mode)
        setItemVisible(this._lockedBannerItem, !isCable);

        // 4. Toggle USB Cable Only Items (Clock Sync, Sched, HUD, Light Presets)
        if (this._cableItems) {
            this._cableItems.forEach(item => {
                setItemVisible(item, isCable);
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
