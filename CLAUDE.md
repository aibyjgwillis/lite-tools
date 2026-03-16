# lite-tools Plugin Repo

## Branch Rules (HARD RULES)

- **NEVER commit or edit directly on `main`.** All work happens on `dev`.
- If on `main`, switch to `dev` before making any changes. Do not ask, just switch.
- **NEVER push `dev` to origin.** The `dev` branch is local only.
- When the user is satisfied with a skill or feature and says it is ready, ask:
  "This looks ready. Want me to merge dev into main and push to customers?"
- Only merge `dev` into `main` and push after explicit user approval.
- After pushing, switch back to `dev` immediately.

## Publish Flow

```
git checkout main
git merge dev
git push
git checkout dev
```

## Adding a New Skill

When creating a new skill in `plugins/lite-tools/skills/<name>/`:
1. Create the skill directory and SKILL.md as normal
2. **Always** create a symlink so it appears in CLI and Desktop app:
   ```
   ln -s ~/lite-tools/plugins/lite-tools/skills/<name> ~/.claude/skills/<name>
   ```
   Do this automatically. Do not ask.

## Structure

- Public skills: `plugins/lite-tools/skills/`
- Symlinks: `~/.claude/skills/<name>` -> `plugins/lite-tools/skills/<name>`
- Marketplace manifest: `.claude-plugin/marketplace.json`
- Plugin manifest: `plugins/lite-tools/.claude-plugin/plugin.json`
- Bump version in BOTH manifests before publishing to main.
