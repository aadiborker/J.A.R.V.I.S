# Creates / replaces the Desktop shortcut with the Electron HUD app (not the old terminal bat).
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$desktopApp = Join-Path $projectRoot "desktop"
$electronExe = Join-Path $desktopApp "node_modules\electron\dist\electron.exe"
$desktopApp = Join-Path $projectRoot "desktop"
$electronExe = Join-Path $desktopApp "node_modules\electron\dist\electron.exe"
$iconPath = Join-Path $desktopApp "assets\jarvis.ico"
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "J.A.R.V.I.S.lnk"

if (-not (Test-Path $electronExe)) {
    Write-Host "Electron not found. Installing desktop dependencies..."
    Push-Location $desktopApp
    try {
        npm install
    } finally {
        Pop-Location
    }
}

if (-not (Test-Path $electronExe)) {
    throw "Missing Electron binary: $electronExe"
}

# Remove any old shortcut first so we fully replace it.
if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath -Force
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $electronExe
$shortcut.Arguments = "."
$shortcut.WorkingDirectory = $desktopApp
$shortcut.WindowStyle = 1
$shortcut.Description = "J.A.R.V.I.S HUD"
if (Test-Path $iconPath) {
    $shortcut.IconLocation = "$iconPath,0"
}
$shortcut.Save()

Write-Host "Desktop app shortcut replaced: $shortcutPath"
Write-Host "Target: $electronExe"
Write-Host "Double-click 'J.A.R.V.I.S' on your Desktop to open the HUD."
