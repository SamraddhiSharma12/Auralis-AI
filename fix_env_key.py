"""
Safely updates the GROQ_API_KEY line in .env, replacing it entirely
with a single clean line - no manual text editing involved, avoiding
hidden line-break/whitespace issues from copy-pasting in an editor.

Usage:
    python fix_env_key.py
    (it will prompt you to paste your key)
"""

import re

new_key = input("Paste your Groq API key here, then press Enter: ").strip()

# Remove ALL whitespace characters (including any embedded newlines/spaces
# that snuck in from copy-pasting) just in case
new_key = re.sub(r"\s+", "", new_key)

print(f"\nKey received - length: {len(new_key)}, starts with gsk_: {new_key.startswith('gsk_')}")

with open(".env", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
replaced = False
skip_next_if_orphan = False

for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("GROQ_API_KEY="):
        new_lines.append(f"GROQ_API_KEY={new_key}\n")
        replaced = True
        # If the ORIGINAL key was broken across two lines, the next line
        # in the file might just be an orphan fragment (e.g. "fT") with
        # no "=" in it - skip it if so, so we don't leave garbage behind.
        skip_next_if_orphan = True
        continue

    if skip_next_if_orphan:
        skip_next_if_orphan = False
        if stripped and "=" not in stripped:
            # This looks like a leftover orphan fragment from the old broken key - skip it
            continue

    new_lines.append(line)

if not replaced:
    # No existing GROQ_API_KEY line found - just append it
    new_lines.append(f"GROQ_API_KEY={new_key}\n")

with open(".env", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("\n.env updated successfully.")
print("Verifying the written line:")
with open(".env", "r", encoding="utf-8") as f:
    for line in f:
        if line.strip().startswith("GROQ_API_KEY="):
            print(repr(line.strip()))