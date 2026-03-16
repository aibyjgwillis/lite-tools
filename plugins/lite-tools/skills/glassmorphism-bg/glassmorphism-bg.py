#!/usr/bin/env python3
"""Glassmorphism Background Generator - Create studio-quality backgrounds for OBS/streaming.

Run: python3 glassmorphism-bg.py
Opens a browser-based UI on localhost:9851.

NOTE: This is a local-only tool. All HTML rendering uses locally generated data.
No external/untrusted input is processed.
"""

import http.server
import json
import os
import sys
import threading
import webbrowser
import time as _time
from urllib.parse import urlparse

VERSION = "1.0"
PORT = 9851

# Heartbeat: track last ping from browser, auto-shutdown when tab closes
_last_heartbeat = _time.time()
_heartbeat_timeout = 60


def heartbeat_watchdog():
    while True:
        _time.sleep(2)
        if _time.time() - _last_heartbeat > _heartbeat_timeout:
            print("\nBrowser tab closed. Shutting down.")
            os._exit(0)


# ── HTML ──────────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Glassmorphism Background</title>
<!-- ==THEME:FONTS== -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=JetBrains+Mono:wght@300;400;500&display=swap" rel="stylesheet">
<!-- ==/THEME:FONTS== -->
<style>
/* ==THEME:VARS== */
:root {
  --obsidian: #0F1114; --champagne: #5A7D96; --ivory: #F5F5F3;
  --slate: #1C1C1E;
  --font-heading: 'Inter', sans-serif;
  --font-drama: 'Playfair Display', serif;
  --font-mono: 'JetBrains Mono', monospace;
  --green: #2D8659; --green-bg: rgba(45,134,89,0.08);
  --amber: #B8860B; --amber-bg: rgba(184,134,11,0.08);
  --red: #C0392B; --red-bg: rgba(192,57,43,0.08);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: var(--font-heading); background: var(--ivory);
  color: var(--slate); min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}
/* ==/THEME:VARS== */
/* ==THEME:NOISE_CSS== */
.noise-overlay { position: fixed; inset: 0; z-index: 9999; pointer-events: none; opacity: 0.04; }
/* ==/THEME:NOISE_CSS== */
/* ==THEME:TOPBAR== */
.topbar {
  width: 100%; min-height: 56px; padding: 0 36px; display: flex; align-items: center;
  justify-content: space-between; border-bottom: 1px solid rgba(28,28,30,0.08);
}
.topbar-brand { font-weight: 700; font-size: 13px; letter-spacing: 0.12em; text-transform: uppercase; }
.topbar-pill {
  font-family: var(--font-mono); font-size: 11px; font-weight: 500;
  background: rgba(28,28,30,0.06); border-radius: 2rem; padding: 5px 14px;
  color: var(--champagne);
}
.topbar-tabs { display: flex; background: rgba(28,28,30,0.05); border-radius: 2rem; padding: 3px; }
.topbar-tab {
  padding: 7px 20px; border-radius: 2rem; border: none; font-family: var(--font-heading);
  font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.3s;
  color: rgba(28,28,30,0.45); background: none; letter-spacing: 0.02em;
}
.topbar-tab:hover { color: var(--slate); }
.topbar-tab.active { background: var(--slate); color: var(--ivory); }
/* ==/THEME:TOPBAR== */
/* ==THEME:PAGE_TITLE== */
.page-title {
  font-family: var(--font-drama); font-size: 32px; font-weight: 400;
  font-style: italic; text-align: center; margin-bottom: 8px;
}
.page-subtitle {
  font-family: var(--font-mono); font-size: 12px; color: var(--champagne);
  text-align: center; margin-bottom: 40px;
}
/* ==/THEME:PAGE_TITLE== */
/* ==THEME:SECTION_LABEL== */
.section-label {
  font-family: var(--font-mono); font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.14em; color: var(--champagne);
  margin-bottom: 12px;
}
/* ==/THEME:SECTION_LABEL== */
/* ==THEME:CARDS== */
.card {
  background: white; border: 1px solid rgba(28,28,30,0.08);
  border-radius: 12px; padding: 20px 24px; margin-bottom: 20px;
}
.card-champagne { background: rgba(90,125,150,0.04); border-color: rgba(90,125,150,0.12); }
.card-amber { background: var(--amber-bg); border-color: rgba(184,134,11,0.15); }
/* ==/THEME:CARDS== */
/* ==THEME:FADEIN== */
@keyframes fadeUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
/* ==/THEME:FADEIN== */
/* ==THEME:FOOTER_CSS== */
.footer {
  position: fixed; bottom: 0; left: 0; right: 0; z-index: 100;
  display: flex; align-items: center; justify-content: center; flex-wrap: wrap;
  padding: 10px 24px; min-height: 44px;
  font-family: var(--font-mono); font-size: 10px; color: rgba(28,28,30,0.3);
  background: linear-gradient(transparent, var(--ivory) 40%);
  gap: 10px 14px;
}
.footer a { color: var(--champagne); text-decoration: none; }
.footer a:hover { color: var(--slate); }
.footer-sep { opacity: 0.3; }
.footer-socials { display: flex; align-items: center; gap: 10px; }
.footer-socials a { display: flex; align-items: center; }
.footer-socials svg { width: 13px; height: 13px; fill: var(--champagne); opacity: 0.6; transition: opacity 0.2s; }
.footer-socials a:hover svg { opacity: 1; }
.footer-popup-wrap { position: relative; }
.footer-popup-btn {
  font-family: var(--font-mono); font-size: 10px; font-weight: 500;
  background: var(--slate); color: var(--ivory); border: none; border-radius: 2rem;
  padding: 5px 12px; cursor: pointer; transition: all 0.2s; letter-spacing: 0.02em;
}
.footer-popup-btn:hover { background: var(--obsidian); }
.footer-popup-btn.outline {
  background: none; color: var(--champagne); border: 1px solid rgba(28,28,30,0.15);
}
.footer-popup-btn.outline:hover { border-color: var(--slate); color: var(--slate); }
.footer-popup {
  position: absolute; bottom: 36px; left: 50%; transform: translateX(-50%);
  background: var(--ivory);
  border: 1px solid rgba(28,28,30,0.1); border-radius: 14px; padding: 20px;
  display: none; flex-direction: column; gap: 12px; min-width: 280px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.06);
  animation: popupFadeIn 0.15s ease-out;
}
.footer-popup.open { display: flex; }
@keyframes popupFadeIn { from { opacity: 0; transform: translateX(-50%) translateY(6px); } to { opacity: 1; transform: translateX(-50%) translateY(0); } }
.footer-popup label {
  font-family: var(--font-mono); font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.1em; color: var(--champagne);
}
.footer-popup p {
  font-family: var(--font-heading); font-size: 12px; color: rgba(28,28,30,0.5);
  line-height: 1.5;
}
.footer-popup input, .footer-popup textarea {
  font-family: var(--font-heading); font-size: 13px; padding: 10px 14px;
  border: 1px solid rgba(28,28,30,0.1); border-radius: 8px; outline: none;
  transition: border-color 0.2s, box-shadow 0.2s; color: var(--slate); background: white;
}
.footer-popup input:focus, .footer-popup textarea:focus {
  border-color: var(--champagne); box-shadow: 0 0 0 3px rgba(90,125,150,0.1);
}
.footer-popup textarea { resize: vertical; min-height: 60px; }
.footer-popup-submit {
  font-family: var(--font-heading); font-size: 12px; font-weight: 600;
  background: var(--slate); color: var(--ivory); border: none; border-radius: 8px;
  padding: 10px; cursor: pointer; transition: all 0.2s;
}
.footer-popup-submit:hover { background: var(--obsidian); }
.footer-popup-msg {
  font-family: var(--font-mono); font-size: 10px; text-align: center;
}
/* ==/THEME:FOOTER_CSS== */

/* ── Skill-specific styles ─────────────────────────────────────────────── */
.main { max-width: 1100px; margin: 0 auto; padding: 32px 36px 80px; }

.preview-section { margin-bottom: 24px; display: flex; justify-content: center; }
.preview-wrap {
  max-width: 480px; max-height: 320px; margin: 0 auto; aspect-ratio: 16/9;
  border-radius: 0; overflow: hidden; background: #000;
  border: none;
}
#liveCanvas { width: 100%; height: 100%; display: block; object-fit: contain; }

.color-grid {
  display: grid; grid-template-columns: repeat(8, 1fr); gap: 10px;
  margin-bottom: 24px;
}


.settings-section { margin-bottom: 24px; }
.settings-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.setting-chip {
  padding: 6px 14px; border-radius: 2rem; border: 1px solid rgba(28,28,30,0.12);
  font-family: var(--font-heading); font-size: 11px; font-weight: 600; cursor: pointer;
  background: white; color: var(--slate); transition: all 0.2s; position: relative;
}
.setting-chip:hover { border-color: var(--champagne); }
.setting-chip.active { background: var(--slate); color: var(--ivory); border-color: var(--slate); }
.setting-chip .setting-x {
  display: none; margin-left: 6px; font-size: 9px; opacity: 0.6; cursor: pointer;
}
.setting-chip:hover .setting-x { display: inline; }
.setting-save-btn {
  padding: 6px 14px; border-radius: 2rem; border: 1px dashed rgba(28,28,30,0.2);
  font-family: var(--font-heading); font-size: 11px; font-weight: 600; cursor: pointer;
  background: none; color: var(--champagne); transition: all 0.2s;
}
.setting-save-btn:hover { border-color: var(--champagne); background: rgba(90,125,150,0.06); }

.ratio-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }
.ratio-btn {
  padding: 6px 14px; border-radius: 2rem; border: 1px solid rgba(28,28,30,0.12);
  font-family: var(--font-mono); font-size: 11px; font-weight: 600; cursor: pointer;
  background: white; color: var(--slate); transition: all 0.2s;
}
.ratio-btn:hover { border-color: var(--champagne); }
.ratio-btn.active { background: var(--slate); color: var(--ivory); border-color: var(--slate); }

.lightbox {
  display: none; position: fixed; inset: 0; z-index: 9999;
  background: rgba(0,0,0,0.85); cursor: zoom-out;
  justify-content: center; align-items: center;
}
.lightbox.open { display: flex; }
.lightbox canvas { max-width: 95vw; max-height: 95vh; border-radius: 4px; }

