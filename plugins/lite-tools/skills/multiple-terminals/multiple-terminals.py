#!/usr/bin/env python3
"""Open multiple color-coded Terminal.app windows tiled across the screen."""

import argparse
import math
import os
import subprocess
import time
import sys


# Gradient ramps derived from folder-colors LAYER_THEMES.
# Each mode goes from darkest to lightest, like the folder-colors layer themes.
# Darkened to terminal-safe range (readable with light text) but with clear gradient steps.
COLOR_MODES = {
    "ocean": [
        "#0a2437",  # Abyss
        "#0d344c",  # Deep Sea
        "#124460",  # Marine
        "#1d5474",  # Steel
        "#2c5f80",  # Cerulean
        "#3a6a8c",  # Surf
    ],
    "forest": [
        "#0a2414",  # Pine
        "#10351e",  # Evergreen
        "#1a442a",  # Moss
        "#245436",  # Jade
        "#306444",  # Canopy
        "#3c7454",  # Fern
    ],
    "sunset": [
        "#3a140c",  # Ember
        "#541c10",  # Brick
        "#6a2818",  # Terracotta
        "#7a3520",  # Clay
        "#8a442c",  # Copper
        "#985438",  # Sandstone
    ],
    "berry": [
        "#240a2a",  # Plum
        "#361440",  # Grape
        "#461e54",  # Orchid
        "#582a68",  # Violet
        "#6a367c",  # Amethyst
        "#7c4290",  # Mulberry
    ],
    "earth": [
        "#1e1410",  # Espresso
        "#302418",  # Walnut
        "#3e3020",  # Umber
        "#4c3c28",  # Bronze
        "#5a4832",  # Caramel
        "#68543c",  # Tan
    ],
    "mono": [
        "#141414",  # Onyx
        "#1e1e1e",  # Charcoal
        "#2a2a2a",  # Graphite
        "#363636",  # Slate
        "#424242",  # Pewter
        "#4e4e4e",  # Ash
    ],
    "warm": [
        "#3a100a",  # Garnet
        "#4e1810",  # Cherry
        "#641e14",  # Cayenne
        "#7a2818",  # Sienna
        "#8e3420",  # Rust
        "#a04028",  # Cinnabar
    ],
    "cool": [
        "#0a1438",  # Midnight
        "#10204c",  # Navy
        "#182c60",  # Cobalt
        "#203a74",  # Royal
        "#2c4888",  # Sapphire
        "#38569c",  # Lapis
    ],
}

DEFAULT_MODE = "ocean"

# Vertical gap between rows to prevent title bar overlap.
# macOS window title bars extend ~28px above the bounds position, so adjacent
# rows need this gap to avoid visual overlap.
TITLEBAR_GAP = 28

def adjust_terminal_rects(rects):
    """Subtract titlebar offset from rects so Terminal.app windows land correctly.

    Terminal.app adds ~32px to all y coordinates (its title bar). By pre-subtracting,
    the windows end up at the intended positions. Currently unused but kept for
    potential future per-app adjustments.
    """
    off = 32
    return [(l, t - off, r, b - off) for l, t, r, b in rects]


TERMINAL_THEMES = [
    "Basic", "Pro", "Homebrew", "Ocean", "Red Sands",
    "Grass", "Man Page", "Novel", "Silver Aerogel",
    "Solid Colors", "Clear Dark", "Clear Light",
]


def hex_to_terminal_rgb(hex_color):
    """Convert a hex color string to Terminal.app's 16-bit RGB format."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r * 257, g * 257, b * 257)


def text_color_for_bg(hex_color):
    """Return a high-contrast text color (16-bit RGB) for the given background."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    # Perceived luminance
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    if lum < 128:
        # Dark background: light text (slightly warm white)
        return (62965, 63993, 62965)  # ~F5F9F5
    else:
        # Light background: dark text
        return (5140, 5140, 5654)  # ~141416


def get_screen_bounds():
    """Get usable screen bounds, detecting dock/menu bar auto-hide."""
    screen_bounds = None
    try:
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "Finder" to get bounds of window of desktop'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(", ")
            if len(parts) == 4:
                screen_bounds = tuple(int(p) for p in parts)
    except Exception:
        pass

    if not screen_bounds:
        screen_bounds = (0, 0, 1440, 900)

    left, top, right, bottom = screen_bounds

    menu_offset = 0
    dock_offset = 0
    try:
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to tell dock preferences to '
             'return {autohide, autohide menu bar}'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(", ")
            dock_autohide = parts[0].strip() == "true" if len(parts) > 0 else False
            menu_autohide = parts[1].strip() == "true" if len(parts) > 1 else False
            if not menu_autohide:
                menu_offset = 25
            if not dock_autohide:
                dock_offset = 70
    except Exception:
        menu_offset = 25
        dock_offset = 70

    return (left, top + menu_offset, right, bottom - dock_offset)


