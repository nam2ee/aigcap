# AIGCAP — AI-Generated Code Annotation Protocol

A system that automatically requires Claude Code to annotate every code file it writes with a structured AI-contribution header, enforces human review before merge, and generates an HTML coverage dashboard.

## Quick Start

### macOS / Linux

```bash
git clone https://github.com/<your-username>/aigcap.git
cd aigcap
bash install.sh
```

### Windows (PowerShell)

```powershell
git clone https://github.com/<your-username>/aigcap.git
cd aigcap
.\install.ps1
```

> **Prerequisite**: Python 3.8+ (on Windows, check "Add Python to PATH" during installation)

## What Gets Installed

```
~/.claude/
  CLAUDE.md                         ← Slim directives (~225 tokens, loaded every turn)
  protocols/
    AIGCAP_PROTOCOL.md              ← Full spec (only read when Claude writes code)
  hooks/
    check_aigcap.py                 ← Blocks writes / warns on edits missing headers
  settings.json                     ← Hook registration (auto-merged with existing config)

~/.local/bin/
  aigcap                            ← CLI tool (available globally)
```

## How It Works

```
Claude attempts to write a code file
       │
  ┌────┴──────────────────────────────────────┐
  │  1st defense: CLAUDE.md (every turn)      │
  │  → "Read AIGCAP protocol before writing"  │
  │  → Claude voluntarily includes header     │
  │  → Always writes REVIEWED-BY-HUMAN: NO    │
  └────┬──────────────────────────────────────┘
       │ if it forgets?
  ┌────┴──────────────────────────────────────┐
  │  2nd defense: Hook (automatic)            │
  │                                           │
  │  Write (PreToolUse):                      │
  │    No header → BLOCKED (exit 2)           │
  │    REVIEWED-BY-HUMAN: YES → BLOCKED       │
  │    Missing REVIEWED-BY-HUMAN → BLOCKED    │
  │                                           │
  │  Edit (PostToolUse):                      │
  │    REVIEWED-BY-HUMAN: YES still set →     │
  │    WARNING: "Reset to NO, you edited it"  │
  └────┬──────────────────────────────────────┘
       │ on PR
  ┌────┴──────────────────────────────────────┐
  │  3rd defense: CI (GitHub Actions)         │
  │                                           │
  │  aigcap --ci scans changed files          │
  │    REVIEWED-BY-HUMAN: NO found → ❌ FAIL  │
  │    All YES → ✅ PASS → merge allowed      │
  └───────────────────────────────────────────┘
```

## REVIEWED-BY-HUMAN Flow

Every AI-generated file gets `REVIEWED-BY-HUMAN: NO` by default. A human must review and change it to `YES` before the PR can merge.

| Action | REVIEWED-BY-HUMAN |
|---|---|
| Claude writes a new file | `NO` (always) |
| Claude edits a reviewed file (`YES`) | Hook warns → Claude resets to `NO` |
| Claude tries to write `YES` itself | Hook **blocks** the write |
| Human reviews and approves | Human changes `NO` → `YES` |
| CI runs `aigcap --ci` | Fails if any `NO` remains |

## Coverage Report

After installation, `aigcap` is available globally:

```bash
aigcap .                          # Scan current directory → HTML dashboard
aigcap ./src -o report.html       # Custom output path
aigcap . --json data.json         # Also export raw JSON data
aigcap . --exclude vendor,dist    # Exclude specific directories
aigcap . --ci                     # CI mode: exit 1 if unreviewed files exist
```


## Report Example 
<img width="3272" height="1980" alt="image" src="https://github.com/user-attachments/assets/98501e55-8d9f-4702-a91c-9ea3ff19c48a" />

## CI Integration (GitHub Actions)

Add this workflow to your project repository at `.github/workflows/aigcap.yml`:

```yaml
name: AIGCAP Review Check

on:
  pull_request:
    branches: [main, master]

jobs:
  aigcap-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install AIGCAP
        run: |
          git clone https://github.com/nam2ee/aigcap.git /tmp/aigcap
          cp /tmp/aigcap/tools/ai_coverage.py /usr/local/bin/aigcap
          chmod +x /usr/local/bin/aigcap

      - name: Check AI code review status
        run: aigcap . --ci --no-open -q
```

This will:
1. Block any PR that contains `REVIEWED-BY-HUMAN: NO`
2. Pass when all AI files have been reviewed (`YES`)
3. Ignore human-only files (no AIGCAP header)

To enforce it, go to **Settings → Branches → Branch protection rules** and enable "Require status checks to pass before merging" with `aigcap-check` as a required check.

## AIGCAP Header Example

Added to the top of every file using the language's comment syntax:

```rust
/*
 * ========================================
 * THIS FILE INCLUDES AI GENERATED CODE
 * ========================================
 * TYPE: ABOVE 50% IN THIS FILE
 * REVIEWED-BY-HUMAN: NO
 *
 * METHOD(FUNCTIONS):
 *   - WHOLE CODE IN THE METHOD `parse_config`
 *   - 45~62 LINE CODE IN THE METHOD `process_batch`
 *
 * STRUCTS(OBJECTS):
 *   - WHOLE CODE IN THE STRUCT `AppConfig`
 *
 * IMPORTED LIBRARY:
 *   - serde: chosen by AI for JSON serialization
 * ========================================
 */
```

## Supported Languages (30+)

Rust, C, C++, Java, JavaScript, TypeScript, Go, Swift, Kotlin, Scala, C#, Python, Ruby, Shell, CSS, SCSS, SQL, Lua, Haskell, HTML, XML, SVG, Vue, YAML, TOML, R, and more.

If you want more, you can customize at `check_aigcap.py` , `ai_coverage.py` and `AIGCAP_PROTOCOL.md`

## Uninstall

```bash
# macOS / Linux
bash uninstall.sh

# Windows
.\uninstall.ps1
```

Automatically restores from backup.

## Repo Structure

```
aigcap/
  dot-claude/                  ← Source files (installer copies to ~/.claude/)
    CLAUDE.md
    protocols/AIGCAP_PROTOCOL.md
    hooks/check_aigcap.py
    settings.json
  tools/
    ai_coverage.py             ← Coverage parser (installer copies to ~/.local/bin/aigcap)
  install.sh                   ← macOS / Linux installer
  install.ps1                  ← Windows installer
  uninstall.sh                 ← macOS / Linux uninstaller
  uninstall.ps1                ← Windows uninstaller
```

## Existing Config Handling

The installer never overwrites your existing configuration:

| Scenario | Behavior |
|---|---|
| No `CLAUDE.md` | Creates new file |
| `CLAUDE.md` exists (no AIGCAP) | Appends AIGCAP section at the end |
| `CLAUDE.md` exists (has AIGCAP) | Skips |
| No `settings.json` | Creates new file |
| `settings.json` exists (no hooks) | Merges AIGCAP hooks into existing config |
| `settings.json` exists (has hooks) | Skips |

All existing files are backed up to `~/.claude/backups/aigcap-<timestamp>/` before any changes.

## License

MIT