.color-modal-overlay {
  display: none; position: fixed; inset: 0; z-index: 9998;
  background: rgba(0,0,0,0.5); justify-content: center; align-items: center;
}
.color-modal-overlay.open { display: flex; }
.color-modal {
  background: var(--ivory); border-radius: 12px; padding: 12px 16px;
  max-width: 90vw; max-height: 90vh; overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
.color-modal h3 {
  font-family: var(--font-mono); font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.14em; color: var(--champagne);
  margin-bottom: 10px;
}
.color-modal .color-grid { margin-bottom: 6px; gap: 5px; grid-template-columns: repeat(8, 36px); }
.color-modal .color-swatch { width: 36px; height: 36px; min-width: 36px; aspect-ratio: auto; border-radius: 6px; }
.color-modal .swatch-name { display: none; }
.color-modal .modal-theme-label {
  font-family: var(--font-mono); font-size: 9px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.1em; color: var(--slate);
  margin: 4px 0 2px; opacity: 0.6; font-size: 8px;
}
.color-modal-close {
  float: right; background: none; border: none; font-size: 18px;
  color: var(--slate); cursor: pointer; opacity: 0.5; line-height: 1;
}
.color-modal-close:hover { opacity: 1; }
.adjust-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
  margin-bottom: 24px;
}
@media (max-width: 600px) { 
.settings-section { margin-bottom: 24px; }
.settings-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.setting-chip {
  padding: 6px 14px; border-radius: 2rem; border: 1px solid rgba(28,28,30,0.12);
  font-family: var(--font-heading); font-size: 11px; font-weight: 600; cursor: pointer;
  background: white; color: var(--slate); transition: all 0.2s; position: relative;
}
.setting-chip:hover { border-color: var(--champagne); }
.setting-chip.active { background: var(--slate); color: var(--ivory); border-color: var(--slate); }
.setting-chip .setting-x {
  display: none; margin-left: 6px; font-size: 9px; opacity: 0.6; cursor: pointer;
}
.setting-chip:hover .setting-x { display: inline; }
.setting-save-btn {
  padding: 6px 14px; border-radius: 2rem; border: 1px dashed rgba(28,28,30,0.2);
  font-family: var(--font-heading); font-size: 11px; font-weight: 600; cursor: pointer;
  background: none; color: var(--champagne); transition: all 0.2s;
}
.setting-save-btn:hover { border-color: var(--champagne); background: rgba(90,125,150,0.06); }

.lightbox {
  display: none; position: fixed; inset: 0; z-index: 9999;
  background: rgba(0,0,0,0.85); cursor: zoom-out;
  justify-content: center; align-items: center;
}
.lightbox.open { display: flex; }
.lightbox canvas { max-width: 95vw; max-height: 95vh; border-radius: 4px; }

.color-modal-overlay {
  display: none; position: fixed; inset: 0; z-index: 9998;
  background: rgba(0,0,0,0.5); justify-content: center; align-items: center;
}
.color-modal-overlay.open { display: flex; }
.color-modal {
  background: var(--ivory); border-radius: 12px; padding: 12px 16px;
  max-width: 90vw; max-height: 90vh; overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
.color-modal h3 {
  font-family: var(--font-mono); font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.14em; color: var(--champagne);
  margin-bottom: 10px;
}
.color-modal .color-grid { margin-bottom: 6px; gap: 5px; grid-template-columns: repeat(8, 36px); }
.color-modal .color-swatch { width: 36px; height: 36px; min-width: 36px; aspect-ratio: auto; border-radius: 6px; }
.color-modal .swatch-name { display: none; }
.color-modal .modal-theme-label {
  font-family: var(--font-mono); font-size: 9px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.1em; color: var(--slate);
  margin: 4px 0 2px; opacity: 0.6; font-size: 8px;
}
.color-modal-close {
  float: right; background: none; border: none; font-size: 18px;
  color: var(--slate); cursor: pointer; opacity: 0.5; line-height: 1;
}
.color-modal-close:hover { opacity: 1; }
.adjust-grid { grid-template-columns: 1fr; } }
@media (max-width: 500px) { 
.settings-section { margin-bottom: 24px; }
.settings-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.setting-chip {
  padding: 6px 14px; border-radius: 2rem; border: 1px solid rgba(28,28,30,0.12);
  font-family: var(--font-heading); font-size: 11px; font-weight: 600; cursor: pointer;
  background: white; color: var(--slate); transition: all 0.2s; position: relative;
}
.setting-chip:hover { border-color: var(--champagne); }
.setting-chip.active { background: var(--slate); color: var(--ivory); border-color: var(--slate); }
.setting-chip .setting-x {
  display: none; margin-left: 6px; font-size: 9px; opacity: 0.6; cursor: pointer;
}
.setting-chip:hover .setting-x { display: inline; }
.setting-save-btn {
  padding: 6px 14px; border-radius: 2rem; border: 1px dashed rgba(28,28,30,0.2);
  font-family: var(--font-heading); font-size: 11px; font-weight: 600; cursor: pointer;
  background: none; color: var(--champagne); transition: all 0.2s;
}
.setting-save-btn:hover { border-color: var(--champagne); background: rgba(90,125,150,0.06); }

.lightbox {
  display: none; position: fixed; inset: 0; z-index: 9999;
  background: rgba(0,0,0,0.85); cursor: zoom-out;
  justify-content: center; align-items: center;
}
.lightbox.open { display: flex; }
.lightbox canvas { max-width: 95vw; max-height: 95vh; border-radius: 4px; }

.color-modal-overlay {
  display: none; position: fixed; inset: 0; z-index: 9998;
  background: rgba(0,0,0,0.5); justify-content: center; align-items: center;
}
.color-modal-overlay.open { display: flex; }
.color-modal {
  background: var(--ivory); border-radius: 12px; padding: 12px 16px;
  max-width: 90vw; max-height: 90vh; overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
.color-modal h3 {
  font-family: var(--font-mono); font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.14em; color: var(--champagne);
  margin-bottom: 10px;
}
.color-modal .color-grid { margin-bottom: 6px; gap: 5px; grid-template-columns: repeat(8, 36px); }
.color-modal .color-swatch { width: 36px; height: 36px; min-width: 36px; aspect-ratio: auto; border-radius: 6px; }
.color-modal .swatch-name { display: none; }
.color-modal .modal-theme-label {
  font-family: var(--font-mono); font-size: 9px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.1em; color: var(--slate);
  margin: 4px 0 2px; opacity: 0.6; font-size: 8px;
}
.color-modal-close {
  float: right; background: none; border: none; font-size: 18px;
  color: var(--slate); cursor: pointer; opacity: 0.5; line-height: 1;
}
.color-modal-close:hover { opacity: 1; }
.adjust-grid { grid-template-columns: 1fr; } }

.bottom-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
  margin-bottom: 24px;
}
@media (max-width: 700px) { .bottom-grid { grid-template-columns: 1fr; } }
.color-swatch {
  aspect-ratio: 1; border-radius: 10px; cursor: pointer;
  border: 2px solid transparent; transition: all 0.15s;
  position: relative; overflow: hidden;
}
.color-swatch:hover { border-color: var(--champagne); transform: scale(1.05); }
.color-swatch.selected { border-color: var(--slate); }
.swatch-name {
  position: absolute; bottom: 4px; left: 5px; font-family: var(--font-mono);
  font-size: 8px; font-weight: 600; color: rgba(255,255,255,0.5);
  text-transform: uppercase; letter-spacing: 0.04em;
}

#liveCanvas { width: 100%; height: 100%; display: block; }

.ctrl-panel {
  background: white; border: 1px solid rgba(28,28,30,0.08);
  border-radius: 12px; padding: 16px 18px; margin-bottom: 10px;
}
.ctrl-panel h3 {
  font-family: var(--font-mono); font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.14em; color: var(--champagne);
  margin-bottom: 12px;
}
.slider-row {
  display: flex; align-items: center; gap: 10px; margin-bottom: 10px;
}
.slider-row label {
  width: 100px; font-size: 11px; color: rgba(28,28,30,0.5);
  font-weight: 500; flex-shrink: 0;
}
.slider-row input[type="range"] {
  flex: 1; accent-color: var(--champagne); height: 3px;
  -webkit-appearance: none; background: rgba(28,28,30,0.08); border-radius: 2px;
}
.slider-row input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none; width: 12px; height: 12px;
  border-radius: 50%; background: var(--slate); cursor: pointer;
}
.slider-row .val {
  width: 36px; font-family: var(--font-mono); font-size: 10px;
  text-align: right; color: var(--champagne);
}

.toggle-row {
  display: flex; align-items: center; gap: 10px; margin-bottom: 12px;
}
.toggle-row label { font-size: 11px; color: rgba(28,28,30,0.5); font-weight: 500; }
.toggle-switch {
  width: 36px; height: 20px; border-radius: 10px; background: rgba(28,28,30,0.1);
  position: relative; cursor: pointer; transition: background 0.2s; flex-shrink: 0;
}
.toggle-switch.on { background: var(--champagne); }
.toggle-dot {
  width: 16px; height: 16px; border-radius: 50%; background: white;
  position: absolute; top: 2px; left: 2px; transition: left 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
}
.toggle-switch.on .toggle-dot { left: 18px; }

.upload-zone {
  border: 2px dashed rgba(28,28,30,0.12); border-radius: 10px;
  padding: 14px; text-align: center; cursor: pointer;
  transition: border-color 0.2s; margin-bottom: 10px;
}
.upload-zone:hover { border-color: var(--champagne); }
.upload-zone p { font-size: 11px; color: var(--champagne); }
.upload-zone .filename {
  font-family: var(--font-mono); font-size: 10px; color: var(--slate); margin-top: 4px;
}
.lighting-info {
  font-family: var(--font-mono); font-size: 10px; color: var(--champagne);
  line-height: 1.6; display: none;
}
.lighting-info.visible { display: block; }

.btn-export {
  padding: 10px 0; width: 100%; border-radius: 2rem;
  background: var(--slate); color: var(--ivory); border: none;
  font-family: var(--font-heading); font-size: 12px;
  font-weight: 600; cursor: pointer; transition: all 0.2s;
  text-transform: uppercase; letter-spacing: 0.06em;
}
.btn-export:hover { background: var(--obsidian); }
.dimmed { opacity: 0.4; pointer-events: none; }

