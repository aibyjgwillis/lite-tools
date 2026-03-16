#!/usr/bin/env python3
"""Background watcher that tints Terminal windows when Claude is waiting for input.

Polls terminal titles every 2 seconds. When a window shows Claude's idle prompt,
shifts its background color toward teal. Restores the original color when active.

The tint is relative to each window's original background, so text contrast is
preserved (the shift is small enough that all existing ANSI colors remain readable).

Usage: python3 watcher.py --colors "#0a0e1a,#111633,#1a1040"
       (launched automatically by multiple-terminals.py --notify)
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time

PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".watcher.pid")

DEFAULT_HIGHLIGHT = "#1a4a5a"
CONFIG_PATH = os.path.expanduser("~/.config/lite-tools/multiple-terminals.json")

# How much to shift each channel toward the tint color (0.0 = no change, 1.0 = full tint)
TINT_STRENGTH = 0.25


def read_config():
    """Read saved config, returning a dict (empty on failure)."""
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_highlight_from_config(fallback):
    """Read highlight color from saved config, falling back to the given default."""
    cfg = read_config()
    color = cfg.get("highlightColor", "").strip()
    if color and color.startswith("#") and len(color) in (4, 7):
        return color
    return fallback


def get_sound_settings_from_config(default_name, default_volume):
    """Read sound name and volume from saved config."""
    cfg = read_config()
    name = cfg.get("soundName", default_name)
    volume = cfg.get("soundVolume", default_volume)
    try:
        volume = float(volume)
    except (TypeError, ValueError):
        volume = default_volume
    return name, max(0.0, min(1.0, volume))


def hex_to_rgb(hex_color):
    """Convert hex to (r, g, b) in 0-255 range."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def tint_color(original_hex, tint_hex, strength=TINT_STRENGTH):
    """Blend original color toward tint color by strength amount.

    A strength of 0.25 means 75% original + 25% tint. This keeps the
    background close enough to the original that all ANSI text colors
    remain readable, while making the shift visible.
    """
    or_, og, ob = hex_to_rgb(original_hex)
    tr, tg, tb = hex_to_rgb(tint_hex)
    r = int(or_ * (1 - strength) + tr * strength)
    g = int(og * (1 - strength) + tg * strength)
    b = int(ob * (1 - strength) + tb * strength)
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_terminal_rgb(hex_color):
    """Convert hex to Terminal.app 16-bit RGB."""
    r, g, b = hex_to_rgb(hex_color)
    return (r * 257, g * 257, b * 257)


def set_window_background(window_index, hex_color):
    """Set background color of a Terminal window."""
    r, g, b = hex_to_terminal_rgb(hex_color)
    try:
        subprocess.run(
            ["osascript", "-e",
             f'tell application "Terminal" to set background color of selected tab '
             f'of window {window_index} to {{{r}, {g}, {b}}}'],
            capture_output=True, text=True, timeout=5
        )
    except Exception:
        pass


def get_window_count():
    """Get current number of Terminal.app windows."""
    try:
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "Terminal" to return count of windows'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass
    return 0


