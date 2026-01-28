"""
Generador de Base de Datos Demo para Panel Dash
Crea una base de datos SQLite con datos ficticios para simular producción
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

DEMO_FIXED_CAJAS_TOTALES = 200
DEMO_FIXED_CAJAS_VACIADAS = 0
DEMO_FIXED_KG_TOTALES = 4000
DEMO_FIXED_KG_POR_HORA = 12000
DEMO_FIXED_CAJAS_STEP = 1

class DemoDatabaseGenerator:
    def __init__(self, db_path="demo_database.db"):
        self.db_path = db_path
        self.conn = None

        # Configuración de empresa ficticia
        self.empresa_config = {
            "nombre": "AgroIndustria XYZ S.A.",
            "productos": [
                {"codigo": "MANZANA", "nombre": "Manzana Gala", "variedades": ["Gala Roja", "Gala Verde", "Gala Premium"]},
                {"codigo": "PERA", "nombre": "Pera Williams", "variedades": ["Williams", "Packham", "Tardía"]},
                {"codigo": "CEREZA", "nombre": "Cereza", "variedades": ["Bing", "Rainier", "Sweetheart"]},
                {"codigo": "UVA", "nombre": "Uva", "variedades": ["Thompson", "Red Globe", "Flame"]},
            ],
            "procesos": [
                {"codigo": "CAL001", "nombre": "Calibrado Línea 1"},
                {"codigo": "CAL002", "nombre": "Calibrado Línea 2"},
                {"codigo": "CAL003", "nombre": "Calibrado Línea 3"},
                {"codigo": "EMP001", "nombre": "Empacado Automático"},
                {"codigo": "EMP002", "nombre": "Empacado Manual"},
            ]
        }

        # Datos maestros
        self.proveedores = [
            {"codigo": "CSG001", "nombre": "ValleVerde Ltda."},
            {"codigo": "CSG002", "nombre": "Hacienda Central"},
            {"codigo": "CSG003", "nombre": "Andes Produce"},
            {"codigo": "CSG004", "nombre": "AgroPatagonia Sur"},
            {"codigo": "CSG005", "nombre": "NorteFruit SpA"},
        ]

        self.exportadores = [
            {"id": 1, "nombre": "Exportadora Global S.A."},
            {"id": 2, "nombre": "Frutas del Mundo Ltda."},
            {"id": 3, "nombre": "AgroExport Premium"},
            {"id": 4, "nombre": "International Fruits Corp."},
            {"id": 5, "nombre": "Premium Produce Export"},
        ]

    def create_connection(self):
        """Crear conexión a la base de datos"""
        self.conn = sqlite3.connect(self.db_path)
        return self.conn

    def create_tables(self):
        """Crear todas las tablas necesarias"""
        queries = [
            # Tabla de productores (ANA_Produttore)
            """
            CREATE TABLE IF NOT EXISTS ANA_Produttore (
                PRO_Codice_Produttore TEXT PRIMARY KEY,
                PRO_Produttore TEXT NOT NULL
            )
            """,

            # Tabla de exportadores (ANA_Esportatore)
            """
            CREATE TABLE IF NOT EXISTS ANA_Esportatore (
                ESP_ID INTEGER PRIMARY KEY,
                ESP_Esportatore TEXT NOT NULL
            )
            """,

            # Tabla de lotes (PROD_Lotto)
            """
            CREATE TABLE IF NOT EXISTS PROD_Lotto (
                LOT_ID INTEGER PRIMARY KEY,
                LOT_Codice_Lotto TEXT NOT NULL,
                LOT_Data_Inizio DATETIME,
                LOT_Data_Fine DATETIME
            )
            """,

            # Tabla de unidades de salida (PROD_Unita_OUT)
            """
            CREATE TABLE IF NOT EXISTS PROD_Unita_OUT (
                UOUT_ID INTEGER PRIMARY KEY,
                UOUT_Lotto_FK INTEGER,
                UOUT_Esportatore_FK INTEGER,
                UOUT_Data_Lettura DATETIME,
                FOREIGN KEY (UOUT_Lotto_FK) REFERENCES PROD_Lotto (LOT_ID),
                FOREIGN KEY (UOUT_Esportatore_FK) REFERENCES ANA_Esportatore (ESP_ID)
            )
            """,

            # Vista de lotes de ingreso (VW_LottiIngresso)
            """
            CREATE TABLE IF NOT EXISTS VW_LottiIngresso (
                CodiceProduttore TEXT,
                CodiceProcesso TEXT,
                CodiceLotto TEXT,
                UnitaPianificate INTEGER,
                UnitaIn INTEGER,
                UnitaRestanti INTEGER,
                Varieta TEXT,
                PesoNetto REAL,
                DataLettura DATETIME,
                ProductorNombre TEXT,
                EsportatoreDescrizione TEXT
            )
            """,

            # Vista de partida corriente (VW_MON_Partita_Corrente)
            """
            CREATE TABLE IF NOT EXISTS VW_MON_Partita_Corrente (
                ProduttoreDescrizione TEXT,
                VarietaDescrizione TEXT,
                ProcessoCodice TEXT,
                LottoCodice TEXT,
                UnitaPianificate INTEGER,
                UnitaSvuotate INTEGER,
                PesoNetto REAL,
                DataAcquisizione DATETIME,
                EsportatoreDescrizione TEXT
            )
            """,

            # Vista de productividad por turno (VW_MON_Produttivita_Turno_Corrente)
            """
            CREATE TABLE IF NOT EXISTS VW_MON_Produttivita_Turno_Corrente (
                TurnoCodice INTEGER,
                TurnoGiornaliero DATE,
                TurnoInizio DATETIME,
                PesoSvuotato REAL,
                PesoSvuotatoOra REAL,
                UnitaSvuotate INTEGER,
                UnitaSvuotateOra INTEGER,
                FermoMacchinaMinuti REAL,
                DataAcquisizione DATETIME
            )
            """,

            # Vista histórica de partida (VW_MON_Partita_Storico_Agent)
            """
            CREATE TABLE IF NOT EXISTS VW_MON_Partita_Storico_Agent (
                ProcessoCodice TEXT,
                LottoCodice TEXT,
                LottoInizio DATETIME,
                LottoFine DATETIME,
                DataAcquisizione DATETIME
            )
            """
        ]

        cursor = self.conn.cursor()
        for query in queries:
            cursor.execute(query)
        self.conn.commit()

    def populate_master_data(self):
        """Poblar datos maestros (proveedores, exportadores)"""
        # Insertar proveedores
        cursor = self.conn.cursor()
        for proveedor in self.proveedores:
            cursor.execute("""
                INSERT OR REPLACE INTO ANA_Produttore (PRO_Codice_Produttore, PRO_Produttore)
                VALUES (?, ?)
            """, (proveedor["codigo"], proveedor["nombre"]))

        # Insertar exportadores
        for exportador in self.exportadores:
            cursor.execute("""
                INSERT OR REPLACE INTO ANA_Esportatore (ESP_ID, ESP_Esportatore)
                VALUES (?, ?)
            """, (exportador["id"], exportador["nombre"]))

        self.conn.commit()


    def generate_lot_data(self, num_lotes=50):
        """Generar datos de lotes para simulacion (determinista, sin aleatoriedad)."""
        cursor = self.conn.cursor()

        # Limpiar datos existentes
        cursor.execute("DELETE FROM VW_LottiIngresso")
        cursor.execute("DELETE FROM VW_MON_Partita_Corrente")
        cursor.execute("DELETE FROM VW_MON_Partita_Storico_Agent")
        cursor.execute("DELETE FROM PROD_Lotto")
        cursor.execute("DELETE FROM PROD_Unita_OUT")

        def _build_fixed_shift_records(shift_date, shift_type):
            if shift_type == "day":
                rows = [
                    ("07:00", "CSG004", "AgroPatagonia Sur", "EMP001", "1008", 154, 9702, "Gala Premium"),
                    ("08:00", "CSG005", "NorteFruit SpA", "EMP002", "1009", 167, 10521, "Williams"),
                    ("09:00", "CSG001", "ValleVerde Ltda.", "CAL001", "1010", 180, 11340, "Rainier"),
                    ("10:00", "CSG002", "Hacienda Central", "CAL002", "1011", 193, 12159, "Flame"),
                    ("11:00", "CSG003", "Andes Produce", "CAL003", "1012", 55, 3465, "Gala Roja"),
                    ("12:00", "CSG004", "AgroPatagonia Sur", "EMP001", "1013", 68, 4284, "Packham"),
                    ("13:00", "CSG005", "NorteFruit SpA", "EMP002", "1014", 81, 5103, "Sweetheart"),
                    ("14:00", "CSG001", "ValleVerde Ltda.", "CAL001", "1015", 94, 5922, "Thompson"),
                    ("15:00", "CSG002", "Hacienda Central", "CAL002", "1016", 107, 6741, "Gala Verde"),
                    ("16:00", "CSG003", "Andes Produce", "CAL003", "1017", 120, 7560, "Tardía"),
                ]
            else:
                rows = [
                    ("17:00", "CSG004", "AgroPatagonia Sur", "EMP001", "1008", 158, 9986, "Gala Premium"),
                    ("18:05", "CSG005", "NorteFruit SpA", "EMP002", "1009", 163, 10236, "Williams"),
                    ("19:10", "CSG001", "ValleVerde Ltda.", "CAL001", "1010", 176, 11176, "Rainier"),
                    ("20:15", "CSG002", "Hacienda Central", "CAL002", "1011", 189, 11888, "Flame"),
                    ("21:10", "CSG003", "Andes Produce", "CAL003", "1012", 58, 3619, "Gala Roja"),
                    ("22:05", "CSG004", "AgroPatagonia Sur", "EMP001", "1013", 71, 4480, "Packham"),
                    ("23:00", "CSG005", "NorteFruit SpA", "EMP002", "1014", 79, 4945, "Sweetheart"),
                    ("00:20", "CSG001", "ValleVerde Ltda.", "CAL001", "1015", 97, 6111, "Thompson"),
                    ("01:55", "CSG002", "Hacienda Central", "CAL002", "1016", 104, 6594, "Gala Verde"),
                    ("03:25", "CSG003", "Andes Produce", "CAL003", "1017", 116, 7274, "Tardía"),
                ]

            records = []
            for row in rows:
                time_str, codigo_proveedor, proveedor_nombre, codigo_proceso, codigo_lote, cajas, kg, variedad = row
                base_date = shift_date
                hora = datetime.strptime(time_str, "%H:%M").time()
                if shift_type == "night" and hora < datetime.strptime("07:00", "%H:%M").time():
                    base_date = shift_date + timedelta(days=1)
                fecha_lectura = datetime.combine(base_date, hora)
                peso_netto = float(kg) * 1000
                unidades_planificadas = int(cajas)
                unidades_vaciadas = int(cajas)
                unidades_restantes = 0
                exportador_nombre = self.exportadores[(int(codigo_lote) - 1000) % len(self.exportadores)]["nombre"]
                records.append({
                    "codigo_proveedor": codigo_proveedor,
                    "proveedor_nombre": proveedor_nombre,
                    "codigo_proceso": codigo_proceso,
                    "codigo_lote": codigo_lote,
                    "unidades_planificadas": unidades_planificadas,
                    "unidades_vaciadas": unidades_vaciadas,
                    "unidades_restantes": unidades_restantes,
                    "variedad": variedad,
                    "peso_netto": peso_netto,
                    "fecha_lectura": fecha_lectura,
                    "producto_codigo": None,
                    "exportador_nombre": exportador_nombre,
                })
            return records

        now = datetime.now()
        t = now.time()
        day_start_time = datetime.strptime("07:00", "%H:%M").time()
        night_start_time = datetime.strptime("17:00", "%H:%M").time()

        if t >= day_start_time and t < night_start_time:
            shift_type = "day"
            shift_date = now.date()
        else:
            shift_type = "night"
            shift_date = now.date() if t >= night_start_time else (now - timedelta(days=1)).date()

        lotes_data = _build_fixed_shift_records(shift_date, shift_type)

        for lote_data in lotes_data:
            cursor.execute("""
                INSERT INTO VW_LottiIngresso
                (CodiceProduttore, CodiceProcesso, CodiceLotto, UnitaPianificate,
                 UnitaIn, UnitaRestanti, Varieta, PesoNetto, DataLettura, ProductorNombre, EsportatoreDescrizione)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lote_data["codigo_proveedor"],
                lote_data["codigo_proceso"],
                lote_data["codigo_lote"],
                lote_data["unidades_planificadas"],
                lote_data["unidades_vaciadas"],
                lote_data["unidades_restantes"],
                lote_data["variedad"],
                lote_data["peso_netto"],
                lote_data["fecha_lectura"],
                lote_data["proveedor_nombre"],
                lote_data["exportador_nombre"],
            ))

            cursor.execute("""
                INSERT INTO PROD_Lotto (LOT_Codice_Lotto, LOT_Data_Inizio)
                VALUES (?, ?)
            """, (lote_data["codigo_lote"], lote_data["fecha_lectura"]))

            lote_id = cursor.lastrowid
            exportador = self.exportadores[(int(lote_data["codigo_lote"]) - 1000) % len(self.exportadores)]
            cursor.execute("""
                INSERT INTO PROD_Unita_OUT (UOUT_Lotto_FK, UOUT_Esportatore_FK, UOUT_Data_Lettura)
                VALUES (?, ?, ?)
            """, (lote_id, exportador["id"], lote_data["fecha_lectura"]))

        self.conn.commit()
        return lotes_data

    def generate_current_production_data(self, lote_actual=None):
        """Generar datos de producción actual (simula VW_MON_Partita_Corrente)"""
        cursor = self.conn.cursor()

        # Limpiar datos actuales
        cursor.execute("DELETE FROM VW_MON_Partita_Corrente")

        if lote_actual:
            # Usar lote específico
            lote = lote_actual
        else:
            # Obtener el lote MÁS RECIENTE (no aleatorio) para mostrar datos actuales
            cursor.execute("""
                SELECT CodiceProduttore, CodiceProcesso, CodiceLotto, UnitaPianificate,
                       UnitaIn, Varieta, PesoNetto, ProductorNombre, EsportatoreDescrizione
                FROM VW_LottiIngresso
                ORDER BY DataLettura DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                lote = {
                    "codigo_proveedor": row[0],
                    "codigo_proceso": row[1],
                    "codigo_lote": row[2],
                    "unidades_planificadas": row[3],
                    "unidades_vaciadas": row[4],
                    "variedad": row[5],
                    "peso_netto": row[6],
                    "proveedor_nombre": row[7],
                    "exportador_nombre": row[8] if len(row) > 8 else self.exportadores[0]["nombre"]
                }
            else:
                # Datos por defecto si no hay lotes (cantidades reducidas)
                lote = {
                    "codigo_proveedor": "CSG001",
                    "codigo_proceso": "CAL001",
                    "codigo_lote": "0001",
                    "unidades_planificadas": DEMO_FIXED_CAJAS_TOTALES,
                    "unidades_vaciadas": DEMO_FIXED_CAJAS_VACIADAS,
                    "variedad": "Gala Roja",
                    "peso_netto": DEMO_FIXED_KG_TOTALES * 1000,
                    "proveedor_nombre": "Campo Verde Ltda."
                }

        # Obtener exportador (del lote o determinista si no existe)
        exportador_nombre = lote.get("exportador_nombre") or self.exportadores[0]["nombre"]
        
        # Insertar datos actuales
        cursor.execute("""
            INSERT INTO VW_MON_Partita_Corrente
            (ProduttoreDescrizione, VarietaDescrizione, ProcessoCodice, LottoCodice,
             UnitaPianificate, UnitaSvuotate, PesoNetto, DataAcquisizione, EsportatoreDescrizione)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lote["proveedor_nombre"],
            lote["variedad"],
            lote["codigo_proceso"],
            lote["codigo_lote"],
            lote["unidades_planificadas"],
            lote["unidades_vaciadas"],
            lote["peso_netto"],
            datetime.now(),
            exportador_nombre
        ))

        self.conn.commit()
        return lote

    def generate_turno_data(self, turno_actual=1):
        """Generar datos de productividad por turno"""
        cursor = self.conn.cursor()

        # Limpiar datos actuales
        cursor.execute("DELETE FROM VW_MON_Produttivita_Turno_Corrente")

        now = datetime.now()

        t = now.time()
        day_start_time = datetime.strptime("07:00", "%H:%M").time()
        night_start_time = datetime.strptime("17:00", "%H:%M").time()

        if t >= day_start_time and t < night_start_time:
            turno_actual = 1
            business_date = now.date()
            turno_inicio = datetime.combine(business_date, day_start_time)
            cajas_totales = 1219
            kg_totales = 76797
            cajas_por_hora = 122
            kg_por_hora = 7680
            fermo_minuti = 0
        else:
            turno_actual = 2
            business_date = now.date() if t >= night_start_time else (now - timedelta(days=1)).date()
            turno_inicio = datetime.combine(business_date, night_start_time)
            cajas_totales = 1211
            kg_totales = 76308
            cajas_por_hora = 110
            kg_por_hora = 6937
            fermo_minuti = 0

        cursor.execute("""
            INSERT INTO VW_MON_Produttivita_Turno_Corrente
            (TurnoCodice, TurnoGiornaliero, TurnoInizio, PesoSvuotato, PesoSvuotatoOra,
             UnitaSvuotate, UnitaSvuotateOra, FermoMacchinaMinuti, DataAcquisizione)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            turno_actual,
            business_date,
            turno_inicio,
            kg_totales,
            kg_por_hora,
            cajas_totales,
            cajas_por_hora,
            fermo_minuti,
            now
        ))

        self.conn.commit()

    def generate_historic_data(self, num_records=100):
        """Generar datos históricos para análisis de tendencias (determinista)."""
        cursor = self.conn.cursor()

        # Limpiar datos históricos
        cursor.execute("DELETE FROM VW_MON_Partita_Storico_Agent")

        now = datetime.now()

        for i in range(num_records):
            dias_atras = (i % 90) + 1
            fecha_base = now - timedelta(days=dias_atras)

            lote_num = f"{1000 + (i % 9000):04d}"
            proceso = self.empresa_config["procesos"][i % len(self.empresa_config["procesos"])]["codigo"]

            duracion_minutos = 30 + ((i * 13) % 211)
            inicio = fecha_base - timedelta(minutes=(i * 17) % 480)
            fin = inicio + timedelta(minutes=duracion_minutos)

            cursor.execute("""
                INSERT INTO VW_MON_Partita_Storico_Agent
                (ProcessoCodice, LottoCodice, LottoInizio, LottoFine, DataAcquisizione)
                VALUES (?, ?, ?, ?, ?)
            """, (proceso, lote_num, inicio, fin, fecha_base))

        self.conn.commit()

    def create_database(self):
        """Crear la base de datos completa con datos iniciales"""
        print("[DB] Creando base de datos demo...")

        self.create_connection()
        self.create_tables()
        print("[OK] Tablas creadas")

        self.populate_master_data()
        print("[OK] Datos maestros insertados")

        self.generate_lot_data()
        print("[OK] Datos de lotes generados")

        self.generate_current_production_data()
        print("[OK] Datos de produccion actual generados")

        self.generate_turno_data()
        print("[OK] Datos de turno generados")

        self.generate_historic_data()
        print("[OK] Datos historicos generados")

        print("[SUCCESS] Base de datos demo creada exitosamente!")
        print(f"[PATH] Ubicacion: {self.db_path}")

    def update_production_data(self, lote_actual=None, incrementar_progreso=True):
        """Actualizar datos de producción para simular cambios en tiempo real"""
        cursor = self.conn.cursor()

        # Obtener lote actual
        cursor.execute("""
            SELECT ProduttoreDescrizione, VarietaDescrizione, ProcessoCodice, LottoCodice,
                   UnitaPianificate, UnitaSvuotate, PesoNetto
            FROM VW_MON_Partita_Corrente
            ORDER BY DataAcquisizione DESC LIMIT 1
        """)
        row = cursor.fetchone()

        if row:
            unidades_planificadas = row[4]
            unidades_actuales = row[5]
            peso_actual = row[6]
            # Obtener peso total del lote desde VW_LottiIngresso para mantener rango realista
            try:
                cursor.execute(
                    """
                    SELECT PesoNetto
                    FROM VW_LottiIngresso
                    WHERE CodiceLotto = ? AND CodiceProcesso = ?
                    ORDER BY DataLettura DESC LIMIT 1
                    """,
                    (row[3], row[2]),
                )
                row_total = cursor.fetchone()
                peso_total_lote = float(row_total[0]) if row_total and row_total[0] is not None else None
            except Exception:
                peso_total_lote = None

            if incrementar_progreso and unidades_actuales < unidades_planificadas:
                # Incrementar progreso (simular producción) - incremento mayor para pruebas más rápidas
                incremento_cajas = DEMO_FIXED_CAJAS_STEP
                nuevas_unidades = min(unidades_actuales + incremento_cajas, unidades_planificadas)

                # Calcular peso por caja basado en el peso total del lote
                if peso_total_lote and unidades_planificadas > 0:
                    kg_por_caja = (peso_total_lote / 1000) / unidades_planificadas
                elif unidades_actuales > 0 and peso_actual > 0:
                    kg_por_caja = (peso_actual / 1000) / unidades_actuales  # kg por caja
                else:
                    kg_por_caja = 1.2  # kg por caja promedio
                
                nuevo_peso = nuevas_unidades * kg_por_caja * 1000  # en gramos

                # Actualizar datos actuales
                cursor.execute("""
                    UPDATE VW_MON_Partita_Corrente
                    SET UnitaSvuotate = ?, PesoNetto = ?, DataAcquisizione = ?
                    WHERE LottoCodice = ?
                """, (nuevas_unidades, nuevo_peso, datetime.now(), row[3]))

                # Tambien actualizar en VW_LottiIngresso (mantener exportador existente)
                # Mantener el peso total del lote en el rango definido
                if peso_total_lote is None and unidades_planificadas > 0:
                    peso_total_lote = unidades_planificadas * kg_por_caja * 1000  # en gramos
                cursor.execute("""
                    UPDATE VW_LottiIngresso
                    SET UnitaIn = ?, UnitaRestanti = ?, PesoNetto = ?
                    WHERE CodiceLotto = ? AND CodiceProcesso = ?
                """, (
                    nuevas_unidades,
                    unidades_planificadas - nuevas_unidades,
                    peso_total_lote,
                    row[3],
                    row[2]
                ))
            else:
                pass

        self.conn.commit()

    def change_to_next_lote(self):
        """Cambiar al siguiente lote para simular rotación de producción"""
        # Obtener un lote diferente al actual
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT CodiceProduttore, CodiceProcesso, CodiceLotto, UnitaPianificate,
                   UnitaIn, Varieta, PesoNetto, ProductorNombre
            FROM VW_LottiIngresso
            WHERE UnitaRestanti > 0
            ORDER BY DataLettura DESC LIMIT 1
        """)
        row = cursor.fetchone()

        if row:
            lote_nuevo = {
                "codigo_proveedor": row[0],
                "codigo_proceso": row[1],
                "codigo_lote": row[2],
                "unidades_planificadas": row[3],
                "unidades_vaciadas": row[4],
                "variedad": row[5],
                "peso_netto": row[6],
                "proveedor_nombre": row[7]
            }

            self.generate_current_production_data(lote_nuevo)
            print(f"[CHANGE] Cambiado a lote: {lote_nuevo['codigo_lote']} - {lote_nuevo['proveedor_nombre']}")
            return lote_nuevo

        return None

    def close_connection(self):
        """Cerrar conexión a la base de datos"""
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    # Crear base de datos demo
    generator = DemoDatabaseGenerator()
    generator.create_database()
    generator.close_connection()

    print("\n[INFO] Para usar la base de datos demo:")
    print("   2. Actualiza las consultas SQL si es necesario")
    print("   3. Ejecuta el dashboard con los datos ficticios")