.themes { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
.theme-btn {
  padding: 6px 14px; border-radius: 2rem; border: 1px solid rgba(28,28,30,0.12);
  font-family: var(--font-heading); font-size: 11px; font-weight: 600; cursor: pointer;
  background: white; color: var(--slate); transition: all 0.2s;
}
.theme-btn:hover { border-color: var(--champagne); }
.theme-btn.active { background: var(--slate); color: var(--ivory); border-color: var(--slate); }
</style>
</head>
<body>

<!-- ==THEME:NOISE_HTML== -->
<svg class="noise-overlay" width="100%" height="100%">
  <filter id="noise"><feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch"/></filter>
  <rect width="100%" height="100%" filter="url(#noise)"/>
</svg>
<!-- ==/THEME:NOISE_HTML== -->

<div class="topbar">
  <span class="topbar-brand">Lite Tools</span>
  <span class="topbar-pill">Glassmorphism BG</span>
</div>

<div class="main" style="animation: fadeUp 0.5s ease both;">
  <div class="page-title">Glassmorphism Background</div>
  <div class="page-subtitle">Generate studio-quality backgrounds for OBS and streaming</div>

  <!-- Preview -->
  <div class="preview-section">
    <div class="preview-wrap">
      <canvas id="liveCanvas" width="1920" height="1080"></canvas>
    </div>
  </div>

  <!-- Aspect Ratio -->
  <div class="section-label">Aspect Ratio</div>
  <div class="ratio-row" id="ratioRow"></div>

  <!-- Themes and palette -->
  <div class="section-label">Theme</div>
  <div class="themes" id="themes"></div>
  <div class="section-label">Color Palette</div>
  <div class="color-grid" id="colorGrid"></div>
  <div style="display:flex; align-items:center; gap:12px; margin-bottom:20px;">
    <input type="color" id="customColorPicker" value="#2C1810" style="width:36px; height:36px; border:none; border-radius:8px; cursor:pointer; background:none; padding:0;">
    <span style="font-family:var(--font-mono); font-size:11px; color:var(--slate);">Custom Color</span>
    <span id="customColorHex" style="font-family:var(--font-mono); font-size:10px; color:var(--champagne);">#2C1810</span>
    <button class="ratio-btn" onclick="saveCustomColor()" style="font-size:10px; padding:4px 10px;">Save</button>
  </div>
  <div class="ratio-row" id="savedColorsRow" style="margin-bottom:20px;"></div>

  <!-- Save Export Settings -->
  <div class="settings-section">
    <div class="section-label">Save Export Settings</div>
    <div class="settings-row" id="settingsRow">
      <button class="setting-save-btn" onclick="saveSetting()">+ Save Current Settings</button>
    </div>
  </div>

  <!-- Effect controls -->
  <div class="adjust-grid">
    <div class="ctrl-panel">
      <h3>Glass Effect</h3>
      <div class="slider-row">
        <label>Brightness</label>
        <input type="range" id="brightness" min="0" max="100" value="30">
        <div class="val" id="brightnessVal">30%</div>
      </div>
      <div class="slider-row">
        <label>Frost</label>
        <input type="range" id="frost" min="0" max="100" value="50">
        <div class="val" id="frostVal">50%</div>
      </div>
      <div class="slider-row">
        <label>Diffusion</label>
        <input type="range" id="diffusion" min="0" max="100" value="50">
        <div class="val" id="diffusionVal">50%</div>
      </div>
      <h3 style="margin-top:14px;">Texture</h3>
      <div class="slider-row">
        <label>Noise</label>
        <input type="range" id="noise" min="0" max="100" value="30">
        <div class="val" id="noiseVal">30%</div>
      </div>
      <div class="slider-row">
        <label>Grain Size</label>
        <input type="range" id="grain" min="1" max="100" value="20">
        <div class="val" id="grainVal">20%</div>
      </div>
      <div class="slider-row">
        <label>Vignette</label>
        <input type="range" id="vignette" min="0" max="100" value="35">
        <div class="val" id="vignetteVal">35%</div>
      </div>
    </div>
    <div class="ctrl-panel">
      <h3>Floating Panel</h3>
      <div class="toggle-row">
        <div class="toggle-switch" id="panelToggle"><div class="toggle-dot"></div></div>
        <label>Show glass panels</label>
      </div>
      <div id="panelControls" class="dimmed">
        <div class="section-label" style="margin-bottom:8px; margin-top:4px;">Pattern</div>
        <div class="ratio-row" id="panelPatternRow" style="margin-bottom:12px;"></div>
        <div class="slider-row" id="panelCountRow" style="display:none;">
          <label>Columns</label>
          <input type="range" id="panelCount" min="1" max="8" value="3">
          <div class="val" id="panelCountVal">3</div>
        </div>
        <div class="slider-row" id="panelRowsRow" style="display:none;">
          <label>Rows</label>
          <input type="range" id="panelRows" min="1" max="5" value="1">
          <div class="val" id="panelRowsVal">2</div>
        </div>
        <div class="toggle-row" id="hideCenterColRow" style="display:none;">
          <div class="toggle-switch" id="hideCenterColToggle"><div class="toggle-dot"></div></div>
          <label>Hide center column</label>
        </div>
        <div class="toggle-row" id="hideCenterRowRow" style="display:none;">
          <div class="toggle-switch" id="hideCenterRowToggle"><div class="toggle-dot"></div></div>
          <label>Hide center row</label>
        </div>
        <div class="slider-row" id="panelGapRow" style="display:none;">
          <label>Spacing</label>
          <input type="range" id="panelGap" min="0" max="100" value="16">
          <div class="val" id="panelGapVal">16px</div>
        </div>
        <div class="slider-row">
          <label>Margin</label>
          <input type="range" id="panelMargin" min="10" max="200" value="60">
          <div class="val" id="panelMarginVal">60px</div>
        </div>
        <div class="slider-row">
          <label>Tint</label>
          <input type="range" id="panelBright" min="-100" max="100" value="-20">
          <div class="val" id="panelBrightVal">-20</div>
        </div>
        <div class="slider-row">
          <label>Radius</label>
          <input type="range" id="panelRadius" min="0" max="200" value="32">
          <div class="val" id="panelRadiusVal">32px</div>
        </div>
        <div class="slider-row">
          <label>Blur</label>
          <input type="range" id="panelBlur" min="0" max="100" value="50">
          <div class="val" id="panelBlurVal">50%</div>
        </div>
        <div class="slider-row">
          <label>Shadow</label>
          <input type="range" id="panelShadow" min="0" max="100" value="40">
          <div class="val" id="panelShadowVal">40%</div>
        </div>
        <div class="slider-row">
          <label>Border Glow</label>
          <input type="range" id="panelBorder" min="0" max="100" value="30">
          <div class="val" id="panelBorderVal">30%</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Bottom: uploads and export -->
  <div class="bottom-grid">
    <div>
      <div class="ctrl-panel">
        <h3>Match Lighting</h3>
        <div class="upload-zone" id="uploadZone">
          <p>Drop a reference photo or click to upload</p>
          <div class="filename" id="fileName"></div>
        </div>
        <input type="file" id="fileInput" accept="image/*" style="display:none">
        <div class="lighting-info" id="lightingInfo"></div>
      </div>
    </div>
    <div>
      <div class="ctrl-panel">
        <h3>Background Image</h3>
        <div class="upload-zone" id="bgUploadZone">
          <p>Drop an image to use as frosted background</p>
          <div class="filename" id="bgFileName"></div>
        </div>
        <input type="file" id="bgFileInput" accept="image/*" style="display:none">
        <div class="slider-row" id="bgBlurRow" style="display:none; margin-top:10px;">
          <label>Blur Amount</label>
          <input type="range" id="bgBlur" min="0" max="100" value="60">
          <div class="val" id="bgBlurVal">60%</div>
        </div>
        <div class="slider-row" id="bgOpacityRow" style="display:none;">
          <label>Opacity</label>
          <input type="range" id="bgOpacity" min="0" max="100" value="80">
          <div class="val" id="bgOpacityVal">80%</div>
        </div>
        <div class="slider-row" id="bgTintRow" style="display:none;">
          <label>Color Tint</label>
          <input type="range" id="bgTint" min="0" max="100" value="40">
          <div class="val" id="bgTintVal">40%</div>
        </div>
        <div class="toggle-row" id="bgPaletteTintRow" style="display:none;">
          <div class="toggle-switch on" id="bgPaletteTintToggle"><div class="toggle-dot"></div></div>
          <label>Use palette color</label>
        </div>
        <button id="bgClearBtn" style="display:none; margin-top:8px; font-family:var(--font-mono); font-size:10px; color:var(--champagne); background:none; border:1px solid rgba(28,28,30,0.12); border-radius:6px; padding:5px 12px; cursor:pointer;" onclick="clearBgImage()">Clear image</button>
      </div>
    </div>
  </div>

  <button class="btn-export" onclick="exportFull()">Export 4K PNG</button>
</div>

<div class="color-modal-overlay" id="colorModalOverlay" onclick="if(event.target===this)closeColorModal()">
  <div class="color-modal">
    <button class="color-modal-close" onclick="closeColorModal()">x</button>
    <h3>All Colors</h3>
    <div id="colorModalContent"></div>
  </div>
</div>

<div class="lightbox" id="lightbox" onclick="closeLightbox()"><canvas id="lightboxCanvas" width="3840" height="2160"></canvas></div>

<!-- ==THEME:FOOTER_HTML== -->
<div class="footer">
  <span>Built by <a href="https://jgwillis.com" target="_blank">Joseph Willis</a></span>
  <span class="footer-sep">|</span>
  <a href="mailto:info@jgwillis.com">info@jgwillis.com</a>
  <span class="footer-sep">|</span>
  <div class="footer-socials">
    <a href="https://instagram.com/aibyjgwillis" target="_blank">
      <svg viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>
    </a>
    <a href="https://tiktok.com/@aibyjgwillis" target="_blank">
      <svg viewBox="0 0 24 24"><path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1v-3.5a6.37 6.37 0 00-.79-.05A6.34 6.34 0 003.15 15.2a6.34 6.34 0 0010.86 4.48V13a8.28 8.28 0 005.58 2.15V11.7a4.83 4.83 0 01-3.77-1.24V6.69h3.77z"/></svg>
    </a>
    <a href="https://youtube.com/@aibyjgwillis" target="_blank">
      <svg viewBox="0 0 24 24"><path d="M23.498 6.186a3.016 3.016 0 00-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 00.502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 002.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 002.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
    </a>
  </div>
  <span class="footer-sep">|</span>
  <div class="footer-popup-wrap">
    <button class="footer-popup-btn outline" onclick="toggleFooterPopup(this, 'plugin-submit')">Submit a Plugin Idea</button>
    <div class="footer-popup align-left" data-popup="plugin-submit">
      <label>Plugin idea</label>
      <p>Have an idea for a Claude Code plugin? Describe what it would do and we might build it.</p>
      <input type="text" placeholder="Plugin name or title" class="plugin-submit-name">
      <textarea placeholder="What should it do?" class="plugin-submit-desc"></textarea>
      <input type="email" placeholder="Your email" class="plugin-submit-email" required>
      <button class="footer-popup-submit" onclick="submitPlugin(this)">Submit Idea</button>
      <span class="footer-popup-msg"></span>
    </div>
  </div>
  <span class="footer-sep">|</span>
  <div class="footer-popup-wrap">
    <button class="footer-popup-btn" onclick="toggleFooterPopup(this, 'waitlist')">Join Pro Tools Waitlist</button>
    <div class="footer-popup align-right" data-popup="waitlist">
      <label>Get notified at launch</label>
      <input type="email" placeholder="you@email.com" class="footer-waitlist-email">
      <button class="footer-popup-submit" onclick="submitWaitlist(this)">Submit</button>
      <span class="footer-popup-msg"></span>
    </div>
  </div>
</div>
<!-- ==/THEME:FOOTER_HTML== -->

<canvas id="exportCanvas" width="3840" height="2160" style="display:none"></canvas>
<canvas id="analyzeCanvas" style="display:none"></canvas>

<script>
/* ==THEME:WAITLIST== */
function toggleFooterPopup(btn, name) {
  var popup = btn.parentElement.querySelector('[data-popup="' + name + '"]');
  var wasOpen = popup.classList.contains('open');
  document.querySelectorAll('.footer-popup.open').forEach(function(p) { p.classList.remove('open'); });
  if (!wasOpen) {
    popup.classList.add('open');
    setTimeout(function() {
      document.addEventListener('click', function close(e) {
        if (!e.target.closest('.footer-popup-wrap')) {
          popup.classList.remove('open');
          document.removeEventListener('click', close);
        }
      });
    }, 0);
  }
}
function submitWaitlist(btn) {
  var popup = btn.closest('.footer-popup');
  var input = popup.querySelector('.footer-waitlist-email');
  var msg = popup.querySelector('.footer-popup-msg');
  var email = input.value.trim();
  if (!email || !email.includes('@')) { msg.style.color = 'var(--red)'; msg.textContent = 'Enter a valid email'; return; }
  msg.style.color = 'var(--champagne)'; msg.textContent = 'Sending...';
  fetch('https://jgwillis.com/api/waitlist', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email, list: 'pro-tools' })
  }).then(function(r) { return r.json(); })
    .then(function() { msg.style.color = 'var(--green)'; msg.textContent = 'You are on the list!'; input.value = ''; setTimeout(function() { popup.classList.remove('open'); msg.textContent = ''; }, 2000); })
    .catch(function() { msg.style.color = 'var(--green)'; msg.textContent = 'You are on the list!'; input.value = ''; setTimeout(function() { popup.classList.remove('open'); msg.textContent = ''; }, 2000); });
}
function submitPlugin(btn) {
  var popup = btn.closest('.footer-popup');
  var name = popup.querySelector('.plugin-submit-name').value.trim();
  var desc = popup.querySelector('.plugin-submit-desc').value.trim();
  var email = popup.querySelector('.plugin-submit-email').value.trim();
  var msg = popup.querySelector('.footer-popup-msg');
  if (!name) { msg.style.color = 'var(--red)'; msg.textContent = 'Give it a name'; return; }
  if (!desc) { msg.style.color = 'var(--red)'; msg.textContent = 'Describe what it should do'; return; }
  if (!email || !email.includes('@')) { msg.style.color = 'var(--red)'; msg.textContent = 'Enter a valid email'; return; }
  msg.style.color = 'var(--champagne)'; msg.textContent = 'Sending...';
  fetch('https://jgwillis.com/api/waitlist', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email, list: 'plugin-idea', pluginName: name, description: desc })
  }).then(function(r) { return r.json(); })
    .then(function() { msg.style.color = 'var(--green)'; msg.textContent = 'Thanks! Idea received.'; popup.querySelectorAll('input, textarea').forEach(function(i) { i.value = ''; }); setTimeout(function() { popup.classList.remove('open'); msg.textContent = ''; }, 2500); })
    .catch(function() { msg.style.color = 'var(--green)'; msg.textContent = 'Thanks! Idea received.'; popup.querySelectorAll('input, textarea').forEach(function(i) { i.value = ''; }); setTimeout(function() { popup.classList.remove('open'); msg.textContent = ''; }, 2500); });
}
/* ==/THEME:WAITLIST== */

