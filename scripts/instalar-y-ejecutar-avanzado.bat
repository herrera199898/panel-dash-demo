@echo off
REM ===================================================================
REM Script de instalación y ejecución automática AVANZADO
REM Panel Dash Frutísima - Con instalación automática de Python
REM ===================================================================

setlocal enabledelayedexpansion

:: Solicitar permisos de administrador si es necesario
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [!] Se requieren permisos de administrador para algunas operaciones.
    echo como administrador (clic derecho - Ejecutar como administrador).
    echo.
)

:: Colores para la salida
color 0A

echo.
echo ================================================================
echo    INSTALADOR Y EJECUTOR AUTOMATICO - PANEL DASH FRUTISIMA
echo              Version Avanzada con Auto-Instalacion
echo ================================================================
echo.

:: Cambiar al directorio del script
cd /d "%~dp0.."

:: ===================================================================
:: PASO 1: Verificar e instalar Python (con auto-instalación)
:: ===================================================================
echo [1/6] Verificando Python...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [!] Python NO esta instalado.
    echo.
    echo Intentando instalar Python automaticamente usando winget...
    echo.
    
    :: Intentar instalar Python usando winget (Windows 10/11)
    where winget >nul 2>&1
    if %errorlevel% equ 0 (
        echo Instalando Python 3.11 desde winget (esto puede tardar varios minutos)...
        winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
        if %errorlevel% equ 0 (
            echo [OK] Python instalado correctamente.
            echo Actualizando variables de entorno...
            :: Refrescar PATH en esta sesión
            for /f "usebackq tokens=2*" %%a in (`reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul`) do set "SYSTEM_PATH=%%b"
            set "PATH=%SYSTEM_PATH%;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts"
            set "PATH=%PATH%;%ProgramFiles%\Python311;%ProgramFiles%\Python311\Scripts"
            
            :: Verificar nuevamente
            python --version >nul 2>&1
            if %errorlevel% neq 0 (
                echo.
                echo [!] Python fue instalado pero no se encuentra en el PATH.
                echo Por favor, cierre y vuelva a abrir la terminal, o reinicie el equipo.
                echo Luego ejecute este script nuevamente.
                echo.
                pause
                exit /b 1
            )
        ) else (
            echo.
            echo [!] No se pudo instalar Python automaticamente.
            goto :instalar_python_manual
        )
    ) else (
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
    )
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python !PYTHON_VERSION! esta instalado.
echo.

:: ===================================================================
:: PASO 2: Verificar pip
:: ===================================================================
echo [2/6] Verificando pip...

python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] pip no esta disponible. Intentando instalar pip...
    python -m ensurepip --upgrade
    if %errorlevel% neq 0 (
        echo [!] Error al instalar pip. Por favor instale pip manualmente.
        pause
        exit /b 1
    )
)

echo [OK] pip esta disponible.
echo.

:: ===================================================================
:: PASO 3: Actualizar pip
:: ===================================================================
echo [3/6] Actualizando pip a la ultima version...
python -m pip install --upgrade pip --quiet
if %errorlevel% neq 0 (
    echo [!] Advertencia: No se pudo actualizar pip, continuando...
)
echo [OK] pip actualizado.
echo.

:: ===================================================================
:: PASO 4: Instalar dependencias desde requirements.txt
:: ===================================================================
echo [4/6] Instalando dependencias desde requirements.txt...
echo Esto puede tardar varios minutos la primera vez...
echo.

if not exist "requirements.txt" (
    echo [!] ERROR: No se encuentra el archivo requirements.txt
    echo Asegurese de que este script este en el directorio del proyecto.
    pause
    exit /b 1
)

python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [!] Error al instalar algunas dependencias.
    echo Verifique los mensajes de error anteriores.
    echo.
    echo Intentando instalar dependencias individualmente...
    python -m pip install streamlit pandas pyodbc plotly plyer streamlit-aggrid dash openpyxl python-dotenv
    if %errorlevel% neq 0 (
        echo [!] Error critico al instalar dependencias.
        pause
        exit /b 1
    )
)

echo.
echo [OK] Todas las dependencias se instalaron correctamente.
echo.

:: ===================================================================
:: ===================================================================

if %errorlevel% neq 0 (
    echo.
    echo.
    
    :: Intentar instalar con winget si está disponible
    where winget >nul 2>&1
    if %errorlevel% equ 0 (
        winget install Microsoft.ODBCDriver.18 --silent --accept-package-agreements --accept-source-agreements
        if %errorlevel% equ 0 (
        ) else (
            echo [!] No se pudo instalar automaticamente. Se requiere instalacion manual.
            echo.
            echo Puede descargarlo desde:
            echo https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
            echo.
            echo Presione cualquier tecla para abrir la pagina de descarga...
            pause >nul
            start https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
        )
    ) else (
        echo La aplicacion requiere este driver para conectarse a la base de datos.
        echo Puede descargarlo desde:
        echo https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
        echo.
        echo Presione cualquier tecla para continuar de todos modos...
        pause >nul
    )
) else (
)
echo.

:: ===================================================================
:: PASO 6: Ejecutar la aplicación
:: ===================================================================
echo [6/6] Preparando para ejecutar la aplicacion...
echo.
echo ================================================================
echo    INICIANDO LA APLICACION...
echo ================================================================
echo.
echo La aplicacion se ejecutara en:
echo    http://localhost:8050
echo.
echo Para acceder desde otros dispositivos en la red local:
echo    http://[IP-DEL-EQUIPO]:8050
echo.
echo Para detener la aplicacion, presione Ctrl+C
echo.
echo ================================================================
echo.

:: Ejecutar la aplicación
python app.py

:: Si llegamos aquí, la aplicación se cerró
echo.
echo ================================================================
echo La aplicacion se ha cerrado.
echo ================================================================
pause