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

from config_demo import get_database_config, APP_CONFIG, is_demo_mode

# Importar DataTable
from dash import dash_table

# Importar módulo de base de datos según configuración
config_db = get_database_config()

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
                        src="/assets/logo.svg",
                        alt="Frutísima",
                        className="header-logo-img",
                    ),
                    className="header-logo",
                ),
            ], className="header-left"),
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
    dcc.Interval(id="interval-eta", interval=1 * 1000, n_intervals=0),
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
    ],
    [Input("interval-act", "n_intervals")],
    [State("panel-snapshot", "data"),
     State("fermo-baseline-store", "data"),
     State("lote-finish-store", "data")],
)
def actualizar_panel(_, prev_snapshot, fermo_baseline_prev, lote_finish_prev):
    try:
        now = datetime.datetime.now()
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
                exportador = get_exportador_nombre(lote_actual) if lote_actual else None

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

        # Métricas (igual que el original)
        metricas = [
            construir_metric_card(
                "Cajas Turno",
                f"{formatear_entero(cajas_vaciadas)}",
                "acumulado turno",
                accent="#2563eb",
                theme="blue",
            ),
            construir_metric_card(
                "Cajas por Hora",
                formatear_entero(cajas_vaciadas // max(1, (datetime.datetime.now().hour - 8))),  # Simulado
                "cajas/h",
                accent="#7c3aed",
                theme="purple",
            ),
            construir_metric_card(
                "Kg por Proceso",
                f"{round(kg_totales):,}".replace(",", ".") if kg_totales else "0",
                "acumulado turno",
                accent="#f97316",
                theme="orange",
            ),
            construir_metric_card(
                "Kg por Hora",
                f"{round(kg_totales // max(1, (datetime.datetime.now().hour - 8))):,}".replace(",", ".") if kg_totales else "0",
                "kg/h",
                accent="#10b981",
                theme="green",
            ),
        ]

        # Gráfico de cajas
        pct_cajas = round(pct_cajas, 1)
        chart_cajas = [
            html.Div([
                html.Div("Cajas Vaciadas", className="chart-title"),
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
        ]

        # Gráfico de kg
        pct_kg_restantes = round((kg_restantes / max(1, kg_totales)) * 100, 1) if kg_totales > 0 else 0
        chart_kg = [
            html.Div([
                html.Div("Kilogramos Restantes", className="chart-title"),
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

            # Convertir columnas numéricas a string para filtrado
            for col in ["Cjs Planificadas", "Cjs Vaciadas", "Cjs Restantes", "Peso (Kg)"]:
                if col in df_detalle_para_tabla.columns:
                    df_detalle_para_tabla[col] = df_detalle_para_tabla[col].fillna('').astype(str)

            data = df_detalle_para_tabla.to_dict("records")
            columns = [{"name": c, "id": c, "type": "text"} for c in columnas_existentes]

            # Resaltar lote actual
            style_conditional = []
            if lote_actual and "Lote" in df_detalle_para_tabla.columns:
                for i, row in enumerate(data):
                    if str(row.get("Lote", "")).strip() == str(lote_actual).strip():
                        style_conditional.append({
                            "if": {"row_index": i},
                            "backgroundColor": "rgba(16,185,129,0.10)",
                            "fontWeight": "800",
                            "borderTop": "1px solid rgba(16,185,129,0.18)",
                            "borderBottom": "1px solid rgba(16,185,129,0.18)",
                        })
        else:
            data, columns, style_conditional = [], [], []

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
        )

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
    print(f"[MODE] Modo: {'DEMO' if is_demo_mode() else 'REAL'}")
    print(f"[DB] Base de datos: {config_db['description']}")

    if is_demo_mode():
        print("\n Para iniciar simulación de datos:")
        print("   python demo_simulation.py --mode continuous")
        print("\n Para cambiar a modo REAL:")
        print("   set MODO_OPERACION=REAL && python app_demo_fixed.py")

    app.run(debug=True, host="0.0.0.0", port=8050)