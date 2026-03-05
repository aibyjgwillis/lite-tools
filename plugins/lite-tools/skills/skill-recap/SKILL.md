---
name: skill-recap
description: Visual summary of what a skill just did. Opens a polished HTML page showing actions, diffs, warnings, and next steps. Use after running any skill or command to see a visual recap.
user_invocable: true
---

# Skill Recap

When this skill is invoked, gather a summary of what just happened in the conversation, then launch the Skill Recap web app.

## Step 1: Gather Context

Look back through the conversation and build a JSON object describing what happened.

**IMPORTANT: Recap the RESULTS of running the skill, not how it was built.** Think like a report card for what the skill produced.

- "Downloaded 12 images to ~/output/" is good. "Built an image pipeline" is bad.
- "Colored 8 folders with earth tones" is good. "Created folder-colors.py" is bad.
- "Committed 3 files with message 'fix auth bug'" is good. "Modified git config" is bad.

The summary and actions should answer: **what did the user get out of running this skill?**

```json
{
  "skill_name": "rapid-download",
  "status": "success",
  "summary": "Downloaded 12 logo images for SHBE businesses to ~/Desktop/SHBE Big Businesses/logos/",
  "timestamp": "2026-03-05T14:30:00",
  "duration_seconds": 42,
  "skill_path": "~/tools/plugins/lite-tools/skills/rapid-download/SKILL.md",
  "actions": [
    { "type": "downloaded", "path": "~/Desktop/SHBE/logos/", "detail": "12 images saved (3 PNG, 9 JPEG)" },
    { "type": "skipped", "path": "Acme Corp, Widget Inc", "detail": "No results found on Google Images" },
    { "type": "saved", "path": "~/Desktop/output/report.csv", "detail": "Export of all 14 items with status" }
  ],
  "diffs": [
    {
      "file": "config change or before/after comparison",
      "before": "old state",
      "after": "new state"
    }
  ],
  "warnings": ["Any warnings or issues encountered"],
  "next_steps": ["What to do next", "Another suggestion"]
}
```

### Action types

Use whichever type best describes what happened. Common types:

| Type | Use for | Example detail |
|------|---------|---------------|
| `downloaded` | Files pulled from the web | "12 images saved (3 PNG, 9 JPEG)" |
| `saved` | Files written or exported | "Report exported to CSV" |
| `colored` | Visual changes applied | "8 folders tinted with warm earth tones" |
| `committed` | Git commits made | "3 files, message: fix auth bug" |
| `deployed` | Code pushed to production | "Live at https://example.com" |
| `fixed` | Bug or issue resolved | "Auth token refresh now works" |
| `configured` | Settings changed | "Output path set to ~/exports/" |
| `tested` | Tests or verification ran | "All 42 tests passed" |
| `skipped` | Items that were skipped | "No results found" |
| `created` | New files/projects scaffolded | "New React project at ~/app/" |
| `deleted` | Files or resources removed | "Cleaned up 3 temp files" |
| `command` | Notable shell command ran | Use `cmd` field instead of `path` |

You are not limited to these. Use any short verb that fits. The UI will auto-format unknown types.

**Required fields:** `skill_name` and `summary`. **Always include** `skill_path` if you know the path to the skill's SKILL.md file (enables View/Edit buttons in the UI). If you don't know the path, omit it and the server will try to find it automatically. Include the other fields when relevant. For diffs, keep them short (just the key changed lines, not entire files).

## Step 2: Start the Server

```bash
lsof -ti:9850 | xargs kill 2>/dev/null; sleep 0.5; python3 ${CLAUDE_PLUGIN_ROOT}/skills/skill-recap/skill-recap.py
```

Run this in the background.

## Step 3: POST the Data

Wait 2 seconds for the server to start, then POST your JSON:

```bash
curl -s -X POST http://localhost:9850/api/recap -H "Content-Type: application/json" -d 'YOUR_JSON_HERE'
```

Tell the user the recap is open at http://localhost:9850. The server stops automatically when the browser tab is closed.

## Auto-trigger via hookify (optional)

You can set up a hookify rule to automatically run skill-recap after every skill execution. Use `/hookify` and create a rule like:

- Event: `postToolUse`
- Tool: `Skill`
- Action: Gather context and run `/skill-recap`

This is not installed automatically. The user must opt in via `/hookify configure`.
