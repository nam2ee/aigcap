#Requires -Version 5.1
<#
.SYNOPSIS
    AIGCAP Installer (Windows)

.DESCRIPTION
    Installs AI-Generated Code Annotation Protocol for Claude Code.

.EXAMPLE
    git clone https://github.com/<you>/aigcap.git
    cd aigcap
    .\install.ps1
#>

$ErrorActionPreference = "Stop"

$ClaudeDir = Join-Path $env:USERPROFILE ".claude"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupDir = Join-Path $ClaudeDir "backups\aigcap-$Timestamp"

# ── Colors ──────────────────────────────────
function Write-OK($msg)   { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  ⚠ $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  ✗ $msg" -ForegroundColor Red }
function Write-Head($msg) { Write-Host "`n$msg" -ForegroundColor Cyan -NoNewline; Write-Host "" }

Write-Host ""
Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  AIGCAP v1.0 Installer (Windows)           ║" -ForegroundColor Cyan
Write-Host "║  AI-Generated Code Annotation Protocol     ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Preflight: Find Python ──────────────────
$PythonCmd = $null
foreach ($cmd in @("python3", "python", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3") {
            $PythonCmd = $cmd
            break
        }
    } catch {}
}

if (-not $PythonCmd) {
    Write-Err "Python 3 not found. Please install from https://python.org"
    Write-Err "Make sure 'Add Python to PATH' is checked during installation."
    exit 1
}
Write-OK "Python found: $(& $PythonCmd --version 2>&1)"

# Check source dir
$SourceDir = Join-Path $ScriptDir "dot-claude"
if (-not (Test-Path $SourceDir)) {
    Write-Err "dot-claude/ directory not found. Are you running this from the repo root?"
    exit 1
}

# ── Create directories ──────────────────────
$dirs = @(
    (Join-Path $ClaudeDir "protocols"),
    (Join-Path $ClaudeDir "hooks"),
    $BackupDir
)
foreach ($d in $dirs) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
    }
}
Write-OK "Directories ready"

# ── Backup existing files ───────────────────
$BackedUp = $false
foreach ($f in @("CLAUDE.md", "settings.json")) {
    $src = Join-Path $ClaudeDir $f
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $BackupDir $f) -Force
        $BackedUp = $true
    }
}
$protoSrc = Join-Path $ClaudeDir "protocols\AIGCAP_PROTOCOL.md"
if (Test-Path $protoSrc) {
    Copy-Item $protoSrc (Join-Path $BackupDir "AIGCAP_PROTOCOL.md") -Force
    $BackedUp = $true
}
$hookSrc = Join-Path $ClaudeDir "hooks\check_aigcap.py"
if (Test-Path $hookSrc) {
    Copy-Item $hookSrc (Join-Path $BackupDir "check_aigcap.py") -Force
    $BackedUp = $true
}
if ($BackedUp) {
    Write-OK "Backed up existing files → $BackupDir"
}

# ════════════════════════════════════════════
# 1. CLAUDE.md
# ════════════════════════════════════════════
Write-Head "[1/4] CLAUDE.md"

$claudeMd = Join-Path $ClaudeDir "CLAUDE.md"
$newContent = Get-Content (Join-Path $SourceDir "CLAUDE.md") -Raw

if (Test-Path $claudeMd) {
    $existing = Get-Content $claudeMd -Raw
    if ($existing -match "AIGCAP") {
        Write-Warn "Already contains AIGCAP section → skipping"
    } else {
        Add-Content $claudeMd "`n---`n"
        Add-Content $claudeMd $newContent
        Write-OK "Appended AIGCAP directives to existing file"
    }
} else {
    Set-Content $claudeMd $newContent -Encoding UTF8
    Write-OK "Installed new file"
}

# ════════════════════════════════════════════
# 2. Protocol file
# ════════════════════════════════════════════
Write-Head "[2/4] AIGCAP_PROTOCOL.md"

