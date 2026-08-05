# Installs J.A.R.V.I.S to start when you log into Windows (Startup folder shortcut).
# No admin rights required. Run uninstall_autostart.ps1 to remove.
$ErrorActionPreference = "Stop"

$batPath = Join-Path $PSScriptRoot "start_jarvis.bat"
$projectRoot = Split-Path -Parent $PSScriptRoot
$startup = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$shortcutPath = Join-Path $startup "J.A.R.V.I.S.lnk"

if (-not (Test-Path $batPath)) {
    throw "Missing launcher: $batPath"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $batPath
$shortcut.WorkingDirectory = $projectRoot
$shortcut.WindowStyle = 1
$shortcut.Description = "Auto-start J.A.R.V.I.S on login"
$shortcut.Save()

Write-Host "Autostart enabled: $shortcutPath"
Write-Host "J.A.R.V.I.S will open a console window when you log in."
Write-Host "To disable: powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\uninstall_autostart.ps1`""
