#!/usr/bin/env bash
#
# AIGCAP Installer (macOS / Linux)
#
# Usage:
#   git clone https://github.com/<you>/aigcap.git
#   cd aigcap
#   bash install.sh
#
set -euo pipefail

CLAUDE_DIR="$HOME/.claude"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$CLAUDE_DIR/backups/aigcap-$(date +%Y%m%d-%H%M%S)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "  ${GREEN}✓${NC} $1"; }
warn()  { echo -e "  ${YELLOW}⚠${NC} $1"; }
error() { echo -e "  ${RED}✗${NC} $1" >&2; }

echo ""
echo -e "${BOLD}╔════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║  AIGCAP v1.0 Installer (macOS / Linux)     ║${NC}"
echo -e "${BOLD}║  AI-Generated Code Annotation Protocol     ║${NC}"
echo -e "${BOLD}╚════════════════════════════════════════════╝${NC}"
echo ""

# --- Preflight checks ---
if ! command -v python3 &>/dev/null; then
    error "python3 not found. Please install Python 3.8+ first."
    exit 1
fi
info "python3 found: $(python3 --version)"

if [ ! -d "$SCRIPT_DIR/dot-claude" ]; then
    error "dot-claude/ directory not found. Are you running this from the repo root?"
    exit 1
fi

# --- Create directories ---
mkdir -p "$CLAUDE_DIR/protocols"
mkdir -p "$CLAUDE_DIR/hooks"
mkdir -p "$BACKUP_DIR"
info "Directories ready"

# --- Backup existing files ---
BACKED_UP=false
for f in CLAUDE.md settings.json; do
    if [ -f "$CLAUDE_DIR/$f" ]; then
        cp "$CLAUDE_DIR/$f" "$BACKUP_DIR/$f"
        BACKED_UP=true
    fi
done
[ -f "$CLAUDE_DIR/protocols/AIGCAP_PROTOCOL.md" ] && cp "$CLAUDE_DIR/protocols/AIGCAP_PROTOCOL.md" "$BACKUP_DIR/" && BACKED_UP=true
[ -f "$CLAUDE_DIR/hooks/check_aigcap.py" ] && cp "$CLAUDE_DIR/hooks/check_aigcap.py" "$BACKUP_DIR/" && BACKED_UP=true

if [ "$BACKED_UP" = true ]; then
    info "Backed up existing files → $BACKUP_DIR"
fi

# ──────────────────────────────────────────────
# 1. CLAUDE.md
# ──────────────────────────────────────────────
echo ""
echo -e "${BOLD}[1/5] CLAUDE.md${NC}"

if [ -f "$CLAUDE_DIR/CLAUDE.md" ]; then
    if grep -q "AIGCAP" "$CLAUDE_DIR/CLAUDE.md" 2>/dev/null; then
        warn "Already contains AIGCAP section → skipping"
    else
        echo "" >> "$CLAUDE_DIR/CLAUDE.md"
        echo "---" >> "$CLAUDE_DIR/CLAUDE.md"
        echo "" >> "$CLAUDE_DIR/CLAUDE.md"
        cat "$SCRIPT_DIR/dot-claude/CLAUDE.md" >> "$CLAUDE_DIR/CLAUDE.md"
        info "Appended AIGCAP directives to existing file"
    fi
else
    cp "$SCRIPT_DIR/dot-claude/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"
    info "Installed new file"
fi

# ──────────────────────────────────────────────
# 2. Protocol file
# ──────────────────────────────────────────────
echo ""
echo -e "${BOLD}[2/5] AIGCAP_PROTOCOL.md${NC}"

cp "$SCRIPT_DIR/dot-claude/protocols/AIGCAP_PROTOCOL.md" "$CLAUDE_DIR/protocols/AIGCAP_PROTOCOL.md"
info "Installed"

# ──────────────────────────────────────────────
# 3. Hook script
# ──────────────────────────────────────────────
echo ""
echo -e "${BOLD}[3/5] check_aigcap.py hook${NC}"

cp "$SCRIPT_DIR/dot-claude/hooks/check_aigcap.py" "$CLAUDE_DIR/hooks/check_aigcap.py"
chmod +x "$CLAUDE_DIR/hooks/check_aigcap.py"
info "Installed & made executable"

# ──────────────────────────────────────────────
# 4. settings.json (hook registration)
# ──────────────────────────────────────────────
echo ""
echo -e "${BOLD}[4/5] settings.json${NC}"