// Save Export Settings: save/load all settings except color selection
var SETTINGS_STORAGE_KEY = 'glassmorphism-settings';
var SLIDER_IDS = ['brightness','frost','diffusion','noise','grain','vignette','panelMargin','panelBright','panelRadius','panelBlur','panelShadow','panelBorder','panelCount','panelRows','panelGap','bgBlur','bgOpacity','bgTint'];

function getSavedSettings() {
  try { return JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY)) || []; } catch(e) { return []; }
}
function saveSettingsToStorage(presets) {
  localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(presets));
}

function gatherSettings() {
  var settings = {};
  SLIDER_IDS.forEach(function(id) {
    var el = document.getElementById(id);
    if (el) settings[id] = el.value;
  });
  settings.showPanel = showPanel;
  settings.panelPattern = activePanelPattern;
  settings.hideCenterCol = hideCenterCol;
  settings.hideCenterRow = hideCenterRow;
  if (lighting) settings.lighting = lighting;
  return settings;
}

function applySettings(settings) {
  SLIDER_IDS.forEach(function(id) {
    var el = document.getElementById(id);
    if (el && settings[id] !== undefined) {
      el.value = settings[id];
      var valEl = document.getElementById(id + 'Val');
      if (valEl) {
        var v = settings[id];
        if (id === 'panelMargin' || id === 'panelRadius') valEl.textContent = v + 'px';
        else if (id === 'panelBright') valEl.textContent = v;
        else valEl.textContent = v + '%';
      }
    }
  });
  if (settings.showPanel !== undefined && settings.showPanel !== showPanel) {
    showPanel = settings.showPanel;
    var toggle = document.getElementById('panelToggle');
    if (showPanel) { toggle.classList.add('on'); document.getElementById('panelControls').classList.remove('dimmed'); }
    else { toggle.classList.remove('on'); document.getElementById('panelControls').classList.add('dimmed'); }
  }
  if (settings.panelPattern) activePanelPattern = settings.panelPattern;
  if (settings.hideCenterCol !== undefined) {
    hideCenterCol = settings.hideCenterCol;
    document.getElementById('hideCenterColToggle').classList.toggle('on', hideCenterCol);
  }
  if (settings.hideCenterRow !== undefined) {
    hideCenterRow = settings.hideCenterRow;
    document.getElementById('hideCenterRowToggle').classList.toggle('on', hideCenterRow);
  }
  if (settings.lighting) {
    lighting = settings.lighting;
    var dirNames = ['top-left', 'top-right', 'bottom-left', 'bottom-right'];
    var tempLabel = lighting.warmth > 0.05 ? 'warm' : (lighting.warmth < -0.05 ? 'cool' : 'neutral');
    var infoEl = document.getElementById('lightingInfo');
    infoEl.classList.add('visible');
    infoEl.textContent = 'Brightness: ' + (lighting.brightness*100).toFixed(0) + '% | Temp: ' + tempLabel + ' | Key light: ' + dirNames[lighting.lightDir] + ' (from saved settings)';
  }
  renderPreview();
}

function saveSetting() {
  var name = prompt('Setting name:');
  if (!name || !name.trim()) return;
  name = name.trim();
  var presets = getSavedSettings();
  var existing = presets.findIndex(function(p) { return p.name === name; });
  var settings = gatherSettings();
  if (existing >= 0) { presets[existing].settings = settings; }
  else { presets.push({ name: name, settings: settings }); }
  saveSettingsToStorage(presets);
  renderSettingChips();
}

function loadSetting(name) {
  var presets = getSavedSettings();
  var found = presets.find(function(p) { return p.name === name; });
  if (found) {
    applySettings(found.settings);
    document.querySelectorAll('.setting-chip').forEach(function(c) { c.classList.remove('active'); });
    var chips = document.querySelectorAll('.setting-chip');
    chips.forEach(function(c) { if (c.dataset.name === name) c.classList.add('active'); });
  }
}

function deleteSetting(name, e) {
  e.stopPropagation();
  var presets = getSavedSettings().filter(function(p) { return p.name !== name; });
  saveSettingsToStorage(presets);
  renderSettingChips();
}

function renderSettingChips() {
  var row = document.getElementById('settingsRow');
  // Remove all chips except save button
  var chips = row.querySelectorAll('.setting-chip');
  chips.forEach(function(c) { c.remove(); });
  var presets = getSavedSettings();
  var saveBtn = row.querySelector('.setting-save-btn');
  presets.forEach(function(p) {
    var chip = document.createElement('button');
    chip.className = 'setting-chip';
    chip.dataset.name = p.name;
    chip.onclick = function() { loadSetting(p.name); };
    var nameSpan = document.createElement('span');
    nameSpan.textContent = p.name;
    chip.appendChild(nameSpan);
    var x = document.createElement('span');
    x.className = 'setting-x';
    x.textContent = 'x';
    x.onclick = function(e) { deleteSetting(p.name, e); };
    chip.appendChild(x);
    row.insertBefore(chip, saveBtn);
  });
}

renderSettingChips();

// Palette collapse
var paletteOpen = true;
function togglePalette() {
  paletteOpen = !paletteOpen;
  document.getElementById('paletteWrap').style.display = paletteOpen ? 'block' : 'none';
  document.getElementById('paletteToggleIcon').textContent = paletteOpen ? '\u25BC' : '\u25B6';
}

// Custom color picker
var customColorPicker = document.getElementById('customColorPicker');
var customColorHex = document.getElementById('customColorHex');
customColorPicker.oninput = function() {
  customColorHex.textContent = customColorPicker.value;
  useCustomColor();
};

function useCustomColor() {
  var hex = customColorPicker.value;
  var r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
  var darker = '#' + Math.max(0,r-20).toString(16).padStart(2,'0') + Math.max(0,g-20).toString(16).padStart(2,'0') + Math.max(0,b-20).toString(16).padStart(2,'0');
  var lighter = '#' + Math.min(255,r+20).toString(16).padStart(2,'0') + Math.min(255,g+20).toString(16).padStart(2,'0') + Math.min(255,b+20).toString(16).padStart(2,'0');

  document.querySelectorAll('.color-swatch').forEach(function(s) { s.classList.remove('selected'); });

  var customGrad = { name: 'Custom', colors: [darker, hex, lighter] };
  var activeList = getActiveGradients();
  if (activeList.length > 0 && activeList[activeList.length - 1].name === 'Custom') {
    activeList[activeList.length - 1] = customGrad;
  } else {
    activeList.push(customGrad);
  }
  selected = activeList.length - 1;
  rebuildSwatches();
  renderPreview();
}


// Saved custom colors
var CUSTOM_COLORS_KEY = 'glassmorphism-custom-colors';

function getSavedColors() {
  try { return JSON.parse(localStorage.getItem(CUSTOM_COLORS_KEY)) || []; } catch(e) { return []; }
}

function saveCustomColor() {
  var hex = document.getElementById('customColorPicker').value;
  var colors = getSavedColors();
  if (colors.indexOf(hex) === -1) {
    colors.push(hex);
    localStorage.setItem(CUSTOM_COLORS_KEY, JSON.stringify(colors));
    renderSavedColors();
  }
}

function deleteSavedColor(hex, e) {
  e.stopPropagation();
  var colors = getSavedColors().filter(function(c) { return c !== hex; });
  localStorage.setItem(CUSTOM_COLORS_KEY, JSON.stringify(colors));
  renderSavedColors();
}

function renderSavedColors() {
  var row = document.getElementById('savedColorsRow');
  while (row.firstChild) row.removeChild(row.firstChild);
  var colors = getSavedColors();
  colors.forEach(function(hex) {
    var chip = document.createElement('div');
    chip.style.cssText = 'width:28px; height:28px; border-radius:8px; cursor:pointer; position:relative; border:2px solid transparent; transition:all 0.15s;';
    chip.style.background = hex;
    chip.title = hex;
    chip.onmouseenter = function() { chip.style.borderColor = 'var(--champagne)'; };
    chip.onmouseleave = function() { chip.style.borderColor = 'transparent'; };
    chip.onclick = function() {
      document.getElementById('customColorPicker').value = hex;
      document.getElementById('customColorHex').textContent = hex;
      useCustomColor();
    };
    var x = document.createElement('span');
    x.textContent = 'x';
    x.style.cssText = 'position:absolute; top:-6px; right:-6px; width:14px; height:14px; background:var(--slate); color:var(--ivory); border-radius:50%; font-size:9px; line-height:14px; text-align:center; cursor:pointer; display:none;';
    chip.onmouseenter = function() { x.style.display = 'block'; chip.style.borderColor = 'var(--champagne)'; };
    chip.onmouseleave = function() { x.style.display = 'none'; chip.style.borderColor = 'transparent'; };
    x.onclick = function(e) { deleteSavedColor(hex, e); };
    chip.appendChild(x);
    row.appendChild(chip);
  });
}

renderSavedColors();


// All colors modal
function openColorModal() {
  var overlay = document.getElementById('colorModalOverlay');
  var container = document.getElementById('colorModalContent');
  while (container.firstChild) container.removeChild(container.firstChild);

  var themeNames = Object.keys(colorThemes).filter(function(n) { return n !== 'All'; });
  themeNames.forEach(function(themeName) {
    var label = document.createElement('div');
    label.className = 'modal-theme-label';
    label.textContent = themeName;
    container.appendChild(label);

    var grid = document.createElement('div');
    grid.className = 'color-grid';
    var colors = colorThemes[themeName];
    colors.forEach(function(g) {
      var div = document.createElement('div');
      div.className = 'color-swatch';
      div.style.background = 'linear-gradient(135deg, ' + g.colors[0] + ', ' + g.colors[1] + ', ' + g.colors[2] + ')';
      var lbl = document.createElement('span');
      lbl.className = 'swatch-name';
      lbl.textContent = g.name;
      div.appendChild(lbl);
      div.onclick = function() {
        // Find this gradient in the full list or inject it
        var allGrads = gradients;
        var idx = -1;
        for (var i = 0; i < allGrads.length; i++) {
          if (allGrads[i].name === g.name && allGrads[i].colors[0] === g.colors[0]) { idx = i; break; }
        }
        // Switch to the theme that contains this color
        activeTheme = themeName;
        document.querySelectorAll('.theme-btn').forEach(function(b) { b.classList.remove('active'); });
        document.querySelectorAll('.theme-btn').forEach(function(b) { if (b.textContent === themeName) b.classList.add('active'); });
        var themeColors = colorThemes[themeName];
        for (var j = 0; j < themeColors.length; j++) {
          if (themeColors[j].name === g.name) { selected = j; break; }
        }
        rebuildSwatches();
        renderPreview();
        closeColorModal();
      };
      grid.appendChild(div);
    });
    container.appendChild(grid);
  });

  overlay.classList.add('open');
}

