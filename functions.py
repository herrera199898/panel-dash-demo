"""
Módulo de funciones para obtener datos de la base de datos
"""
import pandas as pd
import logging
import importlib

logger = logging.getLogger(__name__)
import plotly.graph_objects as go

# Importar configuración para determinar qué módulo de BD usar
try:
    from config_demo import get_database_config
    config_db = get_database_config()
    db_module_name = config_db["module"]
    # Importar dinámicamente el módulo correcto
    db_module = importlib.import_module(db_module_name)
    get_connection = db_module.get_connection
    get_connection_unitec = db_module.get_connection_unitec
except (ImportError, AttributeError):
    # Fallback a database.py si config_demo no está disponible
    from database import get_connection, get_connection_unitec

_EXPORTADOR_PLAN = None

def adapt_sql_query(query):
    """
    Adapta consultas SQL Server a SQLite
    Convierte SELECT TOP N a SELECT ... LIMIT N
    """
    try:
        from config_demo import is_demo_mode
        if is_demo_mode():
            # Convertir SELECT TOP N a LIMIT N
            import re
            # Patrón: SELECT TOP número
            pattern = r'SELECT\s+TOP\s+(\d+)\s+'
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                limit_num = match.group(1)
                # Reemplazar SELECT TOP N con SELECT
                query = re.sub(pattern, 'SELECT ', query, flags=re.IGNORECASE)
                # Agregar LIMIT al final (después de ORDER BY si existe, o al final)
                query_upper = query.upper()
                if 'ORDER BY' in query_upper:
                    # Encontrar la posición del último ORDER BY
                    order_by_pos = query_upper.rfind('ORDER BY')
                    # Encontrar el final de la cláusula ORDER BY (hasta el final o hasta WHERE/GROUP BY/HAVING antes)
                    # Simplemente agregar LIMIT al final
                    query = query.rstrip(';').rstrip() + f' LIMIT {limit_num}'
                else:
                    # Agregar LIMIT al final
                    query = query.rstrip(';').rstrip() + f' LIMIT {limit_num}'
        return query
    except Exception as e:
        logger.debug(f"Error adaptando query SQL: {e}")
        return query

def read_sql_adapted(query, conn, **kwargs):
    """
    Wrapper para pd.read_sql que adapta automáticamente consultas SQL Server a SQLite
    """
    adapted_query = adapt_sql_query(query)
    return pd.read_sql(adapted_query, conn, **kwargs)

def get_data():
    """Obtiene los últimos 50 registros de VW_MON_Partita_Corrente"""
    try:
        conn = get_connection()
        query = "SELECT TOP 50 * FROM VW_MON_Partita_Corrente ORDER BY 1 DESC"
        df = read_sql_adapted(query, conn)
        conn.close()
        return df
    except Exception as e:
        logger.exception("Error en get_data: %s", e)
        return None

def get_produttore_dict():
    """
    Obtiene un diccionario que relaciona el código del productor con su nombre real desde ANA_Produttore.
    Retorna: dict {codigo: nombre}
    """
    try:
        conn = get_connection_unitec()

        # Consulta optimizada (según tu esquema): PROD_Unita_OUT.UOUT_Lotto_FK -> PROD_Lotto.LOT_ID
        # y PROD_Unita_OUT.UOUT_Esportatore_FK -> ANA_Esportatore.ESP_ID
        try:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(lotto_variants))
            query_fast = f"""
            SELECT TOP 1 ana.ESP_Esportatore
            FROM PROD_Unita_OUT uout
            INNER JOIN PROD_Lotto lot ON uout.UOUT_Lotto_FK = lot.LOT_ID
            INNER JOIN ANA_Esportatore ana ON uout.UOUT_Esportatore_FK = ana.ESP_ID
            WHERE lot.LOT_Codice_Lotto IN ({placeholders})
              AND ana.ESP_Esportatore IS NOT NULL
              AND LTRIM(RTRIM(ana.ESP_Esportatore)) != ''
            """
            cursor.execute(query_fast, lotto_variants)
            row = cursor.fetchone()
            if row and row[0]:
                exportador = str(row[0]).strip()
                if exportador:
                    conn.close()
                    return exportador
        except Exception:
            # Fallback si LOT_Codice_Lotto no es texto o hay diferencias de esquema
            try:
                cursor = conn.cursor()
                placeholders = ",".join(["?"] * len(lotto_variants))
                query_fast2 = f"""
                SELECT TOP 1 ana.ESP_Esportatore
                FROM PROD_Unita_OUT uout
                INNER JOIN PROD_Lotto lot ON uout.UOUT_Lotto_FK = lot.LOT_ID
                INNER JOIN ANA_Esportatore ana ON uout.UOUT_Esportatore_FK = ana.ESP_ID
                WHERE LTRIM(RTRIM(CAST(lot.LOT_Codice_Lotto AS varchar(50)))) IN ({placeholders})
                  AND ana.ESP_Esportatore IS NOT NULL
                  AND LTRIM(RTRIM(ana.ESP_Esportatore)) != ''
                """
                cursor.execute(query_fast2, lotto_variants)
                row = cursor.fetchone()
                if row and row[0]:
                    exportador = str(row[0]).strip()
                    if exportador:
                        conn.close()
                        return exportador
            except Exception:
                pass
        query = """
        SELECT PRO_Codice_Produttore, PRO_Produttore
        FROM ANA_Produttore
        """
        df = read_sql_adapted(query, conn)
        conn.close()
        if df.empty:
            return {}
        # Convertir a diccionario {codigo: nombre}
        produttore_dict = dict(zip(df['PRO_Codice_Produttore'].astype(str), df['PRO_Produttore']))
        return produttore_dict
    except Exception as e:
        # st.error(f"Error al obtener ANA_Produttore: {e}")
        return {}

