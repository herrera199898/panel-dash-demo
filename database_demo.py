"""
Módulo de configuración de conexiones a la base de datos - VERSIÓN DEMO
Conexión a SQLite para datos ficticios
"""
import sqlite3
import os

# Configuración de la base de datos demo
demo_db_path = os.path.join(os.path.dirname(__file__), "demo_database.db")

# Timeouts (simulados para compatibilidad)
CONNECT_TIMEOUT_S = 5
QUERY_TIMEOUT_S = 12

def get_connection():
    """Obtiene una conexión a la base de datos demo (SQLite)"""
    # Crear la base de datos si no existe
    if not os.path.exists(demo_db_path):
        print("[DB] Base de datos demo no encontrada. Creandola...")
        from demo_db_generator import DemoDatabaseGenerator
        generator = DemoDatabaseGenerator(demo_db_path)
        generator.create_database()
        generator.close_connection()
        print("[OK] Base de datos demo creada")

    conn = sqlite3.connect(demo_db_path)
    # Configurar para que retorne filas como diccionarios
    conn.row_factory = sqlite3.Row
    # Si la base esta vacia o incompleta, regenerar datos demo
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM VW_LottiIngresso")
        count = cur.fetchone()[0]
        if count < 18:
            conn.close()
            print("[DB] Datos demo incompletos. Regenerando...")
            from demo_db_generator import DemoDatabaseGenerator
            generator = DemoDatabaseGenerator(demo_db_path)
            generator.create_database()
            generator.close_connection()
            conn = sqlite3.connect(demo_db_path)
            conn.row_factory = sqlite3.Row
    except Exception:
        conn.close()
        print("[DB] Error verificando datos demo. Regenerando...")
        from demo_db_generator import DemoDatabaseGenerator
        generator = DemoDatabaseGenerator(demo_db_path)
        generator.create_database()
        generator.close_connection()
        conn = sqlite3.connect(demo_db_path)
        conn.row_factory = sqlite3.Row
    return conn

def get_connection_unitec():
    """Obtiene una conexión a la base de datos UNITEC (simulada con SQLite)"""
    # En la demo, ambas conexiones apuntan a la misma BD
    return get_connection()

# Funciones de compatibilidad para mantener la misma interfaz
def close_connection(conn):
    """Cerrar conexión de forma segura"""
    if conn:
        conn.close()