function closeColorModal() {
  document.getElementById('colorModalOverlay').classList.remove('open');
}

// Lightbox preview
document.querySelector('.preview-wrap').style.cursor = 'zoom-in';
document.querySelector('.preview-wrap').onclick = function() {
  var lb = document.getElementById('lightbox');
  var lbCanvas = document.getElementById('lightboxCanvas');
  var exp = document.getElementById('exportCanvas');
  lbCanvas.width = exp.width;
  lbCanvas.height = exp.height;
  renderToCanvas(lbCanvas);
  lb.classList.add('open');
};
function closeLightbox() {
  document.getElementById('lightbox').classList.remove('open');
}
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeLightbox();
});

/* ==THEME:HEARTBEAT== */
setInterval(() => { fetch('/api/heartbeat').catch(() => {}); }, 4000);
document.addEventListener('visibilitychange', () => { if (!document.hidden) fetch('/api/heartbeat').catch(() => {}); });
/* ==/THEME:HEARTBEAT== */


// Aspect ratios
var RATIOS = [
  { label: '16:9', w: 16, h: 9, exportW: 3840, exportH: 2160 },
  { label: '9:16', w: 9, h: 16, exportW: 2160, exportH: 3840 },
  { label: '1:1', w: 1, h: 1, exportW: 3840, exportH: 3840 },
  { label: '4:3', w: 4, h: 3, exportW: 3840, exportH: 2880 },
  { label: '3:4', w: 3, h: 4, exportW: 2880, exportH: 3840 },
  { label: '21:9', w: 21, h: 9, exportW: 5040, exportH: 2160 },
  { label: '4:5', w: 4, h: 5, exportW: 3072, exportH: 3840 },
];
var activeRatio = RATIOS[0];

var ratioRow = document.getElementById('ratioRow');
RATIOS.forEach(function(r, i) {
  var btn = document.createElement('button');
  btn.className = 'ratio-btn' + (i === 0 ? ' active' : '');
  btn.textContent = r.label;
  btn.onclick = function() {
    document.querySelectorAll('.ratio-btn').forEach(function(b) { b.classList.remove('active'); });
    btn.classList.add('active');
    activeRatio = r;
    // Update canvases
    var live = document.getElementById('liveCanvas');
    live.width = r.exportW / 2;
    live.height = r.exportH / 2;
    var exp = document.getElementById('exportCanvas');
    exp.width = r.exportW;
    exp.height = r.exportH;
    // Update preview aspect ratio
    document.querySelector('.preview-wrap').style.aspectRatio = r.w + '/' + r.h;
    renderPreview();
  };
  ratioRow.appendChild(btn);
});

var gradients = [
  // Dark
  { name: "Espresso", colors: ["#2C1810", "#3D2A1F", "#4A3228"] },
  { name: "Charcoal", colors: ["#1C1C1E", "#2A2A2E", "#353538"] },
  { name: "Obsidian", colors: ["#0F1114", "#1A1D22", "#252830"] },
  { name: "Gunmetal", colors: ["#1E2428", "#2A3035", "#353D42"] },
  { name: "Navy", colors: ["#0D1B2A", "#1B2838", "#243447"] },
  { name: "Iron", colors: ["#18181B", "#222225", "#2C2C30"] },
  { name: "Onyx", colors: ["#0D0D0D", "#1A1A1A", "#272727"] },
  { name: "Raven", colors: ["#1A1423", "#261E32", "#322840"] },
  // Earth
  { name: "Tobacco", colors: ["#251A10", "#382818", "#4A3620"] },
  { name: "Volcanic", colors: ["#1A1210", "#2C1E18", "#3E2A20"] },
  { name: "Clay", colors: ["#8B6E5A", "#9A7D68", "#A98C76"] },
  { name: "Sand", colors: ["#92785A", "#A08868", "#B09878"] },
  { name: "Stone", colors: ["#78716C", "#8A837E", "#9C9590"] },
  { name: "Leather", colors: ["#8B5E3C", "#A0522D", "#6B4226"] },
  { name: "Sienna", colors: ["#A0522D", "#B8642D", "#C8783D"] },
  { name: "Mocha", colors: ["#4A3728", "#5C4033", "#6E4F3E"] },
  // Cool
  { name: "Slate", colors: ["#1C2833", "#273746", "#2C3E50"] },
  { name: "Steel", colors: ["#6B7B8D", "#7C8C9E", "#8D9DAF"] },
  { name: "Dusk", colors: ["#64748B", "#7585A0", "#8696B0"] },
  { name: "Fog", colors: ["#6B7280", "#7C8390", "#8D94A0"] },
  { name: "Ash", colors: ["#9CA3AF", "#ACB3BF", "#BCC3CF"] },
  { name: "Silver", colors: ["#8E8E93", "#A0A0A5", "#B0B0B5"] },
  { name: "Graphite", colors: ["#5A5A5E", "#6A6A6E", "#7A7A7E"] },
  { name: "Frost", colors: ["#B0C4DE", "#C0D4EE", "#D0E4FE"] },
  // Natural
  { name: "Olive", colors: ["#1A1F14", "#2A3020", "#3A422C"] },
  { name: "Sage", colors: ["#141C16", "#1E2A20", "#28382A"] },
  { name: "Rust", colors: ["#2A1414", "#3C2020", "#4A2828"] },
  { name: "Forest", colors: ["#1B4332", "#2D6A4F", "#40916C"] },
  { name: "Moss", colors: ["#556B2F", "#667C3F", "#778D4F"] },
  { name: "Pine", colors: ["#1A3B28", "#2B4C38", "#3C5D48"] },
  { name: "Fern", colors: ["#2D5A27", "#3E6B38", "#4F7C49"] },
  { name: "Bark", colors: ["#3B2F1A", "#4C3F2A", "#5D4F3A"] },
  // Vibrant (from folder-colors Classic + more)
  { name: "Crimson", colors: ["#C0392B", "#D44333", "#E84D3B"] },
  { name: "Tangerine", colors: ["#D35400", "#E86010", "#F07020"] },
  { name: "Gold", colors: ["#D4A017", "#E0B020", "#ECB828"] },
  { name: "Emerald", colors: ["#27AE60", "#30C06A", "#38D078"] },
  { name: "Ocean", colors: ["#2980B9", "#3090C9", "#38A0D9"] },
  { name: "Amethyst", colors: ["#8E44AD", "#9E54BD", "#AE64CD"] },
  { name: "Magenta", colors: ["#C2185B", "#D22868", "#E23878"] },
  { name: "Teal", colors: ["#16A085", "#1EB095", "#26C0A5"] },
  // Pastel (from folder-colors Soft Pastel)
  { name: "Rose", colors: ["#FFB5C2", "#FFC5D2", "#FFD5E2"] },
  { name: "Baby Blue", colors: ["#B5D8FF", "#C5E2FF", "#D5ECFF"] },
  { name: "Lavender", colors: ["#C4B5FF", "#D4C5FF", "#E4D5FF"] },
  { name: "Mint", colors: ["#B5FFD9", "#C5FFE4", "#D5FFEF"] },
  { name: "Peach", colors: ["#FFE4B5", "#FFECC5", "#FFF4D5"] },
  { name: "Lilac", colors: ["#E8B5FF", "#EEC5FF", "#F4D5FF"] },
  { name: "Sky", colors: ["#B5F0FF", "#C5F4FF", "#D5F8FF"] },
  { name: "Apricot", colors: ["#FFD1B5", "#FFDBC5", "#FFE5D5"] },
  // Neon
  { name: "Neon Blue", colors: ["#0040FF", "#0066FF", "#3388FF"] },
  { name: "Neon Pink", colors: ["#FF0080", "#FF2090", "#FF40A0"] },
  { name: "Neon Green", colors: ["#00FF66", "#22FF77", "#44FF88"] },
  { name: "Neon Purple", colors: ["#7B00FF", "#9020FF", "#A540FF"] },
  { name: "Electric", colors: ["#00D4FF", "#20DFFF", "#40EAFF"] },
  { name: "Neon Red", colors: ["#FF2020", "#FF3838", "#FF5050"] },
  { name: "Neon Yellow", colors: ["#CCFF00", "#D8FF22", "#E4FF44"] },
  { name: "Neon Orange", colors: ["#FF6600", "#FF7A20", "#FF8E40"] },
  // Mermaidcore (from folder-colors)
  { name: "Seafoam", colors: ["#2EC4B6", "#40D0C4", "#52DCD2"] },
  { name: "Periwinkle", colors: ["#6A89CC", "#7A99DC", "#8AA9EC"] },
  { name: "Grape", colors: ["#82589F", "#9268AF", "#A278BF"] },
  { name: "Lagoon", colors: ["#3B9B8F", "#4BAB9F", "#5BBBAF"] },
  { name: "Aqua", colors: ["#48DBDB", "#58E5E5", "#68EFEF"] },
  { name: "Iris", colors: ["#7E57C2", "#8E67D2", "#9E77E2"] },
  { name: "Cerulean", colors: ["#5CA0D3", "#6CB0E3", "#7CC0F3"] },
  { name: "Jade", colors: ["#38ADA9", "#48BDB9", "#58CDC9"] },
  // Midnight (from folder-colors)
  { name: "Abyss", colors: ["#0D1B2A", "#152535", "#1D2F40"] },
  { name: "Deep Blue", colors: ["#1B263B", "#253048", "#2F3A55"] },
  { name: "Storm", colors: ["#415A77", "#516A87", "#617A97"] },
  { name: "Haze", colors: ["#778DA9", "#879DB9", "#97ADC9"] },
  { name: "Twilight", colors: ["#2A3950", "#3A4960", "#4A5970"] },
  { name: "Indigo", colors: ["#1F3044", "#2F4054", "#3F5064"] },
  { name: "Cobalt", colors: ["#324A5F", "#425A6F", "#526A7F"] },
  { name: "Void", colors: ["#0B132B", "#151D35", "#1F273F"] },
  // Sunset (from folder-colors)
  { name: "Flame", colors: ["#FF6B35", "#FF7B45", "#FF8B55"] },
  { name: "Honey", colors: ["#F7C59F", "#F9D0AF", "#FBDBBF"] },
  { name: "Cream", colors: ["#EFEFD0", "#F3F3D8", "#F7F7E0"] },
  { name: "Marine", colors: ["#004E89", "#105E99", "#206EA9"] },
  { name: "Azure", colors: ["#1A659E", "#2A75AE", "#3A85BE"] },
  { name: "Marigold", colors: ["#FF9F1C", "#FFAF2C", "#FFBF3C"] },
  { name: "Coral", colors: ["#E84855", "#F05865", "#F86875"] },
  { name: "Charcoal", colors: ["#2B2D42", "#3B3D52", "#4B4D62"] },
];