def get_window_title(window_index):
    """Get the title of a Terminal window."""
    try:
        result = subprocess.run(
            ["osascript", "-e",
             f'tell application "Terminal" to return name of window {window_index}'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def is_idle(title):
    """Check if a Terminal window title indicates Claude is waiting for input."""
    if not title:
        return False
    return "\u2733" in title


def play_sound(sound_name="Submarine", volume=0.2):
    """Play a notification sound."""
    path = f"/System/Library/Sounds/{sound_name}.aiff"
    if not os.path.exists(path):
        path = "/System/Library/Sounds/Submarine.aiff"
    try:
        subprocess.Popen(
            ["afplay", "-v", str(volume), path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass


def kill_existing_watcher():
    """Kill any previously running watcher process."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, signal.SIGTERM)
        except (ProcessLookupError, ValueError, OSError):
            pass
        try:
            os.remove(PID_FILE)
        except OSError:
            pass


def write_pid():
    """Write current PID to file."""
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))


def cleanup(signum=None, frame=None):
    """Clean up PID file on exit."""
    try:
        os.remove(PID_FILE)
    except OSError:
        pass
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Watch Terminal windows for Claude idle state")
    parser.add_argument("--colors", type=str, required=True,
                        help="Comma-separated original hex colors for each window")
    parser.add_argument("--highlight", type=str, default=DEFAULT_HIGHLIGHT,
                        help=f"Tint target color (default: {DEFAULT_HIGHLIGHT})")
    parser.add_argument("--sound", action="store_true", default=False,
                        help="Play a sound when a window becomes idle")
    parser.add_argument("--sound-name", type=str, default="Submarine",
                        help="System sound name (default: Submarine)")
    parser.add_argument("--sound-volume", type=float, default=0.2,
                        help="Sound volume 0.0-1.0 (default: 0.2)")
    parser.add_argument("--window-count", type=int, default=0,
                        help="Number of windows to track (0 = auto-detect)")
    args = parser.parse_args()

    kill_existing_watcher()
    write_pid()
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    original_colors = [c.strip().strip('"').strip("'") for c in args.colors.split(",")]
    tint_target = get_highlight_from_config(args.highlight)
    sound_name, sound_volume = get_sound_settings_from_config(args.sound_name, args.sound_volume)
    tracked_count = args.window_count if args.window_count > 0 else len(original_colors)

    # Pre-compute tinted colors for each window
    tinted_colors = []
    for color in original_colors:
        tinted_colors.append(tint_color(color, tint_target))

    highlighted = set()
    sound_played = set()
    idle_streak = {}
    active_streak = {}
    IDLE_THRESHOLD = 1
    ACTIVE_THRESHOLD = 1
    poll_interval = 2.0
    empty_polls = 0
    config_check_counter = 0

    while True:
        try:
            config_check_counter += 1
            if config_check_counter >= 5:
                config_check_counter = 0
                new_target = get_highlight_from_config(args.highlight)
                if new_target != tint_target:
                    tint_target = new_target
                    tinted_colors = [tint_color(c, tint_target) for c in original_colors]
                    for w in list(highlighted):
                        ci = (w - 1) % len(tinted_colors)
                        set_window_background(w, tinted_colors[ci])
                sound_name, sound_volume = get_sound_settings_from_config(args.sound_name, args.sound_volume)

            current_count = get_window_count()
            if current_count == 0:
                empty_polls += 1
                if empty_polls > 3:
                    break
                time.sleep(poll_interval)
                continue
            empty_polls = 0

            check_count = min(tracked_count, current_count)

            for i in range(check_count):
                window_idx = i + 1
                title = get_window_title(window_idx)
                idle = is_idle(title)

                if idle:
                    idle_streak[window_idx] = idle_streak.get(window_idx, 0) + 1
                    active_streak[window_idx] = 0
                else:
                    active_streak[window_idx] = active_streak.get(window_idx, 0) + 1
                    idle_streak[window_idx] = 0

                color_idx = i % len(original_colors)

                if idle and window_idx not in highlighted:
                    if idle_streak.get(window_idx, 0) >= IDLE_THRESHOLD:
                        set_window_background(window_idx, tinted_colors[color_idx])
                        highlighted.add(window_idx)
                        if args.sound and window_idx not in sound_played:
                            play_sound(sound_name, sound_volume)
                            sound_played.add(window_idx)
                elif not idle and window_idx in highlighted:
                    if active_streak.get(window_idx, 0) >= ACTIVE_THRESHOLD:
                        set_window_background(window_idx, original_colors[color_idx])
                        highlighted.discard(window_idx)
                        sound_played.discard(window_idx)

            time.sleep(poll_interval)

        except Exception:
            time.sleep(poll_interval)

    cleanup()


if __name__ == "__main__":
    main()
