"""
Generador de Base de Datos Demo para Panel Dash
Crea una base de datos SQLite con datos ficticios para simular producción
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
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
            {"codigo": "CSG001", "nombre": "Campo Verde Ltda."},
            {"codigo": "CSG002", "nombre": "Hacienda del Valle"},
            {"codigo": "CSG003", "nombre": "Agrícola Los Andes"},
            {"codigo": "CSG004", "nombre": "Frutícola Patagonia"},
            {"codigo": "CSG005", "nombre": "Campo Norte S.A."},
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

        def _build_shift_records(count, start_dt, end_dt, start_index, partial_last):
            records = []
            if count <= 0:
                return records
            total_seconds = max(0, int((end_dt - start_dt).total_seconds()))
            if partial_last and count > 1:
                end_prev = end_dt - timedelta(minutes=45)
                if end_prev < start_dt:
                    end_prev = start_dt
                prev_seconds = max(0, int((end_prev - start_dt).total_seconds()))
                step = prev_seconds / float(count - 2) if count - 2 > 0 and prev_seconds > 0 else 0
                times = [start_dt + timedelta(seconds=int(round(i * step))) for i in range(count - 1)]
                last_time = end_dt - timedelta(minutes=30)
                if last_time < start_dt:
                    last_time = start_dt
                times.append(last_time)
            elif count == 1:
                times = [end_dt]
            else:
                step = total_seconds / float(count - 1) if total_seconds > 0 else 0
                times = [start_dt + timedelta(seconds=int(round(i * step))) for i in range(count)]
            for i, fecha_lectura in enumerate(times):
                idx = start_index + i
                lote_num = f"{1000 + idx:04d}"
                proveedor = self.proveedores[idx % len(self.proveedores)]
                producto = self.empresa_config["productos"][idx % len(self.empresa_config["productos"])]
                proceso = self.empresa_config["procesos"][idx % len(self.empresa_config["procesos"])]
                variedad = producto["variedades"][idx % len(producto["variedades"])]

                unidades_planificadas = 50 + ((idx * 13) % 151)  # 50-200
                if partial_last and i == len(times) - 1:
                    unidades_vaciadas = int(unidades_planificadas * 0.5)
                    # Inicio teorico del lote actual (cercano al presente, sin actualizarse luego)
                    fecha_lectura = times[-1]
                else:
                    unidades_vaciadas = unidades_planificadas

                unidades_restantes = unidades_planificadas - unidades_vaciadas

                peso_promedio_kg = 1.5  # fijo para consistencia
                peso_netto = unidades_vaciadas * peso_promedio_kg * 1000  # gramos

                records.append({
                    "codigo_proveedor": proveedor["codigo"],
                    "proveedor_nombre": proveedor["nombre"],
                    "codigo_proceso": proceso["codigo"],
                    "codigo_lote": lote_num,
                    "unidades_planificadas": unidades_planificadas,
                    "unidades_vaciadas": unidades_vaciadas,
                    "unidades_restantes": unidades_restantes,
                    "variedad": variedad,
                    "peso_netto": peso_netto,
                    "fecha_lectura": fecha_lectura,
                    "producto_codigo": producto["codigo"],
                    "exportador_nombre": self.exportadores[idx % len(self.exportadores)]["nombre"],
                })
            return records

        now = datetime.now()
        day_start = datetime.combine(now.date(), datetime.strptime("07:00", "%H:%M").time())
        day_end = datetime.combine(now.date(), datetime.strptime("17:00", "%H:%M").time())
        night_start = datetime.combine(now.date(), datetime.strptime("17:30", "%H:%M").time())
        night_end = datetime.combine(now.date(), datetime.strptime("04:00", "%H:%M").time())

        # Determinar turno actual
        t = now.time()
        is_night = t >= night_start.time() or t < night_end.time()

        lotes_data = []
        idx = 0

        if is_night:
            if t < night_end.time():
                # Noche que comenzo ayer
                cur_start = night_start - timedelta(days=1)
                cur_end = now
                # Dia previo completo
                prev_day_start = day_start - timedelta(days=1)
                prev_day_end = day_end - timedelta(days=1)
                lotes_data += _build_shift_records(10, prev_day_start, prev_day_end, idx, partial_last=False)
                idx += 10
            else:
                # Noche que comienza hoy
                cur_start = night_start
                cur_end = now
                # Dia de hoy completo
                lotes_data += _build_shift_records(10, day_start, day_end, idx, partial_last=False)
                idx += 10
            lotes_data += _build_shift_records(8, cur_start, cur_end, idx, partial_last=True)
            idx += 8
        else:
            # Turno dia en curso
            cur_start = day_start
            cur_end = now
            # Noche anterior completa
            prev_night_start = night_start - timedelta(days=1)
            prev_night_end = night_end
            lotes_data += _build_shift_records(8, prev_night_start, prev_night_end, idx, partial_last=False)
            idx += 8
            lotes_data += _build_shift_records(10, cur_start, cur_end, idx, partial_last=True)
            idx += 10

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

        # Calcular fecha del turno
        if turno_actual == 2 and now.hour < 8:
            business_date = (now - timedelta(days=1)).date()
            turno_inicio = datetime.combine(business_date, datetime.strptime("20:00", "%H:%M").time())
        else:
            business_date = now.date()
            turno_inicio = datetime.combine(business_date, datetime.strptime("08:00" if turno_actual == 1 else "20:00", "%H:%M").time())

        # Generar datos realistas del turno
        horas_transcurridas = (now - turno_inicio).total_seconds() / 3600
        if horas_transcurridas < 0:
            horas_transcurridas = 0

        # Estimaciones por hora (reducidas para pruebas más rápidas)
        cajas_por_hora = random.randint(20, 60)  # Reducido de 50-150 a 20-60
        kg_por_hora = cajas_por_hora * random.uniform(1.0, 2.0)

        # Totales acumulados
        cajas_totales = int(cajas_por_hora * horas_transcurridas)
        kg_totales = kg_por_hora * horas_transcurridas

        # Simular algunos minutos de detención
        fermo_minuti = random.uniform(0, 30) if random.random() < 0.3 else 0

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
        """Generar datos históricos para análisis de tendencias"""
        cursor = self.conn.cursor()

        # Limpiar datos históricos
        cursor.execute("DELETE FROM VW_MON_Partita_Storico_Agent")

        now = datetime.now()

        for i in range(num_records):
            # Generar datos históricos aleatorios
            dias_atras = random.randint(1, 90)
            fecha_base = now - timedelta(days=dias_atras)

            lote_num = f"{random.randint(1000, 9999):04d}"
            proceso = random.choice(self.empresa_config["procesos"])["codigo"]

            # Duración del lote (30 min a 4 horas)
            duracion_minutos = random.randint(30, 240)
            inicio = fecha_base - timedelta(minutes=random.randint(0, 480))
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
        # #region agent log
        import json
        log_path = r"c:\Users\rza_w\Documents\Frutisima\Panel_dash\.cursor\debug.log"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"demo_db_generator.py:update_production_data:entry","message":"Update production data called","data":{"incrementar_progreso":incrementar_progreso},"timestamp":int(time.time()*1000)}) + "\n")
                f.flush()
        except: pass
        # #endregion
        cursor = self.conn.cursor()

        # Obtener lote actual
        cursor.execute("""
            SELECT ProduttoreDescrizione, VarietaDescrizione, ProcessoCodice, LottoCodice,
                   UnitaPianificate, UnitaSvuotate, PesoNetto
            FROM VW_MON_Partita_Corrente
            ORDER BY DataAcquisizione DESC LIMIT 1
        """)
        row = cursor.fetchone()

        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"demo_db_generator.py:update_production_data:row_fetched","message":"Row fetched from DB","data":{"row_found":row is not None,"unidades_planificadas":row[4] if row else None,"unidades_actuales":row[5] if row else None,"peso_actual":row[6] if row else None},"timestamp":int(time.time()*1000)}) + "\n")
                f.flush()
        except: pass
        # #endregion

        if row:
            unidades_planificadas = row[4]
            unidades_actuales = row[5]
            peso_actual = row[6]

            if incrementar_progreso and unidades_actuales < unidades_planificadas:
                # Incrementar progreso (simular producción) - incremento mayor para pruebas más rápidas
                incremento_cajas = random.randint(2, 8)  # Aumentado de 1-5 a 2-8 para avanzar más rápido
                nuevas_unidades = min(unidades_actuales + incremento_cajas, unidades_planificadas)

                # Calcular nuevo peso basado en el peso por caja original (mantener consistencia)
                # Obtener peso por caja del peso actual y unidades actuales
                if unidades_actuales > 0 and peso_actual > 0:
                    kg_por_caja = (peso_actual / 1000) / unidades_actuales  # kg por caja
                else:
                    # Si no hay datos previos, usar un valor fijo razonable
                    kg_por_caja = 1.2  # kg por caja promedio
                
                nuevo_peso = nuevas_unidades * kg_por_caja * 1000  # en gramos

                # #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"demo_db_generator.py:update_production_data:before_update","message":"Before update","data":{"unidades_actuales":unidades_actuales,"nuevas_unidades":nuevas_unidades,"incremento_cajas":incremento_cajas,"kg_por_caja":kg_por_caja,"nuevo_peso_gramos":nuevo_peso,"lote_codice":row[3]},"timestamp":int(time.time()*1000)}) + "\n")
                        f.flush()
                except: pass
                # #endregion

                # Actualizar datos actuales
                cursor.execute("""
                    UPDATE VW_MON_Partita_Corrente
                    SET UnitaSvuotate = ?, PesoNetto = ?, DataAcquisizione = ?
                    WHERE LottoCodice = ?
                """, (nuevas_unidades, nuevo_peso, datetime.now(), row[3]))

                # También actualizar en VW_LottiIngresso (mantener exportador existente)
                # Calcular peso total del lote (basado en unidades planificadas)
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

                # #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"demo_db_generator.py:update_production_data:after_update","message":"After update","data":{"nuevas_unidades":nuevas_unidades,"peso_total_lote_gramos":peso_total_lote,"update_success":True},"timestamp":int(time.time()*1000)}) + "\n")
                        f.flush()
                except: pass
                # #endregion
            else:
                # #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"demo_db_generator.py:update_production_data:no_update","message":"No update needed","data":{"incrementar_progreso":incrementar_progreso,"unidades_actuales":unidades_actuales,"unidades_planificadas":unidades_planificadas,"condition_met":incrementar_progreso and unidades_actuales < unidades_planificadas},"timestamp":int(time.time()*1000)}) + "\n")
                        f.flush()
                except: pass
                # #endregion

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
