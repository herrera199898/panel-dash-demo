"""
Configuracion DEMO (solo SQLite con datos ficticios)
"""
import os

# Siempre DEMO
MODO_OPERACION = "DEMO"

# Simulacion en modo demo
# - "1": habilita actualizaciones automaticas en segundo plano
# - "0": deja los datos estaticos (no se actualizan solos)
DEMO_SIMULACION = os.environ.get("DEMO_SIMULACION", "0")


def get_database_config():
    """Retorna la configuracion de base de datos demo (SQLite)."""
    return {
        "type": "sqlite",
        "module": "database_demo",
        "description": "Base de datos demo (SQLite con datos ficticios)",
    }


def is_demo_mode():
    """Siempre True en este proyecto demo."""
    return True


def is_demo_simulation_enabled():
    """Retorna True si la simulacion demo esta habilitada."""
    return str(DEMO_SIMULACION).strip() in {"1", "true", "TRUE", "True"}


def get_status_info():
    """Retorna informacion del estado actual."""
    config = get_database_config()
    return {
        "modo": MODO_OPERACION,
        "tipo_bd": config["type"],
        "descripcion": config["description"],
        "modulo": config["module"],
    }


# Configuracion de la aplicacion
APP_CONFIG = {
    "title": "Panel Dash - AgroIndustria XYZ",
    "empresa": "AgroIndustria XYZ S.A.",
    "description": "Demo de Dashboard de Produccion",
}


if __name__ == "__main__":
    status = get_status_info()
    print("Configuracion del Panel Dash (DEMO)")
    print("=" * 40)
    print(f"Modo: {status['modo']}")
    print(f"Tipo BD: {status['tipo_bd']}")
    print(f"Descripcion: {status['descripcion']}")
    print(f"Modulo: {status['modulo']}")
    print()
    print(f"Empresa: {APP_CONFIG['empresa']}")
    print(f"Titulo: {APP_CONFIG['title']}")
    print()
    print("[START] Para iniciar simulacion en modo DEMO:")
    print("   set DEMO_SIMULACION=1 && python app_demo.py")
