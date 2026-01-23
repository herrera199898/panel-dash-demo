$ErrorActionPreference = "Stop"

$taskName = "PanelDashFrutisima"

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
Write-Host "OK. Tarea eliminada (si exist\u00eda): $taskName"

