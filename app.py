"""
Aplicación principal en Dash - Panel Frutísima
Adaptación completa desde copy.py (Streamlit).
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
from dash import html, dcc, dash_table
from dash.dependencies import Output, Input, State
from flask import abort, send_from_directory

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=False)
except Exception:
    pass

from orden_vaciado import current_turn, load_orden_from_imap, shift_business_date

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

app = dash.Dash(__name__, title="Frutísima")
server = app.server

# Descargas (certificado CA local para HTTPS y scripts)
_DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "downloads")
_PUBLIC_HOSTNAME = (
    os.environ.get("DASH_PUBLIC_HOSTNAME")
    or os.environ.get("COMPUTERNAME")
    or "laptop-5v0qtdi3"
).lower()


@server.route("/downloads/<path:filename>")
def descargar_archivo(filename):
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename or ""):
        return abort(404)
    return send_from_directory(_DOWNLOADS_DIR, filename, as_attachment=True)


@server.route("/setup")
def setup_https_notifs():
    return (
        "<!doctype html><html lang='es'><head><meta charset='utf-8'/>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
        "<title>Configurar HTTPS / Notificaciones</title>"
        "<style>"
        "body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:24px;max-width:820px}"
        "code{background:#f4f4f4;padding:2px 6px;border-radius:6px}"
        ".card{border:1px solid #e6e6e6;border-radius:12px;padding:16px;margin:12px 0}"
        ".btn{display:inline-block;padding:10px 14px;border-radius:10px;border:1px solid #ddd;text-decoration:none}"
        ".btn.primary{background:#111;color:#fff;border-color:#111}"
        ".muted{color:#666}"
        "</style></head><body>"
        "<h2>Configurar HTTPS / Notificaciones</h2>"
        "<div class='card'>"
        "<div><b>Descarga única</b></div>"
        "<p class='muted'>Baja un ZIP con el instalador para Windows (admin) y el certificado (.crt) para otros dispositivos.</p>"
        "<a class='btn primary' href='/downloads/https-setup.zip'>Descargar paquete (ZIP)</a>"
        "</div>"
        "<div class='card'>"
        "<div><b>Luego</b></div>"
        f"<p class='muted'>Cierra y abre el navegador y entra por <code>https://{_PUBLIC_HOSTNAME}:8443/</code> (no <code>http://...:8050</code>).</p>"
        "</div>"
        "</body></html>"
    )

TURN_TIME_ICON_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" stroke="#ffffff"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"> <path d="M12 21C16.9706 21 21 16.9706 21 12C21 7.02944 16.9706 3 12 3C7.02944 3 3 7.02944 3 12C3 16.9706 7.02944 21 12 21Z" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path> <path d="M12 6V12" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path> <path d="M16.24 16.24L12 12" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path> </g></svg>"""

# Logging a archivo para diagnosticar "pegados" sin depender de la consola
_log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(_log_dir, exist_ok=True)
_log_path = os.path.join(_log_dir, "app.log")
_root_logger = logging.getLogger()
if not any(
    isinstance(h, RotatingFileHandler)
    and os.path.abspath(getattr(h, "baseFilename", "")) == os.path.abspath(_log_path)
    for h in _root_logger.handlers
):
    _file_handler = RotatingFileHandler(_log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    _file_handler.setLevel(logging.INFO)
    _file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    _root_logger.addHandler(_file_handler)
    if _root_logger.level > logging.INFO:
        _root_logger.setLevel(logging.INFO)
else:
    _file_handler = next(
        h
        for h in _root_logger.handlers
        if isinstance(h, RotatingFileHandler)
        and os.path.abspath(getattr(h, "baseFilename", "")) == os.path.abspath(_log_path)
    )

# Evitar ruido en consola: dejamos el detalle en logs/app.log
app.logger.propagate = False
app.logger.handlers = []
app.logger.addHandler(_file_handler)
app.logger.setLevel(logging.INFO)

_warnings_logger = logging.getLogger("warnings")
_warnings_logger.propagate = False
_warnings_logger.handlers = []
_warnings_logger.addHandler(_file_handler)
_warnings_logger.setLevel(logging.INFO)

def _warnings_to_log(message, category, filename, lineno, file=None, line=None):
    _warnings_logger.warning("%s:%s: %s: %s", filename, lineno, category.__name__, message)

warnings.showwarning = _warnings_to_log
warnings.filterwarnings(
    "once",
    message=r"pandas only supports SQLAlchemy connectable.*",
    category=UserWarning,
)

ENDLOTE_CHECK_S = 5
ORDEN_REFRESH_S = 60
_orden_cache = {"ts": 0.0, "data": None}
_exportador_cache = {"ts": 0.0, "lote": None, "value": None}
EXPORTADOR_CACHE_S = 120

try:
    _BIN_SIZE = int(os.environ.get("BIN_SIZE", "24") or "24")
except Exception:
    _BIN_SIZE = 24
if _BIN_SIZE <= 0:
    _BIN_SIZE = 24

# Detención por lote (estado en servidor para que sea consistente entre clientes y entre http/https)
_DET_LOCK = threading.Lock()
_DET_STATE = {"turn_key": None, "last_fermo": None, "map": {}}


def truncar_texto(valor, max_len=30):
    texto = str(valor) if valor is not None else "N/A"
    return texto[: max_len - 3] + "..." if len(texto) > max_len else texto


def formatear_entero(valor):
    try:
        return f"{int(round(float(valor))):,}".replace(",", ".")
    except Exception:
        return "0"


def _find_next_lote_from_orden(orden: dict, lote_actual: str):
    try:
        orden = orden or {}
        if not orden.get("ok"):
            return None
        rows = orden.get("rows") or []
        columns = orden.get("columns") or []
        visible_columns = [c for c in columns if c not in ("__row_type", "__section_title")]
        lote_col = next((c for c in visible_columns if "LOTE" in str(c).upper()), None)
        if not lote_col:
            return None
        data_rows = [r for r in rows if (r or {}).get("__row_type") == "data"]
        for i, r in enumerate(data_rows):
            if str((r or {}).get(lote_col, "")).strip() == str(lote_actual).strip():
                if i + 1 < len(data_rows):
                    nxt = str((data_rows[i + 1] or {}).get(lote_col, "")).strip()
                    return nxt or None
                return None
        return None
    except Exception:
        return None


def _lote_para_voz(lote) -> str:
    """
    Normaliza el lote para lectura por voz (ej: '000123' -> '123').
    Mantiene ceros internos; solo elimina ceros a la izquierda de grupos numéricos.
    """
    try:
        s = str(lote or "").strip()
        if not s:
            return "N/A"

        def norm(match: re.Match) -> str:
            digits = match.group(0)
            try:
                return str(int(digits))
            except Exception:
                return digits.lstrip("0") or "0"

        return re.sub(r"\d+", norm, s)
    except Exception:
        return str(lote or "N/A")


def _badge_md(text: str, class_name: str) -> str:
    safe = std_html.escape(str(text if text is not None else ""))
    return f'<span class="badge {class_name}">{safe}</span>'


def _parse_int_maybe(value):
    return int(round(_parse_float_maybe(value)))


def _parse_float_maybe(value):
    try:
        s = str(value or "").strip()
        if s == "":
            return 0.0
        s = s.replace(" ", "")

        # Heurística local-aware:
        # - Si vienen ambos separadores, el último suele ser decimal (ej: 12,345.67 o 12.345,67).
        # - Si viene uno, y tiene 3 dígitos a la derecha => separador de miles.
        # - Si no, se asume separador decimal.
        has_dot = "." in s
        has_comma = "," in s

        if has_dot and has_comma:
            last_dot = s.rfind(".")
            last_comma = s.rfind(",")
            decimal_sep = "." if last_dot > last_comma else ","
            thousands_sep = "," if decimal_sep == "." else "."
            s = s.replace(thousands_sep, "")
            s = s.replace(decimal_sep, ".")
            return float(s)

        if has_comma and not has_dot:
            left, right = s.split(",", 1)
            if right.isdigit() and len(right) == 3 and left.replace("-", "").isdigit():
                return float((left + right))
            return float((left + "." + right))

        if has_dot and not has_comma:
            left, right = s.split(".", 1)
            if right.isdigit() and len(right) == 3 and left.replace("-", "").isdigit():
                return float((left + right))
            return float((left + "." + right))

        return float(s)
    except Exception:
        return 0.0


def _parse_percent_maybe(value) -> float:
    try:
        s = str(value or "").strip()
        if s.endswith("%"):
            s = s[:-1].strip()
        v = _parse_float_maybe(s)
        if 0 < v <= 1:
            v = v * 100.0
        return v
    except Exception:
        return 0.0


def _fmt_hms_seconds(total_seconds: float) -> str:
    try:
        total_seconds = max(0, int(float(total_seconds or 0)))
    except Exception:
        total_seconds = 0
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


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


def _icon_iframe(icon_svg: str, class_name: str = ""):
    return html.Iframe(
        srcDoc=(
            "<!DOCTYPE html><html><head><style>"
            "html,body{margin:0;padding:0;background:transparent;overflow:hidden;width:100%;height:100%;}"
            "body{display:flex;align-items:center;justify-content:center;}"
            "svg{width:100%;height:100%;display:block;}"
            "</style></head><body>"
            f"{icon_svg}"
            "</body></html>"
        ),
        className=class_name,
        style={"border": "none", "width": "100%", "height": "100%", "pointerEvents": "none"},
    )


def _svg_with_color(svg: str, color: str) -> str:
    if not svg:
        return svg
    out = svg.replace("#ffffff", color).replace("#FFFFFF", color)
    out = out.replace('stroke="currentColor"', f'stroke="{color}"')
    out = out.replace('fill="currentColor"', f'fill="{color}"')
    return out


app.layout = html.Div(
    [
        html.Div(id="toast-container", className="toast-container"),
        dcc.Location(id="url", refresh=False),
        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("Configurar HTTPS / Notificaciones", className="modal-title"),
                                html.Button("×", id="setup-modal-close", className="modal-close", n_clicks=0),
                            ],
                            className="modal-header",
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div("Habilitar notificaciones", className="modal-subtitle"),
                                        html.Div(
                                            [
                                                "Esto solo se hace ",
                                                html.B("una vez"),
                                                " por dispositivo (PC o celular).",
                                            ],
                                            className="modal-hint",
                                        ),
                                        html.Div(
                                            [
                                                html.A(
                                                    "Descargar paquete (ZIP)",
                                                    href="/downloads/https-setup.zip",
                                                    className="modal-btn",
                                                ),
                                                html.Div(
                                                    "Incluye instalador Windows + certificado (.crt)",
                                                    className="modal-hint",
                                                ),
                                            ],
                                                    className="modal-actions",
                                        ),
                                        html.Div(
                                            [
                                                html.Div(
                                                    [html.Span("1", className="step-n"), html.Span("Descarga el ZIP", className="step-t")],
                                                    className="step",
                                                ),
                                                html.Div(
                                                    [
                                                        html.Span("2", className="step-n"),
                                                        html.Span(
                                                            "Windows: ejecuta el instalador (admin). Celular: abre el .crt y acepta/instala.",
                                                            className="step-t",
                                                        ),
                                                    ],
                                                    className="step",
                                                ),
                                                html.Div(
                                                    [
                                                        html.Span("3", className="step-n"),
                                                        html.Span(
                                                            [
                                                                "Abre ",
                                                                html.Code(f"https://{_PUBLIC_HOSTNAME}:8443/"),
                                                                " y permite las notificaciones cuando lo pida",
                                                            ],
                                                            className="step-t",
                                                        ),
                                                    ],
                                                    className="step",
                                                ),
                                            ],
                                            className="steps",
                                        ),
                                    ],
                                    className="modal-col modal-col-wide",
                                ),
                            ],
                            className="modal-body",
                        ),
                    ],
                    className="modal-card",
                ),
            ],
            id="setup-modal",
            className="modal-overlay",
            style={"display": "none"},
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    html.Img(
                                        src="/assets/logo.svg",
                                        alt="Frutísima",
                                        className="header-logo-img",
                                    ),
                                    className="header-logo",
                                ),
                            ],
                            className="header-left",
                        ),
                        html.Div(
                            [
                                html.Div(
                                    dcc.Checklist(
                                        id="notif-browser-toggle",
                                        options=[{"label": "Notificación en este PC", "value": "on"}],
                                        value=[],
                                        persistence=True,
                                        persistence_type="local",
                                    ),
                                    className="update-badge header-toggle",
                                    style={"display": "none"},
                                ),
                                html.Div(
                                    [
                                        html.Span("Notificar lote completo", className="toggle-title"),
                                        html.Div(
                                            [
                                                html.Div(
                                                    dcc.Checklist(
                                                        id="notif-endlote-toggle",
                                                        options=[
                                                            {
                                                                "label": html.Img(
                                                                    src="/assets/notification.png",
                                                                    alt="Notificación",
                                                                    className="toggle-icon-img",
                                                                    title="Activar notificación (popup) al terminar el lote",
                                                                ),
                                                                "value": "on",
                                                            }
                                                        ],
                                                        value=[],
                                                        persistence=True,
                                                        persistence_type="local",
                                                    ),
                                                    id="notif-endlote-wrap",
                                                    className="icon-toggle icon-toggle-notif",
                                                ),
                                                html.Div(
                                                    dcc.Checklist(
                                                        id="tts-toggle",
                                                        options=[
                                                            {
                                                                "label": html.Img(
                                                                    src="/assets/megaphone.png",
                                                                    alt="Sonido",
                                                                    className="toggle-icon-img",
                                                                    title="Activar aviso (voz) al terminar el lote",
                                                                ),
                                                                "value": "on",
                                                            }
                                                        ],
                                                        value=[],
                                                        persistence=True,
                                                        persistence_type="local",
                                                    ),
                                                    id="tts-wrap",
                                                    className="icon-toggle icon-toggle-sound",
                                                ),
                                            ],
                                            className="toggle-icons",
                                        ),
                                        html.Div(id="notif-https-hint", className="toggle-help-hint"),
                                        html.Div(
                                            [
                                                html.Button(
                                                    "Configurar HTTPS / Notificaciones",
                                                    id="setup-modal-open",
                                                    n_clicks=0,
                                                    className="toggle-help-link",
                                                )
                                            ],
                                            className="toggle-help",
                                        ),
                                    ],
                                    className="update-badge header-toggle notif-group",
                                ),
                            ],
                            className="header-actions",
                        ),
                        html.Div(
                            [
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
                            ],
                            className="header-stats",
                        ),
                    ],
                    className="header-content",
                )
            ],
            className="main-header",
        ),
        html.Div(id="metricas-lote", className="metric-grid"),
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
        # Contenedores de ambos tabs siempre presentes para evitar errores de callbacks
        html.Div(
            [
                html.Div(id="filtros-actuales", className="filter-card"),
                html.Div(
                    [
                        html.Div(id="chart-cajas", className="chart-card"),
                        html.Div(id="chart-kg", className="chart-card"),
                    ],
                    className="charts-grid",
                    id="charts-wrapper",
                ),
            ],
            id="tab-analisis-container",
        ),
        html.Div(
            [
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
            ],
            id="tab-detalle-container",
            style={"margin": "0 1.5rem 2rem 1.5rem"},
        ),
        html.Div(
            [
                html.Div(id="orden-meta", className="filter-card"),
                html.Div(id="orden-accordion", className="orden-accordion"),
            ],
            id="tab-orden-container",
            style={"margin": "0 1.5rem 2rem 1.5rem", "display": "none"},
        ),
        dcc.Interval(id="interval-act", interval=5 * 1000, n_intervals=0),
        dcc.Interval(id="interval-notif", interval=ENDLOTE_CHECK_S * 1000, n_intervals=0),
        dcc.Interval(id="interval-eta", interval=1 * 1000, n_intervals=0),
        dcc.Interval(id="interval-orden", interval=ORDEN_REFRESH_S * 1000, n_intervals=0),
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
        # Compatibilidad: antes este store era local y era output del callback principal.
        # Lo mantenemos para evitar errores en clientes con caché antiguo.
        dcc.Store(id="det-por-lote-store"),
        dcc.Store(id="setup-modal-open-store", data=False),
    ],
    className="app-root",
)

