---
name: folder-colors
description: Change macOS folder icon colors. Use when the user wants to tint, color, or recolor a folder icon, or reset a folder to its default icon.
user_invocable: true
---

# Folder Colors

When this skill is invoked, immediately launch the Folder Colors web app by running this command in the background:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/folder-colors/folder-colors.py
```

Then tell the user the app is running at http://localhost:9847 and should have opened in their browser. The server stops automatically when the browser tab is closed.

If port 9847 is already in use, kill the existing process first:

```bash
lsof -ti:9847 | xargs kill 2>/dev/null; sleep 0.5; python3 ${CLAUDE_PLUGIN_ROOT}/skills/folder-colors/folder-colors.py
```

## AI Palette Mode

If the user provides a color description as an argument (e.g., `/folder-colors "warm earth tones"`), do the following after launching the server:

1. Wait 2 seconds for the server to start
2. Generate 3 hex colors that match the description (use your judgment for color selection)
3. POST them to the local server to apply:

```bash
curl -s -X POST http://localhost:9847/api/set-layers \
  -H "Content-Type: application/json" \
  -d '{"layers": {"0": "#HEX0", "1": "#HEX1", "2": "#HEX2"}, "path": "PATH", "opacity": 0.55, "description": "USER_DESCRIPTION"}'
```

Replace PATH with `~/Desktop` unless the user specifies a different folder. Replace the hex values with your generated colors.

Tell the user what colors you chose and why, and that they can adjust in the web UI.

Do NOT ask any questions. Just launch the app immediately.
