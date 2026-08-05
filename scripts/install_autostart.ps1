# Installs J.A.R.V.I.S Electron HUD to start at Windows logon (Task Scheduler).
# No admin rights required. Run uninstall_autostart.ps1 to remove.
$ErrorActionPreference = "Stop"

$taskName = "J.A.R.V.I.S"
$projectRoot = Split-Path -Parent $PSScriptRoot
$desktopApp = Join-Path $projectRoot "desktop"
$electronExe = Join-Path $desktopApp "node_modules\electron\dist\electron.exe"
$startupLnk = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\J.A.R.V.I.S.lnk"

if (-not (Test-Path $electronExe)) {
    throw "Missing Electron binary: $electronExe. Run npm install in desktop first."
}

if (Test-Path $startupLnk) {
    Remove-Item $startupLnk -Force
    Write-Host "Removed delayed Startup shortcut: $startupLnk"
}

$action = New-ScheduledTaskAction -Execute $electronExe -Argument "." -WorkingDirectory $desktopApp
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger.Delay = "PT0S"

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

Write-Host "Autostart enabled (Task Scheduler): $taskName"
Write-Host "Electron HUD will open as soon as you log in."
Write-Host "To disable: powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\uninstall_autostart.ps1`""
