---
name: rapid-download
description: Bulk-collect images from Google Images for a list of items. Opens a picker UI where you click images to save them, automatically renamed and organized.
user_invocable: true
---

# Rapid Download

Bulk image collection from Google Images with a visual picker UI.

## Trigger

User wants to collect/download images for a list of items (logos, photos, icons, etc).

## Steps

1. **Parse the input** into a list of items. Accept any of:
   - A pasted list (one per line, comma-separated, or numbered)
   - A file path to CSV or text file (read column A or first column as names)
   - A description to generate items from (e.g. "top 20 fast food chains")

2. **Build items array**. For each item create an object:
   ```json
   { "name": "Display Name", "query": "search query for Google Images", "safeName": "filesystem_safe_name" }
   ```
   - `query` should be tailored to the kind of image wanted (add "logo png transparent", "high resolution photo", etc. based on context)
   - `safeName`: lowercase, no special chars, underscores for spaces

3. **Write session config** to the skill's session directory:
   ```bash
   mkdir -p ${CLAUDE_PLUGIN_ROOT}/skills/rapid-download/session
   ```
   Write to `${CLAUDE_PLUGIN_ROOT}/skills/rapid-download/session/items.json`:
   ```json
   {
     "outputDir": "~/Downloads/fast-food-logos",
     "items": [
       { "name": "McDonald's", "query": "McDonald's logo png transparent", "safeName": "mcdonalds" }
     ]
   }
   ```
   The `outputDir` should be contextual. Default to `~/Downloads/{descriptive_folder_name}/`.

4. **Install deps if needed**:
   ```bash
   pip3 install requests 2>/dev/null
   ```

5. **Start server** (kill existing first):
   ```bash
   lsof -ti:9849 | xargs kill 2>/dev/null; sleep 0.5; python3 ${CLAUDE_PLUGIN_ROOT}/skills/rapid-download/rapid-download.py
   ```
   Run this in the background.

6. **Tell the user the workflow**:
   - The picker UI is open at http://localhost:9849
   - Review and edit the list, then click "Start Downloading"
   - Click any image in the Google Images window to save it
   - The image is automatically renamed and moved to the output folder
   - Press Skip to skip an item
   - When done, results are in the output folder

Do NOT ask any questions. Just write the items and launch the server immediately.