app.clientside_callback(
    """
    function(href, notifValue, ttsValue){
        const secure = (window.isSecureContext && window.location && window.location.protocol === "https:");
        const disabledStyle = secure ? {} : {opacity: 0.35, filter: "grayscale(1)", pointerEvents: "none"};
        const hint = secure ? "" : "Disponible solo por HTTPS (https://laptop-5v0qtdi3:8443/)";
        const no_update = window.dash_clientside && window.dash_clientside.no_update;
        const nextNotif = secure ? (notifValue || []) : [];
        const nextTts = secure ? (ttsValue || []) : [];
        const setupStyle = secure ? {display:"none"} : {};
        return [disabledStyle, disabledStyle, nextNotif, nextTts, hint, setupStyle];
    }
    """,
    Output("notif-endlote-wrap", "style"),
    Output("tts-wrap", "style"),
    Output("notif-endlote-toggle", "value"),
    Output("tts-toggle", "value"),
    Output("notif-https-hint", "children"),
    Output("setup-modal-open", "style"),
    Input("url", "href"),
    State("notif-endlote-toggle", "value"),
    State("tts-toggle", "value"),
)


@app.callback(
    Output("setup-modal-open-store", "data"),
    Input("setup-modal-open", "n_clicks"),
    Input("setup-modal-close", "n_clicks"),
    State("setup-modal-open-store", "data"),
    prevent_initial_call=True,
)
def _toggle_setup_modal(open_clicks, close_clicks, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open
    trig = ctx.triggered[0].get("prop_id", "")
    if trig.startswith("setup-modal-open"):
        return True
    if trig.startswith("setup-modal-close"):
        return False
    return is_open


@app.callback(Output("setup-modal", "style"), Input("setup-modal-open-store", "data"))
def _render_setup_modal(is_open):
    return {"display": "flex"} if is_open else {"display": "none"}

app.clientside_callback(
    """
    function(_, eta) {
        function pad2(n){ return String(n).padStart(2,'0'); }
        function fmtDMY(d){
            return pad2(d.getDate()) + "/" + pad2(d.getMonth()+1) + "/" + d.getFullYear();
        }
        function fmtHMSClock(d){
            return pad2(d.getHours()) + ":" + pad2(d.getMinutes()) + ":" + pad2(d.getSeconds());
        }
        function fmtHMS(totalSeconds){
            totalSeconds = Math.max(0, Math.floor(totalSeconds));
            const h = Math.floor(totalSeconds / 3600);
            const m = Math.floor((totalSeconds % 3600) / 60);
            const s = totalSeconds % 60;
            return pad2(h) + ":" + pad2(m) + ":" + pad2(s);
        }
        if (!eta || typeof eta.remaining_s !== "number" || typeof eta.generated_ms !== "number") {
            return "--:--:--";
        }
        const elapsed = (Date.now() - eta.generated_ms) / 1000.0;
        const remaining = eta.remaining_s - elapsed;
        const now = new Date();
        // Mismo "lineamiento" de formato: fecha actual + temporizador.
        return fmtDMY(now) + " " + fmtHMS(remaining);
    }
    """,
    Output("eta-lote", "children"),
    Input("interval-eta", "n_intervals"),
    State("eta-store", "data"),
)

# Debug en consola del navegador: logs cada tick + snapshot resumido
app.clientside_callback(
    """
    function(n, snap) {
        try {
            const s = snap || {};
            const k = (s.kpis || {});
            const t = (s.table || {});
            console.log("[dash] tick", n, {
                lote: k.lote,
                pct_cajas: k.pct_cajas,
                pct_kg_restantes: k.pct_kg_restantes,
                table: t,
                errors: (s.errors || []),
                dur: (performance && performance.now) ? performance.now() : null
            });
        } catch (e) {
            console.warn("[dash] tick log error", e);
        }
        return (n === undefined || n === null) ? window.dash_clientside.no_update : n;
    }
    """,
    Output("client-debug-store", "data"),
    Input("interval-act", "n_intervals"),
    State("panel-snapshot", "data"),
)

app.clientside_callback(
    """
    function(toggleValue) {
        const enabled = Array.isArray(toggleValue) && toggleValue.indexOf("on") !== -1;
        try {
            if (enabled && ("Notification" in window)) {
                if (Notification.permission === "default") {
                    Notification.requestPermission();
                }
            }
        } catch (e) {}
        return { enabled: enabled, permission: (("Notification" in window) ? Notification.permission : "unsupported") };
    }
    """,
    Output("notif-permission-store", "data"),
    Input("notif-endlote-toggle", "value"),
)

app.clientside_callback(
    """
    function(notifToggleValue, ttsToggleValue, prev) {
        function isOn(v){ return Array.isArray(v) && v.indexOf("on") !== -1; }
        const now = { notif: isOn(notifToggleValue), tts: isOn(ttsToggleValue) };
        const before = (prev && typeof prev === "object") ? prev : null;
        const changes = [];
        if (before) {
            if (before.notif !== now.notif) changes.push({ k: "notif", on: now.notif });
            if (before.tts !== now.tts) changes.push({ k: "tts", on: now.tts });
        }
        if (!changes.length) return now;

        const lines = changes.map(c => {
            if (c.k === "notif") return c.on ? "Notificación habilitada" : "Notificación deshabilitada";
            return c.on ? "Aviso fin de lote habilitado" : "Aviso fin de lote deshabilitado";
        });

        try {
            const host = document.getElementById("toast-container");
            if (host) {
                if (window.__toastTimer) clearTimeout(window.__toastTimer);
                while (host.firstChild) host.removeChild(host.firstChild);

                const toast = document.createElement("div");
                toast.className = "toast toast-show";

                lines.forEach(function(t){
                    const line = document.createElement("div");
                    line.className = "toast-line";
                    const txt = String(t || "");
                    const isOff = /deshabilitad[oa]$/i.test(txt);
                    const isOn_ = /habilitad[oa]$/i.test(txt) && !isOff;
                    if (isOn_ || isOff) {
                        const parts = txt.split(/\\s+/);
                        const last = parts.pop();
                        const prefix = parts.join(" ");
                        const s1 = document.createElement("span");
                        s1.className = "toast-text";
                        s1.textContent = prefix + " ";
                        const s2 = document.createElement("span");
                        s2.className = "toast-status " + (isOn_ ? "on" : "off");
                        s2.textContent = last;
                        line.appendChild(s1);
                        line.appendChild(s2);
                    } else {
                        line.textContent = txt;
                    }
                    toast.appendChild(line);
                });

                host.appendChild(toast);
                window.__toastTimer = setTimeout(function(){
                    try { while (host.firstChild) host.removeChild(host.firstChild); } catch (e) {}
                }, 2600);
            }
        } catch (e) {}
        return now;
    }
    """,
    Output("toggle-toast-store", "data"),
    Input("notif-endlote-toggle", "value"),
    Input("tts-toggle", "value"),
    State("toggle-toast-store", "data"),
)

app.clientside_callback(
    """
    function(payload, notifToggleValue, ttsToggleValue, perm) {
        const __secureCtx = (window.isSecureContext === true) || (location && (location.hostname === "localhost" || location.hostname === "127.0.0.1"));
        function __toast(lines){
            try{
                const host = document.getElementById("toast-container");
                if (!host) return;
                if (window.__toastTimer) clearTimeout(window.__toastTimer);
                while (host.firstChild) host.removeChild(host.firstChild);
                const toast = document.createElement("div");
                toast.className = "toast toast-show";
                (lines || []).forEach(function(t){
                    const line = document.createElement("div");
                    line.className = "toast-line";
                    line.textContent = String(t || "");
                    toast.appendChild(line);
                });
                host.appendChild(toast);
                window.__toastTimer = setTimeout(function(){
                    try { while (host.firstChild) host.removeChild(host.firstChild); } catch (e) {}
                }, 3500);
            }catch(e){}
        }
        function __beep(){
            try{
                const AudioCtx = window.AudioContext || window.webkitAudioContext;
                if (!AudioCtx) return false;
                const ctx = new AudioCtx();
                const o = ctx.createOscillator();
                const g = ctx.createGain();
                o.type = "sine";
                o.frequency.value = 880;
                g.gain.value = 0.08;
                o.connect(g); g.connect(ctx.destination);
                o.start();
                setTimeout(function(){ try{ o.stop(); ctx.close(); }catch(e){} }, 300);
                return true;
            }catch(e){ return false; }
        }
        const notifEnabled = Array.isArray(notifToggleValue) && notifToggleValue.indexOf("on") !== -1;
        const ttsEnabled = Array.isArray(ttsToggleValue) && ttsToggleValue.indexOf("on") !== -1;
        if (!payload) return window.dash_clientside.no_update;
        const titleToast = String(payload.title || "Frutísima").trim();
        const msgToast = String(payload.message || "").trim().replace(/\\s*\\n\\s*/g, " · ").replace(/\\s+/g, " ").trim();
        try {
            if (notifEnabled) {
                const title = String(payload.title || "Frutísima").trim();
                const rawBody = String(payload.message || "").trim();
                const parts = rawBody
                    .split(/\\r?\\n+/g)
                    .map(s => s.trim())
                    .filter(Boolean);
                const body = parts.join(" · ");
                const kind = String(payload.kind || "default");
                const options = {
                    body: body,
                    icon: "/assets/logo.svg",
                    badge: "/assets/logo.svg",
                    tag: "frutisima-" + kind,
                    renotify: true,
                    silent: false,
                    requireInteraction: (kind === "endlote"),
                };
                new Notification(title, options);
            }
        } catch (e) {}
        try {
            if (ttsEnabled && payload.kind === "endlote" && ("speechSynthesis" in window) && ("SpeechSynthesisUtterance" in window)) {
                const raw = payload.voice || payload.message || payload.title || "";
                const text = String(raw)
                    .replace(/\\s*\\n\\s*/g, ". ")
                    .replace(/\\s+/g, " ")
                    .trim();
                if (text) {
                    window.speechSynthesis.cancel();
                    const u = new SpeechSynthesisUtterance(text);
                    u.lang = "es-ES";
                    try {
                        const voices = window.speechSynthesis.getVoices ? window.speechSynthesis.getVoices() : [];
                        const es = (voices || []).find(v => (v.lang || "").toLowerCase().startsWith("es"));
                        if (es) u.voice = es;
                    } catch (e) {}
                    window.speechSynthesis.speak(u);
                }
            }
        } catch (e) {}
        return true;
    }
    """,
    Output("notif-payload-store", "clear_data"),
    Input("notif-payload-store", "data"),
    State("notif-endlote-toggle", "value"),
    State("tts-toggle", "value"),
    State("notif-permission-store", "data"),
    prevent_initial_call=True,
)


@app.callback(
    [
        Output("tab-analisis-container", "style"),
        Output("tab-detalle-container", "style"),
        Output("tab-orden-container", "style"),
    ],
    Input("tabs", "value"),
)
def render_tab(tab_value):
    if tab_value == "tab-detalle":
        return {"display": "none"}, {"display": "block", "margin": "0 1.5rem 2rem 1.5rem"}, {"display": "none"}
    if tab_value == "tab-orden":
        return {"display": "none"}, {"display": "none"}, {"display": "block", "margin": "0 1.5rem 2rem 1.5rem"}
    return {"display": "block"}, {"display": "none"}, {"display": "none"}


@app.callback(
    Output("orden-store", "data"),
    Input("interval-orden", "n_intervals"),
)
def actualizar_orden(_):
    try:
        turno_info = get_turno_corrente_info()
        if turno_info and turno_info.get("turn") in (1, 2) and turno_info.get("business_date"):
            expected_turn = int(turno_info["turn"])
            expected_business_date = str(turno_info["business_date"])
            forced_time = datetime.time(10, 0, 0) if expected_turn == 1 else datetime.time(21, 0, 0)
            now_dt = datetime.datetime.combine(datetime.date.fromisoformat(expected_business_date), forced_time)
        else:
            now_dt = datetime.datetime.now()
            expected_turn = current_turn(now_dt)
            expected_business_date = shift_business_date(now_dt).isoformat()

        lote_detalle = get_current_lote_from_detalle()
        lote_actual = None
        try:
            lote_actual = (lote_detalle or {}).get("Lote")
        except Exception:
            lote_actual = None

        lotes_context = []
        try:
            detalle_df = get_detalle_lotti_ingresso()
            if detalle_df is not None and hasattr(detalle_df, "__getitem__") and "Lote" in getattr(detalle_df, "columns", []):
                raw_lotes = [str(x).strip() for x in detalle_df["Lote"].dropna().tolist()]
                seen = set()
                for x in raw_lotes:
                    if not x or x in seen:
                        continue
                    seen.add(x)
                    lotes_context.append(x)
                    if len(lotes_context) >= 30:
                        break
        except Exception:
            lotes_context = []
        ahora = time.time()
        cached = _orden_cache.get("data")
        if (
            cached
            and cached.get("turn") == expected_turn
            and cached.get("business_date") == expected_business_date
            and (ahora - float(_orden_cache.get("ts") or 0.0)) < (ORDEN_REFRESH_S * 0.90)
        ):
            return cached

        data = load_orden_from_imap(now=now_dt, lote_actual=lote_actual, lotes_context=lotes_context)
        if data and data.get("ok"):
            _orden_cache["ts"] = ahora
            _orden_cache["data"] = data
        return data
    except Exception as e:
        cached = _orden_cache.get("data")
        if cached:
            cached2 = dict(cached)
            cached2["warn"] = f"No se pudo actualizar orden: {e}"
            return cached2
        return {"ok": False, "error": f"Error al leer orden: {e}", "columns": [], "rows": [], "meta": {}}


@app.callback(
    Output("orden-meta", "children"),
    Output("orden-accordion", "children"),
    Input("orden-store", "data"),
)
def render_orden(orden):
    orden = orden or {}
    if not orden.get("ok"):
        err = orden.get("error", "Sin datos")
        return html.Div([html.Div("Orden de Vaciado", className="filter-title"), html.Div(err)]), []

    meta = orden.get("meta") or {}
    sheet = orden.get("sheet") or "N/A"
    turn = orden.get("turn") or "N/A"
    total_kilos = orden.get("total_kilos")
    attachment = meta.get("attachment_filename") or "N/A"
    subject = meta.get("email_subject") or "N/A"
    date = meta.get("email_date") or "N/A"

    email_time_txt = "N/A"
    try:
        dt = email.utils.parsedate_to_datetime(date) if isinstance(date, str) else None
        if dt is not None:
            email_time_txt = dt.strftime("%H:%M")
    except Exception:
        email_time_txt = "N/A"

    total_kg_int = int(round(_parse_float_maybe(total_kilos))) if total_kilos is not None else 0
    header = html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("HOJA", className="orden-meta-label"),
                            html.Div(str(sheet), className="orden-meta-value"),
                            html.Div(_icon_iframe(FILE_ICON_SVG, class_name="orden-meta-icon-svg"), className="orden-meta-icon orden-meta-icon-blue"),
                        ],
                        className="orden-meta-item",
                    ),
                    html.Div(
                        [
                            html.Div("TURNO", className="orden-meta-label"),
                            html.Div(str(turn), className="orden-meta-value"),
                            html.Div(_icon_iframe(CLOCK_ICON_SVG, class_name="orden-meta-icon-svg"), className="orden-meta-icon orden-meta-icon-amber"),
                        ],
                        className="orden-meta-item",
                    ),
                    html.Div(
                        [
                            html.Div("KILOS TOTALES", className="orden-meta-label"),
                            html.Div(f"{formatear_entero(total_kg_int)} kg", className="orden-meta-value"),
                            html.Div(_icon_iframe(KILOS_ICON_SVG, class_name="orden-meta-icon-svg"), className="orden-meta-icon orden-meta-icon-green"),
                        ],
                        className="orden-meta-item orden-meta-highlight",
                    ),
                    html.Div(
                        [
                            html.Div("HORA CORREO", className="orden-meta-label"),
                            html.Div(email_time_txt, className="orden-meta-value"),
                            html.Div(_icon_iframe(MAIL_ICON_SVG, class_name="orden-meta-icon-svg"), className="orden-meta-icon orden-meta-icon-rose"),
                        ],
                        className="orden-meta-item",
                    ),
                ],
                className="orden-meta-grid",
            )
        ]
    )

    rows = orden.get("rows") or []
    all_columns = orden.get("columns") or []
    visible_columns = [c for c in all_columns if c not in ("__row_type", "__section_title")]

    lote_col = next((c for c in visible_columns if "LOTE" in str(c).upper()), None)
    envases_col = next((c for c in visible_columns if "ENVAS" in str(c).upper()), None)
    kilos_col = next((c for c in visible_columns if "KILO" in str(c).upper()), None)

    lote_actual = None
    try:
        lote_detalle = get_current_lote_from_detalle()
        if lote_detalle and lote_detalle.get("Lote"):
            lote_actual = str(lote_detalle.get("Lote")).strip()
        else:
            current_record = get_current_record()
            if current_record and current_record.get("Lote"):
                lote_actual = str(current_record.get("Lote")).strip()
    except Exception:
        lote_actual = None

    sections = []
    current_title = None
    current_data = []

    def flush_section():
        nonlocal current_title, current_data
        if current_title is None and not current_data:
            return

        title = (current_title or "ORDEN DE VACIADO").strip()

        lotes = set()
        if lote_col:
            for r in current_data:
                v = str(r.get(lote_col, "") or "").strip()
                if v:
                    lotes.add(v)

        lotes_count = len(lotes) if lotes else 0
        envases_sum = sum(_parse_int_maybe(r.get(envases_col)) for r in current_data) if envases_col else 0
        kilos_sum = sum(_parse_float_maybe(r.get(kilos_col)) for r in current_data) if kilos_col else 0.0

        cols = [{"name": c, "id": c} for c in visible_columns]
        style_conditional = []
        percent_cols = [c for c in visible_columns if ("%" in str(c)) or ("PORC" in str(c).upper())]
        badge_cols = set([c for c in (lote_col,) if c] + list(percent_cols))

        # Fila destacada del lote actual (por índice, para no depender del HTML/markdown)
        if lote_actual and lote_col:
            normalized_current = _lote_para_voz(lote_actual)
            match_rows = []
            for i, r in enumerate(current_data):
                raw = r.get(lote_col, "")
                if _lote_para_voz(raw) == normalized_current:
                    match_rows.append(i)
            for i in match_rows:
                style_conditional.append(
                    {
                        "if": {"row_index": i},
                        "backgroundColor": "rgba(16,185,129,0.10)",
                        "fontWeight": "800",
                        "borderTop": "1px solid rgba(16,185,129,0.18)",
                        "borderBottom": "1px solid rgba(16,185,129,0.18)",
                    }
                )

        # Badge via clase CSS (markdown con HTML)
        # - Lote: azul, resaltando el lote actual
        # - %: verde (mejor), ámbar (medio), rojo (peor)
        # - Segregación: rojo si "SI", verde si "NO"
        if badge_cols:
            new_cols = []
            for col in cols:
                if col["id"] in badge_cols:
                    new_cols.append({**col, "presentation": "markdown"})
                else:
                    new_cols.append(col)
            cols = new_cols

            for r in current_data:
                if lote_col:
                    raw_lote = r.get(lote_col, "")
                    lote_cls = "badge-gray"
                    if lote_actual and str(raw_lote).strip() == str(lote_actual).strip():
                        lote_cls = "badge-gray badge-strong"
                    r[lote_col] = _badge_md(raw_lote, lote_cls)

                for c in percent_cols:
                    raw = r.get(c, "")
                    v = _parse_percent_maybe(raw)
                    if v >= 80:
                        pct_cls = "badge-green"
                    elif v >= 70:
                        pct_cls = "badge-amber"
                    else:
                        pct_cls = "badge-red"
                    r[c] = _badge_md(raw if str(raw).strip() != "" else f"{v:.0f}%", pct_cls)

        # (la fila destacada se maneja por row_index arriba)

        sections.append(
            html.Details(
                [
                    html.Summary(
                        [
                            html.Div("▦", className="orden-accordion-icon"),
                            html.Div(
                                [
                                    html.Div(title, className="orden-accordion-title"),
                                    html.Div(
                                        [
                                            html.Span(
                                                [
                                                    html.Span(_icon_iframe(STACK_ICON_SVG, class_name="orden-accordion-miniicon-svg"), className="orden-accordion-miniicon"),
                                                    html.Span(f"{lotes_count} lotes"),
                                                ],
                                                className="orden-accordion-metric",
                                            ),
                                            html.Span(
                                                [
                                                    html.Span(
                                                        _icon_iframe(_svg_with_color(BOXES_EMPTIED_ICON_SVG, "#0f172a"), class_name="orden-accordion-miniicon-svg"),
                                                        className="orden-accordion-miniicon",
                                                    ),
                                                    html.Span(f"{formatear_entero(envases_sum)} envases"),
                                                ],
                                                className="orden-accordion-metric",
                                            ),
                                            html.Span(
                                                [
                                                    html.Span(_icon_iframe(KILOS_ICON_SVG, class_name="orden-accordion-miniicon-svg"), className="orden-accordion-miniicon"),
                                                    html.Span(f"{formatear_entero(kilos_sum)} kg"),
                                                ],
                                                className="orden-accordion-metric orden-accordion-metric-kg",
                                            ),
                                        ],
                                        className="orden-accordion-subtitle orden-accordion-metrics",
                                    ),
                                ],
                                className="orden-accordion-text",
                            ),
                            html.Div("⌄", className="orden-accordion-caret"),
                        ],
                        className="orden-accordion-summary",
                    ),
                    html.Div(
                        dash_table.DataTable(
                            data=current_data,
                            columns=cols,
                            markdown_options={"html": True},
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
                            style_data_conditional=style_conditional,
                        ),
                        className="orden-accordion-body",
                    ),
                ],
                className="orden-accordion-item",
                open=False,
            )
        )

        current_title = None
        current_data = []

    for r in rows:
        if r.get("__row_type") == "section":
            flush_section()
            current_title = (r.get("__section_title") or "").strip() or next(
                (str(v).strip() for k, v in r.items() if k not in ("__row_type", "__section_title") and str(v).strip()),
                "ORDEN DE VACIADO",
            )
            continue
        if r.get("__row_type") == "data" or "__row_type" not in r:
            current_data.append({c: r.get(c, "") for c in visible_columns})

    flush_section()

    return header, sections


