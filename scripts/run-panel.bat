@echo off
setlocal

cd /d "%~dp0.."

echo ================================================================
echo    INICIANDO PANEL DASH (Python)...
echo ================================================================
echo.
echo URL (si Caddy ya esta corriendo): https://%COMPUTERNAME%:8443/
echo URL directa Dash:                http://localhost:8050
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
  echo [!] Python no esta disponible en PATH.
echo Instala Python o abre este .bat desde una terminal con Python.
  pause
  exit /b 1
)

echo Iniciando Dash en esta terminal...
echo (Si el navegador abre muy rapido y aparece 502, se va a abrir cuando 8050 este listo.)
echo.

REM Abrir el navegador solo cuando Dash (8050) este listo para evitar 502 en Caddy.
start "" /min powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "if (Test-Path 'scripts\\wait-port.ps1') { " ^
  "  & 'scripts\\wait-port.ps1' -Port 8050 -TimeoutSeconds 120 -HostName '127.0.0.1' | Out-Null; " ^
  "} else { Start-Sleep -Seconds 5 } ; " ^
  "Start-Sleep -Seconds 1; " ^
  "Start-Process (('https://{0}:8443/' -f $env:COMPUTERNAME))"

python app.py
exit /b %errorlevel%
