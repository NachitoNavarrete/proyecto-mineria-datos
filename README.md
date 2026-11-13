# Proyecto Minería de Datos

## Descripción
Aplicación web desarrollada con Flask y Python que permite la carga, validación, limpieza automática y entrenamiento de árboles de decisión sobre archivos CSV.

## Tecnologías
- **Backend:** Python, Flask
- **Procesamiento:** Pandas, Scikit-learn, Matplotlib
- **Frontend:** HTML, Jinja2, Bootstrap

## Estructura
- `app.py`: Punto de entrada y rutas de Flask.
- `Analisis/`: Módulos de procesamiento (limpieza.py y arbol_decision.py).
- `Web/Templates/`: Vistas HTML.
- `Data/Uploads/`: Archivos CSV subidos.
- `Data/modelos.json`: Persistencia de modelos guardados.

## Instalación y Uso
1. Activar entorno: `.venv\Scripts\activate`
2. Instalar dependencias: `pip install -r requirements.txt`
3. Ejecutar: `python app.py`
4. Ir a `http://127.0.0.1:5000`

## Estado del Avance (Nota 1)
- [x] Carga y validación de CSV.
- [x] Limpieza automática (nulos, duplicados, outliers).
- [x] Entrenamiento de Árbol de Decisión y métricas.
- [x] Gestión de modelos (Guardar, listar, eliminar).