def get_detalle_lotti_ingresso():
    """Obtiene los datos de VW_LottiIngresso para la tabla de detalle por proceso y lote
    La tabla se reinicia al cambiar de turno y puede mostrar uno o más lotes"""
    try:
        conn = get_connection_unitec()
        
        # Primero obtener todas las columnas para identificar las columnas disponibles
        query_test = "SELECT TOP 1 * FROM VW_LottiIngresso"
        df_test = read_sql_adapted(query_test, conn)
        columnas_disponibles = [col.lower() for col in df_test.columns]
        
        # Buscar columna de productor (excluyendo CodiceProduttore)
        productor_col = None
        for col in df_test.columns:
            col_lower = col.lower()
            if ('produttore' in col_lower or 'productor' in col_lower) and 'codice' not in col_lower:
                productor_col = col
                break
        
        # Buscar columna de detención/paro (si existe en la vista)
        detencion_col = None
        detencion_keywords = ("deten", "detenz", "fermo", "stop", "paus", "sosta", "downtime")
        for col in df_test.columns:
            col_lower = col.lower()
            if any(k in col_lower for k in detencion_keywords):
                detencion_col = col
                break
        
        # Construir la consulta con las columnas necesarias, verificando que existan
        # Nota: UnitaRemanenti no se incluye porque se calculará siempre como diferencia
        columnas_base = []
        columnas_necesarias = {
            'DataLettura': 'DataLettura',
            'CodiceProduttore': 'CodiceProduttore',
            'CodiceProcesso': 'CodiceProcesso',
            'CodiceLotto': 'CodiceLotto',
            'UnitaPianificate': 'UnitaPianificate',
            'UnitaIn': 'UnitaIn',
            'UnitaRestanti': 'UnitaRestanti',
            'Varieta': 'Varieta',
            'PesoNetto': 'PesoNetto'
        }
        
        # Agregar solo las columnas que existen en la vista
        for col_key, col_name in columnas_necesarias.items():
            if col_name.lower() in columnas_disponibles:
                columnas_base.append(col_name)
        
        if productor_col:
            columnas_base.append(productor_col)
        
        if detencion_col:
            columnas_base.append(detencion_col)
        
        columnas_str = ', '.join(columnas_base)
        query = f"""
        SELECT {columnas_str}
        FROM VW_LottiIngresso
        ORDER BY CodiceProcesso, DataLettura DESC
        """
        
        df = read_sql_adapted(query, conn)
        conn.close()
        
        if df.empty:
            return None
        
        # ================== INICIO MODIFICACIÓN PRODUCTOR ===================
        produttore_dict = get_produttore_dict()
        # Si existe la columna CodiceProduttore y el dict no está vacío,
        # reemplazar donde se pueda el valor por el nombre del productor
        if 'CodiceProduttore' in df.columns and len(produttore_dict) > 0:
            df['ProductorNombre'] = df['CodiceProduttore'].astype(str).map(produttore_dict)
            # Si no hay nombre, fallback al código
            df['ProductorNombre'] = df['ProductorNombre'].fillna(df['CodiceProduttore'].astype(str))
        else:
            df['ProductorNombre'] = df['CodiceProduttore'].astype(str) if 'CodiceProduttore' in df.columns else ''
        # ================== FIN MODIFICACIÓN PRODUCTOR ===================

        # Crear el DataFrame con las columnas requeridas
        resultado = pd.DataFrame()
        
        # Fecha y Hora
        if 'DataLettura' in df.columns:
            df['DataLettura'] = pd.to_datetime(df['DataLettura'], errors='coerce')
            resultado['Fecha y Hora'] = df['DataLettura'].dt.strftime('%d/%m/%Y %H:%M:%S')
        else:
            resultado['Fecha y Hora'] = ''
        
        # CSG
        if 'CodiceProduttore' in df.columns:
            resultado['CSG'] = df['CodiceProduttore'].astype(str)
        else:
            resultado['CSG'] = ''
        
        # Productor (usar ProductorNombre en vez del anterior)
        resultado['Productor'] = df['ProductorNombre']
        
        # Proceso
        if 'CodiceProcesso' in df.columns:
            resultado['Proceso'] = df['CodiceProcesso'].astype(str)
        else:
            resultado['Proceso'] = ''
        
        # Lote
        if 'CodiceLotto' in df.columns:
            resultado['Lote'] = df['CodiceLotto'].astype(str)
        else:
            resultado['Lote'] = ''
        
        # Cajas Planificadas
        if 'UnitaPianificate' in df.columns:
            resultado['Cjs Planificadas'] = df['UnitaPianificate'].astype(int)
        else:
            resultado['Cjs Planificadas'] = 0
        
        # Cajas Vaciadas
        if 'UnitaIn' in df.columns:
            resultado['Cjs Vaciadas'] = df['UnitaIn'].astype(int)
        else:
            resultado['Cjs Vaciadas'] = 0
        
        # Cajas Restantes
        # Importante: en BD puede venir negativo (ej: -13), asÃ­ que en la tabla mostramos el valor real.
        if 'UnitaRestanti' in df.columns:
            resultado['Cjs Restantes'] = df['UnitaRestanti'].astype(int)
        elif 'UnitaPianificate' in df.columns and 'UnitaIn' in df.columns:
            # Fallback si la vista no trae UnitaRestanti: diferencia planificadas - vaciadas (sin clamp).
            resultado['Cjs Restantes'] = (df['UnitaPianificate'].astype(int) - df['UnitaIn'].astype(int))
        else:
            resultado['Cjs Restantes'] = 0
        
        # Variedad Real
        if 'Varieta' in df.columns:
            resultado['Var Real'] = df['Varieta'].astype(str)
        else:
            resultado['Var Real'] = ''
        
        # Peso (Kg) - convertir de gramos a kilogramos
        if 'PesoNetto' in df.columns:
            peso_kg = df['PesoNetto'].astype(float) / 1000
            resultado['Peso (Kg)'] = peso_kg.round(2)
        else:
            resultado['Peso (Kg)'] = 0.0
        
        # Detención/paro (si existe)
        if detencion_col and detencion_col in df.columns:
            resultado['Detención'] = df[detencion_col]
         
        # Calcular acumulado por proceso (suma acumulativa agrupada por proceso)
        # Ordenar por proceso y fecha para calcular el acumulado correctamente
        resultado = resultado.sort_values(['Proceso', 'Fecha y Hora'])
        resultado['Acumulado por Proceso (Kg)'] = resultado.groupby('Proceso')['Peso (Kg)'].cumsum().round(2)
        
        # Ordenar por fecha descendente para mostrar los más recientes primero
        resultado = resultado.sort_values('Fecha y Hora', ascending=False)
        
        # Resetear índice
        resultado = resultado.reset_index(drop=True)
        
        return resultado
        
    except Exception as e:
        logger.exception("Error al obtener datos de VW_LottiIngresso: %s", e)
        return None

