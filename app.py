# ============================================================
# PROYECTO MINERÍA DE DATOS - SEMANA 1: CARGA Y VALIDACIÓN DE CSV
# (Versión Lector a Prueba de Balas)
# ============================================================

import csv
import os
import re

import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from Analisis.limpieza import limpiar_datos #Se agrega la función de limpieza de datos desde el módulo Analisis.limpieza 05-11-2026

# ------------------------------------------------------------
# 1) CONFIGURACIÓN BASE DE LA APLICACIÓN
# ------------------------------------------------------------
# Aquí se define la ruta de trabajo del proyecto y la carpeta
# donde se guardarán los CSVs subidos por el usuario.
# Esto evita errores de rutas relativas cuando el proyecto se ejecuta
# desde otra carpeta o desde Windows/Linux con distinta estructura.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'Web', 'Templates'), static_folder=os.path.join(BASE_DIR, 'Web', 'Static'))
app.secret_key = 'clave_secreta_mineria'
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'Data', 'Uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'csv'}

# ------------------------------------------------------------
# 2) VALIDACIÓN DEL ARCHIVO
# ------------------------------------------------------------
# Esta función comprueba que el nombre del archivo tenga extensión .csv.
# Es una validación simple pero importante: no dejamos subir imágenes,
# Excel ni archivos raros que luego rompan el parser.
def allowed_file(filename):
    """Valida que el archivo sea .csv"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------------------------------------------------
# 3) LECTURA ROBUSTA DEL CSV
# ------------------------------------------------------------
# ¿Qué problema teníamos antes?
# - El archivo venía con BOM invisible al principio.
# - Las filas estaban entre comillas.
# - Algunos nombres tenían espacios raros: " Ciudad ".
# - El separador y la codificación no siempre eran los esperados.
#
# ¿Qué hace esta función?
# 1. Lee el archivo en binario para conservar el texto original.
# 2. Prueba varias codificaciones (UTF-8, UTF-16, Latin-1, etc.).
# 3. Elimina el BOM invisible y normaliza saltos de línea.
# 4. Recorre cada línea y la convierte en una fila limpia.
# 5. Normaliza los nombres de columnas.
# 6. Convierte columnas numéricas a número cuando es posible.
#
# En pocas palabras: es como ponerle un paraguas al CSV para que no
# se rompa por detalles de Windows o exportaciones extrañas.
def leer_csv_robusto(filepath):
    """Lee CSV con BOM, comillas, espacios y texturas extrañas."""
    try:
        with open(filepath, 'rb') as f:
            raw = f.read()
    except FileNotFoundError as exc:
        raise ValueError(f'No se encontró el archivo: {filepath}') from exc

    # Prueba distintas codificaciones porque el mismo CSV puede venir
    # guardado como UTF-8, UTF-16 o Latin-1 dependiendo del editor/Windows.
    encodings = ['utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252']
    text = None

    for enc in encodings:
        try:
            text = raw.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if text is None:
        raise ValueError('El archivo no parece ser un CSV válido.')

    # Quitamos caracteres raros invisibles y uniformamos el texto.
    text = text.replace('\ufeff', '').replace('\r\n', '\n').replace('\r', '\n')
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    if not lines:
        raise ValueError('El archivo está vacío.')

    rows = []
    for line in lines:
        try:
            parsed = next(csv.reader([line], skipinitialspace=True))
        except csv.Error:
            parsed = [line]

        # Si el CSV viene como una sola cadena larga con comas, por ejemplo:
        # "Juan Pérez,25,1500,Santiago,1500"
        # aquí lo dividimos a mano para evitar que pandas lo trate como 1 sola columna.
        if len(parsed) == 1 and ',' in parsed[0]:
            parsed = [part.strip().strip('"') for part in parsed[0].split(',')]

        rows.append([str(cell).strip().strip('"') for cell in parsed])

    if not rows:
        raise ValueError('No se pudo interpretar el archivo como CSV.')

    # Se asegura que todas las filas tengan la misma cantidad de columnas.
    # Si una fila tiene menos, se rellena con cadenas vacías.
    max_cols = max(len(row) for row in rows)
    normalized_rows = [row + [''] * (max_cols - len(row)) for row in rows]
    header = normalized_rows[0]

    clean_header = []
    seen = {}
    for index, col in enumerate(header):
        # Normaliza nombres como " Nombre Completo ", "Nombre-Completo",
        # o "nombre completo" para que queden consistentes.
        base = re.sub(r'[^a-zA-Z0-9]+', ' ', str(col).strip())
        base = base.strip() or f'columna_{index + 1}'
        if base in seen:
            seen[base] += 1
            clean_header.append(f'{base}_{seen[base]}')
        else:
            seen[base] = 0
            clean_header.append(base)

    # Se arma el DataFrame limpio y listo para la vista.
    df = pd.DataFrame(normalized_rows[1:], columns=clean_header)
    df = df.replace(r'^\s*$', pd.NA, regex=True)
    df = df.apply(lambda col: col.map(lambda value: value.strip() if isinstance(value, str) else value))

    # Aquí convertimos columnas numéricas a formato numérico.
    # Es decir: '25' pasa a 25, '1500' a 1500, etc.
    # Si la columna es texto (por ejemplo nombre), no se toca.
    for col in df.columns:
        if col.lower() not in {'nombre completo', 'ciudad'}:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception:
                pass

    if df.empty:
        raise ValueError('El CSV no contiene filas válidas.')

    return df

# ------------------------------------------------------------
# 4) RUTAS DE FLASK
# ------------------------------------------------------------
# Las rutas controlan qué se muestra en pantalla.
# - / : carga el formulario para subir archivo.
# - /upload : recibe el CSV, lo procesa y guarda una vista previa.
# - /preview : muestra la tabla con los datos cargados.

@app.route('/')
def index():
    """Muestra el formulario de subida."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Recibe, guarda y procesa el archivo CSV."""
    # Validación rápida: si no llega el archivo, regresamos al inicio.
    if 'file' not in request.files:
        flash('No se encontró el archivo.')
        return redirect(url_for('index'))

    file = request.files['file']

    # Si el usuario no eligió nada, se evita guardar un archivo vacío.
    if file.filename == '':
        flash('No seleccionaste ningún archivo.')
        return redirect(url_for('index'))

    # Si el archivo es CSV y el nombre es válido, se guarda en la carpeta de uploads.
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # Aquí se ejecuta la lectura robusta del CSV.
            df = leer_csv_robusto(filepath)

            # Se toma una pequeña vista previa para mostrar sin saturar la UI.
            preview_data = df.head(50).to_dict(orient='records')
            columnas = list(df.columns)
            total_filas = len(df)

            # Se guardan los datos en sesión para reutilizarlos al abrir la vista de preview.
            session['preview_data'] = preview_data
            session['columnas'] = columnas
            session['total_filas'] = total_filas
            session['filename'] = filename

            flash('¡Archivo cargado y validado correctamente!')
            return redirect(url_for('preview'))

        except Exception as e:
            flash(f'Error al leer el CSV: {str(e)}')
            return redirect(url_for('index'))
    else:
        flash('Formato inválido. Solo se permiten archivos .csv')
        return redirect(url_for('index'))

