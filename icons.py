"""
Archivo de iconos SVG para la aplicación
"""

from collections import OrderedDict

# Icono de caja/contenedor
BOX_ICON_SVG = """<svg fill="#ffffff" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg" stroke="#ffffff"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"><path d="M510.28 445.86l-73.03-292.13c-3.8-15.19-16.44-25.72-30.87-25.72h-60.25c3.57-10.05 5.88-20.72 5.88-32 0-53.02-42.98-96-96-96s-96 42.98-96 96c0 11.28 2.3 21.95 5.88 32h-60.25c-14.43 0-27.08 10.54-30.87 25.72L1.72 445.86C-6.61 479.17 16.38 512 48.03 512h415.95c31.64 0 54.63-32.83 46.3-66.14zM256 128c-17.64 0-32-14.36-32-32s14.36-32 32-32 32 14.36 32 32-14.36 32-32 32z"></path></g></svg>"""

# Icono para capacidad restante
CAPACITY_ICON_SVG = """<svg viewBox="0 0 16.00 16.00" fill="none" xmlns="http://www.w3.org/2000/svg" stroke="#ffffff" stroke-width="0.00016"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round" stroke="#CCCCCC" stroke-width="0.32"></g><g id="SVGRepo_iconCarrier"> <path d="M10 3L9.00001 4L11.2929 6.29289L8.50001 9.08579L5.50001 6.08579L0.292908 11.2929L1.70712 12.7071L5.50001 8.91421L8.50001 11.9142L12.7071 7.70711L15 10L16 9L16 3H10Z" fill="#ffffff"></path> </g></svg>"""

# Icono para proceso (rayo)
PROCESS_ICON_SVG = """<svg fill="#ffffff" viewBox="0 0 24 24" id="thunder" data-name="Line Color" xmlns="http://www.w3.org/2000/svg" class="icon line-color"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"><path id="primary" d="M17.76,10.63,9,21l2.14-8H7.05a1,1,0,0,1-1-1.36l3.23-8a1.05,1.05,0,0,1,1-.64h4.34a1,1,0,0,1,1,1.36L13.7,9H17A1,1,0,0,1,17.76,10.63Z" style="fill: none; stroke: #ffffff; stroke-linecap: round; stroke-linejoin: round; stroke-width: 2;"></path></g></svg>"""

# Icono para cajas vaciadas
BOXES_EMPTIED_ICON_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"> <path d="M20.3873 7.1575L11.9999 12L3.60913 7.14978" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path> <path d="M12 12V21" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path> <path d="M11 2.57735C11.6188 2.22008 12.3812 2.22008 13 2.57735L19.6603 6.42265C20.2791 6.77992 20.6603 7.44017 20.6603 8.1547V15.8453C20.6603 16.5598 20.2791 17.2201 19.6603 17.5774L13 21.4226C12.3812 21.7799 11.6188 21.7799 11 21.4226L4.33975 17.5774C3.72094 17.2201 3.33975 16.5598 3.33975 15.8453V8.1547C3.33975 7.44017 3.72094 6.77992 4.33975 6.42265L11 2.57735Z" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path> <path d="M8.5 4.5L16 9" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path> </g></svg>"""

def get_box_icon(color="#ffffff"):
    """
    Retorna el SVG del icono de caja con el color especificado
    
    Args:
        color (str): Color hexadecimal para el fill y stroke del SVG
        
    Returns:
        str: SVG del icono de caja
    """
    return BOX_ICON_SVG.replace("#ffffff", color)


# Orden sugerido para las tarjetas superiores (mismo orden que el panel):
# 1) Cajas Totales
# 2) Cajas Vaciadas
# 3) Kg por Proceso
# 4) Capacidad Restante
METRIC_ICONS_ORDERED = OrderedDict(
    [
        ("Cajas Totales", BOX_ICON_SVG),
        ("Cajas Vaciadas", BOXES_EMPTIED_ICON_SVG),
        ("Kg por Proceso", PROCESS_ICON_SVG),
        ("Capacidad Restante", CAPACITY_ICON_SVG),
    ]
)

# Lista en el orden respectivo (por si la necesitas como array)
METRIC_ICON_SVGS = list(METRIC_ICONS_ORDERED.values())

# Iconos para "Orden de Vaciado" (meta + acordeón)
FILE_ICON_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-6Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 2v6h6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 13h8M8 17h8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

CLOCK_ICON_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 22A10 10 0 1 0 12 2a10 10 0 0 0 0 20Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 6v6l4 2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

MAIL_ICON_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 6h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="m22 8-10 7L2 8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

SCALE_ICON_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M6 7h12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 7 6 13h6L9 7Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M15 7 12 13h6l-3-6Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 13v7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 20h8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

STACK_ICON_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 3 3 8l9 5 9-5-9-5Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 12l9 5 9-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 16l9 5 9-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

# Icono personalizado para "Kilos"
KILOS_ICON_SVG = """<svg fill="#000000" version="1.1" id="Capa_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 612 612" xml:space="preserve"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"> <g> <path d="M610.434,512.716l-95.988-296.691c-4.244-13.117-16.459-22.003-30.245-22.003H382.904 c8.211-13.563,13.028-29.399,13.028-46.379c0-49.586-40.346-89.933-89.933-89.933c-49.586,0-89.933,40.346-89.933,89.933 c0,16.979,4.817,32.815,13.029,46.379H127.8c-13.786,0-26.001,8.886-30.245,22.003L1.567,512.716 c-6.643,20.531,8.666,41.573,30.245,41.573h548.376C601.768,554.29,617.076,533.248,610.434,512.716z M258.452,147.643 c0-26.221,21.327-47.548,47.548-47.548c26.221,0,47.548,21.327,47.548,47.548c0,22.705-16.015,41.682-37.327,46.379H295.78 C274.467,189.326,258.452,170.348,258.452,147.643z M263.962,451.032l-27.475-52.756h-13.092v52.756h-31.83V320.978h31.83v50.208 h13.092l26.927-50.208h34.198l-35.117,62.205v0.37l37.116,67.479H263.962z M431.369,451.032h-26.557v-3.644 c0-2.726,0.178-5.45,0.178-5.45h-0.355c0,0-12.56,11.271-34.198,11.271c-33.294,0-63.85-24.912-63.85-67.479 c0-37.827,28.555-66.931,68.219-66.931c33.28,0,50.017,17.271,50.017,17.271l-15.285,23.831c0,0-13.271-11.997-31.65-11.997 c-27.282,0-38.375,17.462-38.375,36.73c0,24.75,17.092,39.472,37.294,39.472c15.27,0,26.362-9.449,26.362-9.449v-10.013h-18.365 v-27.104h46.565L431.369,451.032L431.369,451.032z"></path> </g> </g></svg>"""
