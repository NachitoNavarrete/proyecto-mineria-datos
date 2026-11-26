# Proyecto Minería de Datos

## Descripción
Aplicación web desarrollada con Flask y Python que permite la carga, validación, limpieza automática y entrenamiento de árboles de decisión sobre archivos CSV.

## Tecnologías
- **Backend:** Python, Flask
- **Procesamiento:** Pandas, Scikit-learn, Matplotlib
- **Frontend:** HTML, Jinja2, Bootstrap

## Estructura
- `app.py`: Punto de entrada y rutas de Flask.
- `Analisis/algoritmos/`: Árbol de decisión y reglas de asociación.
- `Analisis/preprocesamiento/`: Limpieza y preparación de datos.
- `Analisis/visualizacion/`: Gráficos del dashboard.
- `Web/Templates/`: Plantillas en `arbol/`, `asociacion/`, `dashboard/`, `datos/`, `informes/` y `modelos/`; `base.html` es compartida.
- `Data/Uploads/`: Archivos CSV subidos.
- `Data/modelos.json`: Persistencia de modelos guardados.

### Mapa de carpetas
```text
Proyecto Minería de Datos/
├── app.py
├── Analisis/
│   ├── __init__.py
│   ├── algoritmos/
│   │   ├── arbol_decision.py
│   │   └── asociacion.py
│   ├── preprocesamiento/
│   │   └── limpieza.py
│   └── visualizacion/
│       └── dashboard.py
├── Data/
│   ├── Uploads/
│   │   └── Archivos CSV
│   └── modelos.json
├── Web/
│   ├── Static/
│   │   ├── css/
│   │   └── js/
│   └── Templates/
│       ├── arbol/
│       │   ├── arbol.html
│       │   └── arbol_resultado.html
│       ├── asociacion/
│       │   └── asociacion.html
│       ├── dashboard/
│       │   └── dashboard.html
│       ├── datos/
│       │   ├── index.html
│       │   └── preview.html
│       ├── informes/
│       │   └── informe.html
│       ├── modelos/
│       │   └── modelos.html
│       └── base.html
├── README.md
└── requirements.txt.txt
```

## Instalación y Uso
1. Activar entorno: `.venv\Scripts\activate`
2. Instalar dependencias: `pip install -r requirements.txt`
3. Ejecutar: `python app.py`
4. Ir a `http://127.0.0.1:5000`

## Estado del Avance 
- [x] Carga y validación de CSV.
- [x] Limpieza automática (nulos, duplicados, outliers).
- [x] Entrenamiento de Árbol de Decisión y métricas.
- [x] Gestión de modelos (Guardar, listar, eliminar).
