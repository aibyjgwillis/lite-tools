#!/usr/bin/env python3
"""Multiple Terminals - Web configurator for launching tiled Terminal.app windows.

Run: python3 server.py
Opens a browser-based UI on localhost:9848.
"""

import http.server
import json
import os
import subprocess
import sys
import threading
import webbrowser
import time as _time

VERSION = "1.0"
PORT = 9848
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_last_heartbeat = _time.time()
_heartbeat_timeout = 30


class QuietServer(http.server.HTTPServer):
    def handle_error(self, request, client_address):
        pass

    def shutdown_request(self, request):
        try:
            request.shutdown(2)
        except Exception:
            pass
        self.close_request(request)


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            body = HTML_PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/heartbeat":
            global _last_heartbeat
            _last_heartbeat = _time.time()
            self.send_json({"ok": True})
        elif self.path == "/api/window-count":
            try:
                result = subprocess.run(
                    ["osascript", "-e", """
tell application "Terminal"
    set validCount to 0
    repeat with i from 1 to (count of windows)
        try
            set n to name of window i
            set b to bounds of window i
            set v to visible of window i
            set bounds of window i to b
            set validCount to validCount + 1
        end try
    end repeat
    return validCount
end tell"""],
                    capture_output=True, text=True, timeout=5
                )
                count = int(result.stdout.strip()) if result.returncode == 0 else 0
            except Exception:
                count = 0
            self.send_json({"count": count})
        else:
            self.send_response(404)
            self.end_headers()

    def _build_cmd(self, body, restyle=False):
        cmd = [sys.executable, os.path.join(SCRIPT_DIR, "multiple-terminals.py")]
        if restyle:
            cmd.append("--restyle")
        else:
            cmd += ["--count", str(body.get("count", 3))]
        cmd += ["--layout", body.get("layout", "side-by-side")]

        theme = body.get("theme")
        colors = body.get("colors")
        mode = body.get("mode")
        if theme:
            cmd += ["--theme", theme]
        elif colors:
            cmd += ["--colors", colors]
        elif mode:
            cmd += ["--mode", mode]

        if body.get("includeAll"):
            cmd.append("--include-all")

        if not restyle:
            if body.get("noClaude"):
                cmd.append("--no-claude")
            if body.get("commands"):
                cmd += ["--commands", body["commands"]]
            if body.get("allNew"):
                cmd.append("--all-new")
            if body.get("notify"):
                cmd.append("--notify")
        return cmd

    def do_POST(self):
        if self.path in ("/api/launch", "/api/restyle"):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            cmd = self._build_cmd(body, restyle=(self.path == "/api/restyle"))
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                self.send_json({
                    "ok": result.returncode == 0,
                    "output": result.stdout.strip(),
                    "error": result.stderr.strip() if result.returncode != 0 else ""
                })
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
        else:
            self.send_response(404)
            self.end_headers()


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Multiple Terminals</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:ital@1&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {
  --obsidian: #0F1114; --champagne: #5A7D96; --ivory: #F5F5F3;
  --slate: #1C1C1E;
  --font-heading: 'Inter', sans-serif;
  --font-drama: 'Playfair Display', serif;
  --font-mono: 'JetBrains Mono', monospace;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: var(--font-heading); background: var(--ivory);
  color: var(--slate); min-height: 100vh; padding: 40px 20px;
}
.container { max-width: 640px; margin: 0 auto; }
.page-title { font-family: var(--font-drama); font-size: 48px; font-weight: 400; font-style: italic; text-align: center; margin-bottom: 6px; }
.page-subtitle { font-family: var(--font-mono); font-size: 12px; color: var(--champagne); text-align: center; margin-bottom: 40px; }

.section { margin-bottom: 32px; }
.section-label {
  font-family: var(--font-mono); font-size: 10px; text-transform: uppercase;
  letter-spacing: 0.12em; color: rgba(28,28,30,0.4); margin-bottom: 10px;
}

