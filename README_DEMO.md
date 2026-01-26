# 🍎 Panel Dash - AgroIndustria XYZ S.A. (Demo)

Versión de demostración del sistema de monitoreo de producción con **datos ficticios** para presentación a potenciales clientes.

## 🎯 ¿Qué es esto?


- **Presentaciones comerciales** 📊
- **Demos a clientes** 👥
- **Desarrollo y testing** 🛠️
- **Portfolio personal** 📁

## 🚀 Inicio Rápido

### Opción 1: Modo Completo (Recomendado)
```bash
python run_demo.py --mode full
```
Esto inicia automáticamente:
- Base de datos demo con datos ficticios
- Simulación de producción en tiempo real
- Dashboard web

### Opción 2: Configuración Manual

1. **Crear base de datos demo:**
```bash
python demo_db_generator.py
```

2. **Iniciar simulación (en terminal separada):**
```bash
python demo_simulation.py --mode continuous --interval 30
```

3. **Iniciar dashboard:**
```bash
python app_demo.py
```

## 📊 Características de la Demo

### 🏢 Empresa Ficticia
- **Nombre:** AgroIndustria XYZ S.A.
- **Productos:** Manzanas, Peras, Cerezas, Uvas
- **Procesos:** Calibrado y Empacado
- **Proveedores:** 5 proveedores ficticios
- **Exportadores:** 5 destinos de exportación

### 📈 Datos Simulados
- **50 lotes** de producción con datos realistas
- **Producción en tiempo real** que se actualiza automáticamente
- **Cambio automático de lotes** cada 5 minutos (en promedio)
- **Métricas por turno** (Turno 1: 08:00-20:00, Turno 2: 20:00-08:00)
- **Datos históricos** para análisis de tendencias

### 🎭 Simulación Inteligente
- **Progreso realista:** Las cajas vaciadas aumentan gradualmente
- **Rotación de lotes:** Cambia automáticamente entre lotes activos
- **Variabilidad:** Pesos y rendimientos variables pero realistas
- **Tiempos de detención:** Simula paradas ocasionales de maquinaria

## 🗄️ Estructura de Archivos

```
├── app_demo.py              # Dashboard modificado para demo
├── demo_db_generator.py     # Generador de base de datos SQLite
├── demo_simulation.py       # Simulador de producción en tiempo real
├── config_demo.py           # Configuración para alternar modos
├── run_demo.py              # Script de inicio simplificado
├── demo_database.db         # Base de datos SQLite (generada automáticamente)
└── README_DEMO.md          # Esta documentación
```

## ⚙️ Configuración

### Variables de Entorno
```bash
# Modo de operación
set MODO_OPERACION=DEMO    # Datos ficticios (por defecto)
```

### Parámetros de Simulación
```bash
# Intervalo de actualización (segundos)
python demo_simulation.py --interval 60

# Modos de simulación
python demo_simulation.py --mode continuous  # Continua
python demo_simulation.py --mode burst       # Burst de producción
python demo_simulation.py --mode change      # Cambiar lote manualmente
```

## 🎨 Personalización

### Modificar Datos de Empresa
Edita `demo_db_generator.py` en la sección `empresa_config`:

```python
self.empresa_config = {
    "nombre": "Tu Empresa S.A.",
    "productos": [
        {"codigo": "TU_PROD", "nombre": "Tu Producto", "variedades": ["Var1", "Var2"]},
    ],
    "procesos": [
        {"codigo": "PROC001", "nombre": "Tu Proceso"},
    ]
}
```

### Ajustar Simulación
En `demo_simulation.py`, modifica:
- `update_interval`: Frecuencia de actualizaciones
- `max_cambio_lote_interval`: Tiempo entre cambios de lote
- Lógica de incremento de producción

## 🔄 Alternar entre Modos

### Para usar datos DEMO (SQLite):
```bash
set MODO_OPERACION=DEMO
python app_demo.py  # Versión demo
```

## 📱 Acceso al Dashboard

- **URL:** http://localhost:8050
- **Configuración HTTPS:** https://localhost:8443 (con Caddy)
- **Información del sistema:** http://localhost:8050/setup

## 🛠️ Desarrollo

### Agregar Nuevas Métricas
1. Modifica `demo_db_generator.py` para agregar columnas/vistas
2. Actualiza `functions.py` si es necesario
3. Ajusta `demo_simulation.py` para actualizar los nuevos datos

### Depuración
```bash
# Ver configuración actual
python config_demo.py

# Ejecutar una sola actualización
python demo_simulation.py --mode single

# Ver logs de la aplicación
tail -f logs/app.log
```

## 📋 Requisitos

- Python 3.8+
- Las mismas dependencias que el proyecto original
- **SQLite** (viene incluido con Python)

## 🎯 Casos de Uso Ideales

1. **Demo a Cliente:** Muestra funcionalidad completa sin datos sensibles
2. **Desarrollo:** Prueba nuevas features sin afectar producción
3. **Training:** Entrena a usuarios con datos realistas
4. **Portfolio:** Presenta tu trabajo a potenciales empleadores

## 🚨 Notas Importantes

- Los datos son **completamente ficticios**
- La simulación es **determinística pero realista**
- **Portable:** Todo funciona en un solo directorio

## 📞 Soporte

Para preguntas sobre la versión demo:
1. Revisa los logs en `logs/app.log`
2. Verifica la configuración con `python config_demo.py`
3. Prueba la base de datos con `python demo_db_generator.py`

---

**¡Listo para impresionar a tus clientes! 🚀**