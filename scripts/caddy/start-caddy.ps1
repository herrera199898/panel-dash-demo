$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..")
$caddyfile = Join-Path $repoRoot "infra\\caddy\\Caddyfile"

if (-not (Test-Path $caddyfile)) {
  throw "No se encontr\u00f3 Caddyfile en: $caddyfile"
}

$caddyExe = (Get-Process caddy -ErrorAction SilentlyContinue | Select-Object -First 1).Path
if (-not $caddyExe) {
  $caddyExe = (Get-Command caddy -ErrorAction SilentlyContinue).Source
}
if (-not $caddyExe) {
  $caddyExe = Join-Path $env:LOCALAPPDATA "Microsoft\\WinGet\\Packages\\CaddyServer.Caddy_Microsoft.Winget.Source_8wekyb3d8bbwe\\caddy.exe"
}
if (-not (Test-Path $caddyExe)) {
  throw "No se encontr\u00f3 caddy.exe. Ruta esperada: $caddyExe"
}

# Si ya est\u00e1 corriendo, no hagas nada.
if (Get-Process caddy -ErrorAction SilentlyContinue) {
  Write-Host "Caddy ya est\u00e1 ejecut\u00e1ndose."
  exit 0
}

Write-Host "Iniciando Caddy..."
Start-Process -FilePath $caddyExe -ArgumentList @("run", "--config", $caddyfile) -WorkingDirectory $repoRoot -WindowStyle Hidden
Write-Host "OK. Verifica con: netstat -ano | findstr `"[:](8443)`""
