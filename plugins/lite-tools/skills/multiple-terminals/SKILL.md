---
name: multiple-terminals
description: Open multiple color-coded Terminal.app windows tiled across your screen, each running claude by default. Use when the user wants a multi-terminal workspace, multiple claude sessions, side-by-side terminals, or to rearrange existing terminal windows.
user_invocable: true
---

# Multiple Terminals

When this skill is invoked, determine the user's intent:

## 1. Quick Launch (default, most common)

If the user just wants terminals opened with their preferences, run the script directly. Do NOT open the configurator UI. Parse the user's request for parameters and run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/multiple-terminals/multiple-terminals.py --count N --layout LAYOUT
```

Optional flags:
- `--mode NAME` for a color palette (ocean, forest, sunset, berry, earth, mono, warm, cool)
- `--theme "NAME"` for a Terminal.app theme (Pro, Homebrew, Ocean, Red Sands, Grass, Man Page, Novel, Basic, Silver Aerogel)
- `--colors "#hex1,#hex2,#hex3"` for custom colors
- `--commands "cmd1,cmd2,cmd3"` for custom commands per window
- `--no-claude` to skip auto-launching claude
- `--notify` to play sounds when claude finishes or needs input
- `--all-new` to open all new windows (default reuses current terminal)
- `--include-all` to resize all visible windows (browsers, editors, etc.) alongside terminals

Defaults: 3 windows, side-by-side, ocean mode, claude running in each, reuses current terminal.

**Limitation:** Only detects and organizes Terminal windows on the active desktop. Windows on other macOS Spaces are ignored.

## 2. Configure (only when asked)

If the user says they want to "configure", "customize", "pick colors", "set up", or "choose a layout", launch the web configurator:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/multiple-terminals/server.py
```

Then tell the user the configurator is running at http://localhost:9848. It auto-closes when the browser tab closes.

If port 9848 is already in use, kill the existing process first:

```bash
lsof -ti:9848 | xargs kill 2>/dev/null; sleep 0.5; python3 ${CLAUDE_PLUGIN_ROOT}/skills/multiple-terminals/server.py
```

## 3. Restyle/Rearrange existing terminals

If the user wants to rearrange or restyle terminals that are already open, use the `--restyle` flag. This applies a new layout, color mode, or theme to all existing Terminal.app windows without opening new ones:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/multiple-terminals/multiple-terminals.py --restyle --layout LAYOUT --mode MODE
```

The `--restyle` flag skips opening new windows and instead applies the layout and appearance to existing windows.

## Examples

- `/multiple-terminals` - 3 side-by-side ocean terminals with claude
- `/multiple-terminals 4 grid ocean` - 4 ocean-themed grid terminals
- `/multiple-terminals configure` - open the web configurator
- `/multiple-terminals rearrange to grid` - rearrange existing windows to grid
- `/multiple-terminals restyle to ember` - change existing windows to ember colors
- `/multiple-terminals 2 with Pro theme` - 2 terminals using Terminal.app Pro theme
- `/multiple-terminals 3 with notifications` - 3 terminals with sound alerts

Do NOT ask questions. Run immediately based on the user's request.