# Build the hook commands with correct python path
PYTHON_CMD="python3"
HOOK_CMD_PRE="$PYTHON_CMD ~/.claude/hooks/check_aigcap.py"
HOOK_CMD_POST="$PYTHON_CMD ~/.claude/hooks/check_aigcap.py"

if [ -f "$CLAUDE_DIR/settings.json" ]; then
    if grep -q "check_aigcap" "$CLAUDE_DIR/settings.json" 2>/dev/null; then
        warn "Hooks already registered → skipping"
    else
        # Merge hooks into existing settings
        python3 << 'PYEOF'
import json, os

claude_dir = os.path.expanduser("~/.claude")
settings_path = os.path.join(claude_dir, "settings.json")

with open(settings_path, "r") as f:
    existing = json.load(f)

new_hooks = {
    "PreToolUse": [
        {
            "matcher": "Write",
            "hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/check_aigcap.py"}]
        }
    ],
    "PostToolUse": [
        {
            "matcher": "Edit|MultiEdit",
            "hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/check_aigcap.py"}]
        }
    ]
}

if "hooks" not in existing:
    existing["hooks"] = {}

for event, rules in new_hooks.items():
    if event not in existing["hooks"]:
        existing["hooks"][event] = []
    existing["hooks"][event].extend(rules)

with open(settings_path, "w") as f:
    json.dump(existing, f, indent=2)
PYEOF
        info "Merged hooks into existing settings"
    fi
else
    # Write fresh settings with correct python command
    cat > "$CLAUDE_DIR/settings.json" << EOF
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "$HOOK_CMD_PRE"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "$HOOK_CMD_POST"
          }
        ]
      }
    ]
  }
}
EOF
    info "Created new settings file"
fi

# ──────────────────────────────────────────────
# 5. CLI tool → ~/.local/bin/aigcap
# ──────────────────────────────────────────────
echo ""
echo -e "${BOLD}[5/5] aigcap CLI${NC}"

LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"

cp "$SCRIPT_DIR/tools/ai_coverage.py" "$LOCAL_BIN/aigcap"
chmod +x "$LOCAL_BIN/aigcap"
info "Installed → $LOCAL_BIN/aigcap"

# Check if ~/.local/bin is in PATH
if ! echo "$PATH" | tr ':' '\n' | grep -qx "$LOCAL_BIN"; then
    # Detect shell config file
    SHELL_RC=""
    case "$(basename "$SHELL")" in
        zsh)  SHELL_RC="$HOME/.zshrc" ;;
        bash)
            if [ -f "$HOME/.bash_profile" ]; then
                SHELL_RC="$HOME/.bash_profile"
            else
                SHELL_RC="$HOME/.bashrc"
            fi
            ;;
        fish) SHELL_RC="$HOME/.config/fish/config.fish" ;;
        *)    SHELL_RC="$HOME/.profile" ;;
    esac

    if [ -n "$SHELL_RC" ]; then
        # Check if already added
        if ! grep -q '\.local/bin' "$SHELL_RC" 2>/dev/null; then
            echo '' >> "$SHELL_RC"
            echo '# Added by AIGCAP installer' >> "$SHELL_RC"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
            warn "Added ~/.local/bin to PATH in $SHELL_RC"
            warn "Run: source $SHELL_RC  (or restart terminal)"
        else
            info "~/.local/bin already in $SHELL_RC"
        fi
    fi
else
    info "~/.local/bin already in PATH"
fi

# ──────────────────────────────────────────────
# Done
# ──────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}${BOLD} Installation complete!${NC}"
echo ""
echo "  Files:"
echo "    ~/.claude/CLAUDE.md                       (slim, always loaded)"
echo "    ~/.claude/protocols/AIGCAP_PROTOCOL.md    (full spec, on-demand)"
echo "    ~/.claude/hooks/check_aigcap.py           (Write blocker + Edit warner)"
echo "    ~/.claude/settings.json                   (hook registration)"
echo "    ~/.local/bin/aigcap                       (CLI tool)"
echo ""
echo "  Usage:"
echo "    aigcap .                          # scan current directory"
echo "    aigcap ./src -o report.html       # custom output"
echo "    aigcap . --json data.json         # also export JSON"
echo "    aigcap . --exclude vendor,dist    # exclude dirs"
echo ""
echo "  Backup: $BACKUP_DIR"
echo "  Uninstall: bash uninstall.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""