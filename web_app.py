#!/usr/bin/env python3
"""
Web Control Panel for LT104 Keyboard on Ubuntu Linux
Multi-language support for all Ubuntu desktop locales.
Runs on http://127.0.0.1:8989
"""
import http.server
import json
import urllib.parse
import urllib.request
import os
import sys
import tempfile
import subprocess
import signal
import time

from lt104_core import LT104Controller, LIGHT_MODES, SIDE_LIGHT_MODES, KB_KEYS, find_lt104_usb, find_lt104_lcd_hidraw

import i18n
from config import load_config, save_config
from PIL import Image, ImageSequence

CFG = load_config()
HUD_PROC = None
HUD_INTERVAL = float(CFG.get("hud_interval", 120.0))

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

def update_lcd_cache(src_path):
    try:
        os.makedirs(STATIC_DIR, exist_ok=True)
        dst_path = os.path.join(STATIC_DIR, "current_lcd.gif")
        im = Image.open(src_path)
        frames = [f.copy().convert("RGB").resize((62, 39)) for f in ImageSequence.Iterator(im)]
        dur = im.info.get("duration", 80)
        frames[0].save(dst_path, save_all=True, append_images=frames[1:], loop=0, duration=dur)
    except Exception as e:
        pass

_UPDATE_CACHE = {"timestamp": 0, "data": None}