@app.route('/preview')
def preview():
    """Muestra la tabla con los datos crudos."""
    # Recupera la información almacenada en la sesión.
    preview_data = session.get('preview_data')
    columnas = session.get('columnas')
    total_filas = session.get('total_filas')
    filename = session.get('filename')

    if not preview_data:
        flash('No hay datos para mostrar. Sube un archivo primero.')
        return redirect(url_for('index'))

    # Renderiza la plantilla HTML con los datos ya cargados.
    return render_template('preview.html', 
                           data=preview_data, 
                           columnas=columnas, 
                           total_filas=total_filas,
                           filename=filename)

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/')
def index():
    """Muestra el formulario de subida."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Recibe, guarda y procesa el archivo CSV."""
    if 'file' not in request.files:
        flash('No se encontró el archivo.')
        return redirect(url_for('index'))
    
    file = request.files['file']

    if file.filename == '':
        flash('No seleccionaste ningún archivo.')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # 1. Leemos el archivo (Datos crudos)
            df_crudo = leer_csv_robusto(filepath)
            
            # 05-11-2026 Integración de limpieza automática
            # Pasamos los datos sucios por la función de limpieza
            df_limpio, resumen_limpieza = limpiar_datos(df_crudo)

            # 3. Preparamos los datos LIMPIOS para la vista
            preview_data = df_limpio.head(50).to_dict(orient='records')
            columnas = list(df_limpio.columns)
            total_filas = len(df_limpio)

            # Guardamos en sesión
            session['preview_data'] = preview_data
            session['columnas'] = columnas
            session['total_filas'] = total_filas
            session['filename'] = filename
            
            #05-11-2026 Guardamos el resumen en sesión
            session['resumen'] = resumen_limpieza 

            flash('¡Archivo procesado y limpiado automáticamente!')
            return redirect(url_for('preview'))

        except Exception as e:
            flash(f'Error al leer el CSV: {str(e)}')
            return redirect(url_for('index'))
    else:
        flash('Formato inválido. Solo se permiten archivos .csv')
        return redirect(url_for('index'))

@app.route('/preview')
def preview():
    preview_data = session.get('preview_data')
    columnas = session.get('columnas')
    total_filas = session.get('total_filas')
    filename = session.get('filename')
    
    #05-11-2026 Recuperamos el resumen de limpieza
    resumen = session.get('resumen') 

    if not preview_data:
        flash('No hay datos para mostrar. Sube un archivo primero.')
        return redirect(url_for('index'))

    #05-11-2026 Enviamos el resumen al HTML
    return render_template('preview.html', 
                           data=preview_data, 
                           columnas=columnas, 
                           total_filas=total_filas,
                           filename=filename,
                           resumen=resumen) 

if __name__ == '__main__':
    app.run(debug=True)