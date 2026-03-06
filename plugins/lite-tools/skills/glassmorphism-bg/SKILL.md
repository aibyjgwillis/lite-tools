---
name: glassmorphism-bg
description: Generate glassmorphism-style backgrounds for OBS, streaming, or video. Offers color palettes, floating glass panels, lighting matching from reference photos, and 4K PNG export. Use when the user wants to create a background, virtual background, OBS background, stream background, or glassmorphism texture.
user_invocable: true
---

# Glassmorphism Background Generator

When this skill is invoked, immediately launch the web app by running this command in the background:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/glassmorphism-bg/glassmorphism-bg.py
```

Then tell the user the app is running at http://localhost:9851 and should have opened in their browser. The server stops automatically when the browser tab is closed.

If port 9851 is already in use, kill the existing process first:

```bash
lsof -ti:9851 | xargs kill 2>/dev/null; sleep 0.5; python3 ${CLAUDE_PLUGIN_ROOT}/skills/glassmorphism-bg/glassmorphism-bg.py
```

Do NOT ask any questions. Just launch the app immediately.