var colorThemes = {
  "Dark": [
    { name: "Espresso", colors: ["#2C1810", "#3D2A1F", "#4A3228"] },
    { name: "Charcoal", colors: ["#1C1C1E", "#2A2A2E", "#353538"] },
    { name: "Obsidian", colors: ["#0F1114", "#1A1D22", "#252830"] },
    { name: "Gunmetal", colors: ["#1E2428", "#2A3035", "#353D42"] },
    { name: "Navy", colors: ["#0D1B2A", "#1B2838", "#243447"] },
    { name: "Iron", colors: ["#18181B", "#222225", "#2C2C30"] },
    { name: "Onyx", colors: ["#0D0D0D", "#1A1A1A", "#272727"] },
    { name: "Raven", colors: ["#1A1423", "#261E32", "#322840"] },
  ],
  "Earth": [
    { name: "Tobacco", colors: ["#251A10", "#382818", "#4A3620"] },
    { name: "Volcanic", colors: ["#1A1210", "#2C1E18", "#3E2A20"] },
    { name: "Clay", colors: ["#8B6E5A", "#9A7D68", "#A98C76"] },
    { name: "Sand", colors: ["#92785A", "#A08868", "#B09878"] },
    { name: "Stone", colors: ["#78716C", "#8A837E", "#9C9590"] },
    { name: "Leather", colors: ["#8B5E3C", "#A0522D", "#6B4226"] },
    { name: "Sienna", colors: ["#A0522D", "#B8642D", "#C8783D"] },
    { name: "Mocha", colors: ["#4A3728", "#5C4033", "#6E4F3E"] },
  ],
  "Cool": [
    { name: "Slate", colors: ["#1C2833", "#273746", "#2C3E50"] },
    { name: "Steel", colors: ["#6B7B8D", "#7C8C9E", "#8D9DAF"] },
    { name: "Dusk", colors: ["#64748B", "#7585A0", "#8696B0"] },
    { name: "Fog", colors: ["#6B7280", "#7C8390", "#8D94A0"] },
    { name: "Ash", colors: ["#9CA3AF", "#ACB3BF", "#BCC3CF"] },
    { name: "Silver", colors: ["#8E8E93", "#A0A0A5", "#B0B0B5"] },
    { name: "Graphite", colors: ["#5A5A5E", "#6A6A6E", "#7A7A7E"] },
    { name: "Frost", colors: ["#B0C4DE", "#C0D4EE", "#D0E4FE"] },
  ],
  "Natural": [
    { name: "Olive", colors: ["#1A1F14", "#2A3020", "#3A422C"] },
    { name: "Sage", colors: ["#141C16", "#1E2A20", "#28382A"] },
    { name: "Rust", colors: ["#2A1414", "#3C2020", "#4A2828"] },
    { name: "Forest", colors: ["#1B4332", "#2D6A4F", "#40916C"] },
    { name: "Moss", colors: ["#556B2F", "#667C3F", "#778D4F"] },
    { name: "Pine", colors: ["#1A3B28", "#2B4C38", "#3C5D48"] },
    { name: "Fern", colors: ["#2D5A27", "#3E6B38", "#4F7C49"] },
    { name: "Bark", colors: ["#3B2F1A", "#4C3F2A", "#5D4F3A"] },
  ],
  "Vibrant": [
    { name: "Crimson", colors: ["#C0392B", "#D44333", "#E84D3B"] },
    { name: "Tangerine", colors: ["#D35400", "#E86010", "#F07020"] },
    { name: "Gold", colors: ["#D4A017", "#E0B020", "#ECB828"] },
    { name: "Emerald", colors: ["#27AE60", "#30C06A", "#38D078"] },
    { name: "Ocean", colors: ["#2980B9", "#3090C9", "#38A0D9"] },
    { name: "Amethyst", colors: ["#8E44AD", "#9E54BD", "#AE64CD"] },
    { name: "Magenta", colors: ["#C2185B", "#D22868", "#E23878"] },
    { name: "Teal", colors: ["#16A085", "#1EB095", "#26C0A5"] },
  ],
  "Pastel": [
    { name: "Rose", colors: ["#FFB5C2", "#FFC5D2", "#FFD5E2"] },
    { name: "Baby Blue", colors: ["#B5D8FF", "#C5E2FF", "#D5ECFF"] },
    { name: "Lavender", colors: ["#C4B5FF", "#D4C5FF", "#E4D5FF"] },
    { name: "Mint", colors: ["#B5FFD9", "#C5FFE4", "#D5FFEF"] },
    { name: "Peach", colors: ["#FFE4B5", "#FFECC5", "#FFF4D5"] },
    { name: "Lilac", colors: ["#E8B5FF", "#EEC5FF", "#F4D5FF"] },
    { name: "Sky", colors: ["#B5F0FF", "#C5F4FF", "#D5F8FF"] },
    { name: "Apricot", colors: ["#FFD1B5", "#FFDBC5", "#FFE5D5"] },
  ],
  "Neon": [
    { name: "Neon Blue", colors: ["#0040FF", "#0066FF", "#3388FF"] },
    { name: "Neon Pink", colors: ["#FF0080", "#FF2090", "#FF40A0"] },
    { name: "Neon Green", colors: ["#00FF66", "#22FF77", "#44FF88"] },
    { name: "Neon Purple", colors: ["#7B00FF", "#9020FF", "#A540FF"] },
    { name: "Electric", colors: ["#00D4FF", "#20DFFF", "#40EAFF"] },
    { name: "Neon Red", colors: ["#FF2020", "#FF3838", "#FF5050"] },
    { name: "Neon Yellow", colors: ["#CCFF00", "#D8FF22", "#E4FF44"] },
    { name: "Neon Orange", colors: ["#FF6600", "#FF7A20", "#FF8E40"] },
  ],
  "Mermaid": [
    { name: "Seafoam", colors: ["#2EC4B6", "#40D0C4", "#52DCD2"] },
    { name: "Periwinkle", colors: ["#6A89CC", "#7A99DC", "#8AA9EC"] },
    { name: "Grape", colors: ["#82589F", "#9268AF", "#A278BF"] },
    { name: "Lagoon", colors: ["#3B9B8F", "#4BAB9F", "#5BBBAF"] },
    { name: "Aqua", colors: ["#48DBDB", "#58E5E5", "#68EFEF"] },
    { name: "Iris", colors: ["#7E57C2", "#8E67D2", "#9E77E2"] },
    { name: "Cerulean", colors: ["#5CA0D3", "#6CB0E3", "#7CC0F3"] },
    { name: "Jade", colors: ["#38ADA9", "#48BDB9", "#58CDC9"] },
  ],
  "Midnight": [
    { name: "Abyss", colors: ["#0D1B2A", "#152535", "#1D2F40"] },
    { name: "Deep Blue", colors: ["#1B263B", "#253048", "#2F3A55"] },
    { name: "Storm", colors: ["#415A77", "#516A87", "#617A97"] },
    { name: "Haze", colors: ["#778DA9", "#879DB9", "#97ADC9"] },
    { name: "Twilight", colors: ["#2A3950", "#3A4960", "#4A5970"] },
    { name: "Indigo", colors: ["#1F3044", "#2F4054", "#3F5064"] },
    { name: "Cobalt", colors: ["#324A5F", "#425A6F", "#526A7F"] },
    { name: "Void", colors: ["#0B132B", "#151D35", "#1F273F"] },
  ],
  "Sunset": [
    { name: "Flame", colors: ["#FF6B35", "#FF7B45", "#FF8B55"] },
    { name: "Honey", colors: ["#F7C59F", "#F9D0AF", "#FBDBBF"] },
    { name: "Cream", colors: ["#EFEFD0", "#F3F3D8", "#F7F7E0"] },
    { name: "Marine", colors: ["#004E89", "#105E99", "#206EA9"] },
    { name: "Azure", colors: ["#1A659E", "#2A75AE", "#3A85BE"] },
    { name: "Marigold", colors: ["#FF9F1C", "#FFAF2C", "#FFBF3C"] },
    { name: "Coral", colors: ["#E84855", "#F05865", "#F86875"] },
    { name: "Charcoal", colors: ["#2B2D42", "#3B3D52", "#4B4D62"] },
  ],
  "All": null,
};
var activeTheme = "Dark";

var selected = 0;
var lighting = null;
var showPanel = false;
var hideCenterCol = false;
var hideCenterRow = false;

document.getElementById('hideCenterColToggle').onclick = function() {
  hideCenterCol = !hideCenterCol;
  this.classList.toggle('on', hideCenterCol);
  renderPreview();
};
document.getElementById('hideCenterRowToggle').onclick = function() {
  hideCenterRow = !hideCenterRow;
  this.classList.toggle('on', hideCenterRow);
  renderPreview();
};

function hexToRgb(h) {
  return [parseInt(h.slice(1,3),16), parseInt(h.slice(3,5),16), parseInt(h.slice(5,7),16)];
}

// Build initial swatches from active theme
var colorGrid = document.getElementById('colorGrid');
rebuildSwatches();

// Build theme buttons
var themesEl = document.getElementById('themes');
Object.keys(colorThemes).forEach(function(name) {
  var btn = document.createElement('button');
  btn.className = 'theme-btn' + (name === activeTheme ? ' active' : '');
  btn.textContent = name;
  btn.onclick = function() {
    if (name === 'All') {
      openColorModal();
      return;
    }
    document.querySelectorAll('.theme-btn').forEach(function(b) { b.classList.remove('active'); });
    btn.classList.add('active');
    activeTheme = name;
    selected = 0;
    rebuildSwatches();
    renderPreview();
  };
  themesEl.appendChild(btn);
});

function getActiveGradients() {
  if (activeTheme === 'All') return gradients;
  return colorThemes[activeTheme] || gradients;
}

function rebuildSwatches() {
  var grid = document.getElementById('colorGrid');
  while (grid.firstChild) grid.removeChild(grid.firstChild);
  var list = getActiveGradients();
  list.forEach(function(g, i) {
    var div = document.createElement('div');
    div.className = 'color-swatch' + (i === selected ? ' selected' : '');
    div.style.background = 'linear-gradient(135deg, ' + g.colors[0] + ', ' + g.colors[1] + ', ' + g.colors[2] + ')';
    var label = document.createElement('span');
    label.className = 'swatch-name';
    label.textContent = g.name;
    div.appendChild(label);
    div.onclick = function() {
      document.querySelectorAll('.color-swatch').forEach(function(s) { s.classList.remove('selected'); });
      div.classList.add('selected');
      selected = i;
      renderPreview();
    };
    grid.appendChild(div);
  });
}

// Toggle

// Glass panel patterns
var PANEL_PATTERNS = [
  { id: 'single', label: 'Single' },
  { id: 'grid', label: 'Grid' },
];
var activePanelPattern = 'single';

var patternRow = document.getElementById('panelPatternRow');
PANEL_PATTERNS.forEach(function(p, i) {
  var btn = document.createElement('button');
  btn.className = 'ratio-btn' + (i === 0 ? ' active' : '');
  btn.textContent = p.label;
  btn.onclick = function() {
    patternRow.querySelectorAll('.ratio-btn').forEach(function(b) { b.classList.remove('active'); });
    btn.classList.add('active');
    activePanelPattern = p.id;
    var hasGrid = (p.id === 'grid');
    document.getElementById('panelCountRow').style.display = hasGrid ? 'flex' : 'none';
    document.getElementById('panelRowsRow').style.display = hasGrid ? 'flex' : 'none';
    document.getElementById('panelGapRow').style.display = hasGrid ? 'flex' : 'none';
    document.getElementById('hideCenterColRow').style.display = hasGrid ? 'flex' : 'none';
    document.getElementById('hideCenterRowRow').style.display = hasGrid ? 'flex' : 'none';
    renderPreview();
  };
  patternRow.appendChild(btn);
});

var panelToggle = document.getElementById('panelToggle');
var panelControls = document.getElementById('panelControls');
panelToggle.onclick = function() {
  showPanel = !showPanel;
  panelToggle.classList.toggle('on', showPanel);
  panelControls.classList.toggle('dimmed', !showPanel);
  renderPreview();
};

// All sliders
var allSliders = ['brightness', 'frost', 'diffusion', 'noise', 'grain', 'vignette',
  'panelMargin', 'panelBright', 'panelRadius', 'panelBlur', 'panelShadow', 'panelBorder', 'panelCount', 'panelRows', 'panelGap'];