Copy-Item (Join-Path $SourceDir "protocols\AIGCAP_PROTOCOL.md") `
          (Join-Path $ClaudeDir "protocols\AIGCAP_PROTOCOL.md") -Force
Write-OK "Installed"

# ════════════════════════════════════════════
# 3. Hook script
# ════════════════════════════════════════════
Write-Head "[3/4] check_aigcap.py hook"

Copy-Item (Join-Path $SourceDir "hooks\check_aigcap.py") `
          (Join-Path $ClaudeDir "hooks\check_aigcap.py") -Force
Write-OK "Installed"

# ════════════════════════════════════════════
# 4. settings.json (hook registration)
# ════════════════════════════════════════════
Write-Head "[4/4] settings.json"

# Determine the hook command — use the detected python command
# Claude Code on Windows uses the system shell, so we need the full python path
$HookPath = Join-Path $ClaudeDir "hooks\check_aigcap.py"
# Use forward slashes for Claude Code compatibility
$HookPathUnix = $HookPath.Replace("\", "/")
$HookCommand = "$PythonCmd `"$HookPathUnix`""

$settingsPath = Join-Path $ClaudeDir "settings.json"

if (Test-Path $settingsPath) {
    $existingJson = Get-Content $settingsPath -Raw
    if ($existingJson -match "check_aigcap") {
        Write-Warn "Hooks already registered → skipping"
    } else {
        # Merge using Python for reliable JSON handling
        $mergeScript = @"
import json, os

settings_path = r'$settingsPath'
hook_cmd = r'$HookCommand'

with open(settings_path, 'r', encoding='utf-8') as f:
    existing = json.load(f)

new_hooks = {
    "PreToolUse": [{
        "matcher": "Write",
        "hooks": [{"type": "command", "command": hook_cmd}]
    }],
    "PostToolUse": [{
        "matcher": "Edit|MultiEdit",
        "hooks": [{"type": "command", "command": hook_cmd}]
    }]
}

if "hooks" not in existing:
    existing["hooks"] = {}

for event, rules in new_hooks.items():
    if event not in existing["hooks"]:
        existing["hooks"][event] = []
    existing["hooks"][event].extend(rules)

with open(settings_path, 'w', encoding='utf-8') as f:
    json.dump(existing, f, indent=2)
"@
        $mergeScript | & $PythonCmd -
        Write-OK "Merged hooks into existing settings"
    }
} else {
    # Write fresh settings
    $settings = @{
        hooks = @{
            PreToolUse = @(
                @{
                    matcher = "Write"
                    hooks = @(
                        @{ type = "command"; command = $HookCommand }
                    )
                }
            )
            PostToolUse = @(
                @{
                    matcher = "Edit|MultiEdit"
                    hooks = @(
                        @{ type = "command"; command = $HookCommand }
                    )
                }
            )
        }
    }
    $settings | ConvertTo-Json -Depth 10 | Set-Content $settingsPath -Encoding UTF8
    Write-OK "Created new settings file"
}

# ════════════════════════════════════════════
# Done
# ════════════════════════════════════════════
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Files:"
Write-Host "    $ClaudeDir\CLAUDE.md                       (slim, always loaded)"
Write-Host "    $ClaudeDir\protocols\AIGCAP_PROTOCOL.md    (full spec, on-demand)"
Write-Host "    $ClaudeDir\hooks\check_aigcap.py           (Write blocker + Edit warner)"
Write-Host "    $ClaudeDir\settings.json                   (hook registration)"
Write-Host ""
Write-Host "  Coverage tool (use from any project):"
Write-Host "    $PythonCmd $ScriptDir\tools\ai_coverage.py C:\path\to\project"
Write-Host ""
Write-Host "  Backup:"
Write-Host "    $BackupDir"
Write-Host ""
Write-Host "  To uninstall:"
Write-Host "    .\uninstall.ps1"
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""
