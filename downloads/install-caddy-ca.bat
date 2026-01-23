@echo off
setlocal EnableExtensions

set "CERT=%~dp0caddy-local-root.crt"
if not exist "%CERT%" (
  echo No se encontro el certificado: "%CERT%"
  pause
  exit /b 1
)

:: Re-lanzar como administrador si no lo es
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Solicitando permisos de administrador...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

set "URL=https://laptop-5v0qtdi3:8443/"
if not "%DASH_PUBLIC_URL%"=="" set "URL=%DASH_PUBLIC_URL%"

echo Instalando CA de Caddy en "Entidades de certificacion raiz de confianza"...
certutil -addstore -f "ROOT" "%CERT%"
if %errorlevel% neq 0 (
  echo Error instalando el certificado.
  pause
  exit /b 1
)

echo OK. Abriendo el navegador en: %URL%
start "" "%URL%"
pause
exit /b 0