@app.callback(
    [
        Output("hora-actual", "children"),
        Output("refresh-indicator", "children"),
        Output("eta-store", "data"),
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
    Input("interval-act", "n_intervals"),
    State("panel-snapshot", "data"),
    State("fermo-baseline-store", "data"),
    State("lote-finish-store", "data"),
)
def actualizar_panel(_, prev_snapshot, fermo_baseline_prev, lote_finish_prev):
    start_ts = datetime.datetime.now()
    t0 = time.perf_counter()
    datos_lote = None
    filtros = {}
    lote_actual = None
    fermo_min = 0.0
    lotti_time_map = {}

    def _log_timing(step: str, t_start: float, extra: str = ""):
        dt = time.perf_counter() - t_start
        msg = f"[tick={_}] {step} {dt:.3f}s{(' ' + extra) if extra else ''}"
        if dt >= 2.0:
            app.logger.warning(msg)
        else:
            app.logger.info(msg)
        return dt
    try:
        app.logger.info(f"actualizar_panel tick start [tick={_}]")
        now = datetime.datetime.now()
        hora = now.strftime("%d/%m/%Y %H:%M:%S")

        ts = time.perf_counter()
        current_record = get_current_record()
        _log_timing("get_current_record", ts)

        ts = time.perf_counter()
        lote_detalle = get_current_lote_from_detalle()
        _log_timing("get_current_lote_from_detalle", ts)

        if lote_detalle:
            datos_lote = lote_detalle
            productor = current_record["Productor"] if current_record else "N/A"
        else:
            datos_lote = current_record
            productor = current_record["Productor"] if current_record else "N/A"

        lote_actual = datos_lote["Lote"] if datos_lote and datos_lote.get("Lote") else None
        exportador = None
        try:
            prev_kpis = (prev_snapshot or {}).get("kpis") if isinstance(prev_snapshot, dict) else None
            prev_filtros = (prev_snapshot or {}).get("filtros") if isinstance(prev_snapshot, dict) else None
            prev_lote = (prev_kpis or {}).get("lote") if isinstance(prev_kpis, dict) else None
            prev_exportador = (prev_filtros or {}).get("Exportador") if isinstance(prev_filtros, dict) else None

            cache_value = _exportador_cache.get("value")
            cache_ok = (
                cache_value
                and str(cache_value).strip().upper() != "N/A"
                and _exportador_cache.get("lote") == lote_actual
                and (time.time() - float(_exportador_cache.get("ts") or 0.0)) <= EXPORTADOR_CACHE_S
            )
            if cache_ok:
                exportador = _exportador_cache["value"]
            elif lote_actual and prev_lote == str(lote_actual) and prev_exportador and str(prev_exportador).strip().upper() != "N/A":
                exportador = prev_exportador
                _exportador_cache.update({"ts": time.time(), "lote": lote_actual, "value": exportador})
            else:
                ts = time.perf_counter()
                exportador = get_exportador_nombre(lote_actual)
                _log_timing("get_exportador_nombre", ts, extra=f"lote={lote_actual}")
                if exportador and str(exportador).strip().upper() != "N/A":
                    _exportador_cache.update({"ts": time.time(), "lote": lote_actual, "value": exportador})
        except Exception as e:
            errors.append(f"get_exportador_nombre: {e}")
            exportador = (
                (prev_exportador if prev_exportador and str(prev_exportador).strip().upper() != "N/A" else None)
                or (_exportador_cache.get("value") if _exportador_cache.get("value") and str(_exportador_cache.get("value")).strip().upper() != "N/A" else None)
                or "N/A"
            )

        filtros = {
            "Exportador": exportador,
            "Productor": productor,
            "Variedad": datos_lote["Variedad"] if datos_lote else "N/A",
            "Proceso": datos_lote["Proceso"] if datos_lote else "N/A",
            "Lote": datos_lote["Lote"] if datos_lote else "N/A",
        }
        filtros = {k: truncar_texto(v) for k, v in filtros.items()}

        cajas_totales = cajas_vaciadas = cajas_restantes = 0
        cajas_restantes_calc = 0
        kg_totales = kg_vaciados = kg_restantes = 0
        pct_vaciadas = pct_restantes = 0

        if datos_lote:
            cajas_totales = int(datos_lote.get("UnitaPianificate", 0) or 0)
            cajas_vaciadas = int(datos_lote.get("UnitaSvuotate", 0) or 0)
            # Mantener el valor real (puede ser -1 segÃºn BD), pero para cÃ¡lculos usar >= 0.
            cajas_restantes = int(datos_lote.get("UnitaRestanti", 0) or 0)
            cajas_restantes_calc = max(0, cajas_restantes)

            ts = time.perf_counter()
            kg_totales = get_kg_total_lote(datos_lote.get("Lote"))
            _log_timing("get_kg_total_lote", ts, extra=f"lote={lote_actual}")
            if kg_totales == 0:
                if datos_lote.get("PesoNetto", 0) > 0:
                    kg_totales = float(datos_lote["PesoNetto"])
                else:
                    ts = time.perf_counter()
                    kg_totales = get_kg_lote_vw_partita(
                        datos_lote.get("Lote"), datos_lote.get("Proceso")
                    )
                    _log_timing("get_kg_lote_vw_partita", ts, extra=f"lote={lote_actual}")
                    if kg_totales == 0:
                        ts = time.perf_counter()
                        kg_totales = get_kg_lote(datos_lote.get("Lote"), datos_lote.get("Proceso"))
                        _log_timing("get_kg_lote", ts, extra=f"lote={lote_actual}")

            ts = time.perf_counter()
            kg_por_caja = get_kg_por_caja_lote(datos_lote.get("Lote"))
            _log_timing("get_kg_por_caja_lote", ts, extra=f"lote={lote_actual}")
            if kg_por_caja == 0 and cajas_totales > 0 and kg_totales > 0:
                kg_por_caja = kg_totales / cajas_totales

            if kg_por_caja > 0:
                kg_restantes = kg_por_caja * cajas_restantes_calc
                kg_vaciados = kg_totales - kg_restantes
            else:
                if cajas_totales > 0 and kg_totales > 0:
                    kg_restantes = (kg_totales * cajas_restantes_calc) / cajas_totales
                    kg_vaciados = kg_totales - kg_restantes

            pct_vaciadas = (cajas_vaciadas / cajas_totales * 100) if cajas_totales > 0 else 0
            pct_restantes = (cajas_restantes_calc / cajas_totales * 100) if cajas_totales > 0 else 0
        elapsed = (datetime.datetime.now() - start_ts).total_seconds()
        app.logger.info(f"actualizar_panel ok ({elapsed:.2f}s) [tick={_}] total={(time.perf_counter()-t0):.3f}s")
    except Exception as e:
        # Si algo falla, log y placeholders visibles
        elapsed = (datetime.datetime.now() - start_ts).total_seconds()
        app.logger.exception(f"ERROR en actualizar_panel ({elapsed:.2f}s) [tick={_}] total={(time.perf_counter()-t0):.3f}s: {e}")
        hora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        datos_lote = None
        filtros = {
            "Exportador": "N/A",
            "Productor": "N/A",
            "Variedad": "N/A",
            "Proceso": "N/A",
            "Lote": "N/A",
        }
        cajas_totales = cajas_vaciadas = cajas_restantes = 0
        kg_totales = kg_vaciados = kg_restantes = 0
        pct_vaciadas = pct_restantes = 0
        lote_actual = None

    # Métricas superiores (4 cards)
    errors = []

    # Detención total del turno (minutos) + mapa de inicio/fin de lotes (histórico)
    try:
        ts = time.perf_counter()
        fermo_min = float(get_fermo_macchina_minuti() or 0.0)
        _log_timing("get_fermo_macchina_minuti", ts, extra=f"min={fermo_min:.2f}")
    except Exception as e:
        fermo_min = 0.0
        errors.append(f"get_fermo_macchina_minuti: {e}")

    try:
        ts = time.perf_counter()
        lotti_time_map = get_lotti_inizio_fine_map() or {}
        _log_timing("get_lotti_inizio_fine_map", ts, extra=f"rows={len(lotti_time_map)}")
    except Exception as e:
        lotti_time_map = {}
        errors.append(f"get_lotti_inizio_fine_map: {e}")

    if datos_lote:
        try:
            ts = time.perf_counter()
            cajas_turno = get_cajas_por_turno()
            _log_timing("get_cajas_por_turno", ts)
        except Exception as e:
            cajas_turno = 0
            errors.append(f"get_cajas_por_turno: {e}")

        try:
            ts = time.perf_counter()
            cajas_hora = get_cajas_por_hora_turno()
            _log_timing("get_cajas_por_hora_turno", ts)
        except Exception as e:
            cajas_hora = 0
            errors.append(f"get_cajas_por_hora_turno: {e}")

        try:
            ts = time.perf_counter()
            kg_turno = get_kg_por_turno()
            _log_timing("get_kg_por_turno", ts)
        except Exception as e:
            kg_turno = 0
            errors.append(f"get_kg_por_turno: {e}")

        try:
            ts = time.perf_counter()
            kg_hora = get_kg_por_hora_turno()
            _log_timing("get_kg_por_hora_turno", ts)
        except Exception as e:
            kg_hora = 0
            errors.append(f"get_kg_por_hora_turno: {e}")
    else:
        cajas_turno = cajas_hora = kg_turno = kg_hora = 0
    eta_store = None
    cajas_restantes_eta = max(0, int(cajas_restantes or 0))
    if datos_lote and lote_actual and cajas_restantes_eta > 0 and cajas_hora > 0:
        eta_s = int(round((cajas_restantes_eta / cajas_hora) * 3600))
        fin_estimado = datetime.datetime.now() + datetime.timedelta(seconds=eta_s)
        eta_store = {
            "lote": str(lote_actual),
            "remaining_s": eta_s,
            "generated_ms": int(time.time() * 1000),
            "end_iso": fin_estimado.isoformat(),
        }

    metricas = [
        construir_metric_card(
            "Cajas Turno",
            f"{cajas_turno:,}".replace(",", "."),
            "acumulado turno",
            accent="#2563eb",
            icon_svg=BOX_ICON_SVG,
            theme="blue",
        ),
        construir_metric_card(
            "Cajas por Hora",
            formatear_entero(cajas_hora),
            "cajas/h",
            accent="#7c3aed",
            icon_svg=BOXES_EMPTIED_ICON_SVG,
            theme="purple",
        ),
        construir_metric_card(
            "Kg por Proceso",
            f"{round(kg_turno):,}".replace(",", ".") if kg_turno else "0",
            "acumulado turno",
            accent="#f97316",
            icon_svg=PROCESS_ICON_SVG,
            theme="orange",
        ),
        construir_metric_card(
            "Kg por Hora",
            f"{round(kg_hora):,}".replace(",", ".") if kg_hora else "0",
            "kg/h",
            accent="#10b981",
            icon_svg=CAPACITY_ICON_SVG,
            theme="green",
        ),
    ]

    # Tarjeta: tiempo total del turno + badge con detención total
    turno_s = 0
    try:
        turno_info = get_turno_corrente_info()
        inicio = (turno_info or {}).get("turno_inicio")
        if isinstance(inicio, datetime.datetime):
            turno_s = int((datetime.datetime.now() - inicio).total_seconds())
    except Exception:
        turno_s = 0

    det_hms = _fmt_hms_seconds(float(fermo_min or 0.0) * 60.0)
    metricas.append(
        construir_metric_card(
            "Tiempo Turno",
            _fmt_hms_seconds(turno_s),
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
        )
    )

    filtros_children = html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                (k[:2] if k else "?").upper(),
                                className="filter-icon",
                                **{"data-key": k},
                            ),
                            html.Div(k, className="filter-label"),
                        ],
                        className="filter-header",
                    ),
                    html.Div(v, className="filter-value"),
                ],
                className="filter-item",
            )
            for k, v in filtros.items()
        ],
        className="filter-grid",
    )

    pct_cajas = round(pct_vaciadas, 1)
    bins_totales = (float(cajas_totales) / float(_BIN_SIZE)) if _BIN_SIZE else 0.0
    bins_vaciadas = (float(cajas_vaciadas) / float(_BIN_SIZE)) if _BIN_SIZE else 0.0
    bins_restantes = (float(cajas_restantes) / float(_BIN_SIZE)) if _BIN_SIZE else 0.0
    chart_cajas = [
        html.Div(
            [
                html.Div("Cajas Vaciadas", className="chart-title"),
                html.Div(className="chart-loader chart-loader-cajas", key=f"cajas-{_}"),
            ],
            className="chart-title-row",
        ),
        html.Div("Porcentaje completado del lote", className="chart-subtitle"),
        html.Div(
            [
                html.Span(f"{pct_cajas}%", style={"fontSize": "3rem", "fontWeight": "900", "color": "#2563eb"}),
                html.Div(
                    [
                        html.Div("Capacidad", style={"fontSize": "1rem", "color": "#6b7280"}),
                        html.Div(
                            f"{formatear_entero(cajas_vaciadas)} de {formatear_entero(cajas_totales)} cajas",
                            style={"fontSize": "1.1rem"},
                        ),
                    ],
                    className="chart-right-block",
                ),
            ],
            style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "margin": "1rem 0"},
        ),
        html.Div(
            html.Div(className="progress-bar", style={"width": f"{pct_cajas}%" if pct_cajas >= 0 else "0%"}),
            className="progress-bar-container",
        ),
        html.Div(className="chart-divider"),
        html.Div(
            [
                html.Div(
                    [
                        html.Div("Totales", className="breakdown-label"),
                        html.Div(formatear_entero(cajas_totales), className="breakdown-value"),
                        html.Div(
                            f"{bins_totales:.1f} bins",
                            style={"fontSize": "0.85rem", "color": "#6b7280", "marginTop": "2px"},
                        ),
                    ],
                    className="breakdown-item",
                ),
                html.Div(
                    [
                        html.Div("Vaciadas", className="breakdown-label"),
                        html.Div(
                            formatear_entero(cajas_vaciadas),
                            className="breakdown-value",
                            style={"color": "#2563eb"},
                        ),
                        html.Div(
                            f"{bins_vaciadas:.1f} bins",
                            style={"fontSize": "0.85rem", "color": "#6b7280", "marginTop": "2px"},
                        ),
                    ],
                    className="breakdown-item",
                ),
                html.Div(
                    [
                        html.Div("Restantes", className="breakdown-label"),
                        html.Div(
                            formatear_entero(cajas_restantes),
                            className="breakdown-value",
                            style={"color": "#f97316"},
                        ),
                        html.Div(
                            f"{bins_restantes:.1f} bins",
                            style={"fontSize": "0.85rem", "color": "#6b7280", "marginTop": "2px"},
                        ),
                    ],
                    className="breakdown-item",
                ),
            ],
            className="breakdown-grid",
        ),
    ]

    kg_totales_safe = kg_totales if kg_totales and kg_totales > 0 else 1
    pct_kg_restantes = round((kg_restantes / kg_totales_safe) * 100, 1)
    chart_kg = [
        html.Div(
            [
                html.Div("Kilogramos Restantes", className="chart-title"),
                html.Div(className="chart-loader chart-loader-kg", key=f"kg-{_}"),
            ],
            className="chart-title-row",
        ),
        html.Div("Disponibilidad en almacén", className="chart-subtitle"),
        html.Div(
            [
                html.Span(
                    f"{pct_kg_restantes}%",
                    style={"fontSize": "3rem", "fontWeight": "900", "color": "#10b981"},
                ),
                html.Div(
                    [
                        html.Div("Restantes", style={"fontSize": "1rem", "color": "#6b7280"}),
                        html.Div(
                            f"{formatear_entero(kg_restantes)} kg",
                            style={"fontSize": "1.1rem"},
                        ),
                    ],
                    className="chart-right-block",
                ),
            ],
            style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "margin": "1rem 0"},
        ),
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
        html.Div(
            [
                html.Div(
                    [
                        html.Div("Total", className="breakdown-label"),
                        html.Div(formatear_entero(kg_totales), className="breakdown-value"),
                    ],
                    className="breakdown-item",
                ),
                html.Div(
                    [
                        html.Div("Usado", className="breakdown-label"),
                        html.Div(
                            formatear_entero(kg_vaciados),
                            className="breakdown-value",
                            style={"color": "#f97316"},
                        ),
                    ],
                    className="breakdown-item",
                ),
                html.Div(
                    [
                        html.Div("Disponible", className="breakdown-label"),
                        html.Div(
                            formatear_entero(kg_restantes),
                            className="breakdown-value",
                            style={"color": "#10b981"},
                        ),
                    ],
                    className="breakdown-item",
                ),
            ],
            className="breakdown-grid",
        ),
    ]

    # Tabla detalle
    try:
        ts = time.perf_counter()
        df_detalle = get_detalle_lotti_ingresso()
        _log_timing("get_detalle_lotti_ingresso", ts)
    except Exception as e:
        df_detalle = None
        errors.append(f"get_detalle_lotti_ingresso: {e}")

    # (fermo_min y lotti_time_map ya se calculan arriba, antes de crear las tarjetas)

    # Baseline de detención por lote: FermoMacchinaMinuti es acumulado del turno,
    # así que guardamos el valor al inicio del lote para restar solo el delta.
    proceso_actual = None
    try:
        proceso_actual = str(datos_lote.get("Proceso")) if datos_lote else None
    except Exception:
        proceso_actual = None

    baseline = fermo_baseline_prev if isinstance(fermo_baseline_prev, dict) else None
    baseline_ok = (
        baseline
        and str(baseline.get("lote") or "") == str(lote_actual or "")
        and str(baseline.get("proceso") or "") == str(proceso_actual or "")
        and isinstance(baseline.get("fermo_start"), (int, float))
    )
    if not baseline_ok and lote_actual is not None:
        baseline = {"lote": str(lote_actual), "proceso": str(proceso_actual or ""), "fermo_start": float(fermo_min or 0.0)}

    # Congelar fin de lote cuando ya terminó de procesar (Restantes==0),
    # para que "Tiempo Real" y "Detención" no sigan creciendo.
    finish = lote_finish_prev if isinstance(lote_finish_prev, dict) else None
    finish_ok = (
        finish
        and str(finish.get("lote") or "") == str(lote_actual or "")
        and str(finish.get("proceso") or "") == str(proceso_actual or "")
        and isinstance(finish.get("finished_ms"), (int, float))
        and isinstance(finish.get("fermo_end"), (int, float))
    )
    if not finish_ok:
        finish = None
    if lote_actual is not None:
        try:
            if int(cajas_restantes or 0) <= 0:
                if finish is None:
                    finish = {
                        "lote": str(lote_actual),
                        "proceso": str(proceso_actual or ""),
                        "finished_ms": float(time.time() * 1000.0),
                        "fermo_end": float(fermo_min or 0.0),
                    }
            else:
                finish = None
        except Exception:
            pass

    # Acumular detención por lote a partir de FermoMacchinaMinuti (acumulado por turno)
    now_turn_key = f"{shift_business_date(datetime.datetime.now())}|{current_turn()}"
    with _DET_LOCK:
        if _DET_STATE.get("turn_key") != now_turn_key:
            _DET_STATE["turn_key"] = now_turn_key
            _DET_STATE["last_fermo"] = None
            _DET_STATE["map"] = {}

        det_map = _DET_STATE.get("map") if isinstance(_DET_STATE.get("map"), dict) else {}
        last_fermo = _DET_STATE.get("last_fermo")
        try:
            last_fermo = float(last_fermo) if last_fermo is not None else None
        except Exception:
            last_fermo = None

        delta_min = 0.0
        try:
            if last_fermo is None:
                delta_min = 0.0
            else:
                delta_min = max(0.0, float(fermo_min or 0.0) - float(last_fermo))
        except Exception:
            delta_min = 0.0

        try:
            if lote_actual is not None and proceso_actual is not None:
                key_cur = f"{str(proceso_actual)}|{str(lote_actual)}"
                is_finished = bool(
                    finish
                    and str(finish.get("lote") or "") == str(lote_actual)
                    and str(finish.get("proceso") or "") == str(proceso_actual)
                )
                if not is_finished and int(cajas_restantes or 0) > 0 and delta_min > 0:
                    det_map[key_cur] = float(det_map.get(key_cur) or 0.0) + float(delta_min)
        except Exception:
            pass

        _DET_STATE["last_fermo"] = float(fermo_min or 0.0)
        _DET_STATE["map"] = det_map

    det_store = {"turn_key": now_turn_key, "last_fermo": _DET_STATE.get("last_fermo"), "map": det_map}
    if df_detalle is not None and not df_detalle.empty:
        columnas_ordenadas = [
            "Fecha y Hora",
            "CSG",
            "Productor",
            "Proceso",
            "Lote",
            "Cjs Planificadas",
            "Cjs Vaciadas",
            "Cjs Restantes",
            "Var Real",
            "Peso (Kg)",
            "Acumulado por Proceso (Kg)",
            "Tiempo Real",
            "Tiempo Detenido",
        ]
        # Calcular Tiempo Real por lote (hh:mm:ss):
        # se usa la diferencia entre el inicio del lote y el inicio del siguiente lote
        # (por Proceso). Para el lote en curso, el fin es "ahora".
        # Si existe detención (FermoMacchinaMinuti), se RESTA al lote en curso.
        def _fmt_hms(total_seconds: float) -> str:
            total_seconds = max(0, int(total_seconds or 0))
            h = total_seconds // 3600
            m = (total_seconds % 3600) // 60
            s = total_seconds % 60
            return f"{h:02d}:{m:02d}:{s:02d}"

        try:
            df_calc = df_detalle.copy()
            df_calc["_dt"] = pd.to_datetime(df_calc.get("Fecha y Hora"), format="%d/%m/%Y %H:%M:%S", errors="coerce")
            now_dt = datetime.datetime.now()

            # Determinar proceso actual (para identificar lote en curso de forma más precisa)
            proceso_actual = None
            try:
                proceso_actual = str(datos_lote.get("Proceso")) if datos_lote else None
            except Exception:
                proceso_actual = None

            fermo_delta_min = 0.0
            try:
                if lote_actual is not None and proceso_actual is not None:
                    fermo_delta_min = float(det_map.get(f"{str(proceso_actual)}|{str(lote_actual)}") or 0.0)
            except Exception:
                fermo_delta_min = 0.0

            # Exponer "Detención" (minutos) en la tabla para el lote en curso
            if False and lote_actual is not None and fermo_delta_min and fermo_delta_min > 0:
                try:
                    if "Detención" not in df_detalle.columns:
                        df_detalle["Detención"] = ""
                    if proceso_actual:
                        mask_cur = (df_detalle["Lote"].astype(str) == str(lote_actual)) & (
                            df_detalle["Proceso"].astype(str) == str(proceso_actual)
                        )
                    else:
                        mask_cur = df_detalle["Lote"].astype(str) == str(lote_actual)
                    df_detalle.loc[mask_cur, "Detención"] = str(int(round(fermo_delta_min)))
                    df_calc["Detención"] = df_detalle.get("Detención")
                except Exception:
                    pass

            demora_map = {}  # key: (Proceso, Lote) -> hh:mm:ss

            base = df_calc.dropna(subset=["_dt"]).copy()
            if "Proceso" in base.columns and "Lote" in base.columns:
                base["_proceso"] = base["Proceso"].astype(str)
                base["_lote"] = base["Lote"].astype(str)
                # Inicio real del lote = primera lectura del lote (por Proceso)
                starts = (
                    base.groupby(["_proceso", "_lote"], dropna=False)["_dt"]
                    .min()
                    .reset_index()
                    .sort_values(["_proceso", "_dt"])
                )

                for proc, grp in starts.groupby("_proceso", dropna=False):
                    grp = grp.sort_values("_dt").reset_index(drop=True)
                    for i in range(len(grp)):
                        lote_i = str(grp.loc[i, "_lote"])
                        start_i = grp.loc[i, "_dt"]
                        if i + 1 < len(grp):
                            end_i = grp.loc[i + 1, "_dt"]
                        else:
                            if (
                                finish
                                and lote_actual is not None
                                and lote_i == str(lote_actual)
                                and (proceso_actual is None or str(proc) == str(proceso_actual))
                                and isinstance(finish.get("finished_ms"), (int, float))
                            ):
                                end_i = datetime.datetime.fromtimestamp(float(finish["finished_ms"]) / 1000.0)
                            else:
                                end_i = now_dt

                        dur_s = (end_i - start_i).total_seconds()

                        # Restar detención al lote en curso (si coincide)
                        if (
                            lote_actual is not None
                            and lote_i == str(lote_actual)
                            and (proceso_actual is None or str(proc) == str(proceso_actual))
                        ):
                            det_min_i = float(det_map.get(f"{str(proc)}|{lote_i}") or 0.0)
                            if det_min_i > 0:
                                dur_s -= det_min_i * 60.0

                        demora_map[(str(proc), lote_i)] = _fmt_hms(dur_s)

                df_detalle["Tiempo Real"] = (
                    df_detalle.apply(lambda r: demora_map.get((str(r.get("Proceso")), str(r.get("Lote"))), ""), axis=1)
                )

                # Si existe historico con LottoInizio/LottoFine, recalcular para todos los lotes (más exacto).
                if lotti_time_map:
                    def _fallback_start(proc: str, lote: str):
                        try:
                            match = base[(base["Proceso"].astype(str) == proc) & (base["Lote"].astype(str) == lote)]
                            if match.empty:
                                return None
                            v = match["_dt"].min()
                            return None if pd.isna(v) else v
                        except Exception:
                            return None

                    def _calc_demora_row(row) -> str:
                        proc = str(row.get("Proceso"))
                        lote = str(row.get("Lote"))
                        rec = lotti_time_map.get((proc, lote)) or {}
                        start_dt = rec.get("start")
                        end_dt = rec.get("end")
                        if not isinstance(start_dt, datetime.datetime):
                            start_dt = _fallback_start(proc, lote)
                        if not isinstance(end_dt, datetime.datetime):
                            if (
                                finish
                                and lote_actual is not None
                                and lote == str(lote_actual)
                                and (proceso_actual is None or proc == str(proceso_actual))
                                and isinstance(finish.get("finished_ms"), (int, float))
                            ):
                                end_dt = datetime.datetime.fromtimestamp(float(finish["finished_ms"]) / 1000.0)
                            else:
                                end_dt = now_dt
                        if not isinstance(start_dt, datetime.datetime) or not isinstance(end_dt, datetime.datetime):
                            return ""
                        dur_s = (end_dt - start_dt).total_seconds()
                        det_min_row = float(det_map.get(f"{proc}|{lote}") or 0.0)
                        if det_min_row > 0:
                            dur_s -= det_min_row * 60.0
                        return _fmt_hms(dur_s)

                    df_detalle["Tiempo Real"] = df_detalle.apply(_calc_demora_row, axis=1)
            else:
                df_detalle["Tiempo Real"] = ""
        except Exception:
            df_detalle["Tiempo Real"] = ""

        # Mostrar detención (min) como superíndice en "Tiempo Real".
        # Nota: la detención disponible proviene del turno (FermoMacchinaMinuti), no por lote histórico;
        # por eso solo se aplica al lote en curso.
        try:
            if "Proceso" in df_detalle.columns and "Lote" in df_detalle.columns and isinstance(det_map, dict):
                df_detalle["Tiempo Detenido"] = [
                    _fmt_hms_seconds(float(det_map.get(f"{str(p)}|{str(l)}") or 0.0) * 60.0)
                    for p, l in zip(df_detalle["Proceso"].astype(str).tolist(), df_detalle["Lote"].astype(str).tolist())
                ]
        except Exception:
            df_detalle["Tiempo Detenido"] = ""

        # Ajustar "Cjs Vaciadas" / "Cjs Restantes" para lotes no actuales:
        # - Lotes anteriores al actual: Vaciadas = Planificadas, Restantes = 0.
        # - Lotes posteriores al actual: Vaciadas = 0, Restantes = Planificadas.
        try:
            if (
                "Cjs Restantes" in df_detalle.columns
                and "Cjs Planificadas" in df_detalle.columns
                and "Cjs Vaciadas" in df_detalle.columns
            ):
                cjs_plan = pd.to_numeric(df_detalle["Cjs Planificadas"], errors="coerce").fillna(0)
                # Usar Fecha y Hora para ordenar lotes y determinar cuáles vienen después
                dt_col = "_orden_dt"
                if "Fecha y Hora" in df_detalle.columns:
                    df_detalle[dt_col] = pd.to_datetime(
                        df_detalle["Fecha y Hora"], format="%d/%m/%Y %H:%M:%S", errors="coerce"
                    )
                else:
                    df_detalle[dt_col] = pd.NaT
                if lote_actual is not None:
                    if proceso_actual and "Proceso" in df_detalle.columns:
                        mask_current = (df_detalle["Lote"].astype(str) == str(lote_actual)) & (
                            df_detalle["Proceso"].astype(str) == str(proceso_actual)
                        )
                    else:
                        mask_current = df_detalle["Lote"].astype(str) == str(lote_actual)
                else:
                    mask_current = pd.Series([False] * len(df_detalle), index=df_detalle.index)
                current_dt = None
                try:
                    if mask_current.any():
                        current_dt = df_detalle.loc[mask_current, dt_col].min()
                except Exception:
                    current_dt = None
                if "Proceso" in df_detalle.columns and current_dt is not None and pd.notna(current_dt):
                    cur_proc = None
                    try:
                        if mask_current.any():
                            cur_proc = str(df_detalle.loc[mask_current, "Proceso"].iloc[0])
                    except Exception:
                        cur_proc = None
                    if cur_proc:
                        in_proc = df_detalle["Proceso"].astype(str) == cur_proc
                    else:
                        in_proc = pd.Series([True] * len(df_detalle), index=df_detalle.index)
                    before_current = in_proc & (df_detalle[dt_col] < current_dt)
                    after_current = in_proc & (df_detalle[dt_col] > current_dt)
                else:
                    before_current = pd.Series([False] * len(df_detalle), index=df_detalle.index)
                    after_current = pd.Series([False] * len(df_detalle), index=df_detalle.index)
                mask_other = ~mask_current
                mask_past = mask_other & before_current
                mask_future = mask_other & after_current
                # Anteriores: ya completados
                df_detalle.loc[mask_past, "Cjs Vaciadas"] = cjs_plan[mask_past]
                df_detalle.loc[mask_past, "Cjs Restantes"] = 0
                # Posteriores: aún no iniciados
                df_detalle.loc[mask_future, "Cjs Vaciadas"] = 0
                df_detalle.loc[mask_future, "Cjs Restantes"] = cjs_plan[mask_future]
        except Exception:
            pass

        # Mostrar solo registros del turno actual:
        # - Turno dia: 07:00 a 17:00
        # - Turno noche: 17:30 a 04:00 (cruza de dia)
        # Mantener siempre el lote actual aunque quede fuera de rango.
        try:
            if "Fecha y Hora" in df_detalle.columns:
                df_detalle["_fecha_dt"] = pd.to_datetime(
                    df_detalle["Fecha y Hora"], format="%d/%m/%Y %H:%M:%S", errors="coerce"
                )
                if lote_actual is not None:
                    if proceso_actual and "Proceso" in df_detalle.columns:
                        mask_current = (df_detalle["Lote"].astype(str) == str(lote_actual)) & (
                            df_detalle["Proceso"].astype(str) == str(proceso_actual)
                        )
                    else:
                        mask_current = df_detalle["Lote"].astype(str) == str(lote_actual)
                else:
                    mask_current = pd.Series([False] * len(df_detalle), index=df_detalle.index)
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
                mask_shift = (df_detalle["_fecha_dt"] >= start_dt) & (df_detalle["_fecha_dt"] <= end_dt)
                df_detalle = df_detalle.loc[mask_shift | mask_current]
        except Exception:
            pass

        # Asegurar fecha/hora visible para el lote actual si viene vacia
        try:
            if "Fecha y Hora" in df_detalle.columns and lote_actual is not None:
                if proceso_actual and "Proceso" in df_detalle.columns:
                    mask_current = (df_detalle["Lote"].astype(str) == str(lote_actual)) & (
                        df_detalle["Proceso"].astype(str) == str(proceso_actual)
                    )
                else:
                    mask_current = df_detalle["Lote"].astype(str) == str(lote_actual)
                empty_mask = df_detalle["Fecha y Hora"].isna() | (
                    df_detalle["Fecha y Hora"].astype(str).str.strip().isin(["", "nan", "None", "NaT"])
                )
                if (mask_current & empty_mask).any():
                    fecha_lote = None
                    try:
                        fecha_lote = datos_lote.get("Fecha y Hora") if isinstance(datos_lote, dict) else None
                    except Exception:
                        fecha_lote = None
                    if fecha_lote:
                        df_detalle.loc[mask_current & empty_mask, "Fecha y Hora"] = fecha_lote
        except Exception:
            pass

        # Dejar solo registros ya procesados + lote actual
        try:
            if "Cjs Vaciadas" in df_detalle.columns:
                cjs_vac = pd.to_numeric(df_detalle["Cjs Vaciadas"], errors="coerce").fillna(0)
                if "Proceso" in df_detalle.columns and proceso_actual and lote_actual is not None:
                    mask_current = (df_detalle["Lote"].astype(str) == str(lote_actual)) & (
                        df_detalle["Proceso"].astype(str) == str(proceso_actual)
                    )
                elif lote_actual is not None:
                    mask_current = df_detalle["Lote"].astype(str) == str(lote_actual)
                else:
                    mask_current = pd.Series([False] * len(df_detalle), index=df_detalle.index)
                keep_mask = (cjs_vac > 0) | mask_current
                df_detalle = df_detalle.loc[keep_mask]
        except Exception:
            pass

        columnas_existentes = [c for c in columnas_ordenadas if c in df_detalle.columns]
        df_detalle = df_detalle[columnas_existentes]
        
        # Convertir columnas numéricas a texto para que el filtro funcione correctamente
        # El filtro de texto requiere que los valores sean strings para hacer coincidencias parciales
        columnas_numericas = ["Cjs Planificadas", "Cjs Vaciadas", "Cjs Restantes", "Peso (Kg)", "Acumulado por Proceso (Kg)"]
        df_detalle_para_tabla = df_detalle.copy()
        for col in columnas_numericas:
            if col in df_detalle_para_tabla.columns:
                # Convertir a string, manejando valores nulos/NaN de forma más robusta
                df_detalle_para_tabla[col] = df_detalle_para_tabla[col].fillna('').astype(str)
                df_detalle_para_tabla[col] = df_detalle_para_tabla[col].replace('nan', '').replace('None', '').replace('NaT', '')
        
        data = df_detalle_para_tabla.to_dict("records")
        
        # Forzar tipo texto: el filtro nativo usa coincidencia parcial (contains) en texto,
        # mientras que en numéricos tiende a igualdad exacta. Esto hace que al buscar
        # encuentre cualquier coincidencia (ej: "706" encuentra "00706").
        columns = [{"name": c, "id": c, "type": "text"} for c in columnas_existentes]

        # Mapas de colores para Proceso y Var Real
        colores_proceso = [
            "#2563eb",
            "#7c3aed",
            "#dc2626",
            "#059669",
            "#ea580c",
            "#0891b2",
            "#4f46e5",
            "#be123c",
            "#65a30d",
            "#0369a1",
        ]
        colores_variedad = [
            "#16a34a",
            "#f59e0b",
            "#dc2626",
            "#ec4899",
            "#8b5cf6",
            "#0891b2",
            "#ca8a04",
            "#7c3aed",
            "#ea580c",
            "#0284c7",
        ]

        procesos_unicos = list(df_detalle["Proceso"].dropna().unique()) if "Proceso" in df_detalle.columns else []
        variedades_unicas = list(df_detalle["Var Real"].dropna().unique()) if "Var Real" in df_detalle.columns else []
        proceso_color_map = {
            p: colores_proceso[i % len(colores_proceso)] for i, p in enumerate(procesos_unicos)
        }
        variedad_color_map = {
            v: colores_variedad[i % len(colores_variedad)] for i, v in enumerate(variedades_unicas)
        }

        style_conditional = []
        if "Proceso" in df_detalle.columns:
            for p, color in proceso_color_map.items():
                style_conditional.append(
                    {
                        "if": {"column_id": "Proceso", "filter_query": f'{{Proceso}} = "{p}"'},
                        "color": color,
                        "fontWeight": "700",
                    }
                )
        if "Var Real" in df_detalle.columns:
            for v, color in variedad_color_map.items():
                style_conditional.append(
                    {
                        "if": {"column_id": "Var Real", "filter_query": f'{{Var Real}} = "{v}"'},
                        "color": color,
                        "fontWeight": "700",
                    }
                )
        if "Tiempo Detenido" in df_detalle.columns:
            style_conditional.append(
                {
                    "if": {"column_id": "Tiempo Detenido"},
                    "color": "#b91c1c",
                    "fontWeight": "900",
                }
            )
        if lote_actual and "Lote" in df_detalle.columns:
            if proceso_actual and "Proceso" in df_detalle.columns:
                query = f'{{Lote}} = "{lote_actual}" && {{Proceso}} = "{proceso_actual}"'
            else:
                query = f'{{Lote}} = "{lote_actual}"'
            style_conditional.append(
                {
                    "if": {"filter_query": query},
                    "backgroundColor": "rgba(16,185,129,0.10)",
                    "fontWeight": "800",
                    "borderTop": "1px solid rgba(16,185,129,0.18)",
                    "borderBottom": "1px solid rgba(16,185,129,0.18)",
                }
            )
    else:
        data, columns, style_conditional = [], [], []

    def _fingerprint_rows(rows, max_rows: int = 3):
        if not rows:
            return None
        sample = rows[:max_rows]
        payload = json.dumps(sample, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.md5(payload.encode("utf-8")).hexdigest()

    next_snapshot = {
        "errors": errors[:6],
        "filtros": filtros,
        "kpis": {
            "lote": str(lote_actual) if lote_actual is not None else None,
            "cajas_totales": int(cajas_totales),
            "cajas_vaciadas": int(cajas_vaciadas),
            "cajas_restantes": int(cajas_restantes),
            "kg_totales": float(kg_totales),
            "kg_vaciados": float(kg_vaciados),
            "kg_restantes": float(kg_restantes),
            "cajas_turno": float(cajas_turno),
            "cajas_hora": float(cajas_hora),
            "kg_turno": float(kg_turno),
            "kg_hora": float(kg_hora),
            "pct_cajas": float(pct_cajas),
            "pct_kg_restantes": float(pct_kg_restantes),
        },
        "table": {
            "rows": len(data) if isinstance(data, list) else 0,
            "cols": len(columns) if isinstance(columns, list) else 0,
            "style_rules": len(style_conditional) if isinstance(style_conditional, list) else 0,
            "sample_md5": _fingerprint_rows(data),
        },
        "eta_core": {
            "lote": eta_store.get("lote") if isinstance(eta_store, dict) else None,
            "remaining_s": eta_store.get("remaining_s") if isinstance(eta_store, dict) else None,
        },
    }

    unchanged = (
        isinstance(prev_snapshot, dict)
        and prev_snapshot.get("filtros") == next_snapshot.get("filtros")
        and prev_snapshot.get("kpis") == next_snapshot.get("kpis")
        and prev_snapshot.get("table") == next_snapshot.get("table")
    )
    eta_unchanged = isinstance(prev_snapshot, dict) and prev_snapshot.get("eta_core") == next_snapshot.get("eta_core")

    return (
        hora,
        html.Div(
            [
                html.Div(className="refresh-loader", key=str(_)),
            ]
        ),
        dash.no_update if eta_unchanged else eta_store,
        dash.no_update if unchanged else metricas,
        dash.no_update if unchanged else filtros_children,
        dash.no_update if unchanged else chart_cajas,
        dash.no_update if unchanged else chart_kg,
        dash.no_update if unchanged else data,
        dash.no_update if unchanged else columns,
        dash.no_update if unchanged else style_conditional,
        next_snapshot,
        baseline,
        finish,
        det_store,
    )


@app.callback(
    Output("endlote-notificados-store", "data"),
    Output("notif-payload-store", "data"),
    Input("interval-notif", "n_intervals"),
    State("endlote-notificados-store", "data"),
    State("notif-endlote-toggle", "value"),
    State("tts-toggle", "value"),
    State("orden-store", "data"),
)
def notificar_fin_lote(_, endlote_notificados, endlote_toggle, tts_toggle, orden):
    endlote_notificados = endlote_notificados or []
    notif_enabled = isinstance(endlote_toggle, list) and ("on" in endlote_toggle)
    tts_enabled = isinstance(tts_toggle, list) and ("on" in tts_toggle)
    endlote_enabled = notif_enabled or tts_enabled
    try:
        current_record = get_current_record()
        lote_detalle = get_current_lote_from_detalle()

        if lote_detalle:
            datos_lote = lote_detalle
            productor = current_record["Productor"] if current_record else "N/A"
        else:
            datos_lote = current_record
            productor = current_record["Productor"] if current_record else "N/A"

        if not datos_lote:
            return endlote_notificados, dash.no_update

        lote_actual = datos_lote.get("Lote")
        if not lote_actual:
            return endlote_notificados, dash.no_update

        cajas_totales = int(datos_lote.get("UnitaPianificate", 0) or 0)
        cajas_restantes = int(datos_lote.get("UnitaRestanti", 0) or 0)
        siguiente_lote = _find_next_lote_from_orden(orden, lote_actual)

        # Notificación fin de lote (cuando llega a 0 restantes)
        if endlote_enabled and cajas_totales > 0 and cajas_restantes <= 0:
            if lote_actual not in endlote_notificados:
                titulo = "Frutísima - Lote Finalizado"
                mensaje = (
                    f"El lote {lote_actual} terminó de procesarse.\n\n"
                    f"Proceso: {datos_lote.get('Proceso', 'N/A')}\n"
                    f"Productor: {truncar_texto(productor, 30)}"
                )
                if siguiente_lote:
                    mensaje += f"\nSiguiente lote: {siguiente_lote}"
                voz = f"Lote {_lote_para_voz(lote_actual)} finalizado."
                if siguiente_lote:
                    voz += f" Siguiente lote {_lote_para_voz(siguiente_lote)}."
                # Mantener historial acotado para no crecer sin límite
                nuevos = (endlote_notificados + [lote_actual])[-50:]
                payload = {"kind": "endlote", "title": titulo, "message": mensaje, "voice": voz, "ts": datetime.datetime.now().isoformat()}
                return nuevos, payload

        return endlote_notificados, dash.no_update



        titulo = "Frutísima - Cambio de Lote Inminente"
        mensaje = (
            f"Lote {lote_actual} está por completarse\n\n"
            f"Proceso: {datos_lote.get('Proceso', 'N/A')}\n"
            f"Productor: {truncar_texto(productor, 30)}"
        )

        if siguiente_lote:
            mensaje += f"\nSiguiente lote: {siguiente_lote}"
        voz = (
            f"Atencion. El lote {_lote_para_voz(lote_actual)} esta por completarse. "
            f"Quedan {cajas_restantes} cajas. "
            f"Proceso {datos_lote.get('Proceso', 'N/A')}."
        )
        if siguiente_lote:
            voz += f" Siguiente lote {_lote_para_voz(siguiente_lote)}."


    except Exception as e:
        app.logger.exception("Error al evaluar/enviar notificación: %s", e)
        return endlote_notificados, dash.no_update


if __name__ == "__main__":
    # Importante: `debug=True` habilita el reloader y puede ejecutar el servidor/callbacks 2 veces,
    # además de degradar estabilidad en accesos remotos (otros equipos).
    def _silenciar_werkzeug_despues_de_arranque():
        time.sleep(2)
        logging.getLogger("werkzeug").setLevel(logging.WARNING)

    threading.Thread(target=_silenciar_werkzeug_despues_de_arranque, daemon=True).start()
    app.run(host="0.0.0.0", port=8050, debug=False, use_reloader=False, threaded=True)
