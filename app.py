# ============================================================
# SEMANA 1: CARGA Y VALIDACIÓN DE CSV
# ============================================================
# Objetivo: Recibir un archivo, validar que sea CSV, 
# revisar su tamaño/extensión y mostrar una vista previa 
# de los datos crudos.
# ============================================================

import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename

app = Flask(__name__, template_folder='web/templates', static_folder='web/static')

# Clave secreta necesaria para usar 'session' y 'flash'
app.secret_key = 'clave_secreta_mineria'

# Configuración de la carpeta donde se guardarán los CSV
app.config['UPLOAD_FOLDER'] = 'data/uploads'
# Validación de tamaño: Máximo 16 MB (16 * 1024 * 1024 bytes)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Validación de formato: Solo aceptamos .csv
ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    """
    ¿Qué hace? Verifica que el archivo tenga un punto y que 
    la extensión sea .csv.
    ¿Por qué? Para evitar que suban imágenes, .exe o .php.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Muestra la página principal con el botón de subir archivo."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Recibe el archivo desde el formulario HTML.
    Valida que exista, que no esté vacío y que sea CSV.
    """
    # 1. Verificar que el formulario envió un archivo
    if 'file' not in request.files:
        flash('No se encontró el archivo en la petición.')
        return redirect(url_for('index'))
    
    file = request.files['file']

    # 2. Verificar que el usuario seleccionó algo
    if file.filename == '':
        flash('No seleccionaste ningún archivo.')
        return redirect(url_for('index'))

    # 3. Validar extensión
    if file and allowed_file(file.filename):
        # Sanitizar el nombre para evitar ataques de rutas (ej: ../../etc/passwd)
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Guardar el archivo físicamente en la carpeta data/uploads
        file.save(filepath)

        try:
            # 4. Validar codificación y separador (Carga cruda)
            # Probamos con UTF-8, si falla usamos Latin-1 (común en Excel de Windows)
            try:
                df = pd.read_csv(filepath, encoding='utf-8', sep=None, engine='python')
            except UnicodeDecodeError:
                df = pd.read_csv(filepath, encoding='latin-1', sep=None, engine='python')

            # 5. Preparar datos para la vista previa
            # Convertimos las primeras 50 filas a un diccionario para enviarlo al HTML
            preview_data = df.head(50).to_dict(orient='records')
            columnas = list(df.columns)
            total_filas = len(df)

            # Guardamos en la sesión del navegador para mostrarlo en /preview
            session['preview_data'] = preview_data
            session['columnas'] = columnas
            session['total_filas'] = total_filas
            session['filename'] = filename

            flash('¡Archivo cargado y validado correctamente!')
            return redirect(url_for('preview'))

        except Exception as e:
            # Si pandas no puede leerlo (ej: archivo corrupto)
            flash(f'Error al leer el CSV: {str(e)}')
            return redirect(url_for('index'))
    else:
        flash('Formato inválido. Solo se permiten archivos .csv')
        return redirect(url_for('index'))

@app.route('/preview')
def preview():
    """Muestra la tabla con los datos crudos."""
    # Recuperamos los datos de la sesión
    preview_data = session.get('preview_data')
    columnas = session.get('columnas')
    total_filas = session.get('total_filas')
    filename = session.get('filename')

    if not preview_data:
        flash('No hay datos para mostrar. Sube un archivo primero.')
        return redirect(url_for('index'))

    return render_template('preview.html', 
                           data=preview_data, 
                           columnas=columnas, 
                           total_filas=total_filas,
                           filename=filename)

if __name__ == '__main__':
    # debug=True permite que el servidor se reinicie solo al guardar cambios
    app.run(debug=True)