def check_github_updates():
    now = time.time()
    if _UPDATE_CACHE["data"] is not None and (now - _UPDATE_CACHE["timestamp"]) < 900:
        return _UPDATE_CACHE["data"]

    current_commit = "unknown"
    try:
        current_commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        pass

    current_version = "v1.0.0"
    version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")
    if os.path.exists(version_file):
        try:
            with open(version_file, "r") as vf:
                current_version = vf.read().strip()
        except Exception:
            pass

    res = {
        "has_update": False,
        "current_version": current_version,
        "current_commit": current_commit,
        "latest_version": current_version,
        "latest_commit": current_commit,
        "release_url": "https://github.com/iiaiiappa/lt104-keyboard-linux/releases",
        "html_url": "https://github.com/iiaiiappa/lt104-keyboard-linux",
        "release_notes": ""
    }

    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/iiaiiappa/lt104-keyboard-linux/releases/latest",
            headers={"User-Agent": "LT104-Keyboard-Linux/1.0", "Accept": "application/vnd.github.v3+json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=4) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    tag = data.get("tag_name", "")
                    res["latest_version"] = tag
                    res["release_url"] = data.get("html_url", res["release_url"])
                    res["release_notes"] = data.get("body", "")
                    if tag and tag.lstrip("v") != current_version.lstrip("v"):
                        res["has_update"] = True
        except Exception:
            # Fallback to commits on master branch if no formal releases yet
            req_commit = urllib.request.Request(
                "https://api.github.com/repos/iiaiiappa/lt104-keyboard-linux/commits/master",
                headers={"User-Agent": "LT104-Keyboard-Linux/1.0", "Accept": "application/vnd.github.v3+json"}
            )
            with urllib.request.urlopen(req_commit, timeout=4) as resp_commit:
                if resp_commit.status == 200:
                    cdata = json.loads(resp_commit.read().decode())
                    remote_sha = cdata.get("sha", "")[:7]
                    res["latest_commit"] = remote_sha
                    res["html_url"] = cdata.get("html_url", res["html_url"])
                    res["commit_message"] = cdata.get("commit", {}).get("message", "").split("\n")[0]
                    if remote_sha and current_commit != "unknown" and remote_sha != current_commit:
                        res["has_update"] = True
                        res["latest_version"] = f"commit {remote_sha}"
    except Exception as e:
        res["error"] = str(e)

    _UPDATE_CACHE["timestamp"] = now
    _UPDATE_CACHE["data"] = res
    return res

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title id="page-title">LT-104 Keyboard Control Center</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    :root {
      --bg: #1e1e1e;
      --card: #282828;
      --card-inner: #323232;
      --accent: #3584e4;
      --accent-hover: #1c71d8;
      --text: #ffffff;
      --subtext: #9a9996;
      --border: #383838;
      --success: #2ec27e;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Cantarell, Ubuntu, sans-serif; }
    body { background: var(--bg); color: var(--text); padding: 18px 24px 32px; min-height: 100vh; display: flex; flex-direction: column; align-items: center; }
    .container { max-width: 1220px; width: 100%; display: flex; flex-direction: column; gap: 16px; }
    
    /* HeaderBar styling matching GNOME / Libadwaita */
    .header { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; background: #262626; border: 1px solid var(--border); border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.25); flex-wrap: wrap; gap: 12px; }
    .header h1 { font-size: 19px; color: #ffffff; font-weight: 700; display: flex; align-items: center; gap: 10px; }
    .header-right { display: flex; align-items: center; gap: 12px; }
    .lang-select { background: var(--card-inner); border: 1px solid var(--border); border-radius: 20px; color: #fff; padding: 6px 14px; font-size: 13px; outline: none; cursor: pointer; transition: border-color 0.15s; }
    .lang-select:focus { border-color: var(--accent); }
    .status-badge { background: rgba(46, 194, 126, 0.15); color: #2ec27e; border: 1px solid rgba(46, 194, 126, 0.35); padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 6px; }
    .status-badge.error { background: rgba(224, 27, 36, 0.15); color: #e01b24; border-color: rgba(224, 27, 36, 0.35); }
    .update-badge { background: rgba(53, 132, 228, 0.15); color: #78aeed; border: 1px solid rgba(53, 132, 228, 0.4); padding: 5px 12px; border-radius: 20px; font-size: 12.5px; font-weight: 600; text-decoration: none; display: none; align-items: center; gap: 6px; cursor: pointer; transition: all 0.2s; }
    .update-badge:hover { background: rgba(53, 132, 228, 0.25); transform: translateY(-1px); }

    /* Top Middle Standalone Preview Card */
    .kb-top-card { background: #181818; border: 1px solid var(--border); border-radius: 14px; padding: 14px 18px 16px; box-shadow: 0 4px 18px rgba(0,0,0,0.3); }
    .kb-top-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; font-size: 13px; color: var(--subtext); flex-wrap: wrap; gap: 8px; }
    .kb-top-header-left { display: flex; align-items: center; gap: 8px; }
    .status-dot-pulse { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #2ec27e; box-shadow: 0 0 8px #2ec27e; }
    .pill-badge { background: rgba(53, 132, 228, 0.2); border: 1px solid rgba(53, 132, 228, 0.4); padding: 2px 10px; border-radius: 12px; font-size: 12px; color: #78aeed; font-weight: 500; }
    .kb-canvas-container { width: 100%; display: flex; justify-content: center; overflow: hidden; background: #121212; border-radius: 10px; border: 1px solid #282828; padding: 4px; }
    #kb-preview { width: 100%; max-width: 954px; aspect-ratio: 954 / 297; display: block; border-radius: 8px; cursor: pointer; }

    /* 2-Column Responsive Layout Below Preview */
    .main-layout { display: flex; flex-direction: column; gap: 16px; }
    @media (min-width: 980px) {
      .main-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }
    }
    .col-left, .col-right { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
    
    .card { background: var(--card); border-radius: 14px; border: 1px solid var(--border); padding: 20px 22px; box-shadow: 0 3px 14px rgba(0,0,0,0.22); }
    .card-title { font-size: 16px; margin-bottom: 14px; color: #fff; font-weight: 700; display: flex; align-items: center; gap: 8px; }
    .card-desc { color: var(--subtext); font-size: 13px; margin-bottom: 16px; line-height: 1.45; }
    
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }
    .form-group { display: flex; flex-direction: column; gap: 7px; }
    label { font-size: 13px; color: var(--subtext); font-weight: 500; }
    select, input[type="range"], input[type="file"] { background: var(--card-inner); border: 1px solid var(--border); border-radius: 8px; color: #fff; padding: 9px 12px; font-size: 13.5px; outline: none; width: 100%; transition: border 0.15s; }
    select:focus { border-color: var(--accent); }
    
    .color-picker-wrap { display: flex; align-items: center; gap: 12px; }
    input[type="color"] { -webkit-appearance: none; border: none; width: 42px; height: 42px; border-radius: 8px; cursor: pointer; background: transparent; }
    input[type="color"]::-webkit-color-swatch-wrapper { padding: 0; }
    input[type="color"]::-webkit-color-swatch { border-radius: 8px; border: 2px solid var(--border); }
    
    /* Buttons with Libadwaita pill style */
    .btn { background: var(--accent); color: #ffffff; border: none; padding: 9px 18px; border-radius: 20px; font-size: 13.5px; font-weight: 600; cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; justify-content: center; gap: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .btn:hover { background: var(--accent-hover); transform: translateY(-1px); }
    .btn-secondary { background: var(--card-inner); color: #fff; border: 1px solid var(--border); }
    .btn-secondary:hover { background: #3d3d3d; }
    .btn-full { width: 100%; }
    
    .presets { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
    .preset-btn { width: 28px; height: 28px; border-radius: 50%; border: 2px solid #fff3; cursor: pointer; transition: transform 0.15s; }
    .preset-btn:hover { transform: scale(1.15); border-color: #fff; }

    .range-val { font-size: 13px; color: var(--accent); float: right; font-weight: 600; }
    .toast { position: fixed; bottom: 24px; right: 24px; background: var(--success); color: #000; padding: 12px 20px; border-radius: 8px; font-weight: 600; opacity: 0; transition: opacity 0.3s; pointer-events: none; z-index: 999; }
    .progress-bar-wrap { width: 100%; height: 8px; background: var(--card-inner); border-radius: 4px; overflow: hidden; margin-top: 12px; display: none; }
    .progress-bar { height: 100%; width: 0%; background: var(--accent); transition: width 0.1s ease; }

    .switch-wrap { display: flex; align-items: center; gap: 10px; cursor: pointer; font-size: 13px; color: var(--text); user-select: none; }
    .switch-wrap input { display: none; }
    .slider { position: relative; width: 40px; height: 22px; background-color: #3c3c3c; border-radius: 22px; transition: .25s; display: inline-block; }
    .slider:before { position: absolute; content: ""; height: 16px; width: 16px; left: 3px; bottom: 3px; background-color: white; border-radius: 50%; transition: .25s; }
    input:checked + .slider { background-color: var(--success); }
    input:checked + .slider:before { transform: translateX(18px); }
  </style>
</head>
<body>
  <div class="container">
    <!-- Top HeaderBar -->
    <div class="header">
      <h1 id="txt-header">⌨️ LT-104 Keyboard Control Center</h1>
      <div class="header-right">
        <select id="lang-select" class="lang-select" onchange="changeLanguage(this.value)">
          <option value="en">English</option>
          <option value="zh-CN">简体中文 (Simplified Chinese)</option>
          <option value="zh-TW">繁體中文 (Traditional Chinese)</option>
          <option value="ja">日本語 (Japanese)</option>
          <option value="ko">한국어 (Korean)</option>
          <option value="de">Deutsch (German)</option>
          <option value="fr">Français (French)</option>
          <option value="es">Español (Spanish)</option>
          <option value="ru">Русский (Russian)</option>
        </select>
        <a id="update-badge" class="update-badge" href="https://github.com/iiaiiappa/lt104-keyboard-linux" target="_blank" rel="noopener noreferrer">🚀 <span id="update-text">New Update Available</span></a>
        <div id="device-badge" class="status-badge">● LT-104 Connected</div>
      </div>
    </div>

    <!-- Top Middle: Standalone Keyboard Animation Visualizer Preview Card (Full Width) -->
    <div class="kb-top-card">
      <div class="kb-top-header">
        <div class="kb-top-header-left">
          <span class="status-dot-pulse"></span>
          <strong id="txt-kb-preview-title" style="color: var(--text);">即时键盘灯效动画预览</strong>
          <span id="kb-preview-mode-tag" class="pill-badge">静态恒亮 (Static)</span>
        </div>
        <span id="txt-kb-preview-hint" style="font-size: 12px; opacity: 0.9; color: #9a9996;">💡 点击按键触发灯光反馈 · 左右侧翼灯带实时同显</span>
      </div>
      <div class="kb-canvas-container">
        <canvas id="kb-preview" width="954" height="297"></canvas>
      </div>
    </div>

    <!-- Two-Column Responsive Settings Layout Below Preview -->
    <div class="main-layout">
      <!-- Left Column: RGB Lighting Card + TFT Clock Calibration Card -->
      <div class="col-left">
        <!-- RGB Lighting Card -->
        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 10px;">
            <div class="card-title" id="txt-rgb-title" style="margin-bottom: 0;">🌈 RGB Lighting & Backlight</div>
            <label class="switch-wrap" style="font-size: 13px;">
              <input type="checkbox" id="chk-auto-apply" checked onchange="toggleAutoApply(this.checked)">
              <span class="slider"></span>
              <span id="txt-auto-apply">Live Apply (Auto Apply on Change)</span>
            </label>
          </div>
          <p class="card-desc" id="txt-rgb-desc">
            Apply immediately and save permanently to keyboard EEPROM
          </p>

          <div class="grid">
            <div class="form-group">
              <label id="txt-light-mode">Lighting Mode</label>
              <select id="light-mode" onchange="onModeChange()">
                __LIGHT_OPTIONS__
              </select>
            </div>

            <div class="form-group" id="group-custom-color">
              <label id="txt-custom-color">Custom Color</label>
              <div class="color-picker-wrap">
                <input type="color" id="light-color" value="#00e5ff" onchange="onColorChange()">
                <span id="color-hex" style="font-family: monospace; font-size: 14px;">#00e5ff</span>
              </div>
              <div class="presets">
                <div class="preset-btn" style="background:#ff0055" onclick="setColor('#ff0055')" title="Magenta"></div>
                <div class="preset-btn" style="background:#00e5ff" onclick="setColor('#00e5ff')" title="Cyan"></div>
                <div class="preset-btn" style="background:#00e676" onclick="setColor('#00e676')" title="Green"></div>
                <div class="preset-btn" style="background:#ffd600" onclick="setColor('#ffd600')" title="Yellow"></div>
                <div class="preset-btn" style="background:#d500f9" onclick="setColor('#d500f9')" title="Purple"></div>
                <div class="preset-btn" style="background:#ff3d00" onclick="setColor('#ff3d00')" title="Orange"></div>
                <div class="preset-btn" style="background:#ffffff" onclick="setColor('#ffffff')" title="White"></div>
              </div>
            </div>

            <div class="form-group" id="group-brightness">
              <label><span id="txt-brightness">Brightness</span> <span id="bright-val" class="range-val">100%</span></label>
              <input type="range" id="light-brightness" min="0" max="4" value="4" oninput="onBrightnessInput(this.value)" onchange="onBrightnessChange()">
            </div>

            <div class="form-group" id="group-speed">
              <label><span id="txt-speed">Animation Speed</span> <span id="speed-val" class="range-val">3</span></label>
              <input type="range" id="light-speed" min="0" max="4" value="3" oninput="onSpeedInput(this.value)" onchange="onSpeedChange()">
            </div>

            <div class="form-group" id="group-side-mode">
              <label id="txt-side-mode">Side Edge Backlight (Dual Lightbars)</label>
              <select id="side-mode" onchange="onSideModeChange()">
                __SIDE_LIGHT_OPTIONS__
              </select>
            </div>

            <div class="form-group" id="group-side-color">
              <label id="txt-side-color">Side Light Color Preview</label>
              <div class="color-picker-wrap" style="align-items: center; gap: 10px;">
                <input type="color" id="side-color" value="#00e5ff" disabled style="pointer-events: none; opacity: 1; cursor: default;">
                <span id="side-color-hex" style="font-family: monospace; font-size: 14px; color: var(--text);">#00e5ff</span>
                <span style="font-size: 12px; color: var(--subtext);">(Preset Hardware Color)</span>
              </div>
            </div>
          </div>
          <div id="wrap-apply-light" style="margin-top: 18px; display: none;">
            <button class="btn btn-full" onclick="applyLight()" id="btn-apply-light">✨ Apply & Save Backlight</button>
          </div>
        </div>

        <!-- Clock Sync Card -->
        <div class="card">
          <div class="card-title" id="txt-clock-title">🕒 TFT Clock Calibration & Auto-Sync</div>
          <p class="card-desc" id="txt-clock-desc">
            Sync PC time immediately or enable 12-hour automated background service.
          </p>
          <div style="display: flex; gap: 14px; flex-wrap: wrap; align-items: center; justify-content: space-between; background: #222222; padding: 12px 16px; border-radius: 10px; border: 1px solid var(--border);">
            <button class="btn btn-secondary" onclick="syncClock()" id="btn-sync-clock">🕒 Sync Clock to Keyboard LCD</button>
            <label class="switch-wrap">
              <input type="checkbox" id="chk-clock-sched" onchange="toggleClockSchedule(this.checked)">
              <span class="slider"></span>
              <span id="txt-clock-sched">Auto-Sync Clock Every 12 Hours</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Right Column: Real-time System Monitoring HUD Card + LCD Upload Card -->
      <div class="col-right">
        <!-- Real-time System HUD Card -->
        <div class="card">
          <div class="card-title" id="txt-hud-title">📊 Real-time System Monitoring HUD</div>
          <p class="card-desc" id="txt-hud-desc">
            Stream live CPU / RAM / Disk telemetry directly to keyboard LCD RAM.
          </p>
          
          <div style="display: flex; flex-direction: column; gap: 14px;">
            <!-- Selectors Row -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
              <div style="display: flex; flex-direction: column; gap: 6px; font-size: 13px;">
                <label id="txt-hud-interval">HUD Refresh Interval:</label>
                <select id="hud-interval" onchange="onIntervalChanged()">
                  <option value="5" id="opt-5s">5s (Fast)</option>
                  <option value="10" id="opt-10s">10s (Moderate)</option>
                  <option value="20" id="opt-20s">20s</option>
                  <option value="30" id="opt-30s">30s (Power Saving)</option>
                  <option value="60" id="opt-60s">60s (Slow)</option>
                  <option value="120" id="opt-120s" selected>120s (2 min - Default)</option>
                  <option value="300" id="opt-300s">300s (5 min - Power Saving)</option>
                </select>
              </div>
              <div style="display: flex; flex-direction: column; gap: 6px; font-size: 13px;">
                <label id="txt-hud-restore">Stop Restore:</label>
                <select id="hud-restore-preset" onchange="onRestorePresetChanged()">
                  <option value="lt104_sample.gif" id="opt-restore-sample" selected>lt104_sample.gif (Default Factory)</option>
                  <option value="0_perfect36.gif" id="opt-restore-p36">0_perfect36.gif</option>
                  <option value="none" id="opt-restore-none">Restore None</option>
                </select>
              </div>
            </div>

            <!-- Buttons: Row 1 (Toggle HUD) & Row 2 (Once & Restore) matching GTK layout -->
            <div style="display: flex; flex-direction: column; gap: 10px;">
              <button class="btn btn-full" id="btn-toggle-hud" onclick="toggleHud()" style="background: linear-gradient(135deg, #059669, #10b981);">📊 Start Real-time System HUD</button>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <button class="btn btn-secondary" id="btn-hud-once" onclick="pushHudOnce()">⚡ Update HUD Once</button>
                <button class="btn btn-secondary" id="btn-restore-anim" onclick="restoreAnimation()">🔄 Restore Animation</button>
              </div>
            </div>

            <div id="hud-status-text" style="font-size: 13px; color: var(--subtext);">
              <span id="txt-hud-status-label">System HUD Status:</span> <span id="hud-badge" style="color: #94a3b8; font-weight: 600;">Stopped</span> (<span id="txt-hud-note">Direct RAM streaming, zero SPI Flash wear, typing 100% responsive</span>)
            </div>
            <div class="hud-hardware-banner" id="txt-hud-hardware-note" style="background: rgba(56, 189, 248, 0.08); border-left: 3px solid #0284c7; padding: 10px 14px; border-radius: 6px; font-size: 12.5px; line-height: 1.5; color: #bae6fd;">
              💡 Note: The 48MHz keyboard MCU dedicates 100% bandwidth to transfer 28KB frame over SPI, pausing software LED PWM for ~0.5s. Recommended interval: 2 to 5 minutes (or use single-shot update).
            </div>
          </div>
        </div>

        <!-- LCD Image / GIF Upload Card -->
        <div class="card" id="card-lcd-upload">
          <div class="card-title" id="txt-lcd-title">📺 LCD Image & GIF Upload</div>
          <p class="card-desc" id="txt-lcd-desc">
            Automatically scaled to 160 × 80 RGB565, multi-frame GIF supported.
          </p>
          <div style="display: flex; flex-direction: column; gap: 14px;">
            <div class="form-group">
              <input type="file" id="lcd-file" accept="image/gif,image/png,image/jpeg,image/webp">
              <div class="progress-bar-wrap" id="progress-wrap">
                <div class="progress-bar" id="progress-bar"></div>
              </div>
              <div id="upload-status" style="font-size: 13px; color: var(--subtext); margin-top: 4px;"></div>
            </div>
            <div>
              <button class="btn btn-full" onclick="uploadLcdImage()" id="btn-upload-lcd">🚀 Upload to Keyboard LCD</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div id="toast" class="toast">Settings applied!</div>

  <script>
    const I18N = __I18N_JSON__;
    const SERVER_CONFIG = __CONFIG_JSON__;
    let currentLang = 'en';

    function detectLanguage() {
      const stored = localStorage.getItem('lt104_lang');
      if (stored && I18N[stored]) return stored;
      const navLang = navigator.language || navigator.userLanguage || 'en';
      if (I18N[navLang]) return navLang;
      const short = navLang.split('-')[0];
      if (I18N[short]) return short;
      if (navLang.startsWith('zh')) return navLang.includes('TW') || navLang.includes('HK') ? 'zh-TW' : 'zh-CN';
      return 'en';
    }

    function changeLanguage(lang) {
      if (!I18N[lang]) return;
      currentLang = lang;
      localStorage.setItem('lt104_lang', lang);
      document.getElementById('lang-select').value = lang;
      applyI18n();
    }

    function t(key, vars = {}) {
      const bundle = I18N[currentLang] || I18N['en'];
      let str = bundle[key] || (I18N['en'] && I18N['en'][key]) || key;
      for (const k in vars) {
        str = str.replace('{' + k + '}', vars[k]);
      }
      return str;
    }

    function applyI18n() {
      document.getElementById('page-title').innerText = t('title');
      document.getElementById('txt-header').innerText = '⌨️ ' + t('title');
      document.getElementById('txt-rgb-title').innerText = '🌈 ' + t('rgb_card_title');
      document.getElementById('txt-rgb-desc').innerText = t('rgb_card_desc');
      document.getElementById('txt-light-mode').innerText = t('light_mode');
      document.getElementById('txt-custom-color').innerText = t('custom_color');
      const txtSideColor = document.getElementById('txt-side-color');
      if (txtSideColor) txtSideColor.innerText = t('side_color_preview') || 'Side Light Color Preview';
      document.getElementById('txt-brightness').innerText = t('brightness');
      document.getElementById('txt-speed').innerText = t('speed');
      document.getElementById('btn-apply-light').innerText = '✨ ' + t('apply_btn');
      const txtAutoApply = document.getElementById('txt-auto-apply');
      if (txtAutoApply) txtAutoApply.innerText = t('auto_apply');
      const txtPreviewTitle = document.getElementById('txt-kb-preview-title');
      if (txtPreviewTitle) txtPreviewTitle.innerText = t('kb_preview_title');
      const txtPreviewHint = document.getElementById('txt-kb-preview-hint');
      if (txtPreviewHint) txtPreviewHint.innerText = '💡 ' + t('kb_preview_hint');
      
      document.getElementById('txt-clock-title').innerText = '🕒 ' + t('clock_card_title');
      document.getElementById('txt-clock-desc').innerText = t('clock_card_desc');
      document.getElementById('btn-sync-clock').innerText = '🕒 ' + t('sync_clock');
      document.getElementById('txt-clock-sched').innerText = t('clock_sched_title');

      document.getElementById('txt-hud-title').innerText = '📊 ' + t('hud_card_title');
      document.getElementById('txt-hud-desc').innerText = t('hud_card_desc');
      document.getElementById('txt-hud-interval').innerText = t('hud_interval') + ':';
      document.getElementById('txt-hud-status-label').innerText = t('hud_status_label') + ':';
      document.getElementById('txt-hud-note').innerText = t('hud_note');
      document.getElementById('btn-hud-once').innerText = '⚡ ' + t('hud_once_btn');
      const btnRestoreAnim = document.getElementById('btn-restore-anim');
      if (btnRestoreAnim) btnRestoreAnim.innerText = '🔄 ' + t('hud_restore_btn');
      document.getElementById('txt-hud-hardware-note').innerText = '💡 ' + t('hud_hardware_note');

      const intervals = [5, 10, 20, 30, 60, 120, 300];
      for (const s of intervals) {
        const el = document.getElementById('opt-' + s + 's');
        if (el) el.innerText = t('opt_' + s + 's');
      }

      const txtRestore = document.getElementById('txt-hud-restore');
      if (txtRestore) txtRestore.innerText = t('hud_restore') + ':';
      const optSample = document.getElementById('opt-restore-sample');
      if (optSample) optSample.innerText = t('opt_restore_sample');
      const optP36 = document.getElementById('opt-restore-p36');
      if (optP36) optP36.innerText = t('opt_restore_p36');
      const optNone = document.getElementById('opt-restore-none');
      if (optNone) optNone.innerText = t('opt_restore_none');

      document.getElementById('txt-lcd-title').innerText = '📺 ' + t('lcd_card_title');
      document.getElementById('txt-lcd-desc').innerText = t('lcd_card_desc');
      document.getElementById('btn-upload-lcd').innerText = '🚀 ' + t('upload_btn');
      if (latestUpdateData && latestUpdateData.has_update) {
        const ver = latestUpdateData.latest_version || ('commit ' + latestUpdateData.latest_commit);
        const txt = document.getElementById('update-text');
        if (txt) txt.innerText = t('update_available', { ver });
      }
      updateHudUI();
    }

    function showToast(msg) {
      const toast = document.getElementById('toast');
      toast.innerText = msg;
      toast.style.opacity = '1';
      setTimeout(() => toast.style.opacity = '0', 2500);
    }

    const SINGLE_COLOR_MODES = [1, 2, 3, 4, 5, 7];

    const SIDE_PRESET_COLORS = {
      0: '#000000',
      1: '#00e5ff',
      2: '#00e5ff',
      3: '#ff0000',
      4: '#ff7f00',
      5: '#ffff00',
      6: '#00ff00',
      7: '#00ffff',
      8: '#0000ff',
      9: '#ff00ff',
      10: '#ffffff'
    };

    function updateSideColorVisibility(sideMode) {
      const modeVal = parseInt(sideMode !== undefined ? sideMode : (document.getElementById('side-mode') ? document.getElementById('side-mode').value : 1));
      const sideColorGroup = document.getElementById('group-side-color');
      if (sideColorGroup) {
        // Mode 0: Off, Mode 1: Breathing, Mode 2: Spectrum Cycle -> NO Side Light Color Preview (hide)
        // Modes 3 to 10 (Red, Orange, Yellow, Green, Cyan, Blue, Magenta, White) -> show non-editable preview
        if (modeVal === 0 || modeVal === 1 || modeVal === 2) {
          sideColorGroup.style.display = 'none';
        } else {
          sideColorGroup.style.display = 'block';
        }
      }
      if (SIDE_PRESET_COLORS[modeVal] && modeVal >= 3) {
        const hex = SIDE_PRESET_COLORS[modeVal];
        const sideColorEl = document.getElementById('side-color');
        const sideColorHexEl = document.getElementById('side-color-hex');
        if (sideColorEl) sideColorEl.value = hex;
        if (sideColorHexEl) sideColorHexEl.innerText = hex;
      }
    }

    function updateColorVisibility(mode) {
      const modeVal = parseInt(mode !== undefined ? mode : document.getElementById('light-mode').value) || 1;
      const colorGroup = document.getElementById('group-custom-color');
      if (colorGroup) {
        if (SINGLE_COLOR_MODES.includes(modeVal)) {
          colorGroup.style.display = 'block';
        } else {
          colorGroup.style.display = 'none';
        }
      }
      const isOff = (modeVal === 20);
      const isStatic = (modeVal === 1);
      const brightGroup = document.getElementById('group-brightness');
      const speedGroup = document.getElementById('group-speed');
      if (brightGroup) brightGroup.style.display = isOff ? 'none' : 'block';
      if (speedGroup) speedGroup.style.display = (isOff || isStatic) ? 'none' : 'block';
      updateSideColorVisibility();
    }

    let autoApplyLight = true;

    function updateAutoApplyUI() {
      const wrapApply = document.getElementById('wrap-apply-light');
      if (wrapApply) {
        wrapApply.style.display = autoApplyLight ? 'none' : 'block';
      }
      const chk = document.getElementById('chk-auto-apply');
      if (chk) chk.checked = autoApplyLight;
    }

    function toggleAutoApply(enabled) {
      autoApplyLight = Boolean(enabled);
      localStorage.setItem('lt104_light_auto_apply', autoApplyLight);
      updateAutoApplyUI();
      showToast(autoApplyLight ? '⚡ ' + t('auto_apply') + ' (ON)' : '⏸️ ' + t('auto_apply') + ' (OFF)');
      if (autoApplyLight) {
        applyLight();
      }
    }

    let rememberedBrightness = parseInt(localStorage.getItem('lt104_remembered_brightness')) || 4;
    if (rememberedBrightness <= 0) rememberedBrightness = 4;
    let previousModeVal = 1;

    function onModeChange() {
      const modeEl = document.getElementById('light-mode');
      const modeVal = parseInt(modeEl ? modeEl.value : 1) || 1;
      const brightInput = document.getElementById('light-brightness');
      const currentBright = parseInt(brightInput ? brightInput.value : 4);

      if (modeVal === 20) {
        // Going to Backlight Off: remember previous brightness
        if (previousModeVal !== 20 && currentBright > 0) {
          rememberedBrightness = currentBright;
          localStorage.setItem('lt104_remembered_brightness', rememberedBrightness);
        }
        if (brightInput) brightInput.value = 0;
        updateRange('bright-val', 0, ['0%', '25%', '50%', '75%', '100%']);
      } else {
        // Any non-off mode: guarantee a non-zero brightness level (at least level 1-4)
        if (previousModeVal === 20 || currentBright <= 0) {
          const restoreBright = (rememberedBrightness > 0 ? rememberedBrightness : 4);
          if (brightInput) brightInput.value = restoreBright;
          updateRange('bright-val', restoreBright, ['0%', '25%', '50%', '75%', '100%']);
        }
      }
      previousModeVal = modeVal;
      updateColorVisibility(modeVal);
      if (autoApplyLight) {
        applyLight();
      }
    }

    function onColorChange() {
      const hex = document.getElementById('light-color').value;
      document.getElementById('color-hex').innerText = hex;
      if (autoApplyLight) {
        applyLight();
      }
    }

    function setColor(hex) {
      let mode = parseInt(document.getElementById('light-mode').value) || 1;
      // If currently in a mode that doesn't support single color, switch to Static (Mode 1)
      if (!SINGLE_COLOR_MODES.includes(mode)) {
        mode = 1;
        document.getElementById('light-mode').value = "1";
        updateColorVisibility(1);
      }
      document.getElementById('light-color').value = hex;
      document.getElementById('color-hex').innerText = hex;
      if (autoApplyLight) {
        applyLight();
      }
    }

    function onBrightnessInput(val) {
      updateRange('bright-val', val, ['0%', '25%', '50%', '75%', '100%']);
      const modeVal = parseInt(document.getElementById('light-mode').value) || 1;
      if (modeVal !== 20 && parseInt(val) > 0) {
        rememberedBrightness = parseInt(val);
        localStorage.setItem('lt104_remembered_brightness', rememberedBrightness);
      }
      if (autoApplyLight) {
        applyLight();
      }
    }

    function onBrightnessChange() {
      const modeVal = parseInt(document.getElementById('light-mode').value) || 1;
      const val = parseInt(document.getElementById('light-brightness').value);
      if (modeVal !== 20 && val > 0) {
        rememberedBrightness = val;
        localStorage.setItem('lt104_remembered_brightness', rememberedBrightness);
      }
      if (autoApplyLight) {
        applyLight();
      }
    }

    function onSpeedInput(val) {
      updateRange('speed-val', val);
      if (autoApplyLight) {
        applyLight();
      }
    }

    function onSpeedChange() {
      if (autoApplyLight) {
        applyLight();
      }
    }

    function updateRange(id, val, textMap) {
      document.getElementById(id).innerText = textMap ? textMap[val] : val;
    }

    function onSideModeChange() {
      const sideModeVal = parseInt(document.getElementById('side-mode') ? document.getElementById('side-mode').value : 1) || 0;
      updateSideColorVisibility(sideModeVal);
      if (autoApplyLight) {
        applyLight();
      }
    }

    function onSideColorChange() {
      const hex = document.getElementById('side-color').value;
      const el = document.getElementById('side-color-hex');
      if (el) el.innerText = hex;
      if (autoApplyLight) {
        applyLight();
      }
    }

    async function applyLight() {
      const mode = parseInt(document.getElementById('light-mode').value) || 1;
      const hex = document.getElementById('light-color').value;
      document.getElementById('color-hex').innerText = hex;
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      let brightness = parseInt(document.getElementById('light-brightness').value);
      const speed = parseInt(document.getElementById('light-speed').value);

      const sideMode = parseInt(document.getElementById('side-mode') ? document.getElementById('side-mode').value : 1) || 1;
      const sideHex = document.getElementById('side-color') ? document.getElementById('side-color').value : '#00e5ff';
      const sideColorHexEl = document.getElementById('side-color-hex');
      if (sideColorHexEl) sideColorHexEl.innerText = sideHex;
      const sideR = parseInt(sideHex.slice(1, 3), 16);
      const sideG = parseInt(sideHex.slice(3, 5), 16);
      const sideB = parseInt(sideHex.slice(5, 7), 16);

      if (mode === 20) {
        brightness = 0;
        document.getElementById('light-brightness').value = 0;
        updateRange('bright-val', 0, ['0%', '25%', '50%', '75%', '100%']);
      } else if (isNaN(brightness) || brightness <= 0) {
        brightness = (rememberedBrightness > 0 ? rememberedBrightness : 4);
        document.getElementById('light-brightness').value = brightness;
        updateRange('bright-val', brightness, ['0%', '25%', '50%', '75%', '100%']);
      }
      updateColorVisibility(mode);

      try {
        localStorage.setItem('lt104_light_mode', mode);
        localStorage.setItem('lt104_light_color', hex);
        localStorage.setItem('lt104_light_brightness', brightness);
        localStorage.setItem('lt104_light_speed', speed);
        localStorage.setItem('lt104_side_mode', sideMode);
        localStorage.setItem('lt104_side_color', sideHex);

        const res = await fetch('/api/set-light', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            mode, r, g, b, brightness, speed,
            side_mode: sideMode,
            side_r: sideR, side_g: sideG, side_b: sideB
          })
        });
        const data = await res.json();
        if (data.success) {
          showToast('✅ ' + t('settings_applied'));
        } else {
          alert(t('clock_sync_fail') + ': ' + data.error);
        }
      } catch (e) {
        alert('Network Error: ' + e);
      }

    }

    async function syncClock() {
      const btn = document.getElementById('btn-sync-clock');
      btn.disabled = true;
      try {
        const res = await fetch('/api/sync-clock', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          showToast('🕒 ' + t('clock_synced'));
        } else {
          alert(t('clock_sync_fail') + ': ' + data.error);
        }
      } catch (e) {
        alert('Error: ' + e);
      } finally {
        btn.disabled = false;
      }
    }

    async function toggleClockSchedule(enable) {
      try {
        const res = await fetch('/api/clock-schedule', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enable })
        });
        const data = await res.json();
        if (data.success) {
          showToast(enable ? '⏱️ ' + t('clock_sched_on') : '⏹️ ' + t('clock_sched_off'));
        }
      } catch (e) {}
    }

    async function checkClockScheduleStatus() {
      try {
        const res = await fetch('/api/clock-schedule-status');
        const data = await res.json();
        document.getElementById('chk-clock-sched').checked = Boolean(data.enabled);
      } catch (e) {}
    }

    async function uploadLcdImage() {
      const fileInput = document.getElementById('lcd-file');
      if (!fileInput.files.length) {
        alert(t('select_file_warn'));
        return;
      }
      const file = fileInput.files[0];
      const formData = new FormData();
      formData.append('image', file);

      const statusEl = document.getElementById('upload-status');
      const progWrap = document.getElementById('progress-wrap');
      const progBar = document.getElementById('progress-bar');
      progWrap.style.display = 'block';
      progBar.style.width = '10%';
      statusEl.innerText = t('uploading');

      try {
        progBar.style.width = '40%';
        const res = await fetch('/api/upload-lcd', {
          method: 'POST',
          body: formData
        });
        progBar.style.width = '100%';
        const data = await res.json();
        if (data.success) {
          statusEl.innerText = '✅ ' + t('upload_success', { frames: data.frames });
          showToast('📺 ' + t('upload_success', { frames: data.frames }));
          if (typeof reloadLcdGif === 'function') setTimeout(reloadLcdGif, 500);
        } else {
          statusEl.innerText = '❌ ' + t('upload_fail') + ': ' + data.error;
          alert(t('upload_fail') + ': ' + data.error);
        }
      } catch (e) {
        statusEl.innerText = '❌ ' + e;
        alert(t('upload_fail') + ': ' + e);
      }
    }

    let hudRunning = false;
    let currentHudInterval = 120;

    function updateHudUI() {
      const badge = document.getElementById('hud-badge');
      const btn = document.getElementById('btn-toggle-hud');
      const sec = currentHudInterval || 120;
      if (hudRunning) {
        badge.innerText = t('running') + ' (' + sec + 's)';
        badge.style.color = '#34d399';
        btn.innerText = '⏹️ ' + t('hud_stop', { sec: sec });
        btn.style.background = 'linear-gradient(135deg, #dc2626, #ef4444)';
      } else {
        badge.innerText = t('stopped');
        badge.style.color = '#94a3b8';
        btn.innerText = '📊 ' + t('hud_start', { sec: sec });
        btn.style.background = 'linear-gradient(135deg, #059669, #10b981)';
      }

      const lcdCard = document.getElementById('card-lcd-upload');
      if (lcdCard) {
        lcdCard.style.display = hudRunning ? 'none' : 'block';
      }
    }

    async function checkHudStatus() {
      try {
        const res = await fetch('/api/hud-status');
        const data = await res.json();
        hudRunning = data.running;
        if (data.interval) {
          currentHudInterval = data.interval;
          document.getElementById('hud-interval').value = String(data.interval);
        }
        updateHudUI();
      } catch (e) {}
    }

    async function toggleHud() {
      const btn = document.getElementById('btn-toggle-hud');
      const interval = document.getElementById('hud-interval').value;
      btn.disabled = true;
      try {
        const endpoint = hudRunning ? '/api/hud-stop' : '/api/hud-start';
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ interval: parseFloat(interval) })
        });
        const data = await res.json();
        if (data.success) {
          showToast(hudRunning ? '⏹️ ' + t('hud_stopped') : '🚀 ' + t('hud_started', { sec: interval }));
        } else {
          alert('Error: ' + data.error);
        }
      } catch (e) {
        alert('Network error: ' + e);
      } finally {
        btn.disabled = false;
        checkHudStatus();
      }
    }

    async function pushHudOnce() {
      const btn = document.getElementById('btn-hud-once');
      btn.disabled = true;
      try {
        const res = await fetch('/api/hud-once', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          showToast('⚡ ' + t('hud_once_success'));
        } else {
          alert('Error: ' + data.error);
        }
      } catch (e) {
        alert('Error: ' + e);
      } finally {
        btn.disabled = false;
      }
    }

    async function restoreAnimation() {
      const btn = document.getElementById('btn-restore-anim');
      const presetSelect = document.getElementById('hud-restore-preset');
      const preset = presetSelect ? presetSelect.value : 'lt104_sample.gif';
      if (btn) btn.disabled = true;
      try {
        const res = await fetch('/api/hud-restore', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ preset })
        });
        const data = await res.json();
        if (data.success) {
          showToast('🔄 ' + t('hud_restore_success'));
          if (typeof reloadLcdGif === 'function') setTimeout(reloadLcdGif, 500);
        } else {
          alert('Error: ' + data.error);
        }
      } catch (e) {
        alert('Error: ' + e);
      } finally {
        if (btn) btn.disabled = false;
      }
    }

    async function onIntervalChanged() {
      const interval = document.getElementById('hud-interval').value;
      currentHudInterval = parseFloat(interval);
      localStorage.setItem('lt104_hud_interval', interval);
      updateHudUI();
      if (hudRunning) {
        await fetch('/api/hud-start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ interval: currentHudInterval })
        });
        showToast('⏱️ ' + t('hud_started', { sec: interval }));
        checkHudStatus();
      } else {
        showToast('⏱️ ' + t('hud_interval') + ': ' + interval + 's');
      }
    }

    async function onRestorePresetChanged() {
      const preset = document.getElementById('hud-restore-preset').value;
      localStorage.setItem('lt104_hud_restore_preset', preset);
      try {
        await fetch('/api/hud-restore-preset', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ preset })
        });
        showToast('💾 ' + t('hud_restore') + ': ' + preset);
      } catch (e) {}
    }

    async function checkDeviceStatus() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        const badge = document.getElementById('device-badge');
        if (data.connected) {
          badge.innerText = '● ' + t('connected');
          badge.className = 'status-badge';
        } else {
          badge.innerText = '● ' + t('disconnected');
          badge.className = 'status-badge error';
        }
      } catch (e) {}
    }

    let latestUpdateData = null;

    async function checkUpdates() {
      try {
        const res = await fetch('/api/check-update');
        const data = await res.json();
        latestUpdateData = data;
        const badge = document.getElementById('update-badge');
        const txt = document.getElementById('update-text');
        if (!badge || !txt) return;
        if (data.has_update) {
          const ver = data.latest_version || ('commit ' + data.latest_commit);
          txt.innerText = t('update_available', { ver });
          badge.href = data.release_url || data.html_url || 'https://github.com/iiaiiappa/lt104-keyboard-linux';
          badge.style.display = 'inline-flex';
          const notifiedKey = 'lt104_notified_' + ver;
          if (!sessionStorage.getItem(notifiedKey)) {
            sessionStorage.setItem(notifiedKey, '1');
            showToast('🚀 ' + t('update_toast', { ver }));
          }
        } else {
          badge.style.display = 'none';
        }
      } catch (e) {}
    }

    window.addEventListener('DOMContentLoaded', () => {
      // 1. Restore persistent user settings
      const savedMode = localStorage.getItem('lt104_light_mode') || SERVER_CONFIG.mode;
      if (savedMode) document.getElementById('light-mode').value = savedMode;
      previousModeVal = parseInt(document.getElementById('light-mode').value) || 1;
      updateColorVisibility(savedMode);

      const savedColor = localStorage.getItem('lt104_light_color') || SERVER_CONFIG.color;
      if (savedColor) {
        document.getElementById('light-color').value = savedColor;
        document.getElementById('color-hex').innerText = savedColor;
      }

      let savedBright = localStorage.getItem('lt104_light_brightness') !== null ? localStorage.getItem('lt104_light_brightness') : SERVER_CONFIG.brightness;
      const currentModeInt = parseInt(document.getElementById('light-mode').value) || 1;
      if (currentModeInt !== 20 && (savedBright === null || savedBright === undefined || parseInt(savedBright) <= 0)) {
        savedBright = (rememberedBrightness > 0 ? rememberedBrightness : 4);
      }
      if (savedBright !== undefined && savedBright !== null) {
        document.getElementById('light-brightness').value = savedBright;
        updateRange('bright-val', savedBright, ['0%', '25%', '50%', '75%', '100%']);
        if (parseInt(savedBright) > 0) {
          rememberedBrightness = parseInt(savedBright);
        }
      }

      const savedSpeed = localStorage.getItem('lt104_light_speed') !== null ? localStorage.getItem('lt104_light_speed') : SERVER_CONFIG.speed;
      if (savedSpeed !== undefined && savedSpeed !== null) {
        document.getElementById('light-speed').value = savedSpeed;
        updateRange('speed-val', savedSpeed);
      }

      const savedInterval = localStorage.getItem('lt104_hud_interval') || SERVER_CONFIG.hud_interval || 120;
      if (savedInterval) {
        currentHudInterval = parseFloat(savedInterval);
        document.getElementById('hud-interval').value = String(savedInterval);
      }

      const savedRestore = localStorage.getItem('lt104_hud_restore_preset') || SERVER_CONFIG.hud_restore_preset || 'lt104_sample.gif';
      if (savedRestore && document.getElementById('hud-restore-preset')) {
        document.getElementById('hud-restore-preset').value = savedRestore;
      }

      const savedSideMode = localStorage.getItem('lt104_side_mode') || SERVER_CONFIG.side_mode || 1;
      if (savedSideMode && document.getElementById('side-mode')) {
        document.getElementById('side-mode').value = String(savedSideMode);
      }
      updateSideColorVisibility(savedSideMode);

      const savedSideColor = localStorage.getItem('lt104_side_color') || SERVER_CONFIG.side_color || '#00e5ff';
      if (savedSideColor && document.getElementById('side-color')) {
        document.getElementById('side-color').value = savedSideColor;
        const sideColorHexEl = document.getElementById('side-color-hex');
        if (sideColorHexEl) sideColorHexEl.innerText = savedSideColor;
      }


      const savedAutoApply = localStorage.getItem('lt104_light_auto_apply');
      if (savedAutoApply !== null) {
        autoApplyLight = (savedAutoApply === 'true' || savedAutoApply === true);
      } else if (SERVER_CONFIG.light_auto_apply !== undefined) {
        autoApplyLight = Boolean(SERVER_CONFIG.light_auto_apply);
      } else {
        autoApplyLight = true;
      }
      updateAutoApplyUI();

      const initialLang = detectLanguage();
      changeLanguage(initialLang);
      checkDeviceStatus();
      checkHudStatus();
      checkClockScheduleStatus();
      checkUpdates();
      setInterval(checkHudStatus, 4000);
      setInterval(checkDeviceStatus, 5000);
      setInterval(checkUpdates, 1800000);
      initKeyboardPreview();
    });

    // -------------------------------------------------------------------------
    //  Photorealistic Keyboard Visualizer Preview Engine (Official 954x297 Skin)
    // -------------------------------------------------------------------------
    const KB_KEYS = __KB_KEYS_JSON__;

    let kbCanvas = null;
    let kbCtx = null;
    let hoveredKeyIdx = -1;
    let pressedKeyIdx = -1;
    let activeRipples = [];
    const keyFlashes = new Float32Array(KB_KEYS.length);
    let lastAutoTapTime = 0;
    let lastAutoRippleTime = 0;

    let dimStarKeys = [];
    let nextStarChangeTime = 0;

    function getKeyRow(ky) {
      if (ky < 45) return 0;
      if (ky < 90) return 1;
      if (ky < 130) return 2;
      if (ky < 172) return 3;
      if (ky < 213) return 4;
      return 5;
    }

    let skinNone = new Image();
    skinNone.src = '/static/keyboard_skin_none.png?v=1.0.3';
    let skinDark = new Image();
    skinDark.src = '/static/keyboard_skin_dark.png?v=1.0.3';
    let skinLit = new Image();
    skinLit.src = '/static/keyboard_skin_lit.png?v=1.0.3';
    let lcdGif = new Image();
    lcdGif.src = '/static/current_lcd.gif?v=1.0.3';

    skinNone.onload = () => { if (kbCtx) requestAnimationFrame(renderKeyboard); };
    skinDark.onload = () => { if (kbCtx) requestAnimationFrame(renderKeyboard); };
    skinLit.onload = () => { if (kbCtx) requestAnimationFrame(renderKeyboard); };

    // Offscreen canvas for fast pixel tinting
    let tintCanvas = document.createElement('canvas');
    tintCanvas.width = 954;
    tintCanvas.height = 297;
    let tintCtx = tintCanvas.getContext('2d');

    function reloadLcdGif() {
      lcdGif = new Image();
      lcdGif.src = '/static/current_lcd.gif?t=' + Date.now();
    }

    function hslToRgb(h, s, l) {
      h = ((h % 360) + 360) % 360 / 360;
      if (s === 0) return [Math.round(l * 255), Math.round(l * 255), Math.round(l * 255)];
      const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
      const p = 2 * l - q;
      const f = t => {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1/6) return p + (q - p) * 6 * t;
        if (t < 1/2) return q;
        if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
        return p;
      };
      return [Math.round(f(h + 1/3) * 255), Math.round(f(h) * 255), Math.round(f(h - 1/3) * 255)];
    }

    function hexToRgb(hex) {
      if (!hex || hex[0] !== '#') return [0, 229, 255];
      return [
        parseInt(hex.slice(1, 3), 16) || 0,
        parseInt(hex.slice(3, 5), 16) || 0,
        parseInt(hex.slice(5, 7), 16) || 0
      ];
    }

    function calcKeyColor(mode, k, idx, t, baseRgb, speedMult, brightMult) {
      if (mode === 20 || brightMult <= 0) return [0, 0, 0];
      const cx = k[1] + k[3] / 2;
      const cy = k[2] + k[4] / 2;

      switch (mode) {
        case 1: // 静态恒亮 (Static)
          return baseRgb;

        case 2: // 单点亮 (Single Light)
          // Lights OFF by default. When pressing a key, that key's light is ON. When not pressing, light back to OFF.
          if (idx === pressedKeyIdx) {
            return baseRgb;
          }
          return [0, 0, 0];

        case 3: // 单熄灭 (Single Off)
          // Lights on ALL the time. When pressing a key, the key's light is OFF. When not pressing, light is back ON.
          if (idx === pressedKeyIdx) {
            return [0, 0, 0];
          }
          return baseRgb;

        case 4: { // 繁星点点 (Stars)
          // All keys lit with static color, randomly turn off 2-3 keys for 0.5s when speed is 1
          if (dimStarKeys.includes(idx)) {
            return [0, 0, 0];
          }
          return baseRgb;
        }

        case 5: { // 漫天飞雪 (Snow)
          const row = getKeyRow(k[2]);
          const phase = (t * speedMult * 3.5 - row * 0.9 + (idx % 5) * 0.4) % 6.283;
          const val = Math.pow(Math.max(0, Math.sin(phase)), 3);
          return [Math.round(baseRgb[0] * val), Math.round(baseRgb[1] * val), Math.round(baseRgb[2] * val)];
        }

        case 6: { // 百花争艳 (Blossom)
          const cluster = Math.sin(cx * 0.015 + t * speedMult * 1.5) + Math.cos(cy * 0.03 + t * speedMult * 1.2);
          const hue = (cluster * 90 + t * speedMult * 40) % 360;
          return hslToRgb(hue, 1.0, 0.5);
        }

        case 7: { // 动态呼吸 (Breathing)
          const factor = 0.12 + 0.88 * (0.5 + 0.5 * Math.sin(t * speedMult * 2.5));
          return [Math.round(baseRgb[0] * factor), Math.round(baseRgb[1] * factor), Math.round(baseRgb[2] * factor)];
        }

        case 8: { // 光谱循环 (Spectrum Cycle)
          const hue = (t * speedMult * 50) % 360;
          return hslToRgb(hue, 1.0, 0.5);
        }

        case 9: { // 彩泉涌动 (Rainbow Wave)
          const hue = (cx * 0.5 - t * speedMult * 90) % 360;
          return hslToRgb(hue, 1.0, 0.5);
        }

        case 10: { // 多彩纵横 (Cross Pattern)
          // 7 rainbow colors alternating on 5 rows in the keyboard.
          // Each row uses different colors from 7 rainbow colors.
          // Each row changes its own color slowly without using color from other rows.
          // At Animation Speed 2 -> changes to another color every 0.5s.
          // Pressing keyboard has no reaction.
          const RAINBOW_7 = [
            [255, 0, 0],      // Red
            [255, 122, 0],    // Orange
            [255, 242, 0],    // Yellow
            [0, 224, 0],      // Green
            [0, 224, 255],    // Cyan
            [0, 56, 255],     // Blue
            [173, 0, 255]     // Purple
          ];
          const stepDur = 0.5 / speedMult;
          const step = Math.floor(t / stepDur);
          const prog = (t % stepDur) / stepDur;

          // 5 rows: F-keys(0), Numbers(1), QWERTY(2), ASDF(3), ZXCV+Space(4)
          const kRow = Math.min(4, getKeyRow(k[2]));
          const c1 = RAINBOW_7[(step + kRow) % 7];
          const c2 = RAINBOW_7[(step + 1 + kRow) % 7];

          const r = Math.round((1.0 - prog) * c1[0] + prog * c2[0]);
          const g = Math.round((1.0 - prog) * c1[1] + prog * c2[1]);
          const b = Math.round((1.0 - prog) * c1[2] + prog * c2[2]);
          return [r, g, b];
        }

        case 11: { // 随波逐流 (River Stream)
          const hue = ((cx + cy * 1.6) * 0.38 - t * speedMult * 80) % 360;
          return hslToRgb(hue, 1.0, 0.5);
        }

        case 12: { // 峰回路转 (Rotary Wave)
          const angle = Math.atan2(cy - 145, cx - 475);
          const hue = (angle * (180 / Math.PI) + t * speedMult * 90) % 360;
          return hslToRgb(hue, 1.0, 0.5);
        }

        case 13: // 一触即发 (Ripple Trigger) - spread purely from pressed keys along same row
        case 14: // 一石二鸟 (Dual Ripple) - spread horizontally from pressed keys
        case 15: // 涟漪扩散 (Ripple Spread) - concentric rings from pressed keys
          return [0, 0, 0];

        case 16: { // 川流不息 (Infinite Stream)
          // Speed slowed down in half: row duration doubled (1.10s base per row)
          // Stream object width: increased from 1 key to 5.4 keys in a row (sigma = 60.0px)
          // Motion: moving smoothly from left to right with Gaussian blur
          // Color: For each key, it assigns itself a random color sustained for each stream;
          //        each key uses another random color for other streams.
          const rowInterval = 1.10 / speedMult;
          const travelDur = 1.15 * rowInterval;
          const sigma = 60.0; // 5.4 keys Gaussian blur width (5.4 * 41px = 221.4px)
          const xStart = -140.0;
          const xEnd = 1098.0;

          const kRow = getKeyRow(k[2]);
          const sBase = Math.floor(t / rowInterval);

          let totalR = 0.0;
          let totalG = 0.0;
          let totalB = 0.0;

          // Check nearby stream passes for this row (at most 1 is active on this row)
          for (let s = sBase - 1; s <= sBase + 1; s++) {
            if (s < 0 || (((s % 6) + 6) % 6) !== kRow) continue;
            const tEl = t - s * rowInterval;
            if (tEl >= 0.0 && tEl <= travelDur) {
              const prog = tEl / travelDur;
              const swipeX = xStart + prog * (xEnd - xStart);
              const distX = Math.abs(cx - swipeX);
              const val = Math.exp(-(distX * distX) / (2.0 * sigma * sigma));
              if (val > 0.005) {
                // Deterministic random hue unique to this (key, stream) combination,
                // sustained continuously throughout the entire passage of this stream
                let h = ((idx * 0x1f1f1f1f + s * 0x3d3d3d3d) >>> 0);
                h = Math.imul(h ^ (h >>> 16), 0x45d9f3b) >>> 0;
                h = Math.imul(h ^ (h >>> 16), 0x45d9f3b) >>> 0;
                const hue = ((h ^ (h >>> 16)) >>> 0) % 360;

                const c = hslToRgb(hue, 1.0, 0.5);
                totalR += c[0] * val;
                totalG += c[1] * val;
                totalB += c[2] * val;
              }
            }
          }

          return [Math.min(255, Math.round(totalR)), Math.min(255, Math.round(totalG)), Math.min(255, Math.round(totalB))];
        }

        case 17: { // 重峦叠嶂 (Rolling Hills)
          // Background all off, 2.5-keys wide 45° slashes with Gaussian blur.
          // Slashes emerge from the 50% middle of keyboard:
          // - Left side (cx <= midX): forward slash (/) and inserted backslash (\\\\) alternating, 3 keys apart, sweeping to the left without bouncing.
          // - Right side (cx >= midX): backslash (\\\\) and inserted forward slash (/) alternating, 3 keys apart, sweeping to the right without bouncing.
          // No cross in the middle of keyboard, 3 keys apart between slashes.
          const midX = 479.0;
          const midY = 141.5;
          const waveSpeed = 220.0 * speedMult;
          const slashSpacing = 164.0; // Exactly 3 unlit keys apart between slashes (4 * 41px pitch)
          const spawnInterval = slashSpacing / waveSpeed; // Delay between alternating slashes
          const travelDuration = 550.0 / waveSpeed; // Distance to edge
          const sigma = 28.0; // 2.5 keys width Gaussian blur (2.5 * 41px ~ 102.5px full span at 95% width, sigma ~ 28px)

          const spawnB = midX - midY;
          const spawnF = midX + midY;

          let maxVal = 0.0;
          let activeHue = 0;

          const currentWaveIndex = Math.floor(t / spawnInterval);
          for (let w = currentWaveIndex - 6; w <= currentWaveIndex; w++) {
            if (w < 0) continue;
            const waveAge = t - w * spawnInterval;
            if (waveAge < 0 || waveAge > travelDuration) continue;

            const distTravelled = waveAge * waveSpeed;

            // Left side (cx <= midX): sweeps to the left
            if (cx <= midX) {
              let dist = 999.0;
              if (w % 2 === 0) {
                // Forward slash (/) sweeping left
                const coordF = cx + cy;
                const waveCoord = spawnF - distTravelled;
                dist = Math.abs(coordF - waveCoord);
              } else {
                // Inserted backslash (\\\\) between forward slashes sweeping left
                const coordB = cx - cy;
                const waveCoord = spawnB - distTravelled;
                dist = Math.abs(coordB - waveCoord);
              }

              const val = Math.exp(-(dist * dist) / (2.0 * sigma * sigma));
              if (val > 0.005 && val > maxVal) {
                maxVal = val;
                activeHue = ((w * 67) + 180 + 360) % 360;
              }
            }

            // Right side (cx >= midX): sweeps to the right
            if (cx >= midX) {
              let dist = 999.0;
              if (w % 2 === 0) {
                // Backslash (\\\\) sweeping right
                const coordB = cx - cy;
                const waveCoord = spawnB + distTravelled;
                dist = Math.abs(coordB - waveCoord);
              } else {
                // Inserted forward slash (/) between backslashes sweeping right
                const coordF = cx + cy;
                const waveCoord = spawnF + distTravelled;
                dist = Math.abs(coordF - waveCoord);
              }

              const val = Math.exp(-(dist * dist) / (2.0 * sigma * sigma));
              if (val > 0.005 && val > maxVal) {
                maxVal = val;
                activeHue = ((w * 67) + 360) % 360;
              }
            }
          }

          if (maxVal < 0.01) return [0, 0, 0];

          // Per-key random color that smoothly changes every second (scaled by speedMult)
          const secStep = t * speedMult;
          const currSec = Math.floor(secStep);
          const frac = secStep - currSec;

          const getKeySecRgb = (kIdx, sIdx) => {
            let h = ((kIdx * 0x1f1f1f1f + sIdx * 0x3d3d3d3d) >>> 0);
            h = Math.imul(h ^ (h >>> 16), 0x45d9f3b) >>> 0;
            h = Math.imul(h ^ (h >>> 16), 0x45d9f3b) >>> 0;
            const hue = ((h ^ (h >>> 16)) >>> 0) % 360;
            return hslToRgb(hue, 1.0, 0.5);
          };

          const c1 = getKeySecRgb(idx, currSec);
          const c2 = getKeySecRgb(idx, currSec + 1);
          const crK = c1[0] + (c2[0] - c1[0]) * frac;
          const cgK = c1[1] + (c2[1] - c1[1]) * frac;
          const cbK = c1[2] + (c2[2] - c1[2]) * frac;

          return [Math.round(crK * maxVal), Math.round(cgK * maxVal), Math.round(cbK * maxVal)];
        }

        case 18: { // 斜风细雨 (Gentle Rain)
          // Multiple 45° backslashes (cx - cy) sweeping continuously from left to right.
          // Spacing: Exactly 5 keys apart from middle of backslash to middle of next backslash (5 * 41px = 205px).
          // Width: 1.8 keys width with Gaussian blur (sigma = 20.0px).
          // Color: For each key, it assigns itself a random color sustained for each backslash,
          //        using another random color for other backslashes.
          // Seamless fade-in and fade-out transitions; slashes flow continuously without on/off popping.
          const waveSpeed = 180.0 * speedMult;
          const slashSpacing = 205.0; // 5 keys pitch from middle of backslash to next middle
          const sigma = 20.0;         // 1.8 keys Gaussian blur width
          const coordB = cx - cy;
          const globalPhase = t * waveSpeed;

          // Check active adjacent slashes
          const kCenter = (coordB - globalPhase) / slashSpacing;
          const kMin = Math.floor(kCenter - 1);
          const kMax = Math.ceil(kCenter + 1);

          let totalR = 0;
          let totalG = 0;
          let totalB = 0;

          for (let k = kMin; k <= kMax; k++) {
            const linePos = k * slashSpacing + globalPhase;
            const dist = Math.abs(coordB - linePos);
            // Gaussian blur falloff across 1.8 keys width
            const val = Math.exp(-(dist * dist) / (2.0 * sigma * sigma));
            if (val > 0.005) {
              // Deterministic random hue unique to this (key, slash) combination,
              // sustained continuously throughout the entire passage of this backslash
              let h = ((idx * 0x1f1f1f1f + k * 0x3d3d3d3d) >>> 0);
              h = Math.imul(h ^ (h >>> 16), 0x45d9f3b) >>> 0;
              h = Math.imul(h ^ (h >>> 16), 0x45d9f3b) >>> 0;
              const hue = ((h ^ (h >>> 16)) >>> 0) % 360;

              const c = hslToRgb(hue, 1.0, 0.5);
              totalR += c[0] * val;
              totalG += c[1] * val;
              totalB += c[2] * val;
            }
          }

          if (totalR < 1 && totalG < 1 && totalB < 1) return [0, 0, 0];
          return [
            Math.min(255, Math.round(totalR)),
            Math.min(255, Math.round(totalG)),
            Math.min(255, Math.round(totalB))
          ];
        }

        case 19: { // 来回穿梭 (Shuttle)
          // Slow flowing harmonic wave across the whole board (does not react to keypresses)
          const hue = (cx * 0.45 - t * speedMult * 35.0 + Math.sin(cy * 0.04) * 40.0 + 360) % 360;
          return hslToRgb(hue, 1.0, 0.5);
        }

        default:
          return baseRgb;
      }
    }

    function renderKeyboard() {
      if (!kbCanvas || !kbCtx) { requestAnimationFrame(renderKeyboard); return; }
      try {
      const now = performance.now();
      const t = now / 1000;

      // Read live form inputs
      const modeEl = document.getElementById('light-mode');
      const modeVal = parseInt(modeEl ? modeEl.value : 1) || 1;
      const hex = (document.getElementById('light-color') ? document.getElementById('light-color').value : '#00e5ff');
      const baseRgb = hexToRgb(hex);
      const brightInput = document.getElementById('light-brightness');
      const brightVal = parseInt(brightInput ? brightInput.value : 4);
      const speedInput = document.getElementById('light-speed');
      const speedVal = parseInt(speedInput ? speedInput.value : 3);

      const brightMult = (modeVal === 20 ? 0 : [0.25, 0.45, 0.65, 0.85, 1.0][brightVal] || 1.0);
      const speedMult = [0.4, 0.7, 1.0, 1.6, 2.4][speedVal] || 1.0;

      // Update mode badge in header
      const modeTag = document.getElementById('kb-preview-mode-tag');
      if (modeTag && modeEl && modeEl.selectedIndex >= 0) {
        modeTag.innerText = modeEl.options[modeEl.selectedIndex].text;
      }

      // Mode 4 Stars: randomly turn off 2 to 3 keys for 0.5s when animation speed is 1
      if (modeVal === 4 && now >= nextStarChangeTime) {
        const count = 2 + Math.floor(Math.random() * 2); // 2 or 3 keys
        dimStarKeys = [];
        for (let c = 0; c < count; c++) {
          dimStarKeys.push(Math.floor(Math.random() * KB_KEYS.length));
        }
        nextStarChangeTime = now + (500 / speedMult);
      }

      // Decay key flashes
      for (let i = 0; i < keyFlashes.length; i++) {
        if (keyFlashes[i] > 0.001) keyFlashes[i] *= 0.94;
      }


      // Simulated ripple for Ripple Trigger / Dual Ripple / Ripple Spread modes
      if ((modeVal === 13 || modeVal === 14 || modeVal === 15) && (now - lastAutoRippleTime > 2400)) {
        const randKey = KB_KEYS[Math.floor(Math.random() * KB_KEYS.length)];
        activeRipples.push({
          x: randKey[1] + randKey[3] / 2,
          y: randKey[2] + randKey[4] / 2,
          row: getKeyRow(randKey[2]),
          t: now,
          color: baseRgb,
          mode: modeVal
        });
        lastAutoRippleTime = now;
      }

      // Filter active ripples
      activeRipples = activeRipples.filter(r => (now - r.t) < 1100);

      // Clear main canvas
      kbCtx.clearRect(0, 0, kbCanvas.width, kbCanvas.height);

      // 1. Draw keyboard background base
      kbCtx.fillStyle = '#090b14';
      kbCtx.fillRect(0, 0, 954, 297);

      // 2. Draw lighting blocks behind the keyboard card
      if (brightMult > 0) {
        if (modeVal === 1 && activeRipples.length === 0) {
          // STATIC MODE: Uniform colored lighting behind keys
          const staticR = Math.round(baseRgb[0] * brightMult);
          const staticG = Math.round(baseRgb[1] * brightMult);
          const staticB = Math.round(baseRgb[2] * brightMult);
          kbCtx.fillStyle = `rgb(${staticR}, ${staticG}, ${staticB})`;
          for (let i = 0; i < KB_KEYS.length; i++) {
            const [, kx, ky, kw, kh] = KB_KEYS[i];
            kbCtx.fillRect(kx - 1, ky - 1, kw + 2, kh + 2);
          }
        } else {
          // DYNAMIC MODES: Render light blocks per key behind keyboard card
          for (let i = 0; i < KB_KEYS.length; i++) {
            const k = KB_KEYS[i];
            const [, kx, ky, kw, kh] = k;
            const cx = kx + kw / 2;
            const cy = ky + kh / 2;

            let [r, g, b] = calcKeyColor(modeVal, k, i, t, baseRgb, speedMult, brightMult);

            // Active ripples overlay (Modes 2 Single Light, 3 Single Off, 5 Snow, 10 Cross Pattern, 16 Infinite Stream, 17 Rolling Hills, 18 Gentle Rain, 19 Shuttle do not react to keypresses)
            if (modeVal !== 2 && modeVal !== 3 && modeVal !== 5 && modeVal !== 10 && modeVal !== 16 && modeVal !== 17 && modeVal !== 18 && modeVal !== 19) {
              for (let j = 0; j < activeRipples.length; j++) {
                const rip = activeRipples[j];
                const age = (now - rip.t) / 1000;
                const ripMode = rip.mode || modeVal;

                if (ripMode === 13) {
                  // Ripple Trigger: spreads left and right on the same row ONLY
                  const kRow = getKeyRow(k[2]);
                  if (kRow === rip.row) {
                    const dx = Math.abs(cx - rip.x);
                    const waveFront = age * 540;
                    const diff = Math.abs(dx - waveFront);
                    if (diff < 36) {
                      const amp = Math.max(0, (1 - age / 0.85) * (1 - diff / 36));
                      r = Math.min(255, r + Math.round(rip.color[0] * amp));
                      g = Math.min(255, g + Math.round(rip.color[1] * amp));
                      b = Math.min(255, b + Math.round(rip.color[2] * amp));
                    }
                  }
                } else if (ripMode === 14) {
                  // Dual Ripple: colorful keys separate towards left and right
                  const dx = Math.abs(cx - rip.x);
                  const waveFront = age * 500;
                  const diff = Math.abs(dx - waveFront);
                  if (diff < 42) {
                    const amp = Math.max(0, (1 - age / 0.95) * (1 - diff / 42));
                    const hue = (dx * 0.9 + age * 180 + k[2] * 0.3) % 360;
                    const c = hslToRgb(hue, 1.0, 0.5);
                    r = Math.min(255, r + Math.round(c[0] * amp));
                    g = Math.min(255, g + Math.round(c[1] * amp));
                    b = Math.min(255, b + Math.round(c[2] * amp));
                  }
                } else if (ripMode === 15) {
                  // Ripple Spread: colorful keys separate outward circles like a ripple, width 3 keys
                  const dist = Math.hypot(cx - rip.x, cy - rip.y);
                  const waveFront = age * 420;
                  const diff = Math.abs(dist - waveFront);
                  if (diff < 48) { // 3 keys width
                    const amp = Math.max(0, (1 - age / 1.1) * (1 - diff / 48));
                    const hue = (dist * 1.2 - age * 140 + Math.atan2(cy - rip.y, cx - rip.x) * 180 / Math.PI) % 360;
                    const c = hslToRgb(hue, 1.0, 0.5);
                    r = Math.min(255, r + Math.round(c[0] * amp));
                    g = Math.min(255, g + Math.round(c[1] * amp));
                    b = Math.min(255, b + Math.round(c[2] * amp));
                  }
                } else {
                  // Generic ripple on click
                  const ripDist = Math.hypot(cx - rip.x, cy - rip.y);
                  const waveFront = age * 480;
                  const diff = Math.abs(ripDist - waveFront);
                  if (diff < 45) {
                    const rippleAmp = Math.max(0, (1 - age / 0.9) * (1 - diff / 45));
                    r = Math.min(255, r + Math.round(rip.color[0] * rippleAmp));
                    g = Math.min(255, g + Math.round(rip.color[1] * rippleAmp));
                    b = Math.min(255, b + Math.round(rip.color[2] * rippleAmp));
                  }
                }
              }
            }

            r = Math.round(r * brightMult);
            g = Math.round(g * brightMult);
            b = Math.round(b * brightMult);

            if (r > 0 || g > 0 || b > 0) {
              kbCtx.fillStyle = `rgb(${r}, ${g}, ${b})`;
              kbCtx.fillRect(kx - 1, ky - 1, kw + 2, kh + 2);
            }
          }
        }
      }

      // 3. Draw singledevice_keyboardK870T_none keyboard card ON TOP of the lighting blocks
      if (skinNone.complete && skinNone.naturalWidth > 0) {
        kbCtx.drawImage(skinNone, 0, 0, 954, 297);
      } else if (skinDark.complete && skinDark.naturalWidth > 0) {
        kbCtx.drawImage(skinDark, 0, 0, 954, 297);
      }

      // 3. Hover Ring Highlight
      if (hoveredKeyIdx >= 0 && hoveredKeyIdx < KB_KEYS.length) {
        const [, hx, hy, hw, hh] = KB_KEYS[hoveredKeyIdx];
        kbCtx.save();
        kbCtx.strokeStyle = 'rgba(255, 255, 255, 0.65)';
        kbCtx.lineWidth = 1.5;
        kbCtx.strokeRect(hx, hy, hw, hh);
        kbCtx.restore();
      }

      // 4. Reactive LCD Screen (X=808, Y=18, W=62, H=39)
      kbCtx.save();
      kbCtx.beginPath();
      kbCtx.rect(808, 18, 62, 39);
      kbCtx.clip();

      if (hudRunning) {
        // Real-time HUD Mode: Display live hardware telemetry & clock
        kbCtx.fillStyle = '#030813';
        kbCtx.fillRect(808, 18, 62, 39);

        const d = new Date();
        const timeStr = String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0') + ':' + String(d.getSeconds()).padStart(2,'0');

        // Clock header
        kbCtx.fillStyle = '#38bdf8';
        kbCtx.font = 'bold 7px monospace';
        kbCtx.textAlign = 'center';
        kbCtx.fillText(timeStr, 839, 26);

        // Divider
        kbCtx.fillStyle = '#1e293b';
        kbCtx.fillRect(810, 28, 58, 1);

        // CPU row
        kbCtx.font = '6px monospace';
        kbCtx.textAlign = 'left';
        kbCtx.fillStyle = '#94a3b8';
        kbCtx.fillText('C', 811, 35);
        kbCtx.fillStyle = '#10b981';
        kbCtx.fillRect(818, 30, 14, 4);
        kbCtx.fillText('28%', 844, 35);

        // RAM row
        kbCtx.fillStyle = '#94a3b8';
        kbCtx.fillText('R', 811, 43);
        kbCtx.fillStyle = '#06b6d4';
        kbCtx.fillRect(818, 38, 20, 4);
        kbCtx.fillText('52%', 844, 43);

        // Dynamic Equalizer bars
        const barCount = 7;
        const barW = 6;
        for (let bi = 0; bi < barCount; bi++) {
          const barH = 2 + Math.abs(Math.sin(t * 3.5 + bi * 0.9)) * 5;
          const bx = 811 + bi * 8;
          kbCtx.fillStyle = (bi % 2 === 0 ? '#10b981' : '#06b6d4');
          kbCtx.fillRect(bx, 55 - barH, barW, barH);
        }
      } else {
        // GIF Animation Mode: Render active custom/preset LCD GIF
        if (lcdGif.complete && lcdGif.naturalWidth > 0) {
          kbCtx.drawImage(lcdGif, 808, 18, 62, 39);
        } else {
          kbCtx.fillStyle = '#030813';
          kbCtx.fillRect(808, 18, 62, 39);
          kbCtx.fillStyle = '#38bdf8';
          kbCtx.font = 'bold 7.5px monospace';
          kbCtx.textAlign = 'center';
          kbCtx.fillText('LT-104', 839, 39);
        }
      }
      kbCtx.restore();

      // 5. Left & Right Edge Ambient Light Strips (侧翼灯带)
      const sideModeEl = document.getElementById('side-mode');
      const sideModeVal = parseInt(sideModeEl ? sideModeEl.value : 1) || 1;
      const sideColorHex = (document.getElementById('side-color') ? document.getElementById('side-color').value : '#00e5ff');
      const sideBaseRgb = hexToRgb(sideColorHex);

      if (sideModeVal !== 0 && brightMult > 0) {
        let sr = sideBaseRgb[0], sg = sideBaseRgb[1], sb = sideBaseRgb[2];
        if (sideModeVal === 1) {        // 动态呼吸 (Breathing)
          const breath = (Math.sin(t * speedMult * 3.0) + 1.0) * 0.45 + 0.1;
          sr = Math.round(sr * breath);
          sg = Math.round(sg * breath);
          sb = Math.round(sb * breath);
        } else if (sideModeVal === 2) { // 幻彩循环 (Spectrum Cycle)
          const hue = (t * speedMult * 60.0) % 360.0;
          [sr, sg, sb] = hslToRgb(hue, 1.0, 0.5);
        } else if (SIDE_PRESET_COLORS[sideModeVal]) {
          // Modes 3-10: Red, Orange, Yellow, Green, Cyan, Blue, Magenta, White
          const prRgb = hexToRgb(SIDE_PRESET_COLORS[sideModeVal]);
          sr = prRgb[0]; sg = prRgb[1]; sb = prRgb[2];
        }

        sr = Math.round(Math.min(255, sr * brightMult));
        sg = Math.round(Math.min(255, sg * brightMult));
        sb = Math.round(Math.min(255, sb * brightMult));

        // Helper to draw rounded rectangle in canvas
        function fillRoundRect(ctx, x, y, w, h, r) {
          ctx.beginPath();
          ctx.moveTo(x + r, y);
          ctx.lineTo(x + w - r, y);
          ctx.quadraticCurveTo(x + w, y, x + w, y + r);
          ctx.lineTo(x + w, y + h - r);
          ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
          ctx.lineTo(x + r, y + h);
          ctx.quadraticCurveTo(x, y + h, x, y + h - r);
          ctx.lineTo(x, y + r);
          ctx.quadraticCurveTo(x, y, x + r, y);
          ctx.closePath();
          ctx.fill();
        }

        // Outer glow
        kbCtx.fillStyle = `rgba(${sr}, ${sg}, ${sb}, 0.45)`;
        fillRoundRect(kbCtx, 1, 26, 12, 245, 6);
        fillRoundRect(kbCtx, 941, 26, 12, 245, 6);

        // Core light strip
        const cr = Math.min(255, Math.round(sr * 1.3));
        const cg = Math.min(255, Math.round(sg * 1.3));
        const cb = Math.min(255, Math.round(sb * 1.3));
        kbCtx.fillStyle = `rgba(${cr}, ${cg}, ${cb}, 0.92)`;
        fillRoundRect(kbCtx, 4, 30, 6, 237, 3);
        fillRoundRect(kbCtx, 944, 30, 6, 237, 3);
      }

      } catch(e) { /* render error: keep loop alive */ }
      requestAnimationFrame(renderKeyboard);
    }


    function initKeyboardPreview() {
      kbCanvas = document.getElementById('kb-preview');
      if (!kbCanvas) return;
      kbCtx = kbCanvas.getContext('2d');

      // Force explicit CSS height based on aspect ratio (canvas != img, height:auto doesn't work)
      function fixCanvasHeight() {
        const cssW = kbCanvas.offsetWidth;
        if (cssW > 0) {
          kbCanvas.style.height = Math.round(cssW * 297 / 954) + 'px';
        }
      }
      fixCanvasHeight();
      window.addEventListener('resize', fixCanvasHeight);

      // Mouse interactive reaction
      function getCanvasPos(e) {
        const rect = kbCanvas.getBoundingClientRect();
        const scaleX = kbCanvas.width / rect.width;
        const scaleY = kbCanvas.height / rect.height;
        return {
          x: (e.clientX - rect.left) * scaleX,
          y: (e.clientY - rect.top) * scaleY
        };
      }

      function findKeyAt(pos) {
        for (let i = 0; i < KB_KEYS.length; i++) {
          const [, kx, ky, kw, kh] = KB_KEYS[i];
          if (pos.x >= kx && pos.x <= kx + kw && pos.y >= ky && pos.y <= ky + kh) {
            return i;
          }
        }
        return -1;
      }

      kbCanvas.addEventListener('mousemove', e => {
        const pos = getCanvasPos(e);
        hoveredKeyIdx = findKeyAt(pos);
      });

      kbCanvas.addEventListener('mouseleave', () => {
        hoveredKeyIdx = -1;
        pressedKeyIdx = -1;
      });

      kbCanvas.addEventListener('mouseup', () => {
        pressedKeyIdx = -1;
      });

      window.addEventListener('mouseup', () => {
        pressedKeyIdx = -1;
      });

      kbCanvas.addEventListener('mousedown', e => {
        const pos = getCanvasPos(e);
        const idx = findKeyAt(pos);
        pressedKeyIdx = idx;
        const hex = (document.getElementById('light-color') ? document.getElementById('light-color').value : '#00e5ff');
        const color = hexToRgb(hex);
        const modeEl = document.getElementById('light-mode');
        const modeVal = parseInt(modeEl ? modeEl.value : 1) || 1;
        if (modeVal === 2 || modeVal === 3 || modeVal === 5 || modeVal === 10 || modeVal === 16 || modeVal === 17 || modeVal === 18 || modeVal === 19) return; // Modes 2, 3 have NO ripples. Modes 5 (Snow), 10, 16, 17, 18, 19 do not react
        if (idx >= 0) {
          keyFlashes[idx] = 1.0;
          const [, kx, ky, kw, kh] = KB_KEYS[idx];
          const kRow = getKeyRow(ky);
          activeRipples.push({ x: kx + kw / 2, y: ky + kh / 2, row: kRow, t: performance.now(), color, mode: modeVal });
        } else {
          const kRow = getKeyRow(pos.y);
          activeRipples.push({ x: pos.x, y: pos.y, row: kRow, t: performance.now(), color, mode: modeVal });
        }
      });

      requestAnimationFrame(renderKeyboard);
    }
  </script>
