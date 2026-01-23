"""
Módulo de estilos CSS para la aplicación
Adaptado del diseño moderno del dashboard Next.js
"""
import streamlit as st

def load_css():
    """Carga los estilos CSS personalizados con diseño moderno mejorado"""
    st.markdown("""
        <style>
        /* Reset y base - Gradiente suave de fondo */
        .stApp {
            background: linear-gradient(to bottom right, #fafafa 0%, #f0f9f4 50%, #fafafa 100%);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }
        
        /* Header moderno con gradiente mejorado */
        .main-header {
            background: linear-gradient(135deg, #059669 0%, #10b981 50%, #34d399 100%);
            padding: 2rem;
            border-radius: 0;
            margin: -1rem -1rem 2rem -1rem;
            color: white;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .main-header::before {
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            width: 400px;
            height: 400px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 50%;
            filter: blur(80px);
            transform: translate(50%, -50%);
            pointer-events: none;
        }
        
        .main-header::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 300px;
            height: 300px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 50%;
            filter: blur(60px);
            transform: translate(-25%, 50%);
            pointer-events: none;
        }
        
        .header-content {
            position: relative;
            z-index: 1;
        }
        
        .header-logo {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 48px;
            height: 48px;
            background: rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            font-size: 24px;
            margin-right: 12px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        .header-title {
            font-size: 2.5rem;
            font-weight: 900;
            letter-spacing: -0.02em;
            margin: 0;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        .header-subtitle {
            color: rgba(255, 255, 255, 0.95);
            font-size: 0.875rem;
            font-weight: 500;
            margin-top: 4px;
        }
        
        .update-badge {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 0.75rem 1rem;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            text-align: right;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        .update-label {
            font-size: 1.7rem;
            color: rgba(255, 255, 255, 0.95);
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .update-time {
            font-size: 1.7rem;
            font-weight: 600;
            color: white;
        }
        
        /* Cards modernos mejorados */
        .metric-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        
        .metric-card:hover {
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
            border-color: #10b981;
            transform: translateY(-2px);
        }
        
        .metric-card::before {
            content: '';
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.05), rgba(147, 51, 234, 0.05));
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
        }
        
        .metric-card:hover::before {
            opacity: 1;
        }
        
        .metric-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 48px;
            height: 48px;
            border-radius: 10px;
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            color: white;
            font-size: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: 900;
            color: #111827;
            margin: 0.5rem 0;
            line-height: 1.2;
        }
        
        .metric-label {
            font-size: 1.5rem;
            font-weight: 500;
            color: #6b7280;
            margin-bottom: 0.25rem;
        }
        
        .metric-subtext {
            font-size: 1.25rem;
            color: #9ca3af;
            font-weight: 500;
            padding-top: 0.5rem;
            border-top: 1px solid #e5e7eb;
        }
        .st-emotion-cache-3qzj0x {
            font-size: 1.875rem;
            color: inherit;
            max-width: 100%;
            overflow-wrap: break-word;
        }
        
        /* Filter bar moderno mejorado */
        .filter-card {
            background: white;
            padding: 1rem;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1);
            margin-bottom: 1.5rem;
        }
        
        .filter-box {
            background: #f9fafb;
            padding: 0.5rem;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
            margin: 0.25rem;
        }
        
        .filter-label {
            font-size: 1.3rem;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.25rem;
        }
        
        .filter-value {
            font-size: 1.6rem;
            font-weight: 500;
            color: #111827;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            padding: 0.5rem;
            background: #f9fafb;
            border-radius: 6px;
        }
        
        /* Section titles mejorados */
        .section-title {
            font-size: 1.125rem;
            font-weight: 700;
            color: #111827;
            margin-bottom: 1rem;
            margin-top: 1.5rem;
        }
        
        /* Chart cards mejorados */
        .chart-card {
            background: white;
            padding: 2rem;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1);
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        
        .chart-card:hover {
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
        }
        
        .chart-card::before {
            content: '';
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.05), rgba(147, 51, 234, 0.05));
            pointer-events: none;
        }
        
        .chart-title {
            font-size: 2.125rem;
            font-weight: 700;
            color: #111827;
            margin-bottom: 0.25rem;
        }
        
        .chart-subtitle {
            font-size: 1.4rem;
            color: #6b7280;
            margin-bottom: 1.5rem;
        }
        
        .progress-bar-container {
            background: #e5e7eb;
            height: 12px;
            border-radius: 6px;
            overflow: hidden;
            margin: 1rem 0;
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.06);
        }
        
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #3b82f6, #2563eb);
            border-radius: 6px;
            transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
        }
        
        /* Table styling mejorado */
        .stDataFrame {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #e5e7eb;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }
        
        .dataframe {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #e5e7eb;
            width: 100%;
        }
        
        .dataframe thead {
            background: #f9fafb;
            border-bottom: 2px solid #e5e7eb;
        }
        
        .dataframe th {
            font-weight: 700;
            color: #111827;
            padding: 0.75rem 1rem;
            border-bottom: 2px solid #e5e7eb;
            text-align: left;
            font-size: 1.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .dataframe td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #e5e7eb;
            color: #374151;
            font-size: 1.75rem;
        }
        
        .dataframe tbody tr {
            transition: background-color 0.15s ease;
        }
        
        .dataframe tbody tr:hover {
            background: #f9fafb;
        }
        
        .dataframe tbody tr:last-child td {
            border-bottom: none;
        }
        
        /* Aumentar tamaño de letra en tablas de detalle */
        .stDataFrame table {
            font-size: 1.75rem !important;
        }
        .stDataFrame th,
        .stDataFrame td {
            font-size: 1.75rem !important;
            line-height: 1.4;
        }
        /* Fallback: apuntar al data-testid que envuelve la tabla de Streamlit */
        div[data-testid="stDataFrame"] table {
            font-size: 1.75rem !important;
        }
        div[data-testid="stDataFrame"] th,
        div[data-testid="stDataFrame"] td {
            font-size: 1.75rem !important;
            line-height: 1.4;
        }
        
        /* Badge styles mejorados */
        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            line-height: 1.5;
        }
        
        .badge-blue {
            background: #2563eb;
            color: white;
        }
        
        .badge-amber {
            background: #d97706;
            color: white;
        }
        
        .badge-secondary {
            background: #f3f4f6;
            color: #374151;
            border: 1px solid #e5e7eb;
        }
        
        /* Metrics grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2rem;
        }
        
        /* Mejoras adicionales para Streamlit */
        .element-container {
            margin-bottom: 1.5rem;
        }
        
        /* Hide Streamlit default elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display: none;}
        
        /* Mejoras de espaciado */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        /* Scrollbar personalizado */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }
        
        /* Estilos para Tabs modernos y destacados */
        .stTabs {
            margin: 2rem 0;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.75rem;
            background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
            padding: 0.75rem;
            border-radius: 16px;
            border: 2px solid #e5e7eb;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.8);
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 3.5rem;
            padding: 0 2rem;
            border-radius: 12px;
            font-weight: 700;
            font-size: 0.9375rem;
            letter-spacing: 0.01em;
            color: #64748b;
            background: transparent;
            border: 2px solid transparent;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            text-transform: none;
        }
        
        .stTabs [data-baseweb="tab"]::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(5, 150, 105, 0.08));
            opacity: 0;
            transition: opacity 0.3s ease;
            border-radius: 10px;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(5, 150, 105, 0.12));
            color: #059669;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.15);
            border-color: rgba(16, 185, 129, 0.3);
        }
        
        .stTabs [data-baseweb="tab"]:hover::before {
            opacity: 1;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #ffffff 0%, #f9fafb 100%);
            color: #059669;
            box-shadow: 0 4px 16px rgba(16, 185, 129, 0.2), 
                        0 2px 4px rgba(0, 0, 0, 0.1),
                        inset 0 1px 0 rgba(255, 255, 255, 0.9);
            border: 2px solid #10b981;
            transform: translateY(-1px);
            font-weight: 800;
            position: relative;
        }
        
        .stTabs [aria-selected="true"]::after {
            content: '';
            position: absolute;
            bottom: -2px;
            left: 50%;
            transform: translateX(-50%);
            width: 60%;
            height: 3px;
            background: linear-gradient(90deg, #10b981, #059669);
            border-radius: 2px 2px 0 0;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.4);
        }
        
        .stTabs [aria-selected="true"]::before {
            opacity: 0;
        }
        
        .stTabs [data-baseweb="tab"]:active {
            transform: translateY(0);
            transition: transform 0.1s ease;
        }
        
        .stTabs [data-baseweb="tab-panel"] {
            padding-top: 2rem;
            animation: fadeIn 0.3s ease-in;
        }
        
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        /* Mejorar el contenedor de tabs */
        .stTabs > div {
            margin-top: 1rem;
        }
        
        /* Mejorar la presentación de los textos en los tabs */
        .stTabs [data-baseweb="tab"] > div {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }
        
        /* Asegurar que los tabs tengan buen espaciado entre ellos */
        .stTabs [data-baseweb="tab-list"] > div {
            flex: 1;
        }
        
        /* Efecto de brillo sutil en el tab activo */
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%);
        }
        
        /* Responsive: ajustar tamaño de fuente en tabs más pequeños */
        @media (max-width: 768px) {
            .stTabs [data-baseweb="tab"] {
                font-size: 0.8125rem;
                padding: 0 1.25rem;
            }
        }
        </style>
    """, unsafe_allow_html=True)