/* Count */
.count-row { display: flex; gap: 8px; align-items: center; }
.count-btn {
  width: 44px; height: 44px; border-radius: 10px; border: 1px solid rgba(28,28,30,0.12);
  background: white; font-family: var(--font-heading); font-size: 16px; font-weight: 600;
  color: var(--slate); cursor: pointer; transition: all 0.2s;
}
.count-btn:hover { border-color: var(--champagne); }
.count-btn.active { background: var(--slate); color: var(--ivory); border-color: var(--slate); }
.count-stepper {
  display: flex; align-items: center; gap: 4px; margin-left: 8px;
  border-left: 1px solid rgba(28,28,30,0.1); padding-left: 12px;
}
.stepper-btn {
  width: 32px; height: 32px; border-radius: 8px; border: 1px solid rgba(28,28,30,0.12);
  background: white; font-size: 18px; font-weight: 400; color: var(--slate);
  cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center;
}
.stepper-btn:hover { border-color: var(--champagne); }
.count-display {
  font-family: var(--font-mono); font-size: 14px; font-weight: 600;
  min-width: 28px; text-align: center;
}
.existing-btn {
  margin-left: auto; display: flex; align-items: center; gap: 6px;
  padding: 6px 14px; border-radius: 2rem; background: rgba(28,28,30,0.04);
  border: 1px solid rgba(28,28,30,0.08); cursor: pointer; transition: all 0.2s;
}
.existing-btn:hover { border-color: var(--champagne); background: rgba(90,125,150,0.08); }
.existing-btn.active { background: var(--slate); border-color: var(--slate); }
.existing-btn.active .existing-label { color: rgba(255,255,255,0.6); }
.existing-btn.active .existing-count { color: var(--ivory); }
.existing-label {
  font-family: var(--font-mono); font-size: 10px; text-transform: uppercase;
  letter-spacing: 0.08em; color: rgba(28,28,30,0.4);
}
.existing-count {
  font-family: var(--font-mono); font-size: 14px; font-weight: 600;
  color: var(--champagne); min-width: 14px; text-align: center;
}

/* Layout */
.layout-row { display: flex; gap: 8px; flex-wrap: wrap; }
.layout-btn {
  padding: 10px 20px; border-radius: 2rem; border: 1px solid rgba(28,28,30,0.12);
  background: white; font-family: var(--font-heading); font-size: 12px; font-weight: 500;
  color: var(--slate); cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 8px;
}
.layout-btn:hover { border-color: var(--champagne); }
.layout-btn.active { background: var(--slate); color: var(--ivory); border-color: var(--slate); }

/* Appearance tabs */
.appearance-tabs { display: flex; background: rgba(28,28,30,0.05); border-radius: 2rem; padding: 3px; margin-bottom: 16px; }
.appearance-tab {
  flex: 1; padding: 7px 12px; border-radius: 2rem; border: none; font-family: var(--font-heading);
  font-size: 11px; font-weight: 600; cursor: pointer; text-align: center;
  color: rgba(28,28,30,0.45); background: none; transition: all 0.2s;
}
.appearance-tab:hover { color: var(--slate); }
.appearance-tab.active { background: var(--slate); color: var(--ivory); }
.appearance-panel { display: none; }
.appearance-panel.active { display: block; }

/* Color modes */
.modes-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.mode-card {
  border-radius: 12px; border: 3px solid transparent; cursor: pointer;
  transition: all 0.2s; padding: 12px; background: white; text-align: center;
}
.mode-card:hover { border-color: rgba(28,28,30,0.15); }
.mode-card.active { border-color: var(--slate); box-shadow: 0 2px 12px rgba(28,28,30,0.12); }
.mode-swatches { display: flex; gap: 3px; margin-bottom: 8px; height: 32px; border-radius: 6px; overflow: hidden; }
.mode-swatch { flex: 1; }
.mode-name { font-family: var(--font-mono); font-size: 10px; color: rgba(28,28,30,0.5); font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }

/* Terminal themes */
.themes-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.theme-card {
  border-radius: 10px; border: 2px solid rgba(28,28,30,0.1); cursor: pointer;
  transition: all 0.2s; padding: 10px 14px; background: white; text-align: center;
  font-family: var(--font-heading); font-size: 12px; font-weight: 500;
}
.theme-card:hover { border-color: var(--champagne); }
.theme-card.active { border-color: var(--slate); background: var(--slate); color: var(--ivory); }
.theme-preview {
  height: 24px; border-radius: 4px; margin-bottom: 6px; display: flex;
  align-items: center; justify-content: center; font-family: var(--font-mono);
  font-size: 9px; letter-spacing: 0.05em;
}

