import datetime as _dt
import email
import imaplib
import io
import os
import re
import socket
from email.header import decode_header, make_header
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=False)
except Exception:
    pass


DEFAULT_MAILBOX = "INBOX"
DEFAULT_SUBJECT_CONTAINS = "ORDEN DE VACIADO"
DEFAULT_FILENAME_CONTAINS = "ORDEN DE VACIADO"


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _parse_hhmm(value: str) -> _dt.time:
    hh, mm = value.strip().split(":")
    return _dt.time(hour=int(hh), minute=int(mm))


def current_turn(now: Optional[_dt.datetime] = None) -> int:
    now = now or _dt.datetime.now()
    t1_start = _parse_hhmm(_env("ORDEN_TURNO_1_START", "08:00"))
    t2_start = _parse_hhmm(_env("ORDEN_TURNO_2_START", "20:00"))
    local_time = now.time()
    if t1_start <= local_time < t2_start:
        return 1
    return 2


def shift_business_date(now: Optional[_dt.datetime] = None) -> _dt.date:
    """
    Fecha "operativa" del turno actual.
    - Turno 1: misma fecha calendario
    - Turno 2 (20:00–08:00): si es antes del inicio del turno 1 (ej. 07:00),
      pertenece al día anterior (ej. 17-12 T2 aunque hoy sea 18-12).
    """
    now = now or _dt.datetime.now()
    t1_start = _parse_hhmm(_env("ORDEN_TURNO_1_START", "08:00"))
    if current_turn(now) == 2 and now.time() < t1_start:
        return (now - _dt.timedelta(days=1)).date()
    return now.date()


def _decode_mime_words(s: str) -> str:
    try:
        return str(make_header(decode_header(s)))
    except Exception:
        return s


def _imap_connect(host: str, port: int, user: str, password: str) -> imaplib.IMAP4_SSL:
    timeout_s = int(_env("IMAP_TIMEOUT_S", "12") or "12")
    try:
        client = imaplib.IMAP4_SSL(host, port, timeout=timeout_s)
    except TypeError:
        prev = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout_s)
        try:
            client = imaplib.IMAP4_SSL(host, port)
        finally:
            socket.setdefaulttimeout(prev)
    client.login(user, password)
    return client


def _search_latest_message_id(
    client: imaplib.IMAP4_SSL,
    mailbox: str,
    subject_contains: str,
) -> Optional[bytes]:
    client.select(mailbox)
    # Buscar por SUBJECT es básico; se hace uppercase para mejor compatibilidad.
    # Si falla, se cae al último correo del mailbox.
    subject_contains = subject_contains.strip()
    if subject_contains:
        typ, data = client.search(None, f'(SUBJECT "{subject_contains}")')
        if typ == "OK" and data and data[0]:
            ids = data[0].split()
            return ids[-1] if ids else None

    typ, data = client.search(None, "ALL")
    if typ != "OK" or not data or not data[0]:
        return None
    ids = data[0].split()
    return ids[-1] if ids else None