def get_current_record():
    """Obtiene el registro más reciente para los filtros y datos del lote"""
    try:
        conn = get_connection()
        # Obtener todas las columnas para buscar el peso automáticamente
        query = """
        SELECT TOP 1 *
        FROM VW_MON_Partita_Corrente 
        ORDER BY 1 DESC
        """
        df = read_sql_adapted(query, conn)
        conn.close()
        if not df.empty:
            unita_pianificate = float(df.iloc[0]['UnitaPianificate']) if pd.notna(df.iloc[0]['UnitaPianificate']) else 0
            unita_svuotate = float(df.iloc[0]['UnitaSvuotate']) if pd.notna(df.iloc[0]['UnitaSvuotate']) else 0
            unita_restanti = unita_pianificate - unita_svuotate
            
            # Buscar el peso en cualquier columna que contenga "Peso" en su nombre
            peso_netto = 0
            try:
                peso_columnas = [col for col in df.columns if 'peso' in col.lower()]
                for col in peso_columnas:
                    try:
                        valor = df.iloc[0][col]
                        if pd.notna(valor):
                            peso_candidato = float(valor)
                            if peso_candidato > 0:
                                # Convertir de gramos a kilogramos
                                peso_netto = peso_candidato / 1000
                                break
                    except:
                        continue
            except:
                peso_netto = 0
            
            return {
                "Productor": str(df.iloc[0]['ProduttoreDescrizione']) if pd.notna(df.iloc[0]['ProduttoreDescrizione']) else "N/A",
                "Variedad": str(df.iloc[0]['VarietaDescrizione']) if pd.notna(df.iloc[0]['VarietaDescrizione']) else "N/A",
                "Proceso": str(df.iloc[0]['ProcessoCodice']) if pd.notna(df.iloc[0]['ProcessoCodice']) else "N/A",
                "Lote": str(df.iloc[0]['LottoCodice']) if pd.notna(df.iloc[0]['LottoCodice']) else "N/A",
                "UnitaPianificate": unita_pianificate,
                "UnitaSvuotate": unita_svuotate,
                "UnitaRestanti": unita_restanti,
                "PesoNetto": peso_netto
            }
        return None
    except Exception as e:
        return None

def get_current_lote_from_detalle():
    """Obtiene los datos del lote actual desde VW_LottiIngresso (el más reciente)
    Retorna un diccionario con los datos más precisos para el análisis gráfico"""
    try:
        conn = get_connection_unitec()
        
        # Obtener el registro más reciente (último lote procesándose)
        query = """
        SELECT TOP 1
            CodiceProduttore,
            CodiceProcesso,
            CodiceLotto,
            UnitaPianificate,
            UnitaIn,
            Varieta,
            PesoNetto,
            DataLettura
        FROM VW_LottiIngresso
        ORDER BY DataLettura DESC
        """
        df = read_sql_adapted(query, conn)
        conn.close()
        
        if df.empty:
            return None
        
        # Calcular unidades restantes
        unita_pianificate = int(df.iloc[0]['UnitaPianificate']) if pd.notna(df.iloc[0]['UnitaPianificate']) else 0
        unita_svuotate = int(df.iloc[0]['UnitaIn']) if pd.notna(df.iloc[0]['UnitaIn']) else 0
        unita_restanti = max(0, unita_pianificate - unita_svuotate)
        
        # Convertir peso de gramos a kilogramos
        peso_netto_kg = float(df.iloc[0]['PesoNetto']) / 1000 if pd.notna(df.iloc[0]['PesoNetto']) else 0
        
        return {
            "CSG": str(df.iloc[0]['CodiceProduttore']) if pd.notna(df.iloc[0]['CodiceProduttore']) else "N/A",
            "Proceso": str(df.iloc[0]['CodiceProcesso']) if pd.notna(df.iloc[0]['CodiceProcesso']) else "N/A",
            "Lote": str(df.iloc[0]['CodiceLotto']) if pd.notna(df.iloc[0]['CodiceLotto']) else "N/A",
            "Variedad": str(df.iloc[0]['Varieta']) if pd.notna(df.iloc[0]['Varieta']) else "N/A",
            "UnitaPianificate": unita_pianificate,
            "UnitaSvuotate": unita_svuotate,
            "UnitaRestanti": unita_restanti,
            "PesoNetto": peso_netto_kg
        }
        
    except Exception as e:
        logger.exception("Error al obtener datos del lote actual: %s", e)
        return None

