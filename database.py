"""
Módulo de configuración de conexiones a la base de datos
"""
import pyodbc

# Configuración de la base de datos
server = '192.168.10.4'
database = 'UNITEC_DB_UNIREPORT'
database_unitec = 'UNITEC_DB'
username = 'sa'
password = 'FS-Km171/'

# Timeouts (evita "pegados" largos por conexiones/consultas colgadas)
CONNECT_TIMEOUT_S = 5
QUERY_TIMEOUT_S = 12

# Cadena de conexión para UNITEC_DB_UNIREPORT
connection_string = f"""
DRIVER={{ODBC Driver 18 for SQL Server}};
SERVER={server};
DATABASE={database};
UID={username};
PWD={password};
Encrypt=no;
"""

# Cadena de conexión para UNITEC_DB
connection_string_unitec = f"""
DRIVER={{ODBC Driver 18 for SQL Server}};
SERVER={server};
DATABASE={database_unitec};
UID={username};
PWD={password};
Encrypt=no;
"""

def get_connection():
    """Obtiene una conexión a la base de datos UNITEC_DB_UNIREPORT"""
    conn = pyodbc.connect(connection_string, timeout=CONNECT_TIMEOUT_S)
    conn.timeout = QUERY_TIMEOUT_S
    return conn

def get_connection_unitec():
    """Obtiene una conexión a la base de datos UNITEC_DB"""
    conn = pyodbc.connect(connection_string_unitec, timeout=CONNECT_TIMEOUT_S)
    conn.timeout = QUERY_TIMEOUT_S
    return conn

