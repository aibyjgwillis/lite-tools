"""Detect the active screen (where the mouse cursor is) and print its usable bounds.

Output format (default):  left, top, right, bottom
With --debug:             also prints per-display info lines prefixed with #

Accepts --screen N to force a specific display index (0-based).
"""
import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--debug", action="store_true", help="Print display arrangement info")
parser.add_argument("--screen", type=int, default=-1,
                    help="Force a specific display index (0-based)")
args = parser.parse_args()

from AppKit import NSScreen
from Quartz import CGEventCreate, CGEventGetLocation

screens = NSScreen.screens()
if not screens:
    # No screens detected (headless or error). Use a safe default.
    print("0, 0, 1440, 900")
    sys.exit(0)

main_screen = NSScreen.mainScreen()
main_h = main_screen.frame().size.height

# Debug: print display arrangement
if args.debug:
    for idx, s in enumerate(screens):
        sf = s.frame()
        scale = s.backingScaleFactor()
        is_main = " [main]" if s == main_screen else ""
        print(f"# Display {idx}{is_main}: "
              f"origin=({int(sf.origin.x)}, {int(sf.origin.y)}) "
              f"size={int(sf.size.width)}x{int(sf.size.height)} "
              f"scale={scale}")

active = None

if 0 <= args.screen < len(screens):
    # User forced a specific display
    active = screens[args.screen]
else:
    # Detect by mouse cursor position (Quartz coords: top-left origin)
    event = CGEventCreate(None)
    loc = CGEventGetLocation(event)
    mx, my = loc.x, loc.y

    for s in screens:
        sf = s.frame()
        # Convert NSScreen frame (bottom-left origin) to Quartz (top-left origin)
        ql = sf.origin.x
        qt = main_h - sf.origin.y - sf.size.height
        qr = ql + sf.size.width
        qb = qt + sf.size.height
        if ql <= mx < qr and qt <= my < qb:
            active = s
            break

if active is None:
    active = main_screen

vf = active.visibleFrame()

# Convert visibleFrame (NSScreen bottom-left coords) to Quartz top-left coords.
# visibleFrame already excludes menu bar and dock for the active display.
vl = int(vf.origin.x)
vt = int(main_h - vf.origin.y - vf.size.height)
vr = int(vf.origin.x + vf.size.width)
vb = int(main_h - vf.origin.y)

# Sanity check: reject nonsensical bounds
width = vr - vl
height = vb - vt
if width <= 0 or height <= 0 or width > 10000 or height > 10000:
    if args.debug:
        print(f"# Bounds sanity check failed: {vl},{vt},{vr},{vb} (w={width} h={height})")
    # Fall back to primary display
    vf = main_screen.visibleFrame()
    vl = int(vf.origin.x)
    vt = int(main_h - vf.origin.y - vf.size.height)
    vr = int(vf.origin.x + vf.size.width)
    vb = int(main_h - vf.origin.y)

print(f"{vl}, {vt}, {vr}, {vb}")
