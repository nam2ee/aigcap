#!/usr/bin/env bash
#
# AIGCAP Uninstaller (macOS / Linux)
#
set -euo pipefail

CLAUDE_DIR="$HOME/.claude"

echo ""
echo "AIGCAP Uninstaller"
echo "━━━━━━━━━━━━━━━━━━"
echo ""

# Find latest backup
LATEST_BACKUP=$(ls -dt "$CLAUDE_DIR/backups/aigcap-"* 2>/dev/null | head -1)

# Remove AIGCAP-specific files
rm -f "$CLAUDE_DIR/protocols/AIGCAP_PROTOCOL.md"
rm -f "$CLAUDE_DIR/hooks/check_aigcap.py"
echo "  ✓ Removed AIGCAP protocol and hook files"

# Remove CLI tool
if [ -f "$HOME/.local/bin/aigcap" ]; then
    rm -f "$HOME/.local/bin/aigcap"
    echo "  ✓ Removed ~/.local/bin/aigcap"
fi

# Remove AIGCAP hooks from settings.json
if [ -f "$CLAUDE_DIR/settings.json" ] && command -v python3 &>/dev/null; then
    python3 << 'PYEOF'
import json, os

path = os.path.expanduser("~/.claude/settings.json")
with open(path, "r") as f:
    data = json.load(f)

changed = False
for event in ["PreToolUse", "PostToolUse"]:
    if event in data.get("hooks", {}):
        original = data["hooks"][event]
        data["hooks"][event] = [
            r for r in original
            if not any("check_aigcap" in h.get("command", "") for h in r.get("hooks", []))
        ]
        if len(data["hooks"][event]) != len(original):
            changed = True
        if not data["hooks"][event]:
            del data["hooks"][event]

if not data.get("hooks"):
    del data["hooks"]

if changed:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
PYEOF
    echo "  ✓ Removed AIGCAP hooks from settings.json"
fi

# Remove AIGCAP section from CLAUDE.md (if it was appended)
if [ -f "$CLAUDE_DIR/CLAUDE.md" ]; then
    if [ -n "$LATEST_BACKUP" ] && [ -f "$LATEST_BACKUP/CLAUDE.md" ]; then
        cp "$LATEST_BACKUP/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"
        echo "  ✓ Restored CLAUDE.md from backup"
    else
        echo "  ⚠ CLAUDE.md may still contain AIGCAP section — edit manually if needed"
    fi
fi

echo ""
echo "  Done. AIGCAP has been removed."
if [ -n "$LATEST_BACKUP" ]; then
    echo "  Backup was at: $LATEST_BACKUP"
fi
echo ""