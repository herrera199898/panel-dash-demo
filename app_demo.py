"""
Aplicación principal en Dash - VERSIÓN DEMO CORREGIDA
Dashboard completo con datos ficticios igual que el original
"""
import datetime
import time
import json
import hashlib
import os
import email.utils
import re
import logging
from logging.handlers import RotatingFileHandler
import html as std_html
import threading
import warnings
import random
import importlib

import pandas as pd
import dash
from dash import html, dcc
from dash.dependencies import Output, Input, State
from flask import abort, send_from_directory

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=False)
except Exception:
    pass

from config_demo import get_database_config, APP_CONFIG, is_demo_mode, is_demo_simulation_enabled

# Importar DataTable
from dash import dash_table

# Importar módulo de base de datos según configuración
config_db = get_database_config()
# Importar función de conexión
db_module = importlib.import_module(config_db["module"])
get_connection = db_module.get_connection

from functions import (
    get_current_record,
    get_current_lote_from_detalle,
    get_cajas_por_turno,
    get_cajas_por_hora_turno,
    get_kg_por_turno,
    get_kg_por_hora_turno,
    get_fermo_macchina_minuti,
    get_lotti_inizio_fine_map,
    get_kg_lote_vw_partita,
    get_kg_lote,
    get_kg_total_lote,
    get_kg_por_caja_lote,
    get_detalle_lotti_ingresso,
    get_exportador_nombre,
    get_turno_corrente_info,
    read_sql_adapted,
)
from icons import (
    BOX_ICON_SVG,
    BOXES_EMPTIED_ICON_SVG,
    PROCESS_ICON_SVG,
    CAPACITY_ICON_SVG,
    FILE_ICON_SVG,
    CLOCK_ICON_SVG,
    MAIL_ICON_SVG,
    SCALE_ICON_SVG,
    STACK_ICON_SVG,
    KILOS_ICON_SVG,
)

TURN_TIME_ICON_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" stroke="#ffffff"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"> <path d="M12 21C16.9706 21 21 16.9706 21 12C21 7.02944 16.9706 3 12 3C7.02944 3 3 7.02944 3 12C3 16.9706 7.02944 21 12 21Z" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path> <path d="M12 6V12" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path> <path d="M16.24 16.24L12 12" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path> </g></svg>"""

DEMO_TOTAL_CAJAS = 200
DEMO_TOTAL_KG = 4000
DEMO_CAJAS_POR_HORA = 0
DEMO_KG_POR_HORA = 0
DEMO_CAJAS_STEP = 1
DEMO_REFRESH_S = 5
DEMO_KG_POR_HORA_TARGET = 4800
DEMO_LOTE_PREFIX = "D"
DEMO_PRODUCTORES = ["Campo Verde Ltda.", "Hacienda del Valle", "Agricola Los Andes", "Fruticola Patagonia", "Campo Norte S.A."]
DEMO_VARIEDADES = ["Gala Roja", "Gala Verde", "Gala Premium", "Williams", "Packham", "Tardia", "Bing", "Rainier", "Sweetheart", "Thompson", "Red Globe", "Flame"]
DEMO_PROCESOS = ["CAL001", "CAL002", "CAL003", "EMP001", "EMP002"]
DEMO_EXPORTADORES = ["Exportadora Global S.A.", "Frutas del Mundo Ltda.", "AgroExport Premium", "International Fruits Corp.", "Premium Produce Export"]

app = dash.Dash(__name__, title=APP_CONFIG['title'])
server = app.server

# Función para crear tarjetas métricas (igual que el original)
def construir_metric_card(label, value, subtext="", accent="#2563eb", icon_svg=None, theme="blue", badge_text=""):
    # El problema: React parsea las etiquetas SVG como componentes en lugar de HTML
    # Solución: usar html.Iframe con srcdoc para renderizar el SVG como HTML crudo
    # Esto evita que React parse el SVG y permite renderizar HTML directamente

    if icon_svg:
        # Usar html.Iframe con srcdoc para renderizar el SVG sin que React lo parse
        # El iframe renderiza HTML crudo sin interferencia de React
        icon_element = html.Div(
            className="metric-icon",
            children=[
                html.Iframe(
                    srcDoc=(
                        "<!DOCTYPE html><html><head><style>"
                        "html,body{margin:0;padding:0;background:transparent;overflow:hidden;width:100%;height:100%;}"
                        "body{display:flex;align-items:center;justify-content:center;}"
                        "svg{width:100%;height:100%;display:block;}"
                        "</style></head><body>"
                        f"{icon_svg}"
                        "</body></html>"
                    ),
                    style={
                        "border": "none",
                        "width": "100%",
                        "height": "100%",
                        "pointerEvents": "none",  # Permitir que los clics pasen a través
                    },
                )
            ]
        )
    else:
        icon_element = html.Div(className="metric-icon")

    return html.Div(
        [
            icon_element,
            html.Div(badge_text, className="metric-badge") if badge_text else html.Div(),
            html.Div(label, className="metric-label"),
            html.Div(value, className="metric-value", style={"color": accent}),
            html.Div(subtext, className="metric-subtext") if subtext else html.Div(),
        ],
        className=f"metric-card metric-{theme}",
    )

# Función auxiliar para truncar texto
def truncar_texto(valor, max_len=30):
    texto = str(valor) if valor is not None else "N/A"
    return texto[: max_len - 3] + "..." if len(texto) > max_len else texto

