# AIGCAP — AI-Generated Code Annotation Protocol

A system that automatically requires Claude Code to annotate every code file it writes with a structured AI-contribution header, and generates an HTML coverage dashboard showing how much of your project is AI-generated.

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
  └────┬──────────────────────────────────────┘
       │ if it forgets?
  ┌────┴──────────────────────────────────────┐
  │  2nd defense: Hook (automatic)            │
  │                                           │
  │  Write (PreToolUse):                      │
  │    No header → BLOCKED (exit 2)           │
  │    → "Read the protocol and retry"        │
  │    → Claude reads protocol & retries      │
  │                                           │
  │  Edit (PostToolUse):                      │
  │    No header → WARNING (stdout)           │
  │    → "Add the header now"                 │
  │    → Claude adds the header               │
  └───────────────────────────────────────────┘
```

## Coverage Report

After installation, `aigcap` is available globally:

```bash
aigcap .                          # Scan current directory → HTML dashboard
aigcap ./src -o report.html       # Custom output path
aigcap . --json data.json         # Also export raw JSON data
aigcap . --exclude vendor,dist    # Exclude specific directories
```

The installer places `aigcap` in `~/.local/bin/`. If that directory isn't in your PATH, the installer automatically adds it to your shell config.

## AIGCAP Header Example

Added to the top of every file using the language's comment syntax:

```rust
/*
 * ========================================
 * THIS FILE INCLUDES AI GENERATED CODE
 * ========================================
 * TYPE: ABOVE 50% IN THIS FILE
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