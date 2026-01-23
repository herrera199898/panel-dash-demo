$ErrorActionPreference = "Stop"

$startupDir = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir "PanelDashFrutisima.lnk"

if (Test-Path $shortcutPath) {
  Remove-Item -Force $shortcutPath
  Write-Host "OK. Acceso directo eliminado: $shortcutPath"
  exit 0
}

Write-Host "No existe el acceso directo: $shortcutPath"

