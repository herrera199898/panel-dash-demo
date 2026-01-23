"""
Aplicación principal en Dash - Panel Frutísima
Adaptación completa desde copy.py (Streamlit).
"""
import datetime
import time
import os
import email.utils
import re
import html as std_html

import dash
from dash import html, dcc, dash_table
from dash.dependencies import Output, Input, State

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=False)
except Exception:
    pass

from orden_vaciado import load_orden_from_imap

from functions import (
    get_current_record,
    get_current_lote_from_detalle,
    get_cajas_por_turno,
    get_cajas_por_hora_turno,
    get_kg_por_turno,
    get_kg_por_hora_turno,
    get_kg_lote_vw_partita,
    get_kg_lote,
    get_kg_total_lote,
    get_kg_por_caja_lote,
    get_detalle_lotti_ingresso,
    get_exportador_nombre,
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

NOTIFICACION_COOLDOWN_S = 30
_ultima_notificacion_por_lote = {}
ORDEN_REFRESH_S = 60
_orden_cache = {"ts": 0.0, "data": None}


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
                                ),
                                html.Div(
                                    dcc.Checklist(
                                        id="notif-endlote-toggle",
                                        options=[{"label": "Avisar fin de lote", "value": "on"}],
                                        value=[],
                                        persistence=True,
                                        persistence_type="local",
                                    ),
                                    className="update-badge header-toggle",
                                ),
                                html.Div(
                                    dcc.Checklist(
                                        id="tts-toggle",
                                        options=[{"label": "Aviso por voz (este navegador)", "value": "on"}],
                                        value=[],
                                        persistence=True,
                                        persistence_type="local",
                                    ),
                                    className="update-badge header-toggle",
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
                                        html.Div(id="eta-lote", className="update-time"),
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
        dcc.Interval(id="interval-notif", interval=NOTIFICACION_COOLDOWN_S * 1000, n_intervals=0),
        dcc.Interval(id="interval-eta", interval=1 * 1000, n_intervals=0),
        dcc.Interval(id="interval-orden", interval=ORDEN_REFRESH_S * 1000, n_intervals=0),
        dcc.Store(id="notificados-store", data=[]),
        dcc.Store(id="endlote-notificados-store", data=[], storage_type="local"),
        dcc.Store(id="notif-payload-store"),
        dcc.Store(id="notif-permission-store"),
        dcc.Store(id="eta-store"),
        dcc.Store(id="orden-store"),
    ],
    className="app-root",
)

app.clientside_callback(
    """
    function(_, eta) {
        function pad2(n){ return String(n).padStart(2,'0'); }
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
        return fmtHMS(remaining);
    }
    """,
    Output("eta-lote", "children"),
    Input("interval-eta", "n_intervals"),
    State("eta-store", "data"),
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
    Input("notif-browser-toggle", "value"),
)