def get_kg_por_turno():
    """Obtiene los kg por turno desde VW_MON_Produttivita_Turno_Corrente (convierte de gramos a kg)"""
    try:
        conn = get_connection()
        query = """
        SELECT TOP 1 
            PesoSvuotato
        FROM VW_MON_Produttivita_Turno_Corrente
        ORDER BY 1 DESC
        """
        df = read_sql_adapted(query, conn)
        conn.close()
        if not df.empty:
            peso_svuotato_gramos = float(df.iloc[0]['PesoSvuotato']) if pd.notna(df.iloc[0]['PesoSvuotato']) else 0
            # Convertir de gramos a kilogramos
            peso_svuotato_kg = peso_svuotato_gramos / 1000
            return peso_svuotato_kg
        return 0
    except Exception as e:
        return 0


def get_turno_corrente_info():
    """
    Obtiene informaci᳇n del turno en curso desde VW_MON_Produttivita_Turno_Corrente.
    Retorna dict con: turn (int), business_date (YYYY-MM-DD), turno_inicio (datetime | None).
    """
    try:
        conn = get_connection()
        query = """
        SELECT TOP 1
            TurnoCodice,
            TurnoGiornaliero,
            TurnoInizio
        FROM VW_MON_Produttivita_Turno_Corrente
        ORDER BY DataAcquisizione DESC
        """
        df = read_sql_adapted(query, conn)
        conn.close()
        if df.empty:
            return None

        turno_codice = df.iloc[0].get("TurnoCodice")
        turno_giornaliero = df.iloc[0].get("TurnoGiornaliero")
        turno_inicio = df.iloc[0].get("TurnoInizio")

        try:
            turn_int = int(str(turno_codice).strip())
        except Exception:
            return None
        if turn_int not in (1, 2):
            return None

        business_date = None
        try:
            if hasattr(turno_giornaliero, "date"):
                business_date = turno_giornaliero.isoformat()
            else:
                business_date = str(turno_giornaliero)
        except Exception:
            business_date = None

        turno_inicio_dt = None
        try:
            turno_inicio_dt = turno_inicio.to_pydatetime() if hasattr(turno_inicio, "to_pydatetime") else turno_inicio
        except Exception:
            turno_inicio_dt = None

        return {"turn": turn_int, "business_date": business_date, "turno_inicio": turno_inicio_dt}
    except Exception:
        return None


def get_cajas_por_turno():
    """Obtiene las cajas acumuladas del turno desde VW_MON_Produttivita_Turno_Corrente."""
    try:
        conn = get_connection()
        query = """
        SELECT TOP 1
            UnitaSvuotate
        FROM VW_MON_Produttivita_Turno_Corrente
        ORDER BY 1 DESC
        """
        df = read_sql_adapted(query, conn)
        conn.close()
        if not df.empty:
            return int(df.iloc[0]["UnitaSvuotate"]) if pd.notna(df.iloc[0]["UnitaSvuotate"]) else 0
        return 0
    except Exception:
        return 0


def get_cajas_por_hora_turno():
    """Obtiene las cajas por hora del turno desde VW_MON_Produttivita_Turno_Corrente."""
    try:
        conn = get_connection()
        query = """
        SELECT TOP 1
            UnitaSvuotateOra
        FROM VW_MON_Produttivita_Turno_Corrente
        ORDER BY 1 DESC
        """
        df = read_sql_adapted(query, conn)
        conn.close()
        if not df.empty:
            return int(df.iloc[0]["UnitaSvuotateOra"]) if pd.notna(df.iloc[0]["UnitaSvuotateOra"]) else 0
        return 0
    except Exception:
        return 0


def get_fermo_macchina_minuti():
    """Obtiene el tiempo de detención (minutos) del turno desde VW_MON_Produttivita_Turno_Corrente."""
    try:
        conn = get_connection()
        query = """
        SELECT TOP 1
            FermoMacchinaMinuti
        FROM VW_MON_Produttivita_Turno_Corrente
        ORDER BY DataAcquisizione DESC
        """
        df = read_sql_adapted(query, conn)
        conn.close()
        if df.empty:
            return 0.0
        v = df.iloc[0].get("FermoMacchinaMinuti")
        return float(v) if pd.notna(v) else 0.0
    except Exception:
        return 0.0


def get_lotti_inizio_fine_map(max_rows: int = 800):
    """
    Obtiene inicio/fin de lote desde VW_MON_Partita_Storico_Agent.

    Retorna dict con llave (ProcesoCodice, LottoCodice) -> {"start": datetime|None, "end": datetime|None}
    """
    try:
        conn = get_connection()
        query = f"""
        SELECT TOP {int(max_rows)}
            ProcessoCodice,
            LottoCodice,
            LottoInizio,
            LottoFine
        FROM VW_MON_Partita_Storico_Agent
        ORDER BY DataAcquisizione DESC
        """
        df = read_sql_adapted(query, conn)
        conn.close()
        if df.empty:
            return {}

        out = {}
        for _, r in df.iterrows():
            proc = r.get("ProcessoCodice")
            lotto = r.get("LottoCodice")
            if proc is None or lotto is None:
                continue
            key = (str(proc), str(lotto))
            if key in out:
                continue
            start = r.get("LottoInizio")
            end = r.get("LottoFine")
            try:
                start_dt = start.to_pydatetime() if hasattr(start, "to_pydatetime") else start
            except Exception:
                start_dt = None
            try:
                end_dt = end.to_pydatetime() if hasattr(end, "to_pydatetime") else end
            except Exception:
                end_dt = None
            out[key] = {"start": start_dt, "end": end_dt}
        return out
    except Exception:
        return {}


