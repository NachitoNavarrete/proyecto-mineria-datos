# ============================================================
# PROYECTO MINERÍA DE DATOS - SEMANA 1: CARGA Y VALIDACIÓN DE CSV
# ============================================================
# ¿Qué hace este archivo?
#   Levanta un servidor web con Flask, muestra un formulario para 
#   subir un archivo CSV, valida que sea correcto y muestra una 
#   vista previa (las primeras 50 filas) de los datos crudos.
#
# ¿Por qué está separado en rutas?
#   Flask usa el patrón de diseño "Ruta -> Función". Cada URL 
#   (@app.route) ejecuta una función específica.
# ============================================================

import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename

# ------------------------------------------------------------
# CONFIGURACIÓN INICIAL DE FLASK
# ------------------------------------------------------------
# template_folder: le dice a Flask dónde buscar los archivos HTML.
# static_folder: le dice dónde buscar CSS/JS (por ahora vacío).
app = Flask(__name__, template_folder='web/templates', static_folder='web/static')

# secret_key: Flask necesita una clave para encriptar la 'session'. 
# Sin esto, no podemos guardar datos entre la página de subida y la de vista previa.
app.secret_key = 'clave_secreta_mineria'

# UPLOAD_FOLDER: Carpeta física donde se guardarán los archivos que suba el usuario.
app.config['UPLOAD_FOLDER'] = 'data/uploads'

# MAX_CONTENT_LENGTH: Límite de tamaño (16 MB). 
# Si alguien intenta subir un archivo de 2 GB, Flask lo rechaza automáticamente para no tumbar el servidor.
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Extensiones permitidas
ALLOWED_EXTENSIONS = {'csv'}


def allowed_file(filename):
    """
    ¿Qué hace? Verifica que el archivo termine en '.csv'.
    ¿Por qué? Por seguridad. Evita que suban scripts .php o .exe.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ------------------------------------------------------------
# RUTA 1: PÁGINA PRINCIPAL
# ------------------------------------------------------------
@app.route('/')
def index():
    """Muestra el formulario para subir el archivo."""
    return render_template('index.html')


# ------------------------------------------------------------
# RUTA 2: PROCESAR LA SUBIDA DEL ARCHIVO
# ------------------------------------------------------------
@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Recibe el archivo desde el formulario, lo valida, lo guarda
    y lo procesa con Pandas para extraer una vista previa.
    """
    
    # 1. Validar que el formulario realmente contenga un archivo
    if 'file' not in request.files:
        flash('No se encontró el archivo.')
        return redirect(url_for('index'))
    
    file = request.files['file']

    # 2. Validar que el usuario no haya dejado el campo vacío
    if file.filename == '':
        flash('No seleccionaste ningún archivo.')
        return redirect(url_for('index'))

    # 3. Validar extensión y guardar
    if file and allowed_file(file.filename):
        # secure_filename limpia el nombre (ej: "../../passwd" se vuelve "passwd")
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Guardamos físicamente el archivo en la carpeta data/uploads
        file.save(filepath)

        try:
            # 4. LECTURA DEL CSV (La parte crítica)
            # encoding='utf-8-sig': Esto es ORO. Windows a veces mete un carácter invisible 
            # al inicio de los archivos (BOM). Si no usamos 'sig', la primera columna se rompe.
            # sep=None y engine='python': Le dicen a Pandas que adivine si es separado 
            # por comas, punto y coma o tabulaciones.
            df = pd.read_csv(filepath, encoding='utf-8-sig', sep=None, engine='python')
            
            # Plan B: Si el archivo venía separado por punto y coma (típico en Excel en español), 
            # Pandas no lo detecta y mete todo en 1 sola columna. Si eso pasa, lo forzamos.
            if len(df.columns) == 1:
                df = pd.read_csv(filepath, encoding='utf-8-sig', sep=';')

            # 5. PREPARAR DATOS PARA LA VISTA PREVIA
            # head(50): Solo tomamos las primeras 50 filas. 
            # Si el archivo tiene 1 millón de filas, no queremos colapsar el navegador.
            # to_dict(orient='records'): Convierte la tabla en una lista de diccionarios para que Jinja2 (HTML) la entienda.
            preview_data = df.head(50).to_dict(orient='records')
            columnas = list(df.columns)
            total_filas = len(df)

            # 6. GUARDAR EN SESIÓN
            # Guardamos los datos temporalmente en la "session" del navegador.
            # ¿Por qué? Para no tener que volver a leer el archivo cuando carguemos la página de vista previa.
            session['preview_data'] = preview_data
            session['columnas'] = columnas
            session['total_filas'] = total_filas
            session['filename'] = filename

            flash('¡Archivo cargado y validado correctamente!')
            return redirect(url_for('preview'))

        except Exception as e:
            # Si Pandas falla (archivo corrupto, texto en vez de CSV, etc.), atrapamos el error y avisamos.
            flash(f'Error al leer el CSV: {str(e)}')
            return redirect(url_for('index'))
    else:
        flash('Formato inválido. Solo se permiten archivos .csv')
        return redirect(url_for('index'))


# ------------------------------------------------------------
# RUTA 3: VISTA PREVIA
# ------------------------------------------------------------
@app.route('/preview')
def preview():
    """Muestra la tabla con los datos crudos del archivo."""
    # Recuperamos los datos que guardamos en la sesión en el paso anterior
    preview_data = session.get('preview_data')
    columnas = session.get('columnas')
    total_filas = session.get('total_filas')
    filename = session.get('filename')

    # Si alguien entra directo a /preview sin subir archivo, lo devolvemos al inicio
    if not preview_data:
        flash('No hay datos para mostrar. Sube un archivo primero.')
        return redirect(url_for('index'))

    # Enviamos las variables al HTML para que Jinja2 las dibuje
    return render_template('preview.html', 
                           data=preview_data, 
                           columnas=columnas, 
                           total_filas=total_filas,
                           filename=filename)


# ------------------------------------------------------------
# PUNTO DE ENTRADA
# ------------------------------------------------------------
if __name__ == '__main__':
    # debug=True hace que el servidor se reinicie solo cada vez que guardas un archivo.
    # ¡Muy útil para programar!
    app.run(debug=True)