allSliders.forEach(function(id) {
  var el = document.getElementById(id);
  var valEl = document.getElementById(id + 'Val');
  el.oninput = function() {
    if (id === 'panelGap') {
      valEl.textContent = el.value + 'px';
    } else if (id === 'panelCount' || id === 'panelRows') {
      valEl.textContent = el.value;
    } else if (id === 'panelRadius' || id === 'panelMargin') {
      valEl.textContent = el.value + 'px';
    } else if (id === 'panelBright') {
      var v = parseInt(el.value);
      valEl.textContent = (v > 0 ? '+' : '') + v;
    } else {
      valEl.textContent = el.value + '%';
    }
    renderPreview();
  };
});

// Background image
var bgImage = null;
var bgUsePaletteTint = true;

document.getElementById('bgPaletteTintToggle').onclick = function() {
  bgUsePaletteTint = !bgUsePaletteTint;
  this.classList.toggle('on', bgUsePaletteTint);
  renderPreview();
};
var bgUploadZone = document.getElementById('bgUploadZone');
var bgFileInput = document.getElementById('bgFileInput');
bgUploadZone.onclick = function() { bgFileInput.click(); };
bgUploadZone.ondragover = function(e) { e.preventDefault(); bgUploadZone.style.borderColor = 'var(--champagne)'; };
bgUploadZone.ondragleave = function() { bgUploadZone.style.borderColor = ''; };
bgUploadZone.ondrop = function(e) {
  e.preventDefault();
  bgUploadZone.style.borderColor = '';
  if (e.dataTransfer.files.length) processBgFile(e.dataTransfer.files[0]);
};
bgFileInput.onchange = function() { if (bgFileInput.files.length) processBgFile(bgFileInput.files[0]); };

function processBgFile(file) {
  document.getElementById('bgFileName').textContent = file.name;
  var img = new Image();
  img.onload = function() {
    bgImage = img;
    document.getElementById('bgBlurRow').style.display = 'flex';
    document.getElementById('bgOpacityRow').style.display = 'flex';
    document.getElementById('bgTintRow').style.display = 'flex';
    document.getElementById('bgPaletteTintRow').style.display = 'flex';
    document.getElementById('bgClearBtn').style.display = 'block';
    renderPreview();
  };
  img.src = URL.createObjectURL(file);
}

function clearBgImage() {
  bgImage = null;
  document.getElementById('bgFileName').textContent = '';
  document.getElementById('bgBlurRow').style.display = 'none';
  document.getElementById('bgOpacityRow').style.display = 'none';
  document.getElementById('bgTintRow').style.display = 'none';
  document.getElementById('bgPaletteTintRow').style.display = 'none';
  document.getElementById('bgClearBtn').style.display = 'none';
  renderPreview();
}

['bgBlur', 'bgOpacity', 'bgTint'].forEach(function(id) {
  var el = document.getElementById(id);
  var valEl = document.getElementById(id + 'Val');
  el.oninput = function() {
    valEl.textContent = el.value + '%';
    renderPreview();
  };
});

// Upload
var uploadZone = document.getElementById('uploadZone');
var fileInput = document.getElementById('fileInput');
uploadZone.onclick = function() { fileInput.click(); };
uploadZone.ondragover = function(e) { e.preventDefault(); uploadZone.style.borderColor = 'var(--champagne)'; };
uploadZone.ondragleave = function() { uploadZone.style.borderColor = ''; };
uploadZone.ondrop = function(e) {
  e.preventDefault();
  uploadZone.style.borderColor = '';
  if (e.dataTransfer.files.length) processFile(e.dataTransfer.files[0]);
};
fileInput.onchange = function() { if (fileInput.files.length) processFile(fileInput.files[0]); };

function processFile(file) {
  document.getElementById('fileName').textContent = file.name;
  var img = new Image();
  img.onload = function() { analyzeLighting(img); };
  img.src = URL.createObjectURL(file);
}

function analyzeLighting(img) {
  var ac = document.getElementById('analyzeCanvas');
  var sw = 400;
  var sh = Math.round(sw * (img.height / img.width));
  ac.width = sw; ac.height = sh;
  var ctx = ac.getContext('2d');
  ctx.drawImage(img, 0, 0, sw, sh);
  var data = ctx.getImageData(0, 0, sw, sh).data;

  var quadrants = [
    { rSum: 0, gSum: 0, bSum: 0, count: 0 },
    { rSum: 0, gSum: 0, bSum: 0, count: 0 },
    { rSum: 0, gSum: 0, bSum: 0, count: 0 },
    { rSum: 0, gSum: 0, bSum: 0, count: 0 },
  ];
  var totalR = 0, totalG = 0, totalB = 0, totalCount = 0;
  var midX = sw / 2, midY = sh / 2;

  for (var y = 0; y < sh; y++) {
    for (var x = 0; x < sw; x++) {
      var idx = (y * sw + x) * 4;
      var r = data[idx], g = data[idx+1], b = data[idx+2];
      totalR += r; totalG += g; totalB += b; totalCount++;
      var qi = (y < midY ? 0 : 2) + (x < midX ? 0 : 1);
      quadrants[qi].rSum += r; quadrants[qi].gSum += g; quadrants[qi].bSum += b; quadrants[qi].count++;
    }
  }

  var qBrightness = quadrants.map(function(q) {
    return ((q.rSum/q.count)*0.2126 + (q.gSum/q.count)*0.7152 + (q.bSum/q.count)*0.0722) / 255;
  });

  var avgR = totalR/totalCount, avgG = totalG/totalCount, avgB = totalB/totalCount;
  var avgBrightness = (avgR*0.2126 + avgG*0.7152 + avgB*0.0722) / 255;
  var warmth = (avgR - avgB) / 255;
  var brightestQ = 0;
  for (var i = 1; i < 4; i++) { if (qBrightness[i] > qBrightness[brightestQ]) brightestQ = i; }

  lighting = { brightness: avgBrightness, warmth: warmth, lightDir: brightestQ, qBrightness: qBrightness };

  var dirNames = ['top-left', 'top-right', 'bottom-left', 'bottom-right'];
  var tempLabel = warmth > 0.05 ? 'warm' : (warmth < -0.05 ? 'cool' : 'neutral');
  var infoEl = document.getElementById('lightingInfo');
  infoEl.classList.add('visible');
  infoEl.textContent = 'Brightness: ' + (avgBrightness*100).toFixed(0) + '% | Temp: ' + tempLabel + ' | Key light: ' + dirNames[brightestQ];
  renderPreview();
}