app.clientside_callback(
    """
    function(payload, notifToggleValue, ttsToggleValue, perm) {
        const notifEnabled = Array.isArray(notifToggleValue) && notifToggleValue.indexOf("on") !== -1;
        const ttsEnabled = Array.isArray(ttsToggleValue) && ttsToggleValue.indexOf("on") !== -1;
        if (!payload) return window.dash_clientside.no_update;
        if (notifEnabled) {
            if (!("Notification" in window)) return window.dash_clientside.no_update;
            if (Notification.permission !== "granted") return window.dash_clientside.no_update;
        }
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
    State("notif-browser-toggle", "value"),
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
        lote_detalle = get_current_lote_from_detalle()
        lote_actual = None
        try:
            lote_actual = (lote_detalle or {}).get("Lote")
        except Exception:
            lote_actual = None
        ahora = time.time()
        cached = _orden_cache.get("data")
        if cached and (ahora - float(_orden_cache.get("ts") or 0.0)) < (ORDEN_REFRESH_S * 0.90):
            return cached

        data = load_orden_from_imap(lote_actual=lote_actual)
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
    ],
    Input("interval-act", "n_intervals"),
)
def actualizar_panel(_):
    start_ts = datetime.datetime.now()
    try:
        app.logger.info("actualizar_panel tick")
        now = datetime.datetime.now()
        hora = now.strftime("%d/%m/%Y %H:%M:%S")

        current_record = get_current_record()
        lote_detalle = get_current_lote_from_detalle()

        if lote_detalle:
            datos_lote = lote_detalle
            productor = current_record["Productor"] if current_record else "N/A"
        else:
            datos_lote = current_record
            productor = current_record["Productor"] if current_record else "N/A"

        lote_actual = datos_lote["Lote"] if datos_lote and datos_lote.get("Lote") else None
        exportador = get_exportador_nombre(lote_actual)

        filtros = {
            "Exportador": exportador,
            "Productor": productor,
            "Variedad": datos_lote["Variedad"] if datos_lote else "N/A",
            "Proceso": datos_lote["Proceso"] if datos_lote else "N/A",
            "Lote": datos_lote["Lote"] if datos_lote else "N/A",
        }
        filtros = {k: truncar_texto(v) for k, v in filtros.items()}

        cajas_totales = cajas_vaciadas = cajas_restantes = 0
        kg_totales = kg_vaciados = kg_restantes = 0
        pct_vaciadas = pct_restantes = 0

        if datos_lote:
            cajas_totales = int(datos_lote.get("UnitaPianificate", 0) or 0)
            cajas_vaciadas = int(datos_lote.get("UnitaSvuotate", 0) or 0)
            cajas_restantes = int(datos_lote.get("UnitaRestanti", 0) or 0)

            kg_totales = get_kg_total_lote(datos_lote.get("Lote"))
            if kg_totales == 0:
                if datos_lote.get("PesoNetto", 0) > 0:
                    kg_totales = float(datos_lote["PesoNetto"])
                else:
                    kg_totales = get_kg_lote_vw_partita(
                        datos_lote.get("Lote"), datos_lote.get("Proceso")
                    )
                    if kg_totales == 0:
                        kg_totales = get_kg_lote(datos_lote.get("Lote"), datos_lote.get("Proceso"))

            kg_por_caja = get_kg_por_caja_lote(datos_lote.get("Lote"))
            if kg_por_caja == 0 and cajas_totales > 0 and kg_totales > 0:
                kg_por_caja = kg_totales / cajas_totales

            if kg_por_caja > 0:
                kg_restantes = kg_por_caja * cajas_restantes
                kg_vaciados = kg_totales - kg_restantes
            else:
                if cajas_totales > 0 and kg_totales > 0:
                    kg_restantes = (kg_totales * cajas_restantes) / cajas_totales
                    kg_vaciados = kg_totales - kg_restantes

            pct_vaciadas = (cajas_vaciadas / cajas_totales * 100) if cajas_totales > 0 else 0
            pct_restantes = (cajas_restantes / cajas_totales * 100) if cajas_totales > 0 else 0
        elapsed = (datetime.datetime.now() - start_ts).total_seconds()
        app.logger.info(f"actualizar_panel ok ({elapsed:.2f}s)")
    except Exception as e:
        # Si algo falla, log y placeholders visibles
        elapsed = (datetime.datetime.now() - start_ts).total_seconds()
        print(f"ERROR en actualizar_panel ({elapsed:.2f}s): {e}")
        hora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
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
    cajas_turno = get_cajas_por_turno() if datos_lote else 0
    cajas_hora = get_cajas_por_hora_turno() if datos_lote else 0
    kg_turno = get_kg_por_turno() if datos_lote else 0
    kg_hora = get_kg_por_hora_turno() if datos_lote else 0
    eta_store = None
    if datos_lote and lote_actual and cajas_restantes > 0 and cajas_hora > 0:
        eta_s = int(round((cajas_restantes / cajas_hora) * 3600))
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
    df_detalle = get_detalle_lotti_ingresso()
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
        ]
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
    else:
        data, columns, style_conditional = [], [], []

    return (
        hora,
        html.Div(
            [
                html.Img(
                    src="/assets/refresh_ring.svg",
                    className="refresh-ring",
                    alt="Actualizando",
                    key=str(_),
                    draggable="false",
                ),
                html.Img(
                    src="/assets/cherry_icon.svg",
                    className="refresh-cherry",
                    alt="Cereza",
                    draggable="false",
                ),
            ]
        ),
        eta_store,
        metricas,
        filtros_children,
        chart_cajas,
        chart_kg,
        data,
        columns,
        style_conditional,
    )


@app.callback(
    Output("notificados-store", "data"),
    Output("endlote-notificados-store", "data"),
    Output("notif-payload-store", "data"),
    Input("interval-notif", "n_intervals"),
    State("notificados-store", "data"),
    State("endlote-notificados-store", "data"),
    State("notif-endlote-toggle", "value"),
    State("orden-store", "data"),
)
def notificar_5pct(_, notificados, endlote_notificados, endlote_toggle, orden):
    notificados = notificados or []
    endlote_notificados = endlote_notificados or []
    endlote_enabled = isinstance(endlote_toggle, list) and ("on" in endlote_toggle)
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
            return notificados, endlote_notificados, dash.no_update

        lote_actual = datos_lote.get("Lote")
        if not lote_actual:
            return notificados, endlote_notificados, dash.no_update

        cajas_totales = int(datos_lote.get("UnitaPianificate", 0) or 0)
        cajas_restantes = int(datos_lote.get("UnitaRestanti", 0) or 0)
        pct_restantes = (cajas_restantes / cajas_totales * 100) if cajas_totales > 0 else 0
        siguiente_lote = _find_next_lote_from_orden(orden, lote_actual)

        # Notificación fin de lote (cuando llega a 0 restantes)
        if endlote_enabled and cajas_totales > 0 and cajas_restantes == 0:
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
                return notificados, nuevos, payload

        if not (0 < pct_restantes <= 5):
            return notificados, endlote_notificados, dash.no_update

        if lote_actual in notificados:
            return notificados, endlote_notificados, dash.no_update

        ahora = datetime.datetime.now()
        ultima_ts = _ultima_notificacion_por_lote.get(lote_actual)
        if ultima_ts and (ahora - ultima_ts).total_seconds() < NOTIFICACION_COOLDOWN_S:
            return notificados, endlote_notificados, dash.no_update

        titulo = "Frutísima - Cambio de Lote Inminente"
        mensaje = (
            f"Lote {lote_actual} está por completarse\n\n"
            f"Quedan {cajas_restantes} cajas por procesar ({pct_restantes:.1f}%)\n"
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

        _ultima_notificacion_por_lote[lote_actual] = ahora
        payload = {"kind": "warn5pct", "title": titulo, "message": mensaje, "ts": ahora.isoformat()}
        return notificados + [lote_actual], endlote_notificados, payload
    except Exception as e:
        print(f"Error al evaluar/enviar notificación: {e}")
        return notificados, endlote_notificados, dash.no_update


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=True)
