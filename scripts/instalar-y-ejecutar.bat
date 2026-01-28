@echo off
REM ===================================================================
REM Instalador/Ejecutor - PANEL DASH (DEMO)
REM - Solo DEMO: SQLite + simulación + dashboard
REM - Sin ODBC / sin BD real
REM ===================================================================

setlocal
color 0A

echo.
echo ================================================================
echo    INSTALADOR Y EJECUTOR AUTOMATICO - PANEL DASH (DEMO)
echo ================================================================
echo.

REM Cambiar al directorio del proyecto (un nivel arriba de scripts)
cd /d "%~dp0.."

echo [1/4] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
  echo.
  echo [!] Python no esta instalado o no esta en PATH.
  echo Instala Python 3.8+ desde: https://www.python.org/downloads/
  echo (marca "Add Python to PATH")
  echo.
  pause
  exit /b 1
)

echo [2/4] Verificando pip...
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
  echo [!] pip no esta disponible. Intentando instalar pip...
  python -m ensurepip --upgrade
  if %errorlevel% neq 0 (
    echo [!] Error al instalar pip.
    pause
    exit /b 1
  )
)

echo [3/4] Instalando dependencias (requirements.txt)...
if not exist "requirements.txt" (
  echo [!] ERROR: No se encuentra requirements.txt
  pause
  exit /b 1
)
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
  echo.
  echo [!] Error instalando dependencias.
  pause
  exit /b 1
)

echo [4/4] Iniciando DEMO (dashboard + simulacion)...
echo WEB: http://localhost:8050
echo INFO: Ctrl+C para detener
echo.

python run_demo.py --mode full
set "APP_EXIT=%errorlevel%"

echo.
echo La aplicacion se ha cerrado. (ExitCode=%APP_EXIT%)
pause