/* Custom colors */
.custom-colors-row { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-top: 8px; }
.color-slot {
  position: relative; width: 36px; height: 36px; border-radius: 8px;
  border: 2px solid rgba(28,28,30,0.15); cursor: pointer; overflow: hidden;
  transition: all 0.2s;
}
.color-slot:hover { border-color: var(--champagne); transform: scale(1.08); }
.color-slot input[type="color"] {
  position: absolute; inset: -4px; width: calc(100% + 8px); height: calc(100% + 8px);
  border: none; cursor: pointer; background: none; padding: 0;
}
.color-slot input[type="color"]::-webkit-color-swatch-wrapper { padding: 0; }
.color-slot input[type="color"]::-webkit-color-swatch { border: none; border-radius: 6px; }
.color-slot-label {
  position: absolute; bottom: -14px; left: 50%; transform: translateX(-50%);
  font-family: var(--font-mono); font-size: 7px; color: rgba(28,28,30,0.3);
  white-space: nowrap;
}

/* Options */
.option-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 0; border-bottom: 1px solid rgba(28,28,30,0.06);
}
.option-row:last-child { border-bottom: none; }
.option-label { font-size: 13px; font-weight: 500; }
.option-desc { font-family: var(--font-mono); font-size: 10px; color: rgba(28,28,30,0.4); margin-top: 2px; }

/* Toggle */
.toggle { position: relative; width: 44px; height: 24px; flex-shrink: 0; }
.toggle input { opacity: 0; width: 0; height: 0; }
.toggle-track {
  position: absolute; inset: 0; background: rgba(28,28,30,0.12); border-radius: 12px;
  cursor: pointer; transition: background 0.2s;
}
.toggle-track::after {
  content: ''; position: absolute; width: 20px; height: 20px; background: white;
  border-radius: 50%; top: 2px; left: 2px; transition: transform 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
}
.toggle input:checked + .toggle-track { background: var(--champagne); }
.toggle input:checked + .toggle-track::after { transform: translateX(20px); }