def get_terminal_window_count():
    """Get the number of valid Terminal.app windows (excludes ghost windows)."""
    return len(get_valid_window_indices())


def get_valid_window_indices():
    """Get list of valid Terminal.app window indices on the active desktop.

    Filters out ghost windows (write test) and windows on other Spaces (visible check).
    Only returns windows visible on the current desktop.
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", """
tell application "Terminal"
    set indices to ""
    repeat with i from 1 to (count of windows)
        try
            set n to name of window i
            set b to bounds of window i
            set v to visible of window i
            if v then
                -- Test that we can actually modify this window
                set bounds of window i to b
                set indices to indices & i & ","
            end if
        end try
    end repeat
    return indices
end tell"""],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            raw = result.stdout.strip().rstrip(",")
            if raw:
                return [int(x) for x in raw.split(",")]
    except Exception:
        pass
    return []


def get_all_visible_windows():
    """Get all visible windows on the active desktop from all applications.

    Uses CoreGraphics kCGWindowListOptionOnScreenOnly to only return windows
    on the current Space. Returns list of dicts with app name and window ID.
    Excludes Terminal (handled separately), Finder, Dock, and small windows.
    """
    try:
        import Quartz
    except ImportError:
        return []

    skip_apps = {"Finder", "Dock", "Notification Center", "Control Center",
                 "WindowManager", "Terminal", "Spotlight"}
    options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
    cg_windows = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)

    # Group by app to determine per-app window index
    app_counts = {}
    windows = []
    for w in cg_windows:
        owner = w.get("kCGWindowOwnerName", "")
        layer = w.get("kCGWindowLayer", 0)
        bounds = w.get("kCGWindowBounds", {})
        bw = bounds.get("Width", 0)
        bh = bounds.get("Height", 0)

        # Layer 0 = normal windows, skip tiny windows and excluded apps
        if layer != 0 or bw < 100 or bh < 100 or owner in skip_apps:
            continue

        app_counts[owner] = app_counts.get(owner, 0) + 1
        windows.append({
            "app": owner,
            "index": app_counts[owner],
            "name": w.get("kCGWindowName", ""),
        })

    return windows


def get_window_min_size(app_name, window_index):
    """Detect the minimum size of an app window by shrinking it and reading back.

    Temporarily resizes the window very small, reads the actual size the app
    allowed, then returns (min_width, min_height).
    """
    escaped_app = app_name.replace('"', '\\"')
    script = f"""
tell application "System Events"
    tell process "{escaped_app}"
        set w to window {window_index}
        set origSize to size of w
        set origPos to position of w
        set size of w to {{100, 100}}
        delay 0.15
        set actualSize to size of w
        set size of w to origSize
        set position of w to origPos
        return (item 1 of actualSize) & "," & (item 2 of actualSize)
    end tell
end tell"""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(",")
            if len(parts) == 2:
                return (int(parts[0].strip()), int(parts[1].strip()))
    except Exception:
        pass
    return (500, 300)


def resize_app_window(app_name, window_index, rect):
    """Resize a window from any application using System Events.

    Sets size first, then position, then position again to handle apps that
    adjust position when resized. Uses a brief delay between operations.
    """
    left, top, right, bottom = rect
    w = right - left
    h = bottom - top
    escaped_app = app_name.replace('"', '\\"')
    script = f"""
tell application "System Events"
    tell process "{escaped_app}"
        set w to window {window_index}
        set size of w to {{{w}, {h}}}
        delay 0.1
        set position of w to {{{left}, {top}}}
        delay 0.1
        set position of w to {{{left}, {top}}}
    end tell
