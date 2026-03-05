#!/usr/bin/env python3
"""Background watcher that highlights Terminal windows when Claude is waiting for input.

Polls terminal contents every 2 seconds. When a window shows Claude's idle prompt,
changes its background to a highlight color. Restores original color when active.

Usage: python3 watcher.py --colors "#0a0e1a,#111633,#1a1040" --highlight "#1a3a5a"
       (launched automatically by multiple-terminals.py --notify)

Pass original colors so they can be restored. Runs until all tracked windows close.
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time

# PID file so we can stop previous watchers
PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".watcher.pid")

# Default highlight color (muted teal-blue glow)
DEFAULT_HIGHLIGHT = "#1a4a5a"

# Patterns that indicate Claude is waiting for input.
# Claude Code shows ">" at the start of a line when idle.
# Also match the compact prompt and "waiting for input" states.
IDLE_PATTERNS = [
    r'(?m)^> $',           # Claude Code default prompt
    r'(?m)^> \s*$',        # Prompt with trailing whitespace
    r'(?m)^\$ $',          # Shell prompt (task finished, back to shell)
    r'(?m)^\$ \s*$',       # Shell prompt variant
]


def hex_to_terminal_rgb(hex_color):
    """Convert hex to Terminal.app 16-bit RGB."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (r * 257, g * 257, b * 257)


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


def get_window_contents(window_index):
    """Get the text contents of a Terminal window's selected tab."""
    try:
        result = subprocess.run(
            ["osascript", "-e",
             f'tell application "Terminal" to return contents of selected tab of window {window_index}'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass
    return ""


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


def is_idle(contents):
    """Check if terminal contents indicate Claude is waiting for input."""
    if not contents:
        return False
    # Check last 500 chars for efficiency
    tail = contents[-500:]
    # Get the last few non-empty lines
    lines = [l for l in tail.split("\n") if l.strip()]
    if not lines:
        return False
    last_line = lines[-1].strip()

    # Direct checks for common idle states
    if last_line == ">":
        return True
    if last_line == "$":
        return True
    if last_line.endswith("$") and len(last_line) < 80:
        return True

    # Regex patterns
    for pattern in IDLE_PATTERNS:
        if re.search(pattern, tail):
            return True

    return False


def play_sound():
    """Play a subtle notification sound."""
    try:
        subprocess.Popen(
            ["afplay", "/System/Library/Sounds/Tink.aiff"],
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
                        help=f"Highlight color when idle (default: {DEFAULT_HIGHLIGHT})")
    parser.add_argument("--sound", action="store_true", default=False,
                        help="Play a sound when a window becomes idle")
    parser.add_argument("--window-count", type=int, default=0,
                        help="Number of windows to track (0 = auto-detect)")
    args = parser.parse_args()

    kill_existing_watcher()
    write_pid()
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    original_colors = [c.strip().strip('"').strip("'") for c in args.colors.split(",")]
    highlight = args.highlight
    tracked_count = args.window_count if args.window_count > 0 else len(original_colors)

    # Track which windows are currently highlighted
    highlighted = set()
    poll_interval = 2.0
    empty_polls = 0

    while True:
        try:
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
                contents = get_window_contents(window_idx)
                idle = is_idle(contents)

                if idle and window_idx not in highlighted:
                    # Window just became idle: highlight it
                    set_window_background(window_idx, highlight)
                    highlighted.add(window_idx)
                    if args.sound:
                        play_sound()
                elif not idle and window_idx in highlighted:
                    # Window is active again: restore original color
                    color_idx = i % len(original_colors)
                    set_window_background(window_idx, original_colors[color_idx])
                    highlighted.discard(window_idx)

            time.sleep(poll_interval)

        except Exception:
            time.sleep(poll_interval)

    cleanup()


if __name__ == "__main__":
    main()
