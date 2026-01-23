$ErrorActionPreference = "Stop"

$p = Get-Process caddy -ErrorAction SilentlyContinue
if (-not $p) {
  Write-Host "Caddy no est\u00e1 ejecut\u00e1ndose."
  exit 0
}

Write-Host "Deteniendo Caddy (PID(s): $($p.Id -join ', '))..."
$p | Stop-Process -Force
Write-Host "OK."

