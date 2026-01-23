$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$batPath = Join-Path $repoRoot "scripts\\run-panel.bat"
if (-not (Test-Path $batPath)) {
  throw "No se encontr\u00f3: $batPath"
}

$desktopDir = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopDir "Iniciar Panel Dash.lnk"

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $batPath
$shortcut.WorkingDirectory = $repoRoot
$shortcut.WindowStyle = 1
$shortcut.Description = "Inicia la app Python (Dash). Caddy puede estar corriendo en segundo plano."
$shortcut.Save()

Write-Host "OK. Acceso directo creado en el Escritorio:"
Write-Host $shortcutPath