def get_kg_por_hora_turno():
    """Obtiene los kg por hora del turno desde VW_MON_Produttivita_Turno_Corrente (convierte de gramos a kg)."""
    try:
        conn = get_connection()
        query = """
        SELECT TOP 1
            PesoSvuotatoOra
        FROM VW_MON_Produttivita_Turno_Corrente
        ORDER BY 1 DESC
        """
        df = read_sql_adapted(query, conn)
        conn.close()
        if not df.empty:
            gramos = float(df.iloc[0]["PesoSvuotatoOra"]) if pd.notna(df.iloc[0]["PesoSvuotatoOra"]) else 0
            return gramos / 1000
        return 0
    except Exception:
        return 0

def get_kg_lote_vw_partita(lotto_codice, processo_codice):
    """Obtiene los kg del lote desde VW_MON_Partita_Corrente
    Busca en la misma vista que se usa para obtener los datos actuales"""
    try:
        if not lotto_codice or lotto_codice == "N/A":
            return 0
        if not processo_codice or processo_codice == "N/A":
            return 0
        
        # Limpiar espacios en blanco y convertir a string
        lotto_codice = str(lotto_codice).strip()
        processo_codice = str(processo_codice).strip()
        
        conn = get_connection()
        
        # Buscar el peso en VW_MON_Partita_Corrente
        # Intentar diferentes nombres de columnas posibles
        query = """
        SELECT TOP 1 
            *
        FROM VW_MON_Partita_Corrente
        WHERE LTRIM(RTRIM(LottoCodice)) = ? AND LTRIM(RTRIM(ProcessoCodice)) = ?
        ORDER BY 1 DESC
        """
        df = read_sql_adapted(query, conn, params=[lotto_codice, processo_codice])
        conn.close()
        
        if not df.empty:
            # Intentar diferentes nombres de columnas de peso
            peso_columnas = ['PesoNetto', 'Peso', 'PesoKg', 'PesoTotal', 'PesoSvuotato']
            for col in peso_columnas:
                if col in df.columns:
                    peso = float(df.iloc[0][col]) if pd.notna(df.iloc[0][col]) else 0
                    if peso > 0:
                        # Convertir de gramos a kilogramos
                        return peso / 1000
        return 0
    except Exception as e:
        return 0

def get_kg_total_lote(lotto_codice):
    """Obtiene los kg totales del lote sumando todos los PesoNetto desde VW_LottiIngresso
    Equivalente a KgTotalDelLote en Power BI: suma de Medidas[KgNetto] donde CodiceLotto = lote actual
    Esta vista está en la base de datos UNITEC_DB"""
    try:
        if not lotto_codice or lotto_codice == "N/A":
            return 0
        
        # Limpiar espacios en blanco y convertir a string
        lotto_codice = str(lotto_codice).strip()
        
        conn = get_connection_unitec()
        
        # Sumar todos los PesoNetto del lote
        query = """
        SELECT 
            SUM(PesoNetto) as PesoNettoTotal
        FROM VW_LottiIngresso
        WHERE LTRIM(RTRIM(CodiceLotto)) = ?
        """
        df = read_sql_adapted(query, conn, params=[lotto_codice])
        
        # Si no encuentra, intentar sin TRIM
        if df.empty or pd.isna(df.iloc[0]['PesoNettoTotal']) or df.iloc[0]['PesoNettoTotal'] == 0:
            query2 = """
            SELECT 
                SUM(PesoNetto) as PesoNettoTotal
            FROM VW_LottiIngresso
            WHERE CodiceLotto = ?
            """
            df = pd.read_sql(query2, conn, params=[lotto_codice])
        
        conn.close()
        
        if not df.empty and pd.notna(df.iloc[0]['PesoNettoTotal']):
            peso_netto_total = float(df.iloc[0]['PesoNettoTotal'])
            if peso_netto_total > 0:
                # Convertir de gramos a kilogramos
                return peso_netto_total / 1000
        return 0
    except Exception as e:
        return 0