/* Preview */
.preview-area {
  background: white; border: 1px solid rgba(28,28,30,0.08); border-radius: 1rem;
  padding: 20px; margin-bottom: 24px;
}
.preview-label { font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(28,28,30,0.35); margin-bottom: 12px; }
.preview-screen {
  background: #e8e8e6; border-radius: 8px; padding: 8px; aspect-ratio: 16/10;
  display: flex; gap: 4px;
}
.preview-window {
  border-radius: 4px; transition: all 0.3s; display: flex; align-items: flex-end;
  padding: 4px 6px; overflow: hidden;
}
.preview-window-label {
  font-family: var(--font-mono); font-size: 7px; color: rgba(255,255,255,0.4);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* Buttons */
.btn-row { display: flex; gap: 8px; }
.launch-btn, .restyle-btn {
  flex: 1; padding: 16px 24px; border: none; border-radius: 2rem;
  font-family: var(--font-heading); font-size: 15px; font-weight: 600;
  cursor: pointer; transition: all 0.2s; letter-spacing: 0.02em;
}
.launch-btn { background: var(--slate); color: var(--ivory); }
.launch-btn:hover { background: var(--obsidian); transform: translateY(-1px); box-shadow: 0 4px 16px rgba(28,28,30,0.2); }
.restyle-btn {
  background: transparent; color: var(--slate); border: 1px solid rgba(28,28,30,0.18);
  font-size: 13px;
}
.restyle-btn:hover { border-color: var(--champagne); color: var(--champagne); }
.btn-success { background: var(--champagne) !important; color: white !important; border-color: var(--champagne) !important; }

.status {
  font-family: var(--font-mono); font-size: 11px; text-align: center;
  margin-top: 12px; min-height: 18px; color: rgba(28,28,30,0.5);
}
.status.error { color: #9a3a3a; }
.badge {
  display: inline-block; background: var(--champagne); color: white; font-size: 10px;
  font-weight: 700; min-width: 18px; height: 18px; line-height: 18px; text-align: center;
  border-radius: 9px; padding: 0 5px; margin-left: 4px; vertical-align: middle;
}
.badge:empty { display: none; }
</style>
</head>
<body>
<div class="container">
  <div class="page-title">Multiple Terminals</div>
  <div class="page-subtitle">lite-tools</div>

  <!-- Count -->
  <div class="section">
    <div class="section-label">Number of Terminals</div>
    <div class="count-row">
      <button class="count-btn" data-count="2">2</button>
      <button class="count-btn active" data-count="3">3</button>
      <button class="count-btn" data-count="4">4</button>
      <button class="count-btn" data-count="5">5</button>
      <button class="count-btn" data-count="6">6</button>
      <div class="count-stepper">
        <button class="stepper-btn" id="count-minus">-</button>
        <span class="count-display" id="count-display">3</span>
        <button class="stepper-btn" id="count-plus">+</button>
      </div>
      <button class="existing-btn" id="existing-btn">
        <span class="existing-label">Existing</span>
        <span class="existing-count" id="existing-count">0</span>
      </button>
    </div>
  </div>

  <!-- Layout -->
  <div class="section">
    <div class="section-label">Arrangement</div>
    <div class="layout-row">
      <button class="layout-btn active" data-layout="side-by-side">||| Side by Side</button>
      <button class="layout-btn" data-layout="grid">## Grid</button>
      <button class="layout-btn" data-layout="rows">=== Rows</button>
      <button class="layout-btn" data-layout="stacked">[] Stacked</button>
    </div>
  </div>

  <!-- Appearance -->
  <div class="section">
    <div class="section-label">Appearance</div>
    <div class="appearance-tabs">
      <button class="appearance-tab active" data-panel="modes">Color Modes</button>
      <button class="appearance-tab" data-panel="themes">Terminal Themes</button>
      <button class="appearance-tab" data-panel="custom">Custom</button>
    </div>

    <div id="panel-modes" class="appearance-panel active">
      <div class="modes-grid" id="modes-grid"></div>
    </div>

    <div id="panel-themes" class="appearance-panel">
      <div class="themes-grid" id="themes-grid"></div>
    </div>

    <div id="panel-custom" class="appearance-panel">
      <div class="section-label" style="margin-top:4px">Pick a color for each terminal</div>
      <div class="custom-colors-row" id="custom-colors"></div>
    </div>
  </div>

  <!-- Options -->
  <div class="section">
    <div class="section-label">Options</div>
    <div class="option-row">
      <div>
        <div class="option-label">Run Claude in each window</div>
        <div class="option-desc">Launches claude automatically</div>
      </div>
      <label class="toggle"><input type="checkbox" id="opt-claude" checked><span class="toggle-track"></span></label>
    </div>
    <div class="option-row">
      <div>
        <div class="option-label">Reuse current terminal</div>
        <div class="option-desc">Restyle your active window as slot 1</div>
      </div>
      <label class="toggle"><input type="checkbox" id="opt-reuse" checked><span class="toggle-track"></span></label>
    </div>
    <div class="option-row">
      <div>
        <div class="option-label">Include all windows</div>
        <div class="option-desc">Resize browsers, editors, and other windows alongside terminals</div>
      </div>
      <label class="toggle"><input type="checkbox" id="opt-include-existing"><span class="toggle-track"></span></label>
    </div>
    <div class="option-row">
      <div>
        <div class="option-label">Idle highlighting</div>
        <div class="option-desc">Highlight windows when claude needs input</div>
      </div>
      <label class="toggle"><input type="checkbox" id="opt-notify"><span class="toggle-track"></span></label>
    </div>
  </div>

  <!-- Preview -->
  <div class="preview-area">
    <div class="preview-label">Preview</div>
    <div class="preview-screen" id="preview"></div>
  </div>

  <!-- Actions -->
  <div class="btn-row">
    <button class="launch-btn" id="launch-btn">Launch Terminals</button>
    <button class="restyle-btn" id="restyle-btn">Restyle Existing <span class="badge" id="existing-badge"></span></button>
  </div>
  <div class="status" id="status"></div>
</div>

<script>
var COLOR_MODES = {
  ocean:   ["#0a2437","#0d344c","#124460","#1d5474","#2c5f80","#3a6a8c"],
  forest:  ["#0a2414","#10351e","#1a442a","#245436","#306444","#3c7454"],
  sunset:  ["#3a140c","#541c10","#6a2818","#7a3520","#8a442c","#985438"],
  berry:   ["#240a2a","#361440","#461e54","#582a68","#6a367c","#7c4290"],
  earth:   ["#1e1410","#302418","#3e3020","#4c3c28","#5a4832","#68543c"],
  mono:    ["#141414","#1e1e1e","#2a2a2a","#363636","#424242","#4e4e4e"],
  warm:    ["#3a100a","#4e1810","#641e14","#7a2818","#8e3420","#a04028"],
  cool:    ["#0a1438","#10204c","#182c60","#203a74","#2c4888","#38569c"]
};

var THEME_DATA = [
  {name:"Pro",           bg:"#1a1a1a", fg:"#4fe34f"},
  {name:"Homebrew",      bg:"#0a0a0a", fg:"#28fe14"},
  {name:"Ocean",         bg:"#224fba", fg:"#ffffff"},
  {name:"Red Sands",     bg:"#7a2d21", fg:"#d7c9a7"},
  {name:"Grass",         bg:"#13773d", fg:"#ffffff"},
  {name:"Man Page",      bg:"#fef49c", fg:"#1a1a1a"},
  {name:"Novel",         bg:"#dfd8c5", fg:"#3b2e1a"},
  {name:"Basic",         bg:"#ffffff", fg:"#1a1a1a"},
  {name:"Silver Aerogel",bg:"#d0d0d0", fg:"#1a1a1a"}
];

var state = { count: 3, layout: "side-by-side", tab: "modes", mode: "ocean", theme: null, customColors: null };

// Build mode cards
(function() {
  var grid = document.getElementById('modes-grid');
  Object.keys(COLOR_MODES).forEach(function(name) {
    var colors = COLOR_MODES[name];
    var card = document.createElement('div');
    card.className = 'mode-card' + (name === 'ocean' ? ' active' : '');
    card.dataset.mode = name;

    var swatches = document.createElement('div');
    swatches.className = 'mode-swatches';
    colors.slice(0, 4).forEach(function(c) {
      var s = document.createElement('div');
      s.className = 'mode-swatch';
      s.style.background = c;
      swatches.appendChild(s);
    });
    card.appendChild(swatches);

    var label = document.createElement('div');
    label.className = 'mode-name';
    label.textContent = name.charAt(0).toUpperCase() + name.slice(1);
    card.appendChild(label);

    card.addEventListener('click', function() {
      document.querySelectorAll('.mode-card').forEach(function(c) { c.classList.remove('active'); });
      document.querySelectorAll('.theme-card').forEach(function(c) { c.classList.remove('active'); });
      card.classList.add('active');
      state.mode = name; state.theme = null; state.customColors = null; state.tab = 'modes';
      updatePreview();
    });

    grid.appendChild(card);
  });
})();

// Build theme cards
(function() {
  var grid = document.getElementById('themes-grid');
  THEME_DATA.forEach(function(t) {
    var card = document.createElement('div');
    card.className = 'theme-card';
    card.dataset.theme = t.name;

    var preview = document.createElement('div');
    preview.className = 'theme-preview';
    preview.style.background = t.bg;
    preview.style.color = t.fg;
    if (t.name === 'Basic') preview.style.border = '1px solid #ddd';
    preview.textContent = '$ claude';
    card.appendChild(preview);

    card.appendChild(document.createTextNode(t.name));

    card.addEventListener('click', function() {
      document.querySelectorAll('.theme-card').forEach(function(c) { c.classList.remove('active'); });
      document.querySelectorAll('.mode-card').forEach(function(c) { c.classList.remove('active'); });
      card.classList.add('active');
      state.theme = t.name; state.mode = null; state.customColors = null; state.tab = 'themes';
      updatePreview();
    });

    grid.appendChild(card);
  });
})();

// Custom color pickers
function buildCustomColors() {
  var container = document.getElementById('custom-colors');
  while (container.firstChild) container.removeChild(container.firstChild);
  var defaults = getBaseColors();
  if (!state.customColors || state.customColors.length !== state.count) {
    state.customColors = defaults.slice(0, state.count);
    while (state.customColors.length < state.count) {
      state.customColors.push(defaults[state.customColors.length % defaults.length]);
    }
  }
  for (var i = 0; i < state.count; i++) {
    (function(idx) {
      var slot = document.createElement('div');
      slot.className = 'color-slot';
      slot.style.background = state.customColors[idx];

      var input = document.createElement('input');
      input.type = 'color';
      input.value = state.customColors[idx];
      input.addEventListener('input', function() {
        state.customColors[idx] = input.value;
        slot.style.background = input.value;
        updatePreview();
      });
      slot.appendChild(input);
      container.appendChild(slot);
    })(i);
  }
}

function getBaseColors() {
  if (state.mode && COLOR_MODES[state.mode]) return COLOR_MODES[state.mode].slice();
  return COLOR_MODES.ocean.slice();
}

// Count
function setCount(n) {
  state.count = Math.max(1, n);
  document.getElementById('count-display').textContent = state.count;
  document.querySelectorAll('.count-btn').forEach(function(b) {
    b.classList.toggle('active', parseInt(b.dataset.count) === state.count);
  });
  var existingN = parseInt(document.getElementById('existing-count').textContent) || 0;
  document.getElementById('existing-btn').classList.toggle('active', existingN > 0 && state.count === existingN);
  if (state.tab === 'custom') buildCustomColors();
  updatePreview();
}
document.querySelectorAll('.count-btn').forEach(function(btn) {
  btn.addEventListener('click', function() { setCount(parseInt(btn.dataset.count)); });
});
document.getElementById('count-minus').addEventListener('click', function() { setCount(state.count - 1); });
document.getElementById('count-plus').addEventListener('click', function() { setCount(state.count + 1); });
document.getElementById('existing-btn').addEventListener('click', function() {
  var n = parseInt(document.getElementById('existing-count').textContent) || 0;
  if (n > 0) setCount(n);
});

// Layout
document.querySelectorAll('.layout-btn').forEach(function(btn) {
  btn.addEventListener('click', function() {
    document.querySelectorAll('.layout-btn').forEach(function(b) { b.classList.remove('active'); });
    btn.classList.add('active');
    state.layout = btn.dataset.layout;
    updatePreview();
  });
});

// Appearance tabs
document.querySelectorAll('.appearance-tab').forEach(function(tab) {
  tab.addEventListener('click', function() {
    document.querySelectorAll('.appearance-tab').forEach(function(t) { t.classList.remove('active'); });
    document.querySelectorAll('.appearance-panel').forEach(function(p) { p.classList.remove('active'); });
    tab.classList.add('active');
    document.getElementById('panel-' + tab.dataset.panel).classList.add('active');
    state.tab = tab.dataset.panel;
    if (state.tab === 'custom') {
      state.theme = null; state.mode = null;
      buildCustomColors();
    }
    updatePreview();
  });
});

function getWindowColors() {
  if (state.tab === 'custom' && state.customColors) return state.customColors.slice();
  if (state.theme) {
    var t = THEME_DATA.find(function(x) { return x.name === state.theme; });
    var c = t ? t.bg : '#1a1a1a';
    return Array(state.count).fill(c);
  }
  var palette = COLOR_MODES[state.mode || 'ocean'];
  return Array.from({length: state.count}, function(_, i) { return palette[i % palette.length]; });
}

function updatePreview() {
  var preview = document.getElementById('preview');
  var colors = getWindowColors();
  var count = state.count;
  var layout = state.layout;
  var reuse = document.getElementById('opt-reuse').checked;
  var runClaude = document.getElementById('opt-claude').checked;

  while (preview.firstChild) preview.removeChild(preview.firstChild);
  preview.style.flexWrap = (layout === 'grid') ? 'wrap' : 'nowrap';
  preview.style.flexDirection = (layout === 'rows') ? 'column' : 'row';
  preview.style.position = (layout === 'stacked') ? 'relative' : '';

  for (var i = 0; i < count; i++) {
    var win = document.createElement('div');
    win.className = 'preview-window';
    win.style.background = colors[i] || '#1a1a1a';
    var label = document.createElement('span');
    label.className = 'preview-window-label';
    label.textContent = (i === 0 && reuse) ? 'current' : (runClaude ? '$ claude' : '$ _');
    win.appendChild(label);

    if (layout === 'side-by-side') { win.style.flex = '1'; win.style.height = '100%'; }
    else if (layout === 'rows') { win.style.width = '100%'; win.style.flex = '1'; }
    else if (layout === 'grid') {
      var cols = Math.ceil(Math.sqrt(count));
      win.style.width = 'calc(' + (100/cols) + '% - 4px)';
      win.style.flex = '0 0 auto';
      win.style.height = 'calc(' + (100/Math.ceil(count/cols)) + '% - 4px)';
    }
    else if (layout === 'stacked') {
      win.style.position = i === 0 ? 'relative' : 'absolute';
      if (i > 0) { win.style.inset = (i*3)+'px'; win.style.opacity = String(1 - i*0.12); }
      win.style.width = '100%'; win.style.height = '100%';
    }
    preview.appendChild(win);
  }
}

function getRequestBody() {
  var body = {
    count: state.count,
    layout: state.layout,
    noClaude: !document.getElementById('opt-claude').checked,
    allNew: !document.getElementById('opt-reuse').checked,
    notify: document.getElementById('opt-notify').checked
  };
  body.includeAll = document.getElementById('opt-include-existing').checked;
  if (state.tab === 'custom' && state.customColors) {
    body.colors = state.customColors.join(',');
  } else if (state.theme) {
    body.theme = state.theme;
  } else if (state.mode) {
    body.mode = state.mode;
  }
  return body;
}

async function doAction(endpoint, btn) {
  var status = document.getElementById('status');
  var origText = btn.textContent;
  btn.textContent = 'Working...';
  btn.disabled = true;
  status.textContent = ''; status.className = 'status';

  try {
    var res = await fetch(endpoint, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(getRequestBody())
    });
    var data = await res.json();
    if (data.ok) {
      btn.textContent = 'Done';
      btn.classList.add('btn-success');
      status.textContent = data.output;
      setTimeout(function() { btn.textContent = origText; btn.classList.remove('btn-success'); btn.disabled = false; }, 2000);
    } else {
      btn.textContent = origText; btn.disabled = false;
      status.textContent = data.error || 'Failed';
      status.className = 'status error';
    }
  } catch(e) {
    btn.textContent = origText; btn.disabled = false;
    status.textContent = 'Connection error';
    status.className = 'status error';
  }
}

document.getElementById('launch-btn').addEventListener('click', function() {
  doAction('/api/launch', document.getElementById('launch-btn'));
});
document.getElementById('restyle-btn').addEventListener('click', function() {
  doAction('/api/restyle', document.getElementById('restyle-btn'));
});

document.getElementById('opt-reuse').addEventListener('change', updatePreview);
document.getElementById('opt-claude').addEventListener('change', updatePreview);

setInterval(function() { fetch('/api/heartbeat').catch(function() {}); }, 4000);

function updateWindowCount() {
  fetch('/api/window-count').then(function(r) { return r.json(); }).then(function(d) {
    document.getElementById('existing-badge').textContent = d.count > 0 ? d.count : '';
    document.getElementById('existing-count').textContent = d.count;
  }).catch(function() {});
}
updateWindowCount();
setInterval(updateWindowCount, 5000);

updatePreview();
</script>
</body>
</html>
"""


def main():
    print(f"\nMultiple Terminals v{VERSION}")
    print(f"  Server ........ http://localhost:{PORT}")
    print(f"  Auto-shutdown . {_heartbeat_timeout}s after tab close\n")

    server = QuietServer(("127.0.0.1", PORT), Handler)
    webbrowser.open(f"http://localhost:{PORT}")

    def heartbeat_watchdog():
        while True:
            _time.sleep(3)
            if _time.time() - _last_heartbeat > _heartbeat_timeout:
                print("Tab closed, shutting down.")
                server.shutdown()
                break

    watchdog = threading.Thread(target=heartbeat_watchdog, daemon=True)
    watchdog.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