def fetch_latest_orden_vaciado_excel_bytes(
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    mailbox: str = DEFAULT_MAILBOX,
    subject_contains: str = DEFAULT_SUBJECT_CONTAINS,
    filename_contains: str = DEFAULT_FILENAME_CONTAINS,
) -> Tuple[Optional[bytes], Dict[str, Any]]:
    """
    Devuelve (excel_bytes, meta). Si no encuentra adjunto, excel_bytes=None.
    """
    meta: Dict[str, Any] = {
        "mailbox": mailbox,
        "subject_contains": subject_contains,
        "filename_contains": filename_contains,
        "email_subject": None,
        "email_date": None,
        "attachment_filename": None,
    }

    client: Optional[imaplib.IMAP4_SSL] = None
    try:
        client = _imap_connect(host, port, user, password)
        msg_id = _search_latest_message_id(client, mailbox, subject_contains)
        if not msg_id:
            return None, meta

        typ, data = client.fetch(msg_id, "(RFC822)")
        if typ != "OK" or not data:
            return None, meta

        raw = data[0][1]
        msg = email.message_from_bytes(raw)

        meta["email_subject"] = _decode_mime_words(msg.get("Subject", "") or "")
        meta["email_date"] = msg.get("Date")

        filename_contains_norm = (filename_contains or "").strip().lower()
        for part in msg.walk():
            content_disposition = (part.get("Content-Disposition") or "").lower()
            if "attachment" not in content_disposition:
                continue

            filename = part.get_filename()
            filename = _decode_mime_words(filename) if filename else ""
            if not filename:
                continue

            filename_norm = filename.lower()
            if filename_contains_norm and filename_contains_norm not in filename_norm:
                continue

            payload = part.get_payload(decode=True)
            if not payload:
                continue

            meta["attachment_filename"] = filename
            return payload, meta

        # Fallback: primer adjunto xlsx/xlsm si no matchea por nombre
        for part in msg.walk():
            content_disposition = (part.get("Content-Disposition") or "").lower()
            if "attachment" not in content_disposition:
                continue
            filename = part.get_filename()
            filename = _decode_mime_words(filename) if filename else ""
            if not filename:
                continue
            if not re.search(r"\.xls[xm]?$", filename.lower()):
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            meta["attachment_filename"] = filename
            return payload, meta

        return None, meta
    finally:
        try:
            if client is not None:
                client.logout()
        except Exception:
            pass


def _normalize_sheet_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip())


def choose_sheet_name(sheet_names: List[str], now: Optional[_dt.datetime] = None) -> Optional[str]:
    if not sheet_names:
        return None
    now = now or _dt.datetime.now()
    turn = current_turn(now)
    business_date = shift_business_date(now)
    ddmm = business_date.strftime("%d-%m")
    ddmmyyyy = business_date.strftime("%d-%m-%Y")

    normalized = [(_normalize_sheet_name(s), s) for s in sheet_names]

    candidates: List[Tuple[int, str]] = []
    for norm, original in normalized:
        upper = norm.upper()
        score = 0
        if ddmmyyyy in norm:
            score += 30
        if ddmm in norm:
            score += 20
        if f"T{turn}" in upper:
            score += 50
        m = re.search(r"\bT(\d)\b", upper)
        if m and int(m.group(1)) == turn:
            score += 50
        if score > 0:
            candidates.append((score, original))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    # Fallback: última hoja (a menudo es la más reciente)
    return sheet_names[-1]


