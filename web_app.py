#!/usr/bin/env python3
"""
Web Control Panel for LT104 Keyboard on Ubuntu Linux
Multi-language support for all Ubuntu desktop locales.
Runs on http://127.0.0.1:8989
"""
import http.server
import json
import urllib.parse
import os
import sys
import tempfile
import subprocess
import signal

from lt104_core import LT104Controller, LIGHT_MODES, find_lt104_usb, find_lt104_lcd_hidraw
import i18n
from config import load_config, save_config

CFG = load_config()
HUD_PROC = None
HUD_INTERVAL = float(CFG.get("hud_interval", 120.0))

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title id="page-title">LT-104 Keyboard Control Center</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    :root {
      --bg: #0f111a;
      --card: #1a1d2e;
      --accent: #00e5ff;
      --accent-hover: #00b4d8;
      --text: #ffffff;
      --subtext: #8e9bb0;
      --border: #2a2f45;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background: var(--bg); color: var(--text); padding: 24px; min-height: 100vh; display: flex; flex-direction: column; align-items: center; }
    .container { max-width: 880px; width: 100%; }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border); flex-wrap: wrap; gap: 12px; }
    .header h1 { font-size: 24px; color: var(--accent); display: flex; align-items: center; gap: 10px; }
    .header-right { display: flex; align-items: center; gap: 12px; }
    .lang-select { background: #121420; border: 1px solid var(--border); border-radius: 8px; color: #fff; padding: 6px 12px; font-size: 13px; outline: none; cursor: pointer; }
    .status-badge { background: #00c85322; color: #00e676; border: 1px solid #00e67644; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 6px; }
    .status-badge.error { background: #d5000022; color: #ff5252; border-color: #ff525244; }
    
    .card { background: var(--card); border-radius: 12px; border: 1px solid var(--border); padding: 24px; margin-bottom: 20px; box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
    .card-title { font-size: 18px; margin-bottom: 18px; color: #fff; font-weight: 600; display: flex; align-items: center; gap: 8px; }
    
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; }
    .form-group { display: flex; flex-direction: column; gap: 8px; }
    label { font-size: 13px; color: var(--subtext); font-weight: 500; }
    select, input[type="range"], input[type="file"] { background: #121420; border: 1px solid var(--border); border-radius: 8px; color: #fff; padding: 10px 14px; font-size: 14px; outline: none; width: 100%; }
    select:focus { border-color: var(--accent); }
    
    .color-picker-wrap { display: flex; align-items: center; gap: 14px; }
    input[type="color"] { -webkit-appearance: none; border: none; width: 44px; height: 44px; border-radius: 8px; cursor: pointer; background: transparent; }
    input[type="color"]::-webkit-color-swatch-wrapper { padding: 0; }
    input[type="color"]::-webkit-color-swatch { border-radius: 8px; border: 2px solid var(--border); }
    
    .btn { background: var(--accent); color: #050b14; border: none; padding: 12px 24px; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; justify-content: center; gap: 8px; }
    .btn:hover { background: var(--accent-hover); transform: translateY(-1px); }
    .btn-secondary { background: #252a40; color: #fff; }
    .btn-secondary:hover { background: #323955; }
    
    .presets { display: flex; gap: 10px; margin-top: 14px; flex-wrap: wrap; }
    .preset-btn { width: 32px; height: 32px; border-radius: 50%; border: 2px solid #fff3; cursor: pointer; transition: transform 0.15s; }
    .preset-btn:hover { transform: scale(1.15); border-color: #fff; }
    
    .range-val { font-size: 13px; color: var(--accent); float: right; }
    .toast { position: fixed; bottom: 24px; right: 24px; background: #00e676; color: #000; padding: 12px 20px; border-radius: 8px; font-weight: 600; opacity: 0; transition: opacity 0.3s; pointer-events: none; z-index: 999; }
    .progress-bar-wrap { width: 100%; height: 8px; background: #121420; border-radius: 4px; overflow: hidden; margin-top: 12px; display: none; }
    .progress-bar { height: 100%; width: 0%; background: var(--accent); transition: width 0.1s ease; }

    .switch-wrap { display: flex; align-items: center; gap: 10px; cursor: pointer; font-size: 14px; color: var(--text); user-select: none; }
    .switch-wrap input { display: none; }
    .slider { position: relative; width: 44px; height: 24px; background-color: #252a40; border-radius: 24px; transition: .3s; display: inline-block; }
    .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; border-radius: 50%; transition: .3s; }
    input:checked + .slider { background-color: #00e676; }
    input:checked + .slider:before { transform: translateX(20px); }
  </style>
</head>
<body>
  <div class="container">
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
        <div id="device-badge" class="status-badge">● LT-104 Connected</div>
      </div>
    </div>

    <!-- RGB Lighting Card -->
    <div class="card">
      <div class="card-title" id="txt-rgb-title">🌈 RGB Lighting & Backlight</div>
      <p style="color: var(--subtext); font-size: 13px; margin-bottom: 16px;" id="txt-rgb-desc">
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
            <input type="color" id="light-color" value="#00e5ff" onchange="applyLight()">
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

        <div class="form-group">
          <label><span id="txt-brightness">Brightness</span> <span id="bright-val" class="range-val">100%</span></label>
          <input type="range" id="light-brightness" min="0" max="4" value="4" oninput="updateRange('bright-val', this.value, ['0%', '25%', '50%', '75%', '100%'])" onchange="applyLight()">
        </div>

        <div class="form-group">
          <label><span id="txt-speed">Animation Speed</span> <span id="speed-val" class="range-val">3</span></label>
          <input type="range" id="light-speed" min="0" max="4" value="3" oninput="updateRange('speed-val', this.value)" onchange="applyLight()">
        </div>
      </div>
      <div style="margin-top: 20px; display: flex; gap: 12px;">
        <button class="btn" onclick="applyLight()" id="btn-apply-light">✨ Apply & Save Backlight</button>
      </div>
    </div>

    <!-- Clock Sync Card -->
    <div class="card">
      <div class="card-title" id="txt-clock-title">🕒 TFT Clock Calibration & Auto-Sync</div>
      <p style="color: var(--subtext); font-size: 14px; margin-bottom: 16px;" id="txt-clock-desc">
        Sync PC time immediately or enable 12-hour automated background service.
      </p>
      <div style="display: flex; gap: 16px; flex-wrap: wrap; align-items: center; justify-content: space-between; background: #121420; padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border);">
        <button class="btn btn-secondary" onclick="syncClock()" id="btn-sync-clock">🕒 Sync Clock to Keyboard LCD</button>
        <label class="switch-wrap">
          <input type="checkbox" id="chk-clock-sched" onchange="toggleClockSchedule(this.checked)">
          <span class="slider"></span>
          <span id="txt-clock-sched">Auto-Sync Clock Every 12 Hours</span>
        </label>
      </div>
    </div>

    <!-- Real-time System HUD Card -->
    <div class="card">
      <div class="card-title" id="txt-hud-title">📊 Real-time System Monitoring HUD</div>
      <p style="color: var(--subtext); font-size: 14px; margin-bottom: 16px;" id="txt-hud-desc">
        Stream live CPU / RAM / Disk telemetry directly to keyboard LCD RAM.
      </p>
      
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div style="display: flex; gap: 12px; flex-wrap: wrap; align-items: center;">
          <button class="btn" id="btn-toggle-hud" onclick="toggleHud()" style="background: linear-gradient(135deg, #059669, #10b981);">📊 Start Real-time System HUD</button>
          <button class="btn btn-secondary" id="btn-hud-once" onclick="pushHudOnce()">⚡ Update HUD Once</button>
          <div style="display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--subtext);">
            <span id="txt-hud-interval">Refresh Interval:</span>
            <select id="hud-interval" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px 10px; border-radius: 6px; font-size: 13px;" onchange="onIntervalChanged()">
              <option value="5" id="opt-5s">5s (Fast)</option>
              <option value="10" id="opt-10s">10s (Moderate)</option>
              <option value="20" id="opt-20s">20s</option>
              <option value="30" id="opt-30s">30s (Power Saving)</option>
              <option value="60" id="opt-60s">60s (Slow)</option>
              <option value="120" id="opt-120s" selected>120s (2 min - Default)</option>
              <option value="300" id="opt-300s">300s (5 min - Power Saving)</option>
            </select>
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
      <p style="color: var(--subtext); font-size: 14px; margin-bottom: 16px;" id="txt-lcd-desc">
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
          <button class="btn" onclick="uploadLcdImage()" id="btn-upload-lcd">🚀 Upload to Keyboard LCD</button>
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
      document.getElementById('txt-brightness').innerText = t('brightness');
      document.getElementById('txt-speed').innerText = t('speed');
      document.getElementById('btn-apply-light').innerText = '✨ ' + t('apply_btn');
      
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
      document.getElementById('txt-hud-hardware-note').innerText = '💡 ' + t('hud_hardware_note');

      const intervals = [5, 10, 20, 30, 60, 120, 300];
      for (const s of intervals) {
        const el = document.getElementById('opt-' + s + 's');
        if (el) el.innerText = t('opt_' + s + 's');
      }

      document.getElementById('txt-lcd-title').innerText = '📺 ' + t('lcd_card_title');
      document.getElementById('txt-lcd-desc').innerText = t('lcd_card_desc');
      document.getElementById('btn-upload-lcd').innerText = '🚀 ' + t('upload_btn');
      updateHudUI();
    }

    function showToast(msg) {
      const toast = document.getElementById('toast');
      toast.innerText = msg;
      toast.style.opacity = '1';
      setTimeout(() => toast.style.opacity = '0', 2500);
    }

    const SINGLE_COLOR_MODES = [1, 2, 3, 4, 5, 7];

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
    }

    function onModeChange() {
      const mode = document.getElementById('light-mode').value;
      updateColorVisibility(mode);
      applyLight();
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
      applyLight();
    }

    function updateRange(id, val, textMap) {
      document.getElementById(id).innerText = textMap ? textMap[val] : val;
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

      if (mode === 20) {
        brightness = 0;
        document.getElementById('light-brightness').value = 0;
        updateRange('bright-val', 0, ['0%', '25%', '50%', '75%', '100%']);
      }
      updateColorVisibility(mode);

      try {
        localStorage.setItem('lt104_light_mode', mode);
        localStorage.setItem('lt104_light_color', hex);
        localStorage.setItem('lt104_light_brightness', brightness);
        localStorage.setItem('lt104_light_speed', speed);

        const res = await fetch('/api/set-light', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mode, r, g, b, brightness, speed })
        });
        const data = await res.json();
        if (data.success) {
          showToast('✅ ' + t('apply_btn'));
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
      }
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

    window.addEventListener('DOMContentLoaded', () => {
      // 1. Restore persistent user settings
      const savedMode = localStorage.getItem('lt104_light_mode') || SERVER_CONFIG.mode;
      if (savedMode) document.getElementById('light-mode').value = savedMode;
      updateColorVisibility(savedMode);

      const savedColor = localStorage.getItem('lt104_light_color') || SERVER_CONFIG.color;
      if (savedColor) {
        document.getElementById('light-color').value = savedColor;
        document.getElementById('color-hex').innerText = savedColor;
      }

      const savedBright = localStorage.getItem('lt104_light_brightness') !== null ? localStorage.getItem('lt104_light_brightness') : SERVER_CONFIG.brightness;
      if (savedBright !== undefined && savedBright !== null) {
        document.getElementById('light-brightness').value = savedBright;
        updateRange('bright-val', savedBright, ['0%', '25%', '50%', '75%', '100%']);
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

      const initialLang = detectLanguage();
      changeLanguage(initialLang);
      checkDeviceStatus();
      checkHudStatus();
      checkClockScheduleStatus();
      setInterval(checkHudStatus, 4000);
      setInterval(checkDeviceStatus, 5000);
    });
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
            html = HTML_PAGE.replace("__LIGHT_OPTIONS__", options_html)
            html = html.replace("__I18N_JSON__", json.dumps(i18n.TRANSLATIONS))
            html = html.replace("__CONFIG_JSON__", json.dumps(load_config()))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
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

                ctl = LT104Controller()
                ctl.set_light(mode=mode, r=r, g=g, b=b, brightness=brightness, speed=speed)
                ctl.close()

                save_config({
                    "mode": mode,
                    "color": f"#{r:02x}{g:02x}{b:02x}",
                    "r": r, "g": g, "b": b,
                    "brightness": brightness,
                    "speed": speed
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
                ctl = LT104Controller()
                ctl.sync_clock()
                ctl.close()
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