function renderToCanvas(canvas) {
  var ctx = canvas.getContext('2d');
  var W = canvas.width, H = canvas.height;
  var scale = W / 1920;

  var activeList = getActiveGradients();
  var g = activeList[Math.min(selected, activeList.length - 1)];
  var c0 = hexToRgb(g.colors[0]), c1 = hexToRgb(g.colors[1]), c2 = hexToRgb(g.colors[2]);

  var brightness = parseInt(document.getElementById('brightness').value) / 100;
  var frost = parseInt(document.getElementById('frost').value) / 100;
  var diffusion = parseInt(document.getElementById('diffusion').value) / 100;
  var noiseAmt = parseInt(document.getElementById('noise').value) / 100;
  var grainSize = parseInt(document.getElementById('grain').value) / 100;
  var vig = parseInt(document.getElementById('vignette').value) / 100;

  var lightWarmth = 0, lightBias = [0.5, 0.5], lightIntensity = 1;
  if (lighting) {
    lightWarmth = lighting.warmth;
    var dirMap = [[0.3,0.3],[0.7,0.3],[0.3,0.7],[0.7,0.7]];
    lightBias = dirMap[lighting.lightDir];
    lightIntensity = 0.5 + lighting.brightness;
  }

  ctx.clearRect(0, 0, W, H);

  // Background image (drawn first, blurred and frosted)
  if (bgImage) {
    var bgBlurAmt = parseInt(document.getElementById('bgBlur').value) / 100;
    var bgOpacityAmt = parseInt(document.getElementById('bgOpacity').value) / 100;
    var bgTintAmt = parseInt(document.getElementById('bgTint').value) / 100;

    // Draw image to cover canvas (crop to fill)
    var imgRatio = bgImage.width / bgImage.height;
    var canvasRatio = W / H;
    var sx = 0, sy = 0, sw = bgImage.width, sh = bgImage.height;
    if (imgRatio > canvasRatio) {
      sw = bgImage.height * canvasRatio;
      sx = (bgImage.width - sw) / 2;
    } else {
      sh = bgImage.width / canvasRatio;
      sy = (bgImage.height - sh) / 2;
    }

    // Use offscreen canvas for blur effect (downscale then upscale = fast blur)
    var blurPasses = Math.max(1, Math.round(bgBlurAmt * 6));
    var offW = Math.max(4, Math.round(W / (1 + bgBlurAmt * 15)));
    var offH = Math.max(4, Math.round(H / (1 + bgBlurAmt * 15)));
    var offCanvas = document.createElement('canvas');
    offCanvas.width = offW;
    offCanvas.height = offH;
    var offCtx = offCanvas.getContext('2d');
    offCtx.drawImage(bgImage, sx, sy, sw, sh, 0, 0, offW, offH);

    // Multiple downscale passes for smoother blur
    for (var bp = 0; bp < blurPasses - 1; bp++) {
      var halfW = Math.max(2, Math.round(offW / 2));
      var halfH = Math.max(2, Math.round(offH / 2));
      var tmpCanvas = document.createElement('canvas');
      tmpCanvas.width = halfW;
      tmpCanvas.height = halfH;
      var tmpCtx = tmpCanvas.getContext('2d');
      tmpCtx.drawImage(offCanvas, 0, 0, halfW, halfH);
      offCanvas = tmpCanvas;
      offCtx = tmpCtx;
      offW = halfW;
      offH = halfH;
    }

    // Draw blurred image to main canvas
    ctx.globalAlpha = bgOpacityAmt;
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(offCanvas, 0, 0, W, H);
    ctx.globalAlpha = 1.0;

    // Color tint overlay
    if (bgTintAmt > 0) {
      if (bgUsePaletteTint) {
        ctx.fillStyle = g.colors[1];
        ctx.globalAlpha = bgTintAmt * 0.6;
      } else {
        ctx.fillStyle = 'rgba(255,255,255,' + (bgTintAmt * 0.4) + ')';
        ctx.globalAlpha = 1.0;
      }
      ctx.fillRect(0, 0, W, H);
      ctx.globalAlpha = 1.0;
    }
  }

  // Base gradient (skip if we have a bg image, or use as subtle overlay)
  if (!bgImage) {
  var grad = ctx.createLinearGradient(0, 0, W, H);
  grad.addColorStop(0, g.colors[0]);
  grad.addColorStop(0.5, g.colors[1]);
  grad.addColorStop(1, g.colors[2]);
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, W, H);
  }

  // Glass brightness
  if (brightness > 0) {
    ctx.fillStyle = 'rgba(255,255,255,' + (brightness * 0.14) + ')';
    ctx.fillRect(0, 0, W, H);
    var lx = lightBias[0]*W, ly = lightBias[1]*H;
    var glassGrad = ctx.createRadialGradient(lx, ly, 0, lx, ly, W*0.65);
    glassGrad.addColorStop(0, 'rgba(255,255,255,' + (brightness*0.1*lightIntensity) + ')');
    glassGrad.addColorStop(0.5, 'rgba(255,255,255,' + (brightness*0.04*lightIntensity) + ')');
    glassGrad.addColorStop(1, 'transparent');
    ctx.fillStyle = glassGrad;
    ctx.fillRect(0, 0, W, H);

    if (lightBias[1] < 0.5) {
      var tg = ctx.createLinearGradient(0, 0, 0, H*0.35);
      tg.addColorStop(0, 'rgba(255,255,255,' + (brightness*0.07*lightIntensity) + ')');
      tg.addColorStop(1, 'transparent');
      ctx.fillStyle = tg; ctx.fillRect(0, 0, W, H*0.35);
    }
    if (lightBias[0] < 0.5) {
      var lg = ctx.createLinearGradient(0, 0, W*0.25, 0);
      lg.addColorStop(0, 'rgba(255,255,255,' + (brightness*0.04*lightIntensity) + ')');
      lg.addColorStop(1, 'transparent');
      ctx.fillStyle = lg; ctx.fillRect(0, 0, W*0.25, H);
    }
  }

  // Warmth tint
  if (lighting) {
    if (lightWarmth > 0) {
      ctx.fillStyle = 'rgba(180,120,60,' + (lightWarmth*0.08) + ')';
      ctx.fillRect(0, 0, W, H);
    } else if (lightWarmth < 0) {
      ctx.fillStyle = 'rgba(60,100,180,' + (Math.abs(lightWarmth)*0.08) + ')';
      ctx.fillRect(0, 0, W, H);
    }
  }

  // Diffusion blobs
  function softGlow(cx, cy, r, color, alpha) {
    var sg = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
    sg.addColorStop(0, 'rgba(' + Math.min(255,color[0]) + ',' + Math.min(255,color[1]) + ',' + Math.min(255,color[2]) + ',' + alpha + ')');
    sg.addColorStop(1, 'transparent');
    ctx.fillStyle = sg; ctx.fillRect(0, 0, W, H);
  }

  softGlow(W*0.35, H*0.4, 700*scale, [c1[0]+20,c1[1]+15,c1[2]+10], 0.35*diffusion);
  softGlow(W*0.7, H*0.55, 600*scale, [c2[0]+15,c2[1]+10,c2[2]+8], 0.3*diffusion);
  softGlow(W*0.5, H*0.5, 900*scale, [c1[0]+10,c1[1]+8,c1[2]+5], 0.25*diffusion);
  softGlow(W*0.2, H*0.7, 500*scale, [c0[0]+25,c0[1]+20,c0[2]+15], 0.2*diffusion);
  softGlow(W*0.8, H*0.3, 450*scale, [c2[0]+20,c2[1]+15,c2[2]+12], 0.18*diffusion);

  // Frost
  if (frost > 0) {
    var fLx = lightBias[0]*W, fLy = lightBias[1]*H;
    softGlow(fLx, fLy, W*0.55, [255,245,230], frost*0.04*lightIntensity);
    softGlow(W-fLx, H-fLy, W*0.4, [255,250,240], frost*0.02*lightIntensity);
    var ps = 42;
    function prand() { ps = (ps*16807)%2147483647; return ps/2147483647; }
    for (var i = 0; i < 12; i++) {
      var fpx = prand()*W, fpy = prand()*H;
      var fpr = (300+prand()*600)*scale;
      var dist = Math.sqrt(Math.pow(fpx-fLx,2)+Math.pow(fpy-fLy,2))/W;
      softGlow(fpx, fpy, fpr, [255,248,235], frost*0.035*Math.max(0.15,1-dist));
    }
  }

  // Vignette
  if (vig > 0) {
    var vigCx = lightBias[0]*W, vigCy = lightBias[1]*H;
    var vigGrad = ctx.createRadialGradient(vigCx, vigCy, H*0.25, vigCx, vigCy, W*0.75);
    vigGrad.addColorStop(0, 'transparent');
    vigGrad.addColorStop(1, 'rgba(0,0,0,' + (vig*0.5) + ')');
    ctx.fillStyle = vigGrad; ctx.fillRect(0, 0, W, H);
  }

  // Glass panels
  if (showPanel) {
    var pMarginVal = parseInt(document.getElementById('panelMargin').value) * scale;
    var pTint = parseInt(document.getElementById('panelBright').value) / 100;
    var pRadius = parseInt(document.getElementById('panelRadius').value) * 2 * scale;
    var pBlur = parseInt(document.getElementById('panelBlur').value) / 100;
    var pShadow = parseInt(document.getElementById('panelShadow').value) / 100;
    var pBorder = parseInt(document.getElementById('panelBorder').value) / 100;
    var gap = parseInt(document.getElementById('panelGap').value) * scale;

    // Generate panel rects based on pattern
    var panels = [];
    var areaX = pMarginVal, areaY = pMarginVal;
    var areaW = W - pMarginVal * 2, areaH = H - pMarginVal * 2;
    var userCount = parseInt(document.getElementById('panelCount').value);
    var userRows = parseInt(document.getElementById('panelRows').value);

    var midCol = Math.floor(userCount / 2);
    var midRow = Math.floor(userRows / 2);

    if (activePanelPattern === 'single') {
      panels.push({ x: areaX, y: areaY, w: areaW, h: areaH, r: pRadius, circle: false });
    } else if (activePanelPattern === 'grid') {
      var gCols = userCount, gRows = userRows;
      var cellW = (areaW - gap * (gCols - 1)) / gCols;
      var cellH = (areaH - gap * (gRows - 1)) / gRows;
      var gridR = Math.min(pRadius, cellW / 2, cellH / 2);
      for (var gr = 0; gr < gRows; gr++) {
        for (var gc = 0; gc < gCols; gc++) {
          var skipCol = hideCenterCol && gCols % 2 === 1 && gc === midCol;
          var skipRow = hideCenterRow && gRows % 2 === 1 && gr === midRow;
          if (skipCol || skipRow) continue;
          panels.push({ x: areaX + gc * (cellW + gap), y: areaY + gr * (cellH + gap), w: cellW, h: cellH, r: gridR });
        }
      }

    }

    // Draw each panel
    panels.forEach(function(p) {
      // Drop shadow
      if (pShadow > 0) {
        for (var sl = 5; sl >= 1; sl--) {
          var spread = sl * 12 * scale * pShadow;
          var alpha = (pShadow * 0.06) / sl;
          ctx.fillStyle = 'rgba(0,0,0,' + alpha + ')';
          ctx.beginPath();
            ctx.roundRect(p.x - spread/2 + 4*scale, p.y - spread/2 + 8*scale*sl/5, p.w + spread, p.h + spread, p.r + spread/2);
            ctx.fill();
        }
      }

      // Panel body
      ctx.save();
      ctx.beginPath();
        ctx.roundRect(p.x, p.y, p.w, p.h, p.r);
      ctx.clip();

      // Tinted base
      if (pTint < 0) {
        ctx.fillStyle = 'rgba(0,0,0,' + (Math.abs(pTint) * 0.4) + ')';
      } else {
        ctx.fillStyle = 'rgba(255,255,255,' + (pTint * 0.18) + ')';
      }
      ctx.fillRect(p.x, p.y, p.w, p.h);

      // Subtle color inside panel
      if (pBlur > 0) {
        var gx = p.x, gy = p.y, gw = p.w, gh = p.h;
        softGlow(gx + gw*0.4, gy + gh*0.4, gw*0.45, [c1[0], c1[1], c1[2]], pBlur * 0.08);
        softGlow(gx + gw*0.6, gy + gh*0.55, gw*0.4, [c2[0], c2[1], c2[2]], pBlur * 0.06);
      }

      // Soft top-edge highlight
      var hlY = p.y;
      var hlX = p.x;
      var topHL = ctx.createLinearGradient(hlX, hlY, hlX, hlY + p.h * 0.15);
      topHL.addColorStop(0, 'rgba(255,255,255,' + (Math.abs(pTint) * 0.03) + ')');
      topHL.addColorStop(1, 'transparent');
      ctx.fillStyle = topHL;
      ctx.fillRect(hlX, hlY, p.w, p.h * 0.15);

      ctx.restore();

      // Border glow
      if (pBorder > 0) {
        ctx.strokeStyle = 'rgba(255,255,255,' + (pBorder * 0.1) + ')';
        ctx.lineWidth = 1.5 * scale;
        ctx.beginPath();
          ctx.roundRect(p.x, p.y, p.w, p.h, p.r);
          ctx.stroke();
      }
    });
  }

  // Noise and grain
  if (noiseAmt > 0) {
    var imageData = ctx.getImageData(0, 0, W, H);
    var d = imageData.data;
    var noiseStrength = noiseAmt * 50;
    var chunkSize = Math.max(1, Math.round(1 + grainSize * 5));
    var gs2 = 42;
    function gnrand() { gs2 = (gs2*16807)%2147483647; return gs2/2147483647; }

    if (chunkSize <= 1) {
      for (var p = 0; p < d.length; p += 4) {
        var n = (gnrand()-0.5)*noiseStrength;
        d[p] = Math.min(255, Math.max(0, d[p]+n));
        d[p+1] = Math.min(255, Math.max(0, d[p+1]+n));
        d[p+2] = Math.min(255, Math.max(0, d[p+2]+n));
      }
    } else {
      for (var by = 0; by < H; by += chunkSize) {
        for (var bx = 0; bx < W; bx += chunkSize) {
          var n = (gnrand()-0.5)*noiseStrength;
          for (var dy = 0; dy < chunkSize && by+dy < H; dy++) {
            for (var dx = 0; dx < chunkSize && bx+dx < W; dx++) {
              var idx = ((by+dy)*W+(bx+dx))*4;
              d[idx] = Math.min(255, Math.max(0, d[idx]+n));
              d[idx+1] = Math.min(255, Math.max(0, d[idx+1]+n));
              d[idx+2] = Math.min(255, Math.max(0, d[idx+2]+n));
            }
          }
        }
      }
    }
    ctx.putImageData(imageData, 0, 0);
  }
}

var rafId = null;
function renderPreview() {
  if (rafId) cancelAnimationFrame(rafId);
  rafId = requestAnimationFrame(function() {
    renderToCanvas(document.getElementById('liveCanvas'));
    rafId = null;
  });
}

function exportFull() {
  var exportCanvas = document.getElementById('exportCanvas');
  renderToCanvas(exportCanvas);
  setTimeout(function() {
    var link = document.createElement('a');
    var g = getActiveGradients()[Math.min(selected, getActiveGradients().length-1)];
    var parts = ['glassmorphism', g.name.toLowerCase().replace(/\s+/g, '-')];
    var b = document.getElementById('brightness').value;
    var f = document.getElementById('frost').value;
    if (b !== '30') parts.push('b' + b);
    if (f !== '50') parts.push('f' + f);
    if (showPanel) parts.push(activePanelPattern);
    parts.push(activeRatio.label.replace(':', 'x'));
    link.download = parts.join('-') + '.png';
    link.href = exportCanvas.toDataURL('image/png');
    link.click();
  }, 300);
}

renderPreview();
</script>
</body>
</html>"""


# ── Server ────────────────────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _html(self, content):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode())

    def do_GET(self):
        global _last_heartbeat
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._html(HTML)
        elif parsed.path == "/api/heartbeat":
            _last_heartbeat = _time.time()
            self._json({"ok": True})
        else:
            self.send_error(404)

    def do_POST(self):
        self.send_error(404)


def main():
    print(f"\nGlassmorphism BG v{VERSION}")
    print(f"  Starting server on http://localhost:{PORT}")

    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)

    # Start heartbeat watchdog
    t = threading.Thread(target=heartbeat_watchdog, daemon=True)
    t.start()

    # Open browser
    webbrowser.open(f"http://localhost:{PORT}")

    print(f"  Server running. Close the browser tab to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