def get_kg_por_caja_lote(lotto_codice=None):
    """Calcula los kg por caja del lote
    Equivalente a KGporCAJAdeLOTE en Power BI:
    - Si se proporciona lotto_codice, calcula para ese lote específico
    - Si no, obtiene el lote más reciente (máximo CodiceLotto donde DataLettura es máxima)
    - Suma PesoNetto de ese lote
    - Suma UnitaPianificate de ese lote
    - Retorna: (Suma PesoNetto / Suma UnitaPianificate) / 1000
    Esta vista está en la base de datos UNITEC_DB"""
    try:
        conn = get_connection_unitec()
        
        if lotto_codice:
            # Usar el lote proporcionado
            lotto_codice = str(lotto_codice).strip()
        else:
            # Obtener el lote más reciente (máximo CodiceLotto donde DataLettura es máxima)
            query_lote = """
            SELECT TOP 1
                CodiceLotto
            FROM VW_LottiIngresso
            WHERE DataLettura = (SELECT MAX(DataLettura) FROM VW_LottiIngresso)
            ORDER BY CodiceLotto DESC
            """
            df_lote = read_sql_adapted(query_lote, conn)
            
            if df_lote.empty:
                conn.close()
                return 0
            
            lotto_codice = str(df_lote.iloc[0]['CodiceLotto']).strip()
        
        # Sumar PesoNetto y UnitaPianificate del lote
        query_suma = """
        SELECT 
            SUM(PesoNetto) as PesoNettoTotal,
            SUM(UnitaPianificate) as UnitaPianificateTotal
        FROM VW_LottiIngresso
        WHERE LTRIM(RTRIM(CodiceLotto)) = ?
        """
        df_suma = pd.read_sql(query_suma, conn, params=[lotto_codice])
        
        # Si no encuentra, intentar sin TRIM
        if df_suma.empty or pd.isna(df_suma.iloc[0]['PesoNettoTotal']) or df_suma.iloc[0]['PesoNettoTotal'] == 0:
            query_suma2 = """
            SELECT 
                SUM(PesoNetto) as PesoNettoTotal,
                SUM(UnitaPianificate) as UnitaPianificateTotal
            FROM VW_LottiIngresso
            WHERE CodiceLotto = ?
            """
            df_suma = pd.read_sql(query_suma2, conn, params=[lotto_codice])
        
        conn.close()
        
        if not df_suma.empty:
            peso_netto_total = float(df_suma.iloc[0]['PesoNettoTotal']) if pd.notna(df_suma.iloc[0]['PesoNettoTotal']) else 0
            unita_pianificate_total = float(df_suma.iloc[0]['UnitaPianificateTotal']) if pd.notna(df_suma.iloc[0]['UnitaPianificateTotal']) else 0
            
            if unita_pianificate_total > 0 and peso_netto_total > 0:
                # Calcular: (PesoNetto / UnitaPianificate) / 1000
                kg_por_caja = (peso_netto_total / unita_pianificate_total) / 1000
                return kg_por_caja
        
        return 0
    except Exception as e:
        return 0

def get_kg_lote(lotto_codice, processo_codice):
    """Obtiene los kg del lote desde VW_LottiIngresso usando PesoNetto
    Usa tanto LottoCodice como ProcessoCodice para identificar el lote correcto
    Esta vista está en la base de datos UNITEC_DB
    NOTA: Esta función está deprecada, usar get_kg_total_lote en su lugar"""
    try:
        if not lotto_codice or lotto_codice == "N/A":
            return 0
        if not processo_codice or processo_codice == "N/A":
            return 0
        
        # Limpiar espacios en blanco y convertir a string
        lotto_codice = str(lotto_codice).strip()
        processo_codice = str(processo_codice).strip()
        
        conn = get_connection_unitec()
        
        # Primero intentar con la búsqueda exacta
        query = """
        SELECT TOP 1 
            PesoNetto
        FROM VW_LottiIngresso
        WHERE LTRIM(RTRIM(LottoCodice)) = ? AND LTRIM(RTRIM(ProcessoCodice)) = ?
        ORDER BY 1 DESC
        """
        df = read_sql_adapted(query, conn, params=[lotto_codice, processo_codice])
        
        # Si no encuentra, intentar sin TRIM (por si acaso)
        if df.empty:
            query2 = """
            SELECT TOP 1 
                PesoNetto
            FROM VW_LottiIngresso
            WHERE LottoCodice = ? AND ProcessoCodice = ?
            ORDER BY 1 DESC
            """
            df = pd.read_sql(query2, conn, params=[lotto_codice, processo_codice])
        
        # Si aún no encuentra, intentar solo con LottoCodice
        if df.empty:
            query3 = """
            SELECT TOP 1 
                PesoNetto
            FROM VW_LottiIngresso
            WHERE LTRIM(RTRIM(LottoCodice)) = ?
            ORDER BY 1 DESC
            """
            df = pd.read_sql(query3, conn, params=[lotto_codice])
        
        conn.close()
        
        if not df.empty:
            peso_netto = float(df.iloc[0]['PesoNetto']) if pd.notna(df.iloc[0]['PesoNetto']) else 0
            if peso_netto > 0:
                # Convertir de gramos a kilogramos
                return peso_netto / 1000
        return 0
    except Exception as e:
        # Mostrar el error para debugging (solo en modo desarrollo)
        # st.error(f"Error en get_kg_lote: {e} - Lote: {lotto_codice}, Proceso: {processo_codice}")
        return 0

def create_gauge(value, max_value, title, color='green'):
    """Crea un medidor semicircular"""
    percentage = (value / max_value * 100) if max_value > 0 else 0
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = percentage,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 100], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    
    return fig

