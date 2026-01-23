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
    return pyodbc.connect(connection_string)

def get_connection_unitec():
    """Obtiene una conexión a la base de datos UNITEC_DB"""
    return pyodbc.connect(connection_string_unitec)