def update_demo_progress():
    """Avanza el demo en cada refresh (sin cambios aleatorios)."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT ProcessoCodice, LottoCodice, UnitaPianificate, UnitaSvuotate, DataAcquisizione
            FROM VW_MON_Partita_Corrente
            ORDER BY DataAcquisizione DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        if not row:
            conn.close()
            return

        processo_codice = row[0]
        lotto_codice = row[1]
        unita_pianificate = int(row[2] or 0)
        unita_svuotate = int(row[3] or 0)

                # Velocidades objetivo (kg/h) y gating por tiempo
        kg_por_caja = DEMO_TOTAL_KG / max(1, DEMO_TOTAL_CAJAS)
        cajas_por_hora = max(1, int(round(DEMO_KG_POR_HORA_TARGET / max(1, kg_por_caja))))
        kg_por_hora = int(round(cajas_por_hora * kg_por_caja))

        # Respetar intervalo m?nimo para avanzar (segundos por caja)
        last_ts = row[4]
        try:
            if isinstance(last_ts, str):
                last_dt = datetime.datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
            elif hasattr(last_ts, 'to_pydatetime'):
                last_dt = last_ts.to_pydatetime()
            else:
                last_dt = last_ts
        except Exception:
            last_dt = None
        if last_dt:
            elapsed = (datetime.datetime.now() - last_dt).total_seconds()
            sec_por_caja = 3600 / max(1, cajas_por_hora)
            if elapsed < sec_por_caja:
                conn.close()
                return

        if unita_svuotate >= unita_pianificate:
            conn.close()
            return

        nuevas_unidades = min(unita_svuotate + DEMO_CAJAS_STEP, unita_pianificate)
        peso_actual = nuevas_unidades * kg_por_caja * 1000  # gramos

        cur.execute(
            """
            UPDATE VW_MON_Partita_Corrente
            SET UnitaSvuotate = ?, PesoNetto = ?, DataAcquisizione = ?
            WHERE LottoCodice = ?
            """,
            (nuevas_unidades, peso_actual, datetime.datetime.now(), lotto_codice),
        )

        cur.execute(
            """
            UPDATE VW_LottiIngresso
            SET UnitaIn = ?, UnitaRestanti = ?, PesoNetto = ?
            WHERE CodiceLotto = ? AND CodiceProcesso = ?
            """,
            (
                nuevas_unidades,
                max(0, unita_pianificate - nuevas_unidades),
                DEMO_TOTAL_KG * 1000,
                lotto_codice,
                processo_codice,
            ),
        )

        cur.execute(
            """
            UPDATE VW_MON_Produttivita_Turno_Corrente
            SET UnitaSvuotate = ?, UnitaSvuotateOra = ?, PesoSvuotato = ?,
                PesoSvuotatoOra = ?, FermoMacchinaMinuti = 0, DataAcquisizione = ?
            """,
            (
                nuevas_unidades,
                cajas_por_hora,
                peso_actual,
                kg_por_hora,
                datetime.datetime.now(),
            ),
        )

        conn.commit()
        conn.close()
    except Exception:
        pass

# Layout principal del dashboard (igual que el original app.py)
app.layout = html.Div([
    # Modal de setup (igual que el original)
    html.Div([
        html.Div([
            html.Div([
                html.Div("Configurar HTTPS / Notificaciones", className="modal-title"),
                html.Button("×", id="setup-modal-close", className="modal-close", n_clicks=0),
            ], className="modal-header"),
            html.Div([
                html.Div([
                    html.Div("Habilitar notificaciones", className="modal-subtitle"),
                    html.Div(
                        [
                            "Esto solo se hace ",
                            html.B("una vez"),
                            " por dispositivo (PC o celular).",
                        ],
                        className="modal-hint",
                    ),
                    html.Div([
                        html.A(
                            "Descargar paquete (ZIP)",
                            href="/downloads/https-setup.zip",
                            className="modal-btn",
                        ),
                        html.Div(
                            "Incluye instalador Windows + certificado (.crt)",
                            className="modal-hint",
                        ),
                    ], className="modal-actions"),
                ], className="modal-col modal-col-wide"),
            ], className="modal-body"),
        ], className="modal-card"),
    ], id="setup-modal", className="modal-overlay", style={"display": "none"}),

    # Header principal (igual que el original)
    html.Div([
        html.Div([
            html.Div([
                html.Div(
                    html.Img(
                        src="/assets/icono_agricola.svg",
                        alt="AgroIndustria XYZ",
                        className="header-logo-img",
                    ),
                    className="header-logo",
                ),
            ], className="header-left"),
            html.Div([
                html.Div(
                    [
                        html.Div("Última actualización", className="update-label"),
                        html.Div(
                            [
                                html.Div(id="refresh-indicator", className="refresh-indicator"),
                                html.Div(id="hora-actual", className="update-time"),
                            ],
                            className="update-time-row",
                        ),
                    ],
                    className="update-badge header-stat",
                ),
                html.Div(
                    [
                        html.Div("Tiempo fin lote", className="update-label"),
                        html.Div(
                            [
                                html.Div(className="eta-clock"),
                                html.Div(id="eta-lote", className="update-time"),
                            ],
                            className="update-time-row",
                        ),
                    ],
                    className="update-badge header-stat",
                ),
            ], className="header-stats"),
        ], className="header-content"),
    ], className="main-header"),

    # Métricas principales (igual que el original)
    html.Div(id="metricas-lote", className="metric-grid"),

    # Tabs (igual que el original)
    dcc.Tabs(
        id="tabs",
        value="tab-analisis",
        children=[
            dcc.Tab(label="Análisis Gráfico", value="tab-analisis", className="tab-analisis"),
            dcc.Tab(label="Detalle Completo", value="tab-detalle", className="tab-detalle"),
            dcc.Tab(label="Orden de Vaciado", value="tab-orden", className="tab-orden"),
        ],
        className="tabs-container",
    ),

    # Contenedor del tab de análisis (igual que el original)
    html.Div([
        # Filtros actuales (información del lote en curso)
        html.Div(id="filtros-actuales", className="filter-card"),

        # Gráficos
        html.Div([
            html.Div(id="chart-cajas", className="chart-card"),
            html.Div(id="chart-kg", className="chart-card"),
        ], className="charts-grid", id="charts-wrapper"),
    ], id="tab-analisis-container"),

    # Contenedor del tab de detalle (igual que el original)
    html.Div([
        dash_table.DataTable(
            id="tabla-detalle",
            data=[],
            columns=[],
            page_size=12,
            filter_action="native",
            filter_options={"case": "insensitive"},
            sort_action="native",
            sort_mode="multi",
            style_table={"overflowX": "auto"},
            style_cell={
                "textAlign": "center",
                "padding": "6px",
                "fontFamily": "inherit",
                "fontSize": "0.95rem",
            },
            style_header={
                "backgroundColor": "#f9fafb",
                "fontWeight": "700",
                "border": "1px solid #e5e7eb",
            },
            style_data={"border": "1px solid #f3f4f6"},
            style_data_conditional=[],
            style_filter={
                "backgroundColor": "#ffffff",
                "fontFamily": "inherit",
            },
        )
    ], id="tab-detalle-container", style={"margin": "0 1.5rem 2rem 1.5rem"}),

    # Contenedor del tab de orden (igual que el original)
    html.Div([
        html.Div(id="orden-meta", className="filter-card"),
        html.Div(id="orden-accordion", className="orden-accordion"),
    ], id="tab-orden-container", style={"margin": "0 1.5rem 2rem 1.5rem", "display": "none"}),

    # Intervalos para actualización automática (igual que el original)
    dcc.Interval(id="interval-act", interval=5 * 1000, n_intervals=0),
    dcc.Interval(id="interval-notif", interval=60 * 1000, n_intervals=0),
    dcc.Interval(id="interval-eta", interval=5 * 1000, n_intervals=0),
    dcc.Interval(id="interval-orden", interval=60 * 1000, n_intervals=0),

    # Stores para estado (igual que el original)
    dcc.Store(id="endlote-notificados-store", data=[], storage_type="local"),
    dcc.Store(id="notif-payload-store"),
    dcc.Store(id="notif-permission-store"),
    dcc.Store(id="eta-store"),
    dcc.Store(id="orden-store"),
    dcc.Store(id="panel-snapshot"),
    dcc.Store(id="client-debug-store"),
    dcc.Store(id="toggle-toast-store"),
    dcc.Store(id="fermo-baseline-store"),
    dcc.Store(id="lote-finish-store"),
    dcc.Store(id="det-por-lote-store"),
    dcc.Store(id="setup-modal-open-store", data=False),
])

# Función auxiliar para formatear enteros
def formatear_entero(valor):
    try:
        return f"{int(round(float(valor))):,}".replace(",", ".")
    except Exception:
        return "0"

# Callbacks principales (basados en el app.py original)
print("[DEBUG] Registering actualizar_panel callback...")
@app.callback(
    [
        Output("metricas-lote", "children"),
        Output("filtros-actuales", "children"),
        Output("chart-cajas", "children"),
        Output("chart-kg", "children"),
        Output("tabla-detalle", "data"),
        Output("tabla-detalle", "columns"),
        Output("tabla-detalle", "style_data_conditional"),
        Output("panel-snapshot", "data"),
        Output("fermo-baseline-store", "data"),
        Output("lote-finish-store", "data"),
        Output("det-por-lote-store", "data"),
        Output("eta-store", "data"),
    ],
    [Input("interval-act", "n_intervals")],
    [State("panel-snapshot", "data"),
     State("fermo-baseline-store", "data"),
     State("lote-finish-store", "data"),
     State("eta-store", "data")],
)
def actualizar_panel(_, prev_snapshot, fermo_baseline_prev, lote_finish_prev, eta_prev):
    print(f"[DEBUG] actualizar_panel FUNCTION CALLED: n_intervals={_}")
    try:
        now = datetime.datetime.now()
        update_demo_progress()
        try:
            cajas_por_hora_turno = get_cajas_por_hora_turno() or 0
            kg_por_hora_turno = get_kg_por_hora_turno() or 0
        except Exception:
            cajas_por_hora_turno = 0
            kg_por_hora_turno = 0


        hora = now.strftime("%d/%m/%Y %H:%M:%S")

        # Obtener datos actuales
        current_record = get_current_record()
        lote_detalle = get_current_lote_from_detalle()

        if lote_detalle:
            datos_lote = lote_detalle
            productor = current_record["Productor"] if current_record else "N/A"
        else:
            datos_lote = current_record
            productor = current_record["Productor"] if current_record else "N/A"

        lote_actual = datos_lote["Lote"] if datos_lote and datos_lote.get("Lote") else None
        
        # #region agent log
        import json
        log_path = r"c:\Users\rza_w\Documents\Frutisima\Panel_dash\.cursor\debug.log"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"app_demo.py:actualizar_panel:data_read","message":"Data read from DB","data":{"lote_actual":str(lote_actual) if lote_actual else None,"cajas_planificadas":datos_lote.get("Cajas Planificadas") if datos_lote else None,"cajas_vaciadas":datos_lote.get("Cajas Vaciadas") if datos_lote else None,"kg_totales":datos_lote.get("PesoNetto") if datos_lote else None},"timestamp":int(time.time()*1000)}) + "\n")
                f.flush()
        except: pass
        # #endregion

        # Obtener exportador
        exportador = None
        try:
            prev_kpis = (prev_snapshot or {}).get("kpis") if isinstance(prev_snapshot, dict) else None
            prev_filtros = (prev_snapshot or {}).get("filtros") if isinstance(prev_snapshot, dict) else None
            prev_lote = (prev_kpis or {}).get("lote") if isinstance(prev_kpis, dict) else None
            prev_exportador = (prev_filtros or {}).get("Exportador") if isinstance(prev_filtros, dict) else None

            if lote_actual and prev_lote == str(lote_actual) and prev_exportador and str(prev_exportador).strip().upper() != "N/A":
                exportador = prev_exportador
            else:
                if lote_actual:
                    # Intentar obtener exportador
                    exportador = get_exportador_nombre(str(lote_actual))
                else:
                    exportador = "N/A"

        except Exception as e:
            exportador = "N/A"

        # Filtros actuales (información del lote en curso)
        filtros = {
            "Exportador": exportador or "N/A",
            "Productor": productor,
            "Variedad": datos_lote["Variedad"] if datos_lote else "N/A",
            "Proceso": datos_lote["Proceso"] if datos_lote else "N/A",
            "Lote": datos_lote["Lote"] if datos_lote else "N/A",
        }
        filtros = {k: truncar_texto(v) for k, v in filtros.items()}

        filtros_children = html.Div([
            html.Div([
                html.Div([
                    html.Div((k[:2] if k else "?").upper(), className="filter-icon"),
                    html.Div(k, className="filter-label"),
                ], className="filter-header"),
                html.Div(v, className="filter-value"),
            ], className="filter-item")
            for k, v in filtros.items()
        ], className="filter-grid")

        # Métricas principales
        if datos_lote:
            cajas_totales = int(datos_lote.get("UnitaPianificate", 0) or 0)
            cajas_vaciadas = int(datos_lote.get("UnitaSvuotate", 0) or 0)
            cajas_restantes = int(datos_lote.get("UnitaRestanti", 0) or 0)

            # Calcular kg
            kg_totales = get_kg_total_lote(datos_lote.get("Lote")) or 0
            if kg_totales == 0 and datos_lote.get("PesoNetto", 0) > 0:
                kg_totales = float(datos_lote["PesoNetto"])

            kg_por_caja = get_kg_por_caja_lote(datos_lote.get("Lote")) or 0
            if kg_por_caja == 0 and cajas_totales > 0 and kg_totales > 0:
                kg_por_caja = kg_totales / cajas_totales

            if kg_por_caja > 0:
                kg_restantes = kg_por_caja * max(0, cajas_restantes)
                kg_vaciados = kg_totales - kg_restantes
            else:
                kg_restantes = kg_vaciados = 0

            pct_cajas = (cajas_vaciadas / cajas_totales * 100) if cajas_totales > 0 else 0
        else:
            cajas_totales = cajas_vaciadas = cajas_restantes = 0
            kg_totales = kg_vaciados = kg_restantes = 0
            pct_cajas = 0

        # Calcular tiempo de turno y detención desde datos ficticios actuales
        turno_s = 0
        fermo_min = 0
        try:
            # Obtener datos del turno desde VW_MON_Produttivita_Turno_Corrente
            conn = get_connection()
            query_turno_completo = """
            SELECT TurnoInizio, FermoMacchinaMinuti
            FROM VW_MON_Produttivita_Turno_Corrente
            ORDER BY DataAcquisizione DESC
            LIMIT 1
            """
            df_turno_completo = read_sql_adapted(query_turno_completo, conn)
            conn.close()
            
            
            if not df_turno_completo.empty:
                # Obtener tiempo de inicio del turno
                turno_inicio = df_turno_completo.iloc[0].get("TurnoInizio")
                if turno_inicio:
                    try:
                        # Convertir a datetime
                        if isinstance(turno_inicio, str):
                            turno_inicio_dt = datetime.datetime.fromisoformat(turno_inicio.replace('Z', '+00:00'))
                        elif hasattr(turno_inicio, "to_pydatetime"):
                            turno_inicio_dt = turno_inicio.to_pydatetime()
                        else:
                            turno_inicio_dt = turno_inicio
                        
                        # Calcular tiempo transcurrido desde inicio del turno
                        if isinstance(turno_inicio_dt, datetime.datetime):
                            turno_s = int((datetime.datetime.now() - turno_inicio_dt).total_seconds())
                            turno_s = max(0, turno_s)  # Asegurar que no sea negativo
                    except Exception as e:
                        turno_s = 0
                
                # Obtener tiempo de detención desde los datos del turno
                fermo_min = float(df_turno_completo.iloc[0].get("FermoMacchinaMinuti", 0) or 0)
                if pd.isna(fermo_min):
                    fermo_min = 0
        except Exception as e:
            turno_s = 0
            fermo_min = 0
        
        # Formatear tiempo de detención
        det_hms = f"{int(fermo_min):02d}:{int((fermo_min % 1) * 60):02d}"

        # Métricas (igual que el original)
        metricas = [
            construir_metric_card(
                "Cajas Turno",
                f"{formatear_entero(cajas_vaciadas)}",
                "acumulado turno",
                accent="#2563eb",
                icon_svg=BOX_ICON_SVG,
                theme="blue",
            ),
            construir_metric_card(
                "Cajas por Hora",
                formatear_entero(cajas_por_hora_turno),
                "cajas/h",
                accent="#7c3aed",
                icon_svg=BOXES_EMPTIED_ICON_SVG,
                theme="purple",
            ),
            construir_metric_card(
                "Kg por Proceso",
                f"{round(kg_totales):,}".replace(",", ".") if kg_totales else "0",
                "acumulado turno",
                accent="#f97316",
                icon_svg=PROCESS_ICON_SVG,
                theme="orange",
            ),
            construir_metric_card(
                "Kg por Hora",
                f"{round(kg_por_hora_turno):,}".replace(",", ".") if kg_por_hora_turno else "0",
                "kg/h",
                accent="#10b981",
                icon_svg=CAPACITY_ICON_SVG,
                theme="green",
            ),
            # Quinta métrica: tiempo de turno con detención
            construir_metric_card(
                "Tiempo Turno",
                f"{turno_s // 3600:02d}:{(turno_s % 3600) // 60:02d}:{turno_s % 60:02d}",
                "tiempo total",
                accent="#991b1b",
                icon_svg=TURN_TIME_ICON_SVG,
                theme="red",
                badge_text=html.Span(
                    [
                        html.Span("Detención: ", className="metric-badge-label"),
                        html.Span(det_hms, className="metric-badge-time"),
                    ]
                ),
            ),
        ]

        # Gráfico de cajas
        pct_cajas = round(pct_cajas, 1)
        # Calcular bins (cajas por bin, asumiendo ~20 cajas por bin)
        bins_por_caja = 20.0
        bins_totales = cajas_totales / bins_por_caja if cajas_totales > 0 else 0
        bins_vaciadas = cajas_vaciadas / bins_por_caja if cajas_vaciadas > 0 else 0
        bins_restantes = cajas_restantes / bins_por_caja if cajas_restantes > 0 else 0
        
        chart_cajas = [
            html.Div([
                html.Div("Cajas Vaciadas", className="chart-title"),
                html.Div(className="chart-loader chart-loader-cajas", key=f"cajas-{_}"),
            ], className="chart-title-row"),
            html.Div("Porcentaje completado del lote", className="chart-subtitle"),
            html.Div([
                html.Span(f"{pct_cajas}%", style={"fontSize": "3rem", "fontWeight": "900", "color": "#2563eb"}),
                html.Div([
                    html.Div("Capacidad", style={"fontSize": "1rem", "color": "#6b7280"}),
                    html.Div(
                        f"{formatear_entero(cajas_vaciadas)} de {formatear_entero(cajas_totales)} cajas",
                        style={"fontSize": "1.1rem"},
                    ),
                ], className="chart-right-block"),
            ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "margin": "1rem 0"}),
            html.Div(
                html.Div(className="progress-bar", style={"width": f"{pct_cajas}%" if pct_cajas >= 0 else "0%"}),
                className="progress-bar-container",
            ),
            html.Div(className="chart-divider"),
            html.Div([
                html.Div([
                    html.Div("Planificadas", className="breakdown-label"),
                    html.Div(formatear_entero(cajas_totales), className="breakdown-value"),
                    html.Div(
                        f"{bins_totales:.1f} bins",
                        style={"fontSize": "0.85rem", "color": "#6b7280", "marginTop": "2px"},
                    ),
                ], className="breakdown-item"),
                html.Div([
                    html.Div("Usadas", className="breakdown-label"),
                    html.Div(
                        formatear_entero(cajas_vaciadas),
                        className="breakdown-value",
                        style={"color": "#2563eb"},
                    ),
                    html.Div(
                        f"{bins_vaciadas:.1f} bins",
                        style={"fontSize": "0.85rem", "color": "#6b7280", "marginTop": "2px"},
                    ),
                ], className="breakdown-item"),
                html.Div([
                    html.Div("Disponibles", className="breakdown-label"),
                    html.Div(
                        formatear_entero(cajas_restantes),
                        className="breakdown-value",
                        style={"color": "#f97316"},
                    ),
                    html.Div(
                        f"{bins_restantes:.1f} bins",
                        style={"fontSize": "0.85rem", "color": "#6b7280", "marginTop": "2px"},
                    ),
                ], className="breakdown-item"),
            ], className="breakdown-grid"),
        ]

        # Gráfico de kg
        kg_totales_safe = kg_totales if kg_totales and kg_totales > 0 else 1
        pct_kg_restantes = round((kg_restantes / kg_totales_safe) * 100, 1) if kg_totales > 0 else 0
        chart_kg = [
            html.Div([
                html.Div("Kilogramos Restantes", className="chart-title"),
                html.Div(className="chart-loader chart-loader-kg", key=f"kg-{_}"),
            ], className="chart-title-row"),
            html.Div("Disponibilidad en almacén", className="chart-subtitle"),
            html.Div([
                html.Span(
                    f"{pct_kg_restantes}%",
                    style={"fontSize": "3rem", "fontWeight": "900", "color": "#10b981"},
                ),
                html.Div([
                    html.Div("Restantes", style={"fontSize": "1rem", "color": "#6b7280"}),
                    html.Div(
                        f"{formatear_entero(kg_restantes)} kg",
                        style={"fontSize": "1.1rem"},
                    ),
                ], className="chart-right-block"),
            ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "margin": "1rem 0"}),
            html.Div(
                html.Div(
                    className="progress-bar",
                    style={
                        "width": f"{pct_kg_restantes}%" if pct_kg_restantes >= 0 else "0%",
                        "background": "linear-gradient(90deg, #10b981, #059669)",
                    },
                ),
                className="progress-bar-container",
            ),
            html.Div(className="chart-divider"),
            html.Div([
                html.Div([
                    html.Div("Total", className="breakdown-label"),
                    html.Div(formatear_entero(kg_totales), className="breakdown-value"),
                ], className="breakdown-item"),
                html.Div([
                    html.Div("Usado", className="breakdown-label"),
                    html.Div(
                        formatear_entero(kg_vaciados),
                        className="breakdown-value",
                        style={"color": "#f97316"},
                    ),
                ], className="breakdown-item"),
                html.Div([
                    html.Div("Disponible", className="breakdown-label"),
                    html.Div(
                        formatear_entero(kg_restantes),
                        className="breakdown-value",
                        style={"color": "#10b981"},
                    ),
                ], className="breakdown-item"),
            ], className="breakdown-grid"),
        ]

        # Tabla de detalle
        detalle_df = get_detalle_lotti_ingresso()

        if detalle_df is not None and not detalle_df.empty:
            columnas_ordenadas = [
                "Fecha y Hora", "CSG", "Productor", "Proceso", "Lote",
                "Cjs Planificadas", "Cjs Vaciadas", "Cjs Restantes", "Var Real", "Peso (Kg)"
            ]
            columnas_existentes = [c for c in columnas_ordenadas if c in detalle_df.columns]
            df_detalle_para_tabla = detalle_df.copy()

            # Mostrar solo registros del turno actual:
            # - Turno dia: 07:00 a 17:00
            # - Turno noche: 17:30 a 04:00 (cruza de dia)
            # Mantener siempre el lote actual aunque quede fuera de rango.
            try:
                if "Fecha y Hora" in df_detalle_para_tabla.columns:
                    df_detalle_para_tabla["_fecha_dt"] = pd.to_datetime(
                        df_detalle_para_tabla["Fecha y Hora"], format="%d/%m/%Y %H:%M:%S", errors="coerce"
                    )
                    if lote_actual is not None:
                        mask_current = df_detalle_para_tabla["Lote"].astype(str) == str(lote_actual)
                    else:
                        mask_current = pd.Series([False] * len(df_detalle_para_tabla), index=df_detalle_para_tabla.index)
                    now = datetime.datetime.now()
                    t = now.time()
                    day_start = datetime.time(7, 0)
                    day_end = datetime.time(17, 0)
                    night_start = datetime.time(17, 30)
                    night_end = datetime.time(4, 0)
                    if t >= night_start or t < night_end:
                        # Turno noche: desde hoy 17:30 o desde ayer 17:30 si es madrugada
                        if t < night_end:
                            start_dt = datetime.datetime.combine(now.date() - datetime.timedelta(days=1), night_start)
                            end_dt = datetime.datetime.combine(now.date(), night_end)
                        else:
                            start_dt = datetime.datetime.combine(now.date(), night_start)
                            end_dt = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), night_end)
                    else:
                        # Turno dia (incluye 17:00-17:30 si cae en ese rango)
                        start_dt = datetime.datetime.combine(now.date(), day_start)
                        end_dt = datetime.datetime.combine(now.date(), day_end)
                    mask_shift = (df_detalle_para_tabla["_fecha_dt"] >= start_dt) & (
                        df_detalle_para_tabla["_fecha_dt"] <= end_dt
                    )
                    df_detalle_para_tabla = df_detalle_para_tabla.loc[mask_shift | mask_current]
            except Exception:
                pass

            # Asegurar fecha/hora visible para el lote actual si viene vacia
            try:
                if "Fecha y Hora" in df_detalle_para_tabla.columns and lote_actual is not None:
                    mask_current = df_detalle_para_tabla["Lote"].astype(str) == str(lote_actual)
                    empty_mask = df_detalle_para_tabla["Fecha y Hora"].isna() | (
                        df_detalle_para_tabla["Fecha y Hora"].astype(str).str.strip().isin(["", "nan", "None", "NaT"])
                    )
                    if (mask_current & empty_mask).any():
                        fecha_lote = None
                        try:
                            fecha_lote = datos_lote.get("Fecha y Hora") if isinstance(datos_lote, dict) else None
                        except Exception:
                            fecha_lote = None
                        if fecha_lote:
                            df_detalle_para_tabla.loc[mask_current & empty_mask, "Fecha y Hora"] = fecha_lote
            except Exception:
                pass

            # Dejar solo registros ya procesados + lote actual
            try:
                if "Cjs Vaciadas" in df_detalle_para_tabla.columns:
                    cjs_vac = pd.to_numeric(df_detalle_para_tabla["Cjs Vaciadas"], errors="coerce").fillna(0)
                    if lote_actual is not None:
                        mask_current = df_detalle_para_tabla["Lote"].astype(str) == str(lote_actual)
                    else:
                        mask_current = pd.Series([False] * len(df_detalle_para_tabla), index=df_detalle_para_tabla.index)
                    keep_mask = (cjs_vac > 0) | mask_current
                    df_detalle_para_tabla = df_detalle_para_tabla.loc[keep_mask]
            except Exception:
                pass

            # Ajustar "Cjs Vaciadas" / "Cjs Restantes" para lotes no actuales:
            # - Lotes anteriores al actual: Vaciadas = Planificadas, Restantes = 0.
            # - Lotes posteriores al actual: Vaciadas = 0, Restantes = Planificadas.
            try:
                if (
                    "Cjs Restantes" in df_detalle_para_tabla.columns
                    and "Cjs Planificadas" in df_detalle_para_tabla.columns
                    and "Cjs Vaciadas" in df_detalle_para_tabla.columns
                ):
                    cjs_plan = pd.to_numeric(df_detalle_para_tabla["Cjs Planificadas"], errors="coerce").fillna(0)
                    dt_col = "_orden_dt"
                    if "Fecha y Hora" in df_detalle_para_tabla.columns:
                        df_detalle_para_tabla[dt_col] = pd.to_datetime(
                            df_detalle_para_tabla["Fecha y Hora"], format="%d/%m/%Y %H:%M:%S", errors="coerce"
                        )
                    else:
                        df_detalle_para_tabla[dt_col] = pd.NaT
                    if lote_actual is not None:
                        mask_current = df_detalle_para_tabla["Lote"].astype(str) == str(lote_actual)
                    else:
                        mask_current = pd.Series([False] * len(df_detalle_para_tabla), index=df_detalle_para_tabla.index)
                    current_dt = None
                    try:
                        if mask_current.any():
                            current_dt = df_detalle_para_tabla.loc[mask_current, dt_col].min()
                    except Exception:
                        current_dt = None
                    if "Proceso" in df_detalle_para_tabla.columns and current_dt is not None and pd.notna(current_dt):
                        cur_proc = None
                        try:
                            if mask_current.any():
                                cur_proc = str(df_detalle_para_tabla.loc[mask_current, "Proceso"].iloc[0])
                        except Exception:
                            cur_proc = None
                        if cur_proc:
                            in_proc = df_detalle_para_tabla["Proceso"].astype(str) == cur_proc
                        else:
                            in_proc = pd.Series([True] * len(df_detalle_para_tabla), index=df_detalle_para_tabla.index)
                        before_current = in_proc & (df_detalle_para_tabla[dt_col] < current_dt)
                        after_current = in_proc & (df_detalle_para_tabla[dt_col] > current_dt)
                    else:
                        before_current = pd.Series([False] * len(df_detalle_para_tabla), index=df_detalle_para_tabla.index)
                        after_current = pd.Series([False] * len(df_detalle_para_tabla), index=df_detalle_para_tabla.index)
                    mask_other = ~mask_current
                    mask_past = mask_other & before_current
                    mask_future = mask_other & after_current
                    # Anteriores: ya completados
                    df_detalle_para_tabla.loc[mask_past, "Cjs Vaciadas"] = cjs_plan[mask_past]
                    df_detalle_para_tabla.loc[mask_past, "Cjs Restantes"] = 0
                    # Posteriores: aún no iniciados
                    df_detalle_para_tabla.loc[mask_future, "Cjs Vaciadas"] = 0
                    df_detalle_para_tabla.loc[mask_future, "Cjs Restantes"] = cjs_plan[mask_future]
            except Exception:
                pass

            # Convertir columnas numéricas a string para filtrado
            for col in ["Cjs Planificadas", "Cjs Vaciadas", "Cjs Restantes", "Peso (Kg)"]:
                if col in df_detalle_para_tabla.columns:
                    df_detalle_para_tabla[col] = df_detalle_para_tabla[col].fillna('').astype(str)

            data = df_detalle_para_tabla.to_dict("records")
            columns = [{"name": c, "id": c, "type": "text"} for c in columnas_existentes]

            # Resaltar lote actual
            style_conditional = []
            if lote_actual and "Lote" in df_detalle_para_tabla.columns:
                query = f'{{Lote}} = "{lote_actual}"'
                style_conditional.append({
                    "if": {"filter_query": query},
                    "backgroundColor": "rgba(16,185,129,0.10)",
                    "fontWeight": "800",
                    "borderTop": "1px solid rgba(16,185,129,0.18)",
                    "borderBottom": "1px solid rgba(16,185,129,0.18)",
                })
        else:
            data, columns, style_conditional = [], [], []

        # Calcular ETA (tiempo estimado de fin de lote) basado en datos ficticios actuales
        cajas_restantes_eta = max(0, int(cajas_restantes or 0))
        kg_por_caja = DEMO_TOTAL_KG / max(1, DEMO_TOTAL_CAJAS)
        cajas_por_hora = max(1, int(round(DEMO_KG_POR_HORA_TARGET / max(1, kg_por_caja))))
        if cajas_restantes_eta == 0:
            eta_store = {
                "lote": str(lote_actual) if lote_actual else None,
                "remaining_s": 0,
                "generated_ms": int(time.time() * 1000.0),
                "end_iso": datetime.datetime.now().isoformat(),
            }
        else:
            eta_s = int(round((cajas_restantes_eta / cajas_por_hora) * 3600))
            eta_s = max(0, eta_s)
            fin_estimado = datetime.datetime.now() + datetime.timedelta(seconds=eta_s)
            eta_store = {
                "lote": str(lote_actual),
                "remaining_s": eta_s,
                "generated_ms": int(time.time() * 1000.0),
                "end_iso": fin_estimado.isoformat(),
            }

        # Snapshot para optimización
        next_snapshot = {
            "kpis": {
                "lote": str(lote_actual) if lote_actual else None,
                "cajas_totales": cajas_totales,
                "cajas_vaciadas": cajas_vaciadas,
                "kg_totales": float(kg_totales),
            },
            "filtros": filtros,
        }


        return (
            metricas,
            filtros_children,
            chart_cajas,
            chart_kg,
            data,
            columns,
            style_conditional,
            next_snapshot,
            None,  # fermo-baseline-store
            None,  # lote-finish-store
            None,  # det-por-lote-store
            eta_store,  # eta-store
        )

    except Exception as e:
        # En caso de error, devolver valores por defecto
        error_msg = f"Error: {str(e)}"
        return (
            [construir_metric_card("Error", error_msg, "", "#ef4444", theme="red")],
            html.Div("Error cargando filtros", className="filter-grid"),
            html.Div(error_msg, style={"padding": "20px", "color": "red"}),
            html.Div(error_msg, style={"padding": "20px", "color": "red"}),
            [],
            [],
            [],
            {},
            None,
            None,
            None,
            None,  # eta-store
        )

    # Callbacks para actualizar la hora y el indicador de refresh
@app.callback(
    Output("hora-actual", "children"),
    Output("refresh-indicator", "children"),
    Input("interval-eta", "n_intervals"),
)
def update_time_and_refresh(n):
    hora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    # Indicador de refresh (igual que el original)
    refresh_indicator = html.Div(
        [
            html.Div(className="refresh-loader", key=str(n)),
        ]
    )
    return hora, refresh_indicator

# Callback para el tiempo estimado de fin de lote
@app.callback(
    Output("eta-lote", "children"),
    Input("interval-eta", "n_intervals"),
    State("eta-store", "data"),
)
def update_eta(n, eta_data):
    if not eta_data:
        return "--:--:--"

    try:
        remaining_s = eta_data.get("remaining_s", 0)
        generated_ms = eta_data.get("generated_ms", 0)
        end_iso = eta_data.get("end_iso")

        if end_iso:
            try:
                if isinstance(end_iso, str):
                    end_iso_clean = end_iso.replace('Z', '').split('+')[0].split('.')[0]
                    try:
                        end_dt = datetime.datetime.fromisoformat(end_iso_clean)
                    except Exception:
                        end_dt = datetime.datetime.strptime(end_iso_clean, "%Y-%m-%dT%H:%M:%S")
                else:
                    end_dt = end_iso

                now = datetime.datetime.now()
                remaining_delta = end_dt - now
                remaining = max(0, remaining_delta.total_seconds())

                if remaining < 1:
                    remaining = 0
                    hours = minutes = seconds = 0
                else:
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    seconds = int(remaining % 60)
            except Exception:
                elapsed = (datetime.datetime.now().timestamp() * 1000 - generated_ms) / 1000
                remaining = max(0, remaining_s - elapsed)

            if 'hours' not in locals():
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                seconds = int(remaining % 60)

            result = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y")
            return f"{fecha_actual} {result}"
        return "--:--:--"
    except Exception:
        return "--:--:--"

# Callbacks para tabs (igual que el original)
@app.callback(
    [Output("tab-analisis-container", "style"),
     Output("tab-detalle-container", "style"),
     Output("tab-orden-container", "style")],
    [Input("tabs", "value")],
)
def render_tab(tab_value):
    if tab_value == "tab-detalle":
        return {"display": "none"}, {"display": "block", "margin": "0 1.5rem 2rem 1.5rem"}, {"display": "none"}
    if tab_value == "tab-orden":
        return {"display": "none"}, {"display": "none"}, {"display": "block", "margin": "0 1.5rem 2rem 1.5rem"}
    return {"display": "block"}, {"display": "none"}, {"display": "none"}

if __name__ == "__main__":
    print(f"[START] Iniciando {APP_CONFIG['title']}")
    print(f"[COMPANY] Empresa: {APP_CONFIG['empresa']}")
    print(f"[MODE] Modo: DEMO")
    print(f"[DB] Base de datos: {config_db['description']}")

    if is_demo_mode():
        print("\n[INFO] Modo DEMO activado")
        if is_demo_simulation_enabled():
            print("[INFO] Iniciando simulacion de datos en segundo plano...")

            def run_simulation():
                try:
                    from demo_simulation import ProductionSimulator
                    simulator = ProductionSimulator(update_interval=30)
                    simulator.start_simulation()
                except Exception as e:
                    print(f"[WARN] Error en simulacion: {e}")

            sim_thread = threading.Thread(target=run_simulation, daemon=True)
            sim_thread.start()
            print("[OK] Simulacion iniciada (actualizacion cada 30 segundos)")
        else:
            print("[INFO] Simulacion demo desactivada (datos estaticos)")

    port = int(os.environ.get("PORT", 8050))
    app.run(debug=False, host="0.0.0.0", port=port)
