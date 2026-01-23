@echo off
setlocal

echo ========================================
echo    PANEL DASH - VERSION DEMO
echo    AgroIndustria XYZ S.A.
echo ========================================
echo.

cd /d "%~dp0"

REM Verificar si Python está disponible
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no está disponible en PATH
    echo.
    echo Posibles soluciones:
    echo 1. Instalar Python desde https://python.org
    echo 2. Marcar "Add Python to PATH" durante instalación
    echo 3. Usar python3 en lugar de python
    echo.
    pause
    exit /b 1
)

REM Menú de opciones
echo Selecciona una opción:
echo [1] Modo Completo (Dashboard + Simulación)
echo [2] Solo Dashboard
echo [3] Solo Simulación
echo [4] Configurar Base de Datos
echo [5] Ver Configuración
echo.

set /p opcion="Opción: "

if "%opcion%"=="1" goto modo_completo
if "%opcion%"=="2" goto solo_dashboard
if "%opcion%"=="3" goto solo_simulacion
if "%opcion%"=="4" goto configurar_bd
if "%opcion%"=="5" goto ver_config
echo Opción inválida
pause
exit /b 1

:modo_completo
echo.
echo 🚀 Iniciando Modo Completo...
echo.
echo 1. Verificando base de datos...
if not exist "demo_database.db" (
    echo Creando base de datos demo...
    python demo_db_generator.py
    if %errorlevel% neq 0 (
        echo [ERROR] No se pudo crear la base de datos
        pause
        exit /b 1
    )
) else (
    echo ✅ Base de datos demo encontrada
)

echo.
echo 2. Iniciando simulación en segundo plano...
start "Simulación Panel Dash" cmd /c "python demo_simulation.py --mode continuous --interval 30"

echo.
echo 3. Iniciando dashboard...
timeout /t 3 /nobreak >nul
python app_demo.py
goto end

:solo_dashboard
echo.
echo 📊 Iniciando Dashboard...
python app_demo.py
goto end

:solo_simulacion
echo.
echo 🎭 Iniciando Simulación...
python demo_simulation.py --mode continuous --interval 30
goto end

:configurar_bd
echo.
echo 🔧 Configurando Base de Datos...
python demo_db_generator.py
pause
goto end

:ver_config
echo.
echo 🔧 Configuración Actual:
python config_demo.py
echo.
pause
goto end

:end
echo.
echo ¡Gracias por usar Panel Dash Demo!
pause