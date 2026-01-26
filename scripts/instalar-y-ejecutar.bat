@echo off
REM ===================================================================
REM Script de instalación y ejecución automática - Panel Dash Frutísima
REM Este script instala Python (si es necesario) y todas las dependencias
REM ===================================================================

setlocal

:: Colores para la salida (si el terminal lo soporta)
color 0A

echo.
echo ================================================================
echo    INSTALADOR Y EJECUTOR AUTOMATICO - PANEL DASH FRUTISIMA
echo ================================================================
echo.

:: Cambiar al directorio del script
cd /d "%~dp0.."

:: ===================================================================
:: PASO 1: Verificar e instalar Python (auto si es posible)
:: ===================================================================
echo [1/5] Verificando Python...

python --version >nul 2>&1
if not errorlevel 1 goto :python_ok

echo.
echo [!] Python NO esta instalado.
echo.
echo Intentando instalar Python automaticamente usando winget...
echo.

where winget >nul 2>&1
if errorlevel 1 goto :instalar_python_manual

echo Instalando Python 3.11 desde winget (esto puede tardar varios minutos)...
winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto :instalar_python_manual

echo [OK] Python instalado correctamente.
echo Actualizando variables de entorno...

for /f "usebackq tokens=2*" %%a in (`reg query "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" /v PATH 2^>nul`) do set "SYSTEM_PATH=%%b"
set "PATH=%SYSTEM_PATH%;%LOCALAPPDATA%\\Programs\\Python\\Python311;%LOCALAPPDATA%\\Programs\\Python\\Python311\\Scripts"
set "PATH=%PATH%;%ProgramFiles%\\Python311;%ProgramFiles%\\Python311\\Scripts"

python --version >nul 2>&1
if not errorlevel 1 goto :python_ok

echo.
echo [!] Python fue instalado pero no se encuentra en el PATH.
echo Por favor, cierre y vuelva a abrir la terminal, o reinicie el equipo.
echo Luego ejecute este script nuevamente.
echo.
pause
exit /b 1

:python_ok

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% esta instalado.
echo.

goto :after_python_install

:instalar_python_manual
echo.
echo [!] winget no esta disponible o fallo la instalacion automatica.
echo.
echo Por favor, instale Python 3.8 o superior manualmente desde:
echo https://www.python.org/downloads/
echo.
echo IMPORTANTE: Durante la instalacion, marque la opcion
echo "Add Python to PATH" (Agregar Python al PATH)
echo.
echo Presione cualquier tecla para abrir la pagina de descarga...
pause >nul
start https://www.python.org/downloads/
echo.
echo Despues de instalar Python, ejecute este script nuevamente.
echo.
pause
exit /b 1

:after_python_install

:: ===================================================================
:: PASO 2: Verificar pip
:: ===================================================================
echo [2/5] Verificando pip...

python -m pip --version >nul 2>&1
if not errorlevel 1 goto :pip_ok

echo [!] pip no esta disponible. Intentando instalar pip...
python -m ensurepip --upgrade
if not errorlevel 1 goto :pip_ok

echo [!] Error al instalar pip. Por favor instale pip manualmente.
pause
exit /b 1

:pip_ok

echo [OK] pip esta disponible.
echo.

:: ===================================================================
:: PASO 3: Actualizar pip
:: ===================================================================
echo [3/5] Actualizando pip a la ultima version...
python -m pip install --upgrade pip --quiet
if %errorlevel% neq 0 (
    echo [!] Advertencia: No se pudo actualizar pip, continuando...
)
echo [OK] pip actualizado.
echo.

:: ===================================================================
:: PASO 4: Instalar dependencias desde requirements.txt
:: ===================================================================
echo [4/5] Instalando dependencias desde requirements.txt...
echo Esto puede tardar varios minutos la primera vez...
echo.

if not exist "requirements.txt" (
    echo [!] ERROR: No se encuentra el archivo requirements.txt
    echo Asegurese de que este script este en el directorio del proyecto.
    pause
    exit /b 1
)

python -m pip install -r requirements.txt
if not errorlevel 1 goto :deps_ok
echo.
echo [!] Error al instalar algunas dependencias.
echo Verifique los mensajes de error anteriores.
echo.
pause
exit /b 1

:deps_ok

echo.
echo [OK] Todas las dependencias se instalaron correctamente.
echo.

:: ===================================================================
:: ===================================================================

if not errorlevel 1 goto :odbc_ok

echo.
echo.
echo.

where winget >nul 2>&1
if errorlevel 1 goto :odbc_manual

winget install Microsoft.ODBCDriver.18 --silent --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto :odbc_manual

goto :odbc_ok

:odbc_manual
echo.
echo [!] No se pudo instalar automaticamente (puede requerir permisos de administrador o no tener winget).
echo.
echo La aplicacion requiere este driver para conectarse a la base de datos.
echo Puede descargarlo desde:
echo https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
echo.
echo Presione cualquier tecla para abrir la pagina de descarga...
pause >nul
start "" "https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server"
echo.
echo Presione cualquier tecla para continuar de todos modos...
pause >nul

:odbc_ok
echo.

:: ===================================================================
:: PASO 6: Instalar certificado HTTPS (Caddy)
:: ===================================================================
echo [6/6] Configurando HTTPS (certificado de Caddy)...

if not exist "downloads\\install-caddy-ca.bat" goto :https_skip

net session >nul 2>&1
if not errorlevel 1 goto :https_admin

echo [!] Se requieren permisos de administrador para instalar el certificado.
echo     Se abrira un prompt de UAC. Acepta para habilitar HTTPS (8443).
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%CD%\\downloads\\install-caddy-ca.bat' -WorkingDirectory '%CD%\\downloads' -Verb RunAs"
echo.
echo Si cancelas el UAC, igual puedes usar http://localhost:8050
echo.
goto :https_done

:https_admin
call "downloads\\install-caddy-ca.bat"
echo.
goto :https_done

:https_skip
echo [!] No se encontro downloads\\install-caddy-ca.bat (se omite HTTPS).
echo.

:https_done

:: ===================================================================
:: PASO 7: Ejecutar la aplicación
:: ===================================================================
echo ================================================================
echo    INICIANDO LA APLICACION...
echo ================================================================
echo.
echo La aplicacion se ejecutara en:
echo    http://localhost:8050
echo.
echo Para detener la aplicacion, presione Ctrl+C
echo.
echo ================================================================
echo.

:: Ejecutar la aplicación
python app.py
set "APP_EXIT=%errorlevel%"

:: Si llegamos aquí, la aplicación se cerró
echo.
echo La aplicacion se ha cerrado. (ExitCode=%APP_EXIT%)
pause

