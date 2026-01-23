$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..")

function Test-TcpPortListening {
  param(
    [Parameter(Mandatory = $true)][int]$Port
  )
  $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  return ($null -ne $connections -and $connections.Count -gt 0)
}

function Start-CaddyIfNeeded {
  if (Test-TcpPortListening -Port 8443) {
    Write-Host "Caddy ya est\u00e1 escuchando en 8443."
    return
  }

  $caddyScript = Join-Path $repoRoot "scripts\\caddy\\start-caddy.ps1"
  if (-not (Test-Path $caddyScript)) {
    throw "No se encontr\u00f3 el script de Caddy: $caddyScript"
  }

  Write-Host "Iniciando Caddy..."
  powershell -NoProfile -ExecutionPolicy Bypass -File $caddyScript | Out-Null
}

Start-CaddyIfNeeded

$hostname = $env:DASH_PUBLIC_HOSTNAME
if (-not $hostname) { $hostname = $env:COMPUTERNAME }
if (-not $hostname) { $hostname = "localhost" }
$hostname = $hostname.ToLower()

Write-Host ("OK. URL: https://{0}:8443/" -f $hostname)