</body>
</html>
"""

class LT104Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Quiet logs

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            options_html = ""
            for m in LIGHT_MODES:
                options_html += f'<option value="{m["id"]}">{m["name"]}</option>\n'

            side_options_html = ""
            for sm in SIDE_LIGHT_MODES:
                side_options_html += f'<option value="{sm["id"]}">{sm["name"]}</option>\n'

            html = HTML_PAGE.replace("__LIGHT_OPTIONS__", options_html)
            html = html.replace("__SIDE_LIGHT_OPTIONS__", side_options_html)
            html = html.replace("__I18N_JSON__", json.dumps(i18n.TRANSLATIONS))
            html = html.replace("__CONFIG_JSON__", json.dumps(load_config()))
            html = html.replace("__KB_KEYS_JSON__", json.dumps(KB_KEYS))

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif self.path == "/api/config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(load_config()).encode())

        elif self.path == "/api/status":
            usb_dev = find_lt104_usb()
            lcd_dev = find_lt104_lcd_hidraw()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "connected": bool(usb_dev),
                "usb_dev": usb_dev,
                "lcd_dev": lcd_dev
            }).encode())

        elif self.path == "/api/hud-status":
            global HUD_PROC, HUD_INTERVAL
            running = False
            if HUD_PROC:
                if HUD_PROC.poll() is None:
                    running = True
                else:
                    HUD_PROC = None
            if not running and os.path.exists("/tmp/lt104_indicator.pid"):
                try:
                    p = int(open("/tmp/lt104_indicator.pid").read().strip())
                    os.kill(p, 0)
                    running = True
                except (OSError, ValueError):
                    pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"running": running, "interval": HUD_INTERVAL}).encode())

        elif self.path == "/api/clock-schedule-status":
            timer_path = os.path.expanduser("~/.config/systemd/user/timers.target.wants/lt104-clock-sync.timer")
            enabled = os.path.exists(timer_path)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"enabled": enabled}).encode())

        elif self.path == "/api/check-update":
            up_info = check_github_updates()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps(up_info).encode())

        elif self.path.startswith("/static/"):
            clean_sub = self.path[len("/static/"):].split("?")[0]
            file_path = os.path.join(STATIC_DIR, clean_sub)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                ext = clean_sub.split(".")[-1].lower()
                mime = "image/png" if ext == "png" else ("image/gif" if ext == "gif" else "application/octet-stream")
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global HUD_PROC, HUD_INTERVAL
        if self.path == "/api/set-light":
            content_len = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_len).decode())
            try:
                mode = int(body.get("mode", 1))
                r = int(body.get("r", 0))
                g = int(body.get("g", 255))
                b = int(body.get("b", 255))
                brightness = int(body.get("brightness", 4))
                speed = int(body.get("speed", 3))

                side_mode = int(body.get("side_mode", 1))
                side_r = int(body.get("side_r", 0))
                side_g = int(body.get("side_g", 229))
                side_b = int(body.get("side_b", 255))

                ctl = LT104Controller()
                ctl.set_light(mode=mode, r=r, g=g, b=b, brightness=brightness, speed=speed)
                try:
                    ctl.set_side_light(mode=side_mode, r=side_r, g=side_g, b=side_b, brightness=brightness, speed=speed)
                except Exception:
                    pass
                ctl.close()

                save_config({
                    "mode": mode,
                    "color": f"#{r:02x}{g:02x}{b:02x}",
                    "r": r, "g": g, "b": b,
                    "brightness": brightness,
                    "speed": speed,
                    "side_mode": side_mode,
                    "side_color": f"#{side_r:02x}{side_g:02x}{side_b:02x}",
                    "side_r": side_r, "side_g": side_g, "side_b": side_b
                })
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode())
            except Exception as e:

                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())

        elif self.path == "/api/sync-clock":
            try:
                last_err = None
                for attempt in range(3):
                    try:
                        ctl = LT104Controller()
                        ctl.sync_clock()
                        ctl.close()
                        last_err = None
                        break
                    except OSError as e:
                        last_err = e
                        if e.errno in (16, 11) and attempt < 2:
                            time.sleep(0.2 * (attempt + 1))
                            continue
                        raise
                if last_err:
                    raise last_err
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())

        elif self.path == "/api/clock-schedule":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(content_len).decode())
                enable = bool(body.get("enable", False))
                cli_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lt104_cli.py")
                cmd = ["/usr/bin/python3", cli_script,
                       "clock-schedule-enable" if enable else "clock-schedule-disable"]
                subprocess.run(cmd, check=False)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "enabled": enable}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())

        elif self.path == "/api/upload-lcd":
            try:
                content_type = self.headers.get("Content-Type", "")
                content_len = int(self.headers.get("Content-Length", 0))
                data = self.rfile.read(content_len)

                # Multipart parser
                boundary = content_type.split("boundary=")[-1].encode()
                parts = data.split(b"--" + boundary)
                file_bytes = None
                for part in parts:
                    if b'filename="' in part:
                        header_end = part.find(b"\r\n\r\n")
                        if header_end != -1:
                            file_bytes = part[header_end + 4:].rstrip(b"\r\n")
                            break

                if not file_bytes:
                    raise ValueError("No file uploaded")

                with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as tmp:
                    tmp.write(file_bytes)
                    tmp_path = tmp.name

                ctl = LT104Controller()
                frames = ctl.upload_lcd_image(tmp_path)
                ctl.close()
                update_lcd_cache(tmp_path)
                os.unlink(tmp_path)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "frames": frames}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())

        elif self.path == "/api/hud-start":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                if content_len > 0:
                    try:
                        req_data = json.loads(self.rfile.read(content_len).decode())
                        HUD_INTERVAL = float(req_data.get("interval", 20.0))
                    except Exception:
                        pass

                cli_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lt104_cli.py")
                subprocess.run([sys.executable, cli_script, "hud-stop"], check=False)
                subprocess.run([sys.executable, cli_script, "hud-start", "--interval", str(HUD_INTERVAL)], check=False)
                save_config({"hud_interval": HUD_INTERVAL})

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "interval": HUD_INTERVAL}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())

        elif self.path == "/api/hud-stop":
            try:
                cli_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lt104_cli.py")
                subprocess.run([sys.executable, cli_script, "hud-stop"], check=False)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())

        elif self.path == "/api/hud-restore-preset":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                req_data = json.loads(self.rfile.read(content_len).decode())
                preset = req_data.get("preset", "lt104_sample.gif")
                save_config({"hud_restore_preset": preset})
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "preset": preset}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())

        elif self.path == "/api/hud-restore":
            try:
                preset = "lt104_sample.gif"
                content_len = int(self.headers.get("Content-Length", 0))
                if content_len > 0:
                    try:
                        req_data = json.loads(self.rfile.read(content_len).decode())
                        preset = req_data.get("preset", preset)
                    except Exception:
                        pass
                cli_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lt104_cli.py")
                cmd = [sys.executable, cli_script, "hud-restore"]
                if preset:
                    cmd.extend(["--preset", preset])
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                if res.returncode == 0:
                    if preset and preset != "none":
                        preset_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), preset)
                        if os.path.exists(preset_file):
                            update_lcd_cache(preset_file)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True, "preset": preset}).encode())
                else:
                    err_msg = res.stderr.strip() or res.stdout.strip() or f"CLI returned code {res.returncode}"
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": False, "error": err_msg}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())

        elif self.path == "/api/hud-once":
            try:
                cli_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lt104_cli.py")
                res = subprocess.run([sys.executable, cli_script, "hud-once"], capture_output=True, text=True, timeout=10)
                if res.returncode == 0:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True}).encode())
                else:
                    err_msg = res.stderr.strip() or res.stdout.strip() or f"CLI returned code {res.returncode}"
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": False, "error": err_msg}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

def run_server(port=8989):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), LT104Handler)
    print(f"LT104 Linux Native Server running at http://127.0.0.1:{port}")
    server.serve_forever()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8989
    run_server(port)
