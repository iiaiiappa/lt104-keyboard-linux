#!/usr/bin/env python3
"""
LT-104 Configuration Persistence Manager
Saves and loads user preferences (lighting, HUD interval, schedule, language)
to ~/.config/lt104/config.json, ensuring settings are remembered even when
services, browsers, or extensions are closed or restarted.
"""
import os
import json

CONFIG_DIR = os.path.expanduser("~/.config/lt104")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "mode": 1,
    "color": "#00e5ff",
    "r": 0,
    "g": 229,
    "b": 255,
    "brightness": 4,
    "speed": 3,
    "hud_interval": 20.0,
    "lang": "en"
}

def load_config():
    """Load settings from ~/.config/lt104/config.json with default fallbacks."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                cfg = dict(DEFAULT_CONFIG)
                cfg.update(data)
                return cfg
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(updates):
    """Update and persist settings to ~/.config/lt104/config.json."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        cfg = load_config()
        cfg.update(updates)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

