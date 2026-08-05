# Removes J.A.R.V.I.S autostart (Task Scheduler task and any old Startup shortcut).
$ErrorActionPreference = "Stop"

$taskName = "J.A.R.V.I.S"
$startupLnk = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\J.A.R.V.I.S.lnk"

$removed = $false

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Removed scheduled task: $taskName"
    $removed = $true
}

if (Test-Path $startupLnk) {
    Remove-Item $startupLnk -Force
    Write-Host "Removed Startup shortcut: $startupLnk"
    $removed = $true
}

if (-not $removed) {
    Write-Host "No autostart found (already disabled)."
}
