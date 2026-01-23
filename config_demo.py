"""
Configuración para alternar entre modo REAL (SQL Server) y DEMO (SQLite)
"""
import os

# Modo de operación
# Cambia esta variable para alternar entre modos:
# - "REAL": Usa SQL Server (producción)
# - "DEMO": Usa SQLite con datos ficticios
MODO_OPERACION = os.environ.get("MODO_OPERACION", "DEMO").upper()

def get_database_config():
    """Retorna la configuración de base de datos según el modo"""
    if MODO_OPERACION == "REAL":
        # Configuración real (SQL Server)
        return {
            "type": "sqlserver",
            "module": "database",  # importa database.py
            "description": "Base de datos real (SQL Server)"
        }
    else:
        # Configuración demo (SQLite)
        return {
            "type": "sqlite",
            "module": "database_demo",  # importa database_demo.py
            "description": "Base de datos demo (SQLite con datos ficticios)"
        }

def is_demo_mode():
    """Retorna True si está en modo demo"""
    return MODO_OPERACION == "DEMO"

def get_status_info():
    """Retorna información del estado actual"""
    config = get_database_config()
    return {
        "modo": MODO_OPERACION,
        "tipo_bd": config["type"],
        "descripcion": config["description"],
        "modulo": config["module"]
    }

# Configuración de la aplicación
APP_CONFIG = {
    "title": "Panel Dash - AgroIndustria XYZ" if is_demo_mode() else "Panel Frutísima",
    "empresa": "AgroIndustria XYZ S.A." if is_demo_mode() else "Frutísima",
    "description": "Demo de Dashboard de Producción" if is_demo_mode() else "Panel de Control en Tiempo Real"
}

if __name__ == "__main__":
    # Mostrar configuración actual
    status = get_status_info()
    print("🔧 Configuración del Panel Dash")
    print("=" * 40)
    print(f"Modo: {status['modo']}")
    print(f"Tipo BD: {status['tipo_bd']}")
    print(f"Descripción: {status['descripcion']}")
    print(f"Módulo: {status['modulo']}")
    print()
    print(f"Empresa: {APP_CONFIG['empresa']}")
    print(f"Título: {APP_CONFIG['title']}")
    print()
    print("💡 Para cambiar de modo:")
    print("   - Modo REAL: set MODO_OPERACION=REAL")
    print("   - Modo DEMO: set MODO_OPERACION=DEMO (o dejar vacío)")
    print()
    print("[START] Para iniciar simulacion en modo DEMO:")
    print("   python demo_simulation.py --mode continuous")