end tell"""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def restyle_existing_window(window_index, rect, color_hex=None, theme=None):
    """Restyle an existing Terminal.app window (color/theme + bounds). No new window opened."""
    left, top, right, bottom = rect

    script_lines = [
        'tell application "Terminal"',
        '    activate',
        f'    set targetWindow to window {window_index}',
    ]

    if theme:
        escaped_theme = theme.replace('"', '\\"')
        script_lines.append(
            f'    set current settings of selected tab of targetWindow '
            f'to settings set "{escaped_theme}"'
        )

    if color_hex:
        r, g, b = hex_to_terminal_rgb(color_hex)
        tr, tg, tb = text_color_for_bg(color_hex)
        script_lines.append(
            f'    set background color of selected tab of targetWindow '
            f'to {{{r}, {g}, {b}}}'
        )
        script_lines.append(
            f'    set normal text color of selected tab of targetWindow '
            f'to {{{tr}, {tg}, {tb}}}'
        )

    script_lines.append(
        f'    set bounds of targetWindow to {{{left}, {top}, {right}, {bottom}}}'
    )

    script_lines.append("end tell")
    script = "\n".join(script_lines)

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Warning: Failed to restyle window: {e}", file=sys.stderr)
        return False


def open_new_terminal_window(rect, command, color_hex=None, theme=None):
    """Open a new Terminal.app window with color or theme, position, and command."""
    left, top, right, bottom = rect

    script_lines = [
        'tell application "Terminal"',
        '    activate',
        '    do script ""',
        '    set targetWindow to window 1',
    ]

    if theme:
        escaped_theme = theme.replace('"', '\\"')
        script_lines.append(
            f'    set current settings of selected tab of targetWindow '
            f'to settings set "{escaped_theme}"'
        )

    if color_hex:
        r, g, b = hex_to_terminal_rgb(color_hex)
        tr, tg, tb = text_color_for_bg(color_hex)
        script_lines.append(
            f'    set background color of selected tab of targetWindow '
            f'to {{{r}, {g}, {b}}}'
        )
        script_lines.append(
            f'    set normal text color of selected tab of targetWindow '
            f'to {{{tr}, {tg}, {tb}}}'
        )

    script_lines.append(
        f'    set bounds of targetWindow to {{{left}, {top}, {right}, {bottom}}}'
    )

    if command:
        escaped_cmd = command.replace("\\", "\\\\").replace('"', '\\"')
        script_lines.append(f'    do script "{escaped_cmd}" in targetWindow')

    script_lines.append("end tell")
    script = "\n".join(script_lines)

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Warning: Failed to open window: {e}", file=sys.stderr)
        return False


def calculate_layout(count, layout, bounds, row_gap=0):
    """Calculate window rects for the given layout.

    row_gap: vertical pixels reserved between rows to prevent title bar overlap.
    Applied to grid and rows layouts only.
    """
    x0, y0, x1, y1 = bounds
    width = x1 - x0
    height = y1 - y0
    rects = []

    if layout == "side-by-side":
        col_width = width // count
        for i in range(count):
            l = x0 + i * col_width
            r = x0 + (i + 1) * col_width if i < count - 1 else x1
            rects.append((l, y0, r, y1))

    elif layout == "grid":
        cols = math.ceil(math.sqrt(count))
        rows = math.ceil(count / cols)
        total_gap = row_gap * (rows - 1)
        usable_height = height - total_gap
        col_width = width // cols
        row_height = usable_height // rows
        for i in range(count):
            row = i // cols
            col = i % cols
            l = x0 + col * col_width
            t = y0 + row * (row_height + row_gap)
            r = x0 + (col + 1) * col_width if col < cols - 1 else x1
            b = t + row_height if row < rows - 1 else y1
            rects.append((l, t, r, b))

    elif layout == "rows":
        total_gap = row_gap * (count - 1)
        usable_height = height - total_gap
        row_height = usable_height // count
        for i in range(count):
            t = y0 + i * (row_height + row_gap)
            b = t + row_height if i < count - 1 else y1
            rects.append((x0, t, x1, b))

    elif layout == "stacked":
        for _ in range(count):
            rects.append((x0, y0, x1, y1))

    return rects


def main():
    mode_names = ", ".join(COLOR_MODES.keys())
    theme_names = ", ".join(TERMINAL_THEMES)

    parser = argparse.ArgumentParser(
        description="Open multiple color-coded Terminal windows"
    )
    parser.add_argument("--count", type=int, default=3,
                        help="Number of terminal windows (default: 3)")
    parser.add_argument("--layout",
                        choices=["side-by-side", "grid", "rows", "stacked"],
                        default="side-by-side",
                        help="Window layout (default: side-by-side)")
    parser.add_argument("--mode", type=str, default=None,
                        help=f"Color mode: {mode_names} (default: midnight)")
    parser.add_argument("--theme", type=str, default=None,
                        help=f"Terminal.app theme: {theme_names}")
    parser.add_argument("--colors", type=str, default=None,
                        help="Comma-separated hex colors (overrides --mode)")
    parser.add_argument("--commands", type=str, default=None,
                        help="Comma-separated commands per window")
    parser.add_argument("--no-claude", action="store_true",
                        help="Skip auto-running claude in each window")
    parser.add_argument("--all-new", action="store_true",
                        help="Open all new windows instead of reusing existing one")
    parser.add_argument("--restyle", action="store_true",
                        help="Restyle/rearrange existing Terminal windows without opening new ones")
    parser.add_argument("--notify", action="store_true",
                        help="Play a sound when claude finishes or needs input")
    parser.add_argument("--include-all", action="store_true",
                        help="Include all visible windows (browsers, editors, etc.) in the layout")
    parser.add_argument("--list-modes", action="store_true",
                        help="List available color modes and exit")
    parser.add_argument("--list-themes", action="store_true",
                        help="List available Terminal.app themes and exit")
    args = parser.parse_args()

    if args.list_modes:
        print("Available color modes:")
        for name in COLOR_MODES:
            swatches = "  ".join(COLOR_MODES[name])
            print(f"  {name:12s}  {swatches}")
        sys.exit(0)

    if args.list_themes:
        print("Available Terminal.app themes:")
        for t in TERMINAL_THEMES:
            print(f"  {t}")
        sys.exit(0)

    count = max(1, args.count)
    use_theme = None
    colors = []

    if args.theme:
        use_theme = args.theme
    elif args.colors:
        color_list = [c.strip().strip('"').strip("'") for c in args.colors.split(",")]
        colors = [color_list[i % len(color_list)] for i in range(count)]
    else:
        mode = args.mode or DEFAULT_MODE
        if mode not in COLOR_MODES:
            print(f"Unknown mode '{mode}'. Available: {mode_names}", file=sys.stderr)
            sys.exit(1)
        color_list = COLOR_MODES[mode]
        colors = [color_list[i % len(color_list)] for i in range(count)]

    # Resolve commands
    if args.commands:
        cmd_list = [c.strip() for c in args.commands.split(",")]
    else:
        cmd_list = []

    commands = []
    for i in range(count):
        if i < len(cmd_list) and cmd_list[i]:
            cmd = cmd_list[i]
        elif not args.no_claude:
            cmd = "claude"
        else:
            cmd = None

        # Wrap command to play a sound when it exits (task done)
        if cmd and args.notify:
            sound = "/System/Library/Sounds/Glass.aiff"
            cmd = f'{cmd}; afplay {sound} &'
        commands.append(cmd)

    bounds = get_screen_bounds()

    # Restyle mode: apply layout/colors to existing windows
    if args.restyle:
        valid_indices = get_valid_window_indices()
        other_windows = []

        if args.include_all:
            all_windows = get_all_visible_windows()
            # Filter out Terminal windows (handled separately) and this script's process
            other_windows = [w for w in all_windows if w["app"] != "Terminal"]

        term_count = len(valid_indices)
        other_count = len(other_windows)
        total_count = term_count + other_count
        if total_count == 0:
            print("No windows to restyle.", file=sys.stderr)
            sys.exit(1)

        # Calculate layout: terminals get their own layout, other windows
        # are placed in remaining space with their minimum widths respected.
        x0, y0, x1, y1 = bounds
        if other_count > 0 and args.layout in ("side-by-side", "rows"):
            # Detect minimum sizes only when needed (side-by-side/rows may
            # produce cells smaller than an app's minimum width)
            other_min_sizes = []
            for win_info in other_windows:
                min_w, min_h = get_window_min_size(win_info["app"], win_info["index"])
                other_min_sizes.append((min_w, min_h))
            screen_w = x1 - x0
            # Use detected minimum widths, but cap total at 50% of screen
            other_total_w = sum(mw for mw, _ in other_min_sizes)
            max_other = int(screen_w * 0.5)
            if other_total_w > max_other:
                other_total_w = max_other

            term_bounds = (x0, y0, x1 - other_total_w, y1)
            term_rects = calculate_layout(term_count, args.layout, term_bounds, row_gap=TITLEBAR_GAP)

            # Place other windows on the right side, respecting their min widths
            other_rects = []
            other_x = x1 - other_total_w
            if args.layout == "side-by-side":
                # Stack vertically on right
                other_h = (y1 - y0) // max(1, other_count)
                for j in range(other_count):
                    ot = y0 + j * other_h
                    ob = y0 + (j + 1) * other_h if j < other_count - 1 else y1
                    other_rects.append((other_x, ot, x1, ob))
            else:
                # Rows: other windows get columns on the right
                cur_x = other_x
                for j in range(other_count):
                    w = other_min_sizes[j][0] if j < other_count - 1 else (x1 - cur_x)
                    other_rects.append((cur_x, y0, cur_x + w, y1))
                    cur_x += w
        else:
            # Grid or stacked: all windows get equal cells with row gaps.
            all_rects = calculate_layout(total_count, args.layout, (x0, y0, x1, y1), row_gap=TITLEBAR_GAP)
            term_rects = all_rects[:term_count]
            other_rects = all_rects[term_count:]

        # Terminal windows get colors/themes
        restyled_colors = colors if colors else [None] * term_count
        if colors:
            restyled_colors = [colors[i % len(colors)] for i in range(term_count)]

        restyled = 0

        # Restyle Terminal windows first
        for i, win_idx in enumerate(valid_indices):
            success = restyle_existing_window(
                win_idx, term_rects[i],
                color_hex=restyled_colors[i] if i < len(restyled_colors) and restyled_colors[i] else None,
                theme=use_theme
            )
            if success:
                restyled += 1
            time.sleep(0.1)

        # Resize other app windows
        other_resized = 0
        for j, win_info in enumerate(other_windows):
            success = resize_app_window(win_info["app"], win_info["index"], other_rects[j])
            if success:
                other_resized += 1
            time.sleep(0.1)

        label = args.layout
        if use_theme:
            label += f", theme: {use_theme}"
        elif args.mode or not args.colors:
            label += f", mode: {args.mode or DEFAULT_MODE}"

        msg = f"Restyled {restyled} terminal window{'s' if restyled != 1 else ''}"
        if other_resized > 0:
            msg += f" + resized {other_resized} other window{'s' if other_resized != 1 else ''}"
        msg += f" ({label})"
        print(msg)
        sys.exit(0)

    rects = calculate_layout(count, args.layout, bounds, row_gap=TITLEBAR_GAP)

    # Check if we can reuse an existing Terminal window
    existing_count = get_terminal_window_count()
    reuse_existing = existing_count > 0 and not args.all_new

    opened = 0

    use_notify = args.notify

    if reuse_existing:
        # Restyle the frontmost existing window as slot 0
        color = colors[0] if colors else None
        success = restyle_existing_window(
            1, rects[0],
            color_hex=color,
            theme=use_theme
        )
        if success:
            opened += 1
        time.sleep(0.3)

        # Open new windows for the remaining slots
        for i in range(1, count):
            color = colors[i] if colors else None
            success = open_new_terminal_window(
                rects[i], commands[i],
                color_hex=color,
                theme=use_theme
            )
            if success:
                opened += 1
            if i < count - 1:
                time.sleep(0.3)
    else:
        # All new windows
        for i in range(count):
            color = colors[i] if colors else None
            success = open_new_terminal_window(
                rects[i], commands[i],
                color_hex=color,
                theme=use_theme
            )
            if success:
                opened += 1
            if i < count - 1:
                time.sleep(0.3)

    label = args.layout
    if use_theme:
        label += f", theme: {use_theme}"
    elif args.mode or not args.colors:
        label += f", mode: {args.mode or DEFAULT_MODE}"

    reused_msg = ""
    if reuse_existing and opened > 0:
        reused_msg = " (reused existing window for slot 1)"

    print(f"Opened {opened} terminal window{'s' if opened != 1 else ''} ({label}){reused_msg}")
    if opened < count:
        print(f"Warning: {count - opened} window(s) failed to open", file=sys.stderr)

    # Launch background watcher for idle detection
    if use_notify and colors and opened > 0:
        watcher_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "watcher.py"
        )
        color_str = ",".join(colors[:opened])
        watcher_cmd = [
            sys.executable, watcher_script,
            "--colors", color_str,
            "--sound",
            "--window-count", str(opened)
        ]
        try:
            subprocess.Popen(
                watcher_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            print("Background watcher started (highlights idle terminals)")
        except Exception as e:
            print(f"Warning: Could not start watcher: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