def _norm_lote(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip().upper()


def _sheet_contains_lote(xls: pd.ExcelFile, sheet_name: str, lote_actual: str) -> bool:
    lote_norm = _norm_lote(lote_actual)
    if not lote_norm:
        return False

    try:
        raw = pd.read_excel(xls, sheet_name=sheet_name, header=None, dtype=str, nrows=120)
    except Exception:
        return False

    header_row = _find_header_row(raw)
    if header_row is None:
        return False

    header = raw.iloc[header_row].tolist()
    header = [str(h).strip() if h is not None else "" for h in header]
    body = raw.iloc[header_row + 1 :].copy()
    body.columns = header
    body = body.loc[:, [c for c in body.columns if str(c).strip() not in ("", "nan", "None")]]
    body = body.fillna("")

    lote_col = next((c for c in body.columns if "LOTE" in str(c).upper()), None)
    if not lote_col:
        return False

    series = body[lote_col].astype(str).fillna("").map(_norm_lote)
    return bool((series == lote_norm).any())


def _extract_lotes_from_sheet(xls: pd.ExcelFile, sheet_name: str, *, nrows: int = 180) -> List[str]:
    """
    Extrae una lista de lotes (normalizados) desde una hoja, leyendo pocas filas para ser liviano.
    """
    try:
        raw = pd.read_excel(xls, sheet_name=sheet_name, header=None, dtype=str, nrows=max(60, int(nrows)))
    except Exception:
        return []

    header_row = _find_header_row(raw)
    if header_row is None:
        return []

    header = raw.iloc[header_row].tolist()
    header = [str(h).strip() if h is not None else "" for h in header]
    body = raw.iloc[header_row + 1 :].copy()
    body.columns = header
    body = body.loc[:, [c for c in body.columns if str(c).strip() not in ("", "nan", "None")]]
    body = body.fillna("")

    lote_col = next((c for c in body.columns if "LOTE" in str(c).upper()), None)
    if not lote_col:
        return []

    lotes = []
    seen = set()
    for v in body[lote_col].astype(str).fillna("").tolist():
        n = _norm_lote(v)
        if not n or n in seen:
            continue
        seen.add(n)
        lotes.append(n)
        if len(lotes) >= 60:
            break
    return lotes


def _sheet_priority(sheet_name: str, now: _dt.datetime) -> int:
    name = _normalize_sheet_name(sheet_name)
    upper = name.upper()
    turn = current_turn(now)
    business_date = shift_business_date(now)
    ddmm = business_date.strftime("%d-%m")
    ddmmyyyy = business_date.strftime("%d-%m-%Y")

    score = 0
    if ddmmyyyy in name:
        score += 30
    if ddmm in name:
        score += 20
    if f"T{turn}" in upper:
        score += 50
    m = re.search(r"\bT(\d)\b", upper)
    if m and int(m.group(1)) == turn:
        score += 50
    return score


def _sheet_mentions_turn(sheet_name: str) -> Optional[int]:
    """
    Extrae el turno (1/2) desde el nombre de hoja si est᳇ expl᳇cito (ej: '... T1 ...').
    """
    try:
        name = _normalize_sheet_name(sheet_name).upper()
        m = re.search(r"\bT(\d)\b", name)
        if not m:
            return None
        t = int(m.group(1))
        return t if t in (1, 2) else None
    except Exception:
        return None


def _sheet_matches_turn_convention(sheet_name: str, now: _dt.datetime) -> bool:
    """
    Convenci᳇n del cliente:
    - Turno 2: la hoja incluye 'T2' (ej: '22-12 T2')
    - Turno 1: la hoja NO incluye 'T2' (ej: '22-12')
    Se usa la fecha operativa (shift_business_date) para no confundir T2 de madrugada.
    """
    try:
        turn_now = current_turn(now)
        name = _normalize_sheet_name(sheet_name).upper()
        business_date = shift_business_date(now)
        ddmm = business_date.strftime("%d-%m")
        has_ddmm = ddmm in _normalize_sheet_name(sheet_name)
        has_t2 = bool(re.search(r"\bT2\b", name))

        if turn_now == 2:
            return has_t2 and (has_ddmm or True)
        # Turno 1: preferir hojas con la fecha y sin T2
        return (not has_t2) and has_ddmm
    except Exception:
        return False


def _find_header_row(df: pd.DataFrame) -> Optional[int]:
    # Busca una fila que contenga "N° DE LOTE" (o variantes) y otras columnas típicas.
    targets = [
        "N° DE LOTE",
        "Nº DE LOTE",
        "N° LOTE",
        "Nº LOTE",
        "LOTE",
    ]
    for r in range(min(len(df), 60)):
        row = df.iloc[r].astype(str).fillna("")
        joined = " | ".join([c.strip().upper() for c in row.tolist()])
        if any(t in joined for t in targets) and ("EXPORT" in joined or "EXPORTAD" in joined):
            return r
    return None


def parse_orden_vaciado_table(
    excel_bytes: bytes,
    now: Optional[_dt.datetime] = None,
    *,
    lote_actual: Optional[str] = None,
    lotes_context: Optional[List[str]] = None,
) -> Dict[str, Any]:
    now = now or _dt.datetime.now()
    xls = pd.ExcelFile(io.BytesIO(excel_bytes))
    sheet: Optional[str] = None
    turn_now = current_turn(now)
    sheet_names = list(xls.sheet_names)
    lotes_ctx_norm = [_norm_lote(x) for x in (lotes_context or []) if _norm_lote(x)]
    lotes_ctx_set = set(lotes_ctx_norm)

    if lote_actual:
        prioritized = sorted(sheet_names, key=lambda s: _sheet_priority(s, now), reverse=True)
        scan_limit = int(_env("ORDEN_SHEET_SCAN_LIMIT", "6") or "6")

        def _try_pick(candidates: List[str]) -> Optional[str]:
            for s in candidates:
                if _sheet_contains_lote(xls, s, lote_actual):
                    return s
            return None

        # 1) Si hay contexto de lotes (tabla detalle), elegir por similitud de contenido.
        #    Esto evita casos donde el turno calculado/convención no coincide con la realidad.
        if lotes_ctx_set:
            candidates = [s for s in sheet_names if shift_business_date(now).strftime("%d-%m") in _normalize_sheet_name(s)]
            if not candidates:
                candidates = sheet_names

            best = None
            best_score = -1
            lote_norm = _norm_lote(lote_actual)
            for s in candidates:
                lotes_sheet = _extract_lotes_from_sheet(xls, s)
                lotes_sheet_set = set(lotes_sheet)

                score = 0
                if lote_norm and lote_norm in lotes_sheet_set:
                    score += 10_000
                # Overlap con detalle (lotes vistos en el turno)
                score += 10 * len(lotes_sheet_set & lotes_ctx_set)
                # Preferir hojas del turno actual seg򳇞n convención (empate)
                if _sheet_matches_turn_convention(s, now):
                    score += 5

                if score > best_score:
                    best_score = score
                    best = s
            sheet = best
        else:
            # 2) Sin contexto: buscar SIEMPRE dentro del turno actual seg򳇞n convención.
            by_turn = [s for s in prioritized if _sheet_matches_turn_convention(s, now)]
            if by_turn:
                sheet = _try_pick(by_turn[: max(1, scan_limit)]) or _try_pick(by_turn[max(1, scan_limit) :])
                if sheet is None:
                    sheet = by_turn[0]
            else:
                sheet = _try_pick(prioritized[: max(1, scan_limit)]) or _try_pick(prioritized[max(1, scan_limit) :])

    if not sheet:
        sheet = choose_sheet_name(sheet_names, now=now)
    else:
        # Validaci᳇n liviana: si la hoja elegida indica expl᳇citamente otro turno,
        # preferir una hoja del turno actual (aunque no contenga el lote) para evitar
        # quedarse "pegado" en la hoja del turno anterior al cambiar de turno.
        picked_turn = _sheet_mentions_turn(sheet)
        # Si la hoja trae T2 y estamos en T1, es un error claro seg򳇞n convenci᳇n.
        if (picked_turn == 2 and turn_now == 1) or (picked_turn in (1, 2) and picked_turn != turn_now):
            preferred = choose_sheet_name(sheet_names, now=now)
            if preferred:
                preferred_turn = _sheet_mentions_turn(preferred)
                if (turn_now == 2 and preferred_turn == 2) or (turn_now == 1 and preferred_turn != 2):
                    sheet = preferred
    if not sheet:
        return {"ok": False, "error": "No hay hojas en el Excel", "sheet": None, "columns": [], "rows": []}

    raw = pd.read_excel(xls, sheet_name=sheet, header=None, dtype=str)
    header_row = _find_header_row(raw)
    if header_row is None:
        return {"ok": False, "error": "No se encontró encabezado de tabla", "sheet": sheet, "columns": [], "rows": []}

    header = raw.iloc[header_row].tolist()
    header = [str(h).strip() if h is not None else "" for h in header]
    body = raw.iloc[header_row + 1 :].copy()
    body.columns = header

    # Eliminar columnas vacías (sin nombre)
    body = body.loc[:, [c for c in body.columns if str(c).strip() not in ("", "nan", "None")]]

    # Cortar al primer bloque vacío (cuando no hay lote y no hay productor)
    lote_col = next((c for c in body.columns if "LOTE" in str(c).upper()), None)
    prod_col = next((c for c in body.columns if "PRODUCTOR" in str(c).upper()), None)

    if lote_col:
        def _is_row_empty(row: pd.Series) -> bool:
            v1 = str(row.get(lote_col, "") or "").strip()
            v2 = str(row.get(prod_col, "") or "").strip() if prod_col else ""
            return v1 == "" and v2 == ""

        cut_idx = None
        for i in range(len(body)):
            if _is_row_empty(body.iloc[i]):
                cut_idx = i
                break
        if cut_idx is not None:
            body = body.iloc[:cut_idx]

    body = body.fillna("")

    def _norm(s: Any) -> str:
        return str(s).strip() if s is not None else ""

    def _is_placeholder_token(value: Any) -> bool:
        """
        Algunas órdenes usan filas "título" (separadores) donde solo una celda trae texto
        (a veces la columna C), pero el resto puede quedar con 0 / '-' / 'N/A' por formato.
        Para detectar esas secciones, tratamos esos tokens como "vacío".
        """
        s = _norm(value).strip().upper()
        return s in {"0", "-", "—", "N/A", "NA", "NONE", "NULL"}

    def _parse_kilos(value: Any) -> float:
        s = _norm(value)
        if s == "":
            return 0.0
        s = s.replace(" ", "")

        has_dot = "." in s
        has_comma = "," in s

        def _to_float(x: str) -> float:
            try:
                return float(x)
            except Exception:
                return 0.0

        if has_dot and has_comma:
            last_dot = s.rfind(".")
            last_comma = s.rfind(",")
            decimal_sep = "." if last_dot > last_comma else ","
            thousands_sep = "," if decimal_sep == "." else "."
            s2 = s.replace(thousands_sep, "").replace(decimal_sep, ".")
            return _to_float(s2)

        if has_comma and not has_dot:
            left, right = s.split(",", 1)
            if right.isdigit() and len(right) == 3 and left.replace("-", "").isdigit():
                return _to_float(left + right)
            return _to_float(left + "." + right)

        if has_dot and not has_comma:
            left, right = s.split(".", 1)
            if right.isdigit() and len(right) == 3 and left.replace("-", "").isdigit():
                return _to_float(left + right)
            return _to_float(left + "." + right)

        return _to_float(s)

    columns = [str(c).strip() for c in body.columns.tolist()]
    kilo_col = next((c for c in columns if "KILO" in c.upper()), None)
    prod_col2 = next((c for c in columns if "PRODUCTOR" in c.upper()), None) or prod_col
    lote_col2 = next((c for c in columns if "LOTE" in c.upper()), None) or lote_col

    cleaned_rows: List[Dict[str, Any]] = []
    total_kilos = 0.0

    for _, r in body.iterrows():
        row = {c: _norm(r.get(c, "")) for c in columns}

        # Saltar filas completamente vacías
        if all(v == "" for v in row.values()):
            continue

        productor_txt = _norm(row.get(prod_col2, "")) if prod_col2 else ""
        lote_txt = _norm(row.get(lote_col2, "")) if lote_col2 else ""
        productor_upper = productor_txt.upper()

        non_empty_cells = [(c, v) for c, v in row.items() if _norm(v) != "" and not _is_placeholder_token(v)]
        non_empty_count = len(non_empty_cells)

        # Detectar fila total (suele venir al final con solo kilos)
        non_kilo_values = [v for c, v in row.items() if c != kilo_col and v != ""]
        if kilo_col and row.get(kilo_col, "") != "" and len(non_kilo_values) == 0:
            total_kilos = _parse_kilos(row.get(kilo_col))
            continue

        # Si NO hay lote pero hay contenido, tomarlo como separador/agrupador.
        # Hay archivos donde el título viene repartido en varias columnas (ej. EXPORTADORA + VARIEDAD).
        if lote_txt == "" and non_empty_count >= 1:
            title_parts = []
            for c, v in non_empty_cells:
                if kilo_col and c == kilo_col:
                    continue
                vv = _norm(v)
                if vv:
                    title_parts.append(vv)
            title_val = " - ".join(title_parts).strip() or _norm(non_empty_cells[0][1])

            section_row = {c: "" for c in columns}
            section_row["__row_type"] = "section"
            section_row["__section_title"] = title_val
            cleaned_rows.append(section_row)
            continue

        # Detectar separadores: no hay lote y la fila es "título" (una celda con texto; resto vacío).
        # No se limita a "CAMBIO ..." (puede ser productor u otro texto).
        if lote_txt == "" and non_empty_count == 1:
            # Si la única celda con valor es KILOS, ya se manejó arriba como total.
            title_col, title_val = non_empty_cells[0]
            section_row = {c: "" for c in columns}
            section_row["__row_type"] = "section"
            section_row["__section_title"] = title_val
            section_row[title_col] = title_val
            cleaned_rows.append(section_row)
            continue

        # Fallback para separadores tipo "CAMBIO ..." aunque haya más celdas con texto
        if lote_txt == "" and productor_txt != "" and "CAMBIO" in productor_upper:
            section_row = {c: "" for c in columns}
            if prod_col2:
                section_row[prod_col2] = productor_txt
            section_row["__row_type"] = "section"
            section_row["__section_title"] = productor_txt
            cleaned_rows.append(section_row)
            continue

        row["__row_type"] = "data"
        if kilo_col:
            total_kilos += _parse_kilos(row.get(kilo_col))
        cleaned_rows.append(row)

    # Agregar columna oculta para estilos
    out_columns = columns + ["__row_type"]

    return {
        "ok": True,
        "sheet": sheet,
        "columns": out_columns,
        "rows": cleaned_rows,
        "turn": current_turn(now),
        "business_date": shift_business_date(now).isoformat(),
        "total_kilos": total_kilos,
        "generated_at": now.isoformat(),
    }


def load_orden_from_imap(
    now: Optional[_dt.datetime] = None,
    *,
    lote_actual: Optional[str] = None,
    lotes_context: Optional[List[str]] = None,
) -> Dict[str, Any]:
    now = now or _dt.datetime.now()
    host = _env("IMAP_HOST")
    port = int(_env("IMAP_PORT", "993") or "993")
    user = _env("IMAP_USER")
    password = _env("IMAP_PASS")
    mailbox = _env("IMAP_MAILBOX", DEFAULT_MAILBOX) or DEFAULT_MAILBOX
    subject_contains = _env("ORDEN_SUBJECT_CONTAINS", DEFAULT_SUBJECT_CONTAINS) or DEFAULT_SUBJECT_CONTAINS
    filename_contains = _env("ORDEN_FILENAME_CONTAINS", DEFAULT_FILENAME_CONTAINS) or DEFAULT_FILENAME_CONTAINS

    if not host or not user or not password:
        return {
            "ok": False,
            "error": "Faltan variables de entorno IMAP_HOST/IMAP_USER/IMAP_PASS",
            "meta": {},
            "columns": [],
            "rows": [],
        }

    excel_bytes, meta = fetch_latest_orden_vaciado_excel_bytes(
        host=host,
        port=port,
        user=user,
        password=password,
        mailbox=mailbox,
        subject_contains=subject_contains,
        filename_contains=filename_contains,
    )
    if not excel_bytes:
        return {"ok": False, "error": "No se encontró adjunto Excel", "meta": meta, "columns": [], "rows": []}

    parsed = parse_orden_vaciado_table(excel_bytes, now=now, lote_actual=lote_actual, lotes_context=lotes_context)
    parsed["meta"] = meta
    return parsed
