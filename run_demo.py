"""
Script de inicio para la versión demo del Panel Dash
"""
import os
import sys
import subprocess
import time
import argparse

def run_command(cmd, description):
    """Ejecutar comando y mostrar resultado"""
    print(f"[+] {description}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print("[OK] Ejecutado exitosamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Error ejecutando comando: {e}")
        print(f"Salida de error: {e.stderr}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Panel Dash - Versión Demo")
    parser.add_argument("--mode", choices=["full", "dashboard", "simulation", "setup"], default="full",
                       help="Modo de ejecución")
    parser.add_argument("--sim-interval", type=int, default=30,
                       help="Intervalo de simulación en segundos")

    args = parser.parse_args()

    print("Panel Dash - AgroIndustria XYZ S.A. (Demo)")
    print("=" * 50)

    if args.mode == "setup":
        print("[CONFIG] Configurando base de datos demo...")
        run_command("python demo_db_generator.py", "Creando base de datos SQLite con datos ficticios")
        return

    elif args.mode == "dashboard":
        print("[DASHBOARD] Iniciando dashboard...")
        os.environ["MODO_OPERACION"] = "DEMO"
        run_command("python app_demo.py", "Ejecutando dashboard demo")
        return

    elif args.mode == "simulation":
        print("[SIMULACION] Iniciando simulacion de datos...")
        cmd = f"python demo_simulation.py --mode continuous --interval {args.sim_interval}"
        run_command(cmd, f"Ejecutando simulación cada {args.sim_interval}s")
        return

    elif args.mode == "full":
        print("[FULL] Iniciando modo completo (Dashboard + Simulacion)")
        print("\n1. Configurando base de datos...")

        # Verificar/crear base de datos
        if not os.path.exists("demo_database.db"):
            if not run_command("python demo_db_generator.py", "Creando base de datos demo"):
                print("[ERROR] No se pudo crear la base de datos")
                return
        else:
            print("[OK] Base de datos demo ya existe")

        print("\n2. Iniciando simulacion en segundo plano...")
        # Iniciar simulación en background
        sim_process = subprocess.Popen([
            sys.executable, "demo_simulation.py",
            "--mode", "continuous",
            "--interval", str(args.sim_interval)
        ])

        print(f"[OK] Simulacion iniciada (cada {args.sim_interval}s) - PID: {sim_process.pid}")

        # Pequeña pausa para que la BD se inicialice
        time.sleep(3)

        print("\n3. Iniciando dashboard...")
        print("WEB: El dashboard estara disponible en: http://localhost:8050")
        print("INFO: Presiona Ctrl+C para detener")

        try:
            # Configurar modo demo
            os.environ["MODO_OPERACION"] = "DEMO"
            # Ejecutar dashboard
            run_command("python app_demo.py", "Ejecutando dashboard demo")

        except KeyboardInterrupt:
            print("\n[STOP] Deteniendo servicios...")
        finally:
            # Detener simulación
            try:
                sim_process.terminate()
                sim_process.wait(timeout=5)
                print("[OK] Simulacion detenida")
            except:
                sim_process.kill()
                print("[WARN] Simulacion forzadamente detenida")

if __name__ == "__main__":
    main()