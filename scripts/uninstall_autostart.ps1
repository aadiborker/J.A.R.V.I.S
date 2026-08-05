# Removes J.A.R.V.I.S from Windows Startup.
$ErrorActionPreference = "Stop"

$startup = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$shortcutPath = Join-Path $startup "J.A.R.V.I.S.lnk"

if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath -Force
    Write-Host "Autostart removed: $shortcutPath"
} else {
    Write-Host "No autostart shortcut found (already disabled)."
}
