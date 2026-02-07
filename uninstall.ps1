#Requires -Version 5.1
<#
.SYNOPSIS
    AIGCAP Uninstaller (Windows)
.EXAMPLE
    .\uninstall.ps1
#>

$ClaudeDir = Join-Path $env:USERPROFILE ".claude"

Write-Host ""
Write-Host "AIGCAP Uninstaller" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""

# Find latest backup
$BackupParent = Join-Path $ClaudeDir "backups"
$LatestBackup = Get-ChildItem $BackupParent -Directory -Filter "aigcap-*" -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1

# Remove AIGCAP files
$filesToRemove = @(
    (Join-Path $ClaudeDir "protocols\AIGCAP_PROTOCOL.md"),
    (Join-Path $ClaudeDir "hooks\check_aigcap.py")
)
foreach ($f in $filesToRemove) {
    if (Test-Path $f) { Remove-Item $f -Force }
}
Write-Host "  ✓ Removed AIGCAP protocol and hook files" -ForegroundColor Green

# Remove hooks from settings.json
$settingsPath = Join-Path $ClaudeDir "settings.json"
$PythonCmd = $null
foreach ($cmd in @("python3", "python", "py")) {
    try { if ((& $cmd --version 2>&1) -match "Python 3") { $PythonCmd = $cmd; break } } catch {}
}

if ((Test-Path $settingsPath) -and $PythonCmd) {
    $script = @"
import json
path = r'$settingsPath'
with open(path, 'r') as f:
    data = json.load(f)
for event in ['PreToolUse', 'PostToolUse']:
    if event in data.get('hooks', {}):
        data['hooks'][event] = [
            r for r in data['hooks'][event]
            if not any('check_aigcap' in h.get('command', '') for h in r.get('hooks', []))
        ]
        if not data['hooks'][event]:
            del data['hooks'][event]
if not data.get('hooks'):
    data.pop('hooks', None)
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
"@
    $script | & $PythonCmd -
    Write-Host "  ✓ Removed AIGCAP hooks from settings.json" -ForegroundColor Green
}

# Restore CLAUDE.md from backup
$claudeMd = Join-Path $ClaudeDir "CLAUDE.md"
if ((Test-Path $claudeMd) -and $LatestBackup) {
    $backupMd = Join-Path $LatestBackup.FullName "CLAUDE.md"
    if (Test-Path $backupMd) {
        Copy-Item $backupMd $claudeMd -Force
        Write-Host "  ✓ Restored CLAUDE.md from backup" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "  Done. AIGCAP has been removed." -ForegroundColor Green
if ($LatestBackup) {
    Write-Host "  Backup was at: $($LatestBackup.FullName)"
}
Write-Host ""
