$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$startScript = Join-Path $repoRoot "scripts\\startup\\start-panel.ps1"
if (-not (Test-Path $startScript)) {
  throw "No se encontr\u00f3: $startScript"
}

$startupDir = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir "PanelDashFrutisima.lnk"

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$startScript`""
$shortcut.WorkingDirectory = $repoRoot
$shortcut.WindowStyle = 7 # minimized
$shortcut.Description = "Inicia Dash (8050) y Caddy (8443) al iniciar sesi\u00f3n."
$shortcut.Save()

Write-Host "OK. Acceso directo creado en Startup:"
Write-Host $shortcutPath
