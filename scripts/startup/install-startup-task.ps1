$ErrorActionPreference = "Stop"

$taskName = "PanelDashFrutisima"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..")
$startScript = Join-Path $repoRoot "scripts\\startup\\start-panel.ps1"

if (-not (Test-Path $startScript)) {
  throw "No se encontr\u00f3: $startScript"
}

$action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument ("-NoProfile -ExecutionPolicy Bypass -File `"{0}`"" -f $startScript) `
  -WorkingDirectory $repoRoot

$trigger = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -MultipleInstances IgnoreNew

try {
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
} catch { }

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Inicia Dash (8050) y Caddy (8443) al iniciar sesi\u00f3n." | Out-Null

Write-Host "OK. Tarea creada: $taskName"
Write-Host "Para probar ahora: Start-ScheduledTask -TaskName $taskName"