def get_exportador_nombre(lotto_codice):
    """Obtiene el nombre del exportador vinculando dos tablas usando el código de lote
    ANA_Esportatore tiene ESP_ID y ESP_Esportatore pero NO tiene la columna del lote
    PROD_Unita_OUT tiene UOUT_Esportatore_FK y la columna del lote
    Hace JOIN: PROD_Unita_OUT.UOUT_Esportatore_FK = ANA_Esportatore.ESP_ID
    Ambas tablas están en la base de datos UNITEC_DB
    
    Args:
        lotto_codice (str): Código del lote a buscar
        
    Returns:
        str: Nombre del exportador o "N/A" si no se encuentra
    """
    try:
        if not lotto_codice or lotto_codice == "N/A":
            return "N/A"
        
        # Limpiar espacios en blanco y convertir a string
        lotto_codice = str(lotto_codice).strip()

        # Generar variantes comunes del código (ej: "262" vs "00262") para mejorar match
        # y cubrir casos donde la columna en SQL sea numérica o texto con ceros a la izquierda.
        variantes = [lotto_codice]
        solo_digitos = lotto_codice.isdigit()
        if solo_digitos:
            sin_ceros = lotto_codice.lstrip("0") or "0"
            variantes.extend(
                [
                    sin_ceros,
                    sin_ceros.zfill(5),
                    sin_ceros.zfill(6),
                    lotto_codice.zfill(5),
                    lotto_codice.zfill(6),
                ]
            )
        # Unificar preservando orden
        vistos = set()
        lotto_variants = []
        for v in variantes:
            v = str(v).strip()
            if v and v not in vistos:
                vistos.add(v)
                lotto_variants.append(v)
        
        conn = get_connection_unitec()
        
        # Primero, revisar qué columnas tiene ANA_Esportatore
        columnas_ana = []
        try:
            query_test = "SELECT TOP 1 * FROM ANA_Esportatore"
            df_test = read_sql_adapted(query_test, conn)
            columnas_ana = list(df_test.columns)
        except Exception as e:
            # Si ANA_Esportatore no existe, intentar otras tablas
            pass
        
        # Buscar tabla que tiene PROD_Unita_OUT, UOUT_Esportatore_FK y columna del lote
        tabla_unita = None
        lote_col = None
        lote_fk_col = None
        tablas_posibles_unita = ['PROD_Unita_OUT', 'PRODUnitaOUT', 'Prod_Unita_OUT']
        
        for tabla in tablas_posibles_unita:
            try:
                query_test = f"SELECT TOP 1 * FROM {tabla}"
                df_test = read_sql_adapted(query_test, conn)
                columnas = [col.lower() for col in df_test.columns]
                columnas_originales = list(df_test.columns)
                
                # Verificar que tenga UOUT_Esportatore_FK
                tiene_uout_fk = 'uout_esportatore_fk' in columnas or 'UOUT_Esportatore_FK' in columnas_originales
                
                if tiene_uout_fk:
                    tabla_unita = tabla
                    # Buscar columna del lote
                    posibles_nombres_lote = ['codicelotto', 'lottocodice', 'lotto', 'codice_lotto']
                    for col in df_test.columns:
                        col_lower = col.lower()
                        if col_lower in posibles_nombres_lote and 'fk' not in col_lower:
                            lote_col = col
                            break
                    # Si no encuentra con nombres exactos, buscar cualquier columna con "lotto" o "lote"
                    if not lote_col:
                        for col in df_test.columns:
                            col_lower = col.lower()
                            if ('lotto' in col_lower or 'lote' in col_lower) and 'fk' not in col_lower:
                                lote_col = col
                                break
                    if not lote_fk_col:
                        for col in df_test.columns:
                            col_lower = col.lower()
                            if ('lotto' in col_lower or 'lote' in col_lower) and 'fk' in col_lower:
                                lote_fk_col = col
                                break
                    break
            except Exception as e:
                continue
        
        # Si encontramos la tabla con el lote, hacer JOIN con ANA_Esportatore
        if tabla_unita and (lote_col or lote_fk_col):
            # Verificar que ANA_Esportatore tenga las columnas necesarias
            usar_ana = False
            if columnas_ana:
                columnas_ana_lower = [col.lower() for col in columnas_ana]
                tiene_esp_id = 'esp_id' in columnas_ana_lower or 'ESP_ID' in columnas_ana
                tiene_esp_nombre = 'esp_esportatore' in columnas_ana_lower or 'ESP_Esportatore' in columnas_ana
                usar_ana = tiene_esp_id and tiene_esp_nombre
            
            if usar_ana:
                # Usar ANA_Esportatore para el JOIN
                placeholders = ", ".join(["?"] * len(lotto_variants))
                query = """
                SELECT DISTINCT TOP 1
                    ana.ESP_Esportatore
                FROM {} uout
                INNER JOIN ANA_Esportatore ana ON uout.UOUT_Esportatore_FK = ana.ESP_ID
                WHERE LTRIM(RTRIM(CAST(uout.{} AS varchar(50)))) IN ({})
                    AND ana.ESP_Esportatore IS NOT NULL 
                    AND LTRIM(RTRIM(ana.ESP_Esportatore)) != ''
                ORDER BY ana.ESP_Esportatore
                """.format(tabla_unita, lote_col, placeholders)
                
                df = read_sql_adapted(query, conn, params=lotto_variants)
                
                if df.empty:
                    # Intento adicional sin TRIM para casos raros de comparación
                    query2 = """
                    SELECT DISTINCT TOP 1
                        ana.ESP_Esportatore
                    FROM {} uout
                    INNER JOIN ANA_Esportatore ana ON uout.UOUT_Esportatore_FK = ana.ESP_ID
                    WHERE CAST(uout.{} AS varchar(50)) IN ({})
                        AND ana.ESP_Esportatore IS NOT NULL 
                        AND LTRIM(RTRIM(ana.ESP_Esportatore)) != ''
                    ORDER BY ana.ESP_Esportatore
                    """.format(tabla_unita, lote_col, placeholders)
                    df = pd.read_sql(query2, conn, params=lotto_variants)
                
                # Fallback: si la columna de lote encontrada es texto pero viene NULL (ej: UOUT_Lotto_Etichettato),
                # usar el FK del lote (ej: UOUT_Lotto_FK) y hacer JOIN con PROD_Lotto para filtrar por código.
                if (df.empty or df is None) and lote_fk_col:
                    query_fk = """
                    SELECT DISTINCT TOP 1
                        ana.ESP_Esportatore
                    FROM {0} uout
                    INNER JOIN PROD_Lotto lot ON uout.{1} = lot.LOT_ID
                    INNER JOIN ANA_Esportatore ana ON uout.UOUT_Esportatore_FK = ana.ESP_ID
                    WHERE LTRIM(RTRIM(CAST(lot.LOT_Codice_Lotto AS varchar(50)))) IN ({2})
                        AND ana.ESP_Esportatore IS NOT NULL 
                        AND LTRIM(RTRIM(ana.ESP_Esportatore)) != ''
                    ORDER BY ana.ESP_Esportatore
                    """.format(tabla_unita, lote_fk_col, placeholders)
                    df = pd.read_sql(query_fk, conn, params=lotto_variants)
                    
                    if df.empty:
                        query_fk2 = """
                        SELECT DISTINCT TOP 1
                            ana.ESP_Esportatore
                        FROM {0} uout
                        INNER JOIN PROD_Lotto lot ON uout.{1} = lot.LOT_ID
                        INNER JOIN ANA_Esportatore ana ON uout.UOUT_Esportatore_FK = ana.ESP_ID
                        WHERE CAST(lot.LOT_Codice_Lotto AS varchar(50)) IN ({2})
                            AND ana.ESP_Esportatore IS NOT NULL 
                            AND LTRIM(RTRIM(ana.ESP_Esportatore)) != ''
                        ORDER BY ana.ESP_Esportatore
                        """.format(tabla_unita, lote_fk_col, placeholders)
                        df = pd.read_sql(query_fk2, conn, params=lotto_variants)
                
                conn.close()
                
                if not df.empty:
                    col_name = df.columns[0]
                    if pd.notna(df.iloc[0][col_name]):
                        exportador = str(df.iloc[0][col_name]).strip()
                        if exportador:
                            return exportador
            else:
                # Si ANA_Esportatore no tiene las columnas, buscar otra tabla de exportadores
                tablas_posibles_esp = ['ESP_Esportatori', 'ESP_Esportatore', 'Esportatori']
                
                for tabla_esp in tablas_posibles_esp:
                    try:
                        query_test = f"SELECT TOP 1 * FROM {tabla_esp}"
                        df_test = read_sql_adapted(query_test, conn)
                        columnas = [col.lower() for col in df_test.columns]
                        
                        if ('esp_id' in columnas or 'ESP_ID' in df_test.columns) and \
                           ('esp_esportatore' in columnas or 'ESP_Esportatore' in df_test.columns):
                            query = """
                            SELECT DISTINCT TOP 1
                                esp.ESP_Esportatore
                            FROM {} uout
                            INNER JOIN {} esp ON uout.UOUT_Esportatore_FK = esp.ESP_ID
                            WHERE LTRIM(RTRIM(CAST(uout.{} AS varchar(50)))) IN ({})
                                AND esp.ESP_Esportatore IS NOT NULL 
                                AND LTRIM(RTRIM(esp.ESP_Esportatore)) != ''
                            ORDER BY esp.ESP_Esportatore
                            """.format(tabla_unita, tabla_esp, lote_col, placeholders)
                            
                            df = read_sql_adapted(query, conn, params=lotto_variants)
                            
                            if df.empty:
                                query2 = """
                                SELECT DISTINCT TOP 1
                                    esp.ESP_Esportatore
                                FROM {} uout
                                INNER JOIN {} esp ON uout.UOUT_Esportatore_FK = esp.ESP_ID
                                WHERE CAST(uout.{} AS varchar(50)) IN ({})
                                    AND esp.ESP_Esportatore IS NOT NULL 
                                    AND LTRIM(RTRIM(esp.ESP_Esportatore)) != ''
                                ORDER BY esp.ESP_Esportatore
                                """.format(tabla_unita, tabla_esp, lote_col, placeholders)
                                df = pd.read_sql(query2, conn, params=lotto_variants)
                            
                            if (df.empty or df is None) and lote_fk_col:
                                query_fk = """
                                SELECT DISTINCT TOP 1
                                    esp.ESP_Esportatore
                                FROM {0} uout
                                INNER JOIN PROD_Lotto lot ON uout.{1} = lot.LOT_ID
                                INNER JOIN {2} esp ON uout.UOUT_Esportatore_FK = esp.ESP_ID
                                WHERE LTRIM(RTRIM(CAST(lot.LOT_Codice_Lotto AS varchar(50)))) IN ({3})
                                    AND esp.ESP_Esportatore IS NOT NULL 
                                    AND LTRIM(RTRIM(esp.ESP_Esportatore)) != ''
                                ORDER BY esp.ESP_Esportatore
                                """.format(tabla_unita, lote_fk_col, tabla_esp, placeholders)
                                df = pd.read_sql(query_fk, conn, params=lotto_variants)
                                
                                if df.empty:
                                    query_fk2 = """
                                    SELECT DISTINCT TOP 1
                                        esp.ESP_Esportatore
                                    FROM {0} uout
                                    INNER JOIN PROD_Lotto lot ON uout.{1} = lot.LOT_ID
                                    INNER JOIN {2} esp ON uout.UOUT_Esportatore_FK = esp.ESP_ID
                                    WHERE CAST(lot.LOT_Codice_Lotto AS varchar(50)) IN ({3})
                                        AND esp.ESP_Esportatore IS NOT NULL 
                                        AND LTRIM(RTRIM(esp.ESP_Esportatore)) != ''
                                    ORDER BY esp.ESP_Esportatore
                                    """.format(tabla_unita, lote_fk_col, tabla_esp, placeholders)
                                    df = pd.read_sql(query_fk2, conn, params=lotto_variants)
                            
                            if not df.empty:
                                col_name = df.columns[0]
                                if pd.notna(df.iloc[0][col_name]):
                                    exportador = str(df.iloc[0][col_name]).strip()
                                    if exportador:
                                        conn.close()
                                        return exportador
                    except:
                        continue
        
        conn.close()
        return "N/A"
    except Exception as e:
        # En caso de error, retornar N/A sin interrumpir la aplicación
        return "N/A"
