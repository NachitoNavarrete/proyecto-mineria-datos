# ============================================================
# PROYECTO MINERÍA DE DATOS - APP PRINCIPAL
# ============================================================

import csv
import os
import re
import json 


import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response

# Se agrega la función de limpieza de datos desde el módulo Analisis.limpieza 05-11-2026
# [NUEVO - 05-11-2026] se importa la función del árbol
from Analisis.limpieza import limpiar_datos
from Analisis.arbol_decision import entrenar_arbol
#Nuevo 25-11-2026 Se importa la función de reglas de asociación
from Analisis.asociacion import generar_reglas
#Nuevo 25-11-2026 se importa la función de dashboard
from Analisis.dashboard import generar_graficos
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
# ¿Qué problema se tenía antes?
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
    """Lee CSV de forma segura sin destruir el texto."""
    codificaciones = ['utf-8-sig', 'utf-16', 'latin-1', 'cp1252']
    
    for enc in codificaciones:
        try:
            # Intento con separador automático
            df = pd.read_csv(filepath, encoding=enc, sep=None, engine='python')
            if len(df.columns) > 1:
                return df
        except:
            pass
        try:
            # Intento con punto y coma (Excel en español)
            df = pd.read_csv(filepath, encoding=enc, sep=';')
            if len(df.columns) > 1:
                return df
        except:
            pass
            
    # Plan de rescate
    try:
        return pd.read_csv(filepath, encoding='utf-8-sig', sep=',', on_bad_lines='skip')
    except Exception as e:
        raise ValueError(f"No se pudo interpretar el CSV: {e}")

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

                # [NUEVO - 12-11-2026] DETECCIÓN DE SEPARADOR
        # Si el CSV viene como una sola cadena larga, detectamos si usa coma (,), 
        # punto y coma (;) o tabulación (\t). Esto pasa porque Excel en español 
        # guarda los archivos con punto y coma en lugar de comas.
        if len(parsed) == 1:
            if ',' in parsed[0]:
                parsed = [part.strip().strip('"') for part in parsed[0].split(',')]
            elif ';' in parsed[0]:
                parsed = [part.strip().strip('"') for part in parsed[0].split(';')]
            elif '\t' in parsed[0]:
                parsed = [part.strip().strip('"') for part in parsed[0].split('\t')]

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
            # 1. Leemos el archivo
            df_crudo = leer_csv_robusto(filepath)
            
            # [NUEVO 25-11-2026] Capturo las opciones que marcó el usuario.
            # Si el checkbox está en el formulario, devuelve True. Si no está, False.
            opciones_usuario = {
                'duplicados': 'opt_duplicados' in request.form,
                'incoherencias': 'opt_incoherencias' in request.form,
                'nulos': 'opt_nulos' in request.form,
                'outliers': 'opt_outliers' in request.form
            }
                        # [NUEVO 25-11-2026] PASO 3: Proceso los reemplazos personalizados.
            # Recibo el texto del input (ej: "f=femenino, m=masculino")
            texto_reemplazos = request.form.get('reemplazos', '')
            reemplazos_dict = {}
            
            if texto_reemplazos:
                # Separo por comas
                pares = texto_reemplazos.split(',')
                for par in pares:
                    if '=' in par:
                        buscar, reemplazar = par.split('=')
                        # Limpio los espacios, paso todo a minúsculas y guardo en el diccionario
                        reemplazos_dict[buscar.strip().lower()] = reemplazar.strip().lower()

            # Y AHORA SÍ, LLAMO A LA FUNCIÓN DE LIMPIEZA CON EL DICCIONARIO INCLUIDO
            df_limpio, resumen_limpieza = limpiar_datos(df_crudo, opciones_usuario, reemplazos_dict)

            # 2. Llamo a la función de limpieza pasándole el diccionario
            df_limpio, resumen_limpieza = limpiar_datos(df_crudo, opciones_usuario)

            # 3. Preparamos los datos LIMPIOS para la vista
            preview_data = df_limpio.head(50).to_dict(orient='records')
            columnas = list(df_limpio.columns)
            total_filas = len(df_limpio)

            # ... (el resto del código sigue exactamente igual)
            # [NUEVO - 05-11-2026] Guardar el CSV limpio en el disco duro
            # Para que el módulo del árbol pueda leerlo después sin volver a procesar todo.
            cleaned_filename = 'clean_' + filename
            cleaned_filepath = os.path.join(app.config['UPLOAD_FOLDER'], cleaned_filename)
            df_limpio.to_csv(cleaned_filepath, index=False)

            # Se guardan los datos en sesión para reutilizarlos al abrir la vista de preview.
            session['preview_data'] = preview_data
            session['columnas'] = columnas
            session['total_filas'] = total_filas
            session['filename'] = filename
            
            #05-11-2026 Guardamos el resumen en sesión
            session['resumen'] = resumen_limpieza 
            session['cleaned_filepath'] = cleaned_filepath # Guardamos la ruta en la sesión

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
    """Muestra la tabla con los datos crudos."""
    # Recupera la información almacenada en la sesión.
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
    # Renderiza la plantilla HTML con los datos ya cargados.
    return render_template('preview.html', 
                           data=preview_data, 
                           columnas=columnas, 
                           total_filas=total_filas,
                           filename=filename,
                           resumen=resumen) 

# ============================================================
# 5) RUTAS PARA EL ÁRBOL DE DECISIÓN (Semana 3)
# ============================================================

@app.route('/arbol')
def arbol():
    """Muestra el formulario para configurar el árbol."""
    columnas = session.get('columnas')
    if not columnas:
        flash('Primero debes subir un archivo CSV.')
        return redirect(url_for('index'))
    
    # Le pasamos las columnas al HTML para que el usuario elija en los menús desplegables
    return render_template('arbol.html', columnas=columnas)


@app.route('/entrenar_arbol', methods=['POST'])
def entrenar():
    """Recibe los parámetros del formulario, entrena el modelo y muestra resultados."""
    cleaned_filepath = session.get('cleaned_filepath')
    
    if not cleaned_filepath or not os.path.exists(cleaned_filepath):
        flash('No se encontraron los datos limpios. Sube el archivo de nuevo.')
        return redirect(url_for('index'))

    try:
        # 1. Recuperar parámetros del formulario HTML
        variable_objetivo = request.form.get('variable_objetivo')
        variables_predictoras = request.form.getlist('predictoras') # getlist porque son checkboxes
        profundidad = int(request.form.get('profundidad', 3))
        test_size = float(request.form.get('test_size', 0.2))

        if not variables_predictoras:
            flash('Debes seleccionar al menos una variable predictora.')
            return redirect(url_for('arbol'))

        # 2. Leer el CSV limpio desde el disco
        df_limpio = pd.read_csv(cleaned_filepath)

        # 3. Entrenar el modelo llamando al archivo que creaste en /analisis
        resultado = entrenar_arbol(
            df=df_limpio, 
            variable_objetivo=variable_objetivo, 
            variables_predictoras=variables_predictoras, 
            profundidad=profundidad, 
            test_size=test_size
        )

        # 4. Enviar los resultados a la plantilla HTML
        return render_template('arbol_resultado.html', 
                               resultado=resultado, 
                               variable_objetivo=variable_objetivo)

    except Exception as e:
        flash(f'Error al entrenar el árbol: {str(e)}')
        return redirect(url_for('arbol'))


# NUEVO - 12-11-2026 RUTAS PARA GESTIÓN DE MODELOS
@app.route('/guardar_modelo', methods=['POST'])
def guardar_modelo():
    import datetime
    ruta_modelos = os.path.join(BASE_DIR, 'Data', 'modelos.json')
    
    # 1. Recuperar los datos de la sesión
    resumen = session.get('resumen', {})
    exactitud = request.form.get('exactitud')
    objetivo = request.form.get('variable_objetivo')
    
    if not exactitud:
        flash('No hay modelo para guardar.')
        return redirect(url_for('index'))

    # 2. Crear el registro del modelo
    nuevo_modelo = {
        'id': str(datetime.datetime.now().timestamp()),
        'fecha': datetime.datetime.now().strftime("%d-%m-%Y %H:%M"),
        'variable_objetivo': objetivo,
        'exactitud': exactitud,
        'filas_entrenadas': resumen.get('filas_despues', 0)
    }

    # 3. Leer los modelos existentes y agregar el nuevo
    modelos = []
    if os.path.exists(ruta_modelos):
        with open(ruta_modelos, 'r', encoding='utf-8') as f:
            modelos = json.load(f)
    
    modelos.append(nuevo_modelo)

    # 4. Guardar en el archivo JSON
    with open(ruta_modelos, 'w', encoding='utf-8') as f:
        json.dump(modelos, f, indent=4)

    flash('¡Modelo guardado exitosamente!')
    return redirect(url_for('listar_modelos'))

@app.route('/modelos')
def listar_modelos():
    ruta_modelos = os.path.join(BASE_DIR, 'Data', 'modelos.json')
    modelos = []
    if os.path.exists(ruta_modelos):
        with open(ruta_modelos, 'r', encoding='utf-8') as f:
            modelos = json.load(f)
    
    return render_template('modelos.html', modelos=modelos)

@app.route('/eliminar_modelo/<modelo_id>', methods=['POST'])
def eliminar_modelo(modelo_id):
    ruta_modelos = os.path.join(BASE_DIR, 'Data', 'modelos.json')
    if os.path.exists(ruta_modelos):
        with open(ruta_modelos, 'r', encoding='utf-8') as f:
            modelos = json.load(f)
        
        # Filtrar para quitar el modelo seleccionado
        modelos = [m for m in modelos if m['id'] != modelo_id]
        
        with open(ruta_modelos, 'w', encoding='utf-8') as f:
            json.dump(modelos, f, indent=4)
            
    flash('Modelo eliminado.')
    return redirect(url_for('listar_modelos'))

# ============================================================
# RUTAS PARA REGLAS DE ASOCIACIÓN (RF4)
# ============================================================

@app.route('/asociacion')
def asociacion():
    """Muestra el formulario para configurar las reglas."""
    columnas = session.get('columnas')
    if not columnas:
        flash('Primero debes subir un archivo CSV.')
        return redirect(url_for('index'))
    
    # Le paso las reglas guardadas en sesión (si es que hay) para mostrarlas
    reglas = session.get('reglas_asociacion', [])
    return render_template('asociacion.html', columnas=columnas, reglas=reglas)


@app.route('/generar_asociacion', methods=['POST'])
def generar_asociacion():
    """Recibe los parámetros y calcula las reglas."""
    cleaned_filepath = session.get('cleaned_filepath')
    if not cleaned_filepath or not os.path.exists(cleaned_filepath):
        flash('No hay datos limpios. Sube el archivo nuevamente.')
        return redirect(url_for('index'))

    try:
        # 1. Recupero los parámetros del formulario
        min_support = float(request.form.get('min_support', 0.05)) / 100.0
        min_confidence = float(request.form.get('min_confidence', 50)) / 100.0

        # 2. Leo el CSV limpio
        df_limpio = pd.read_csv(cleaned_filepath)

                # 3. Llamo a la función
        reglas = generar_reglas(df_limpio, min_support=min_support, min_confidence=min_confidence)

        # 4. Si no hay reglas, aviso y vuelvo a cargar la página
        if len(reglas) == 0:
            flash('No se encontraron reglas con esos parámetros. Intenta bajarlos.')
            return redirect(url_for('asociacion'))
            
        # [CAMBIO 25-11-2026] El navegador se congela con tantas reglas. 
        # Guardo el total, pero solo me quedo con las 100 mejores para mostrar en pantalla.
        total_reglas = len(reglas)
        reglas_mostrar = reglas[:100] 

        flash(f'¡Éxito! Se encontraron {total_reglas} reglas. Mostrando las 100 más fuertes (mayor Lift).')

        # 5. Renderizo el HTML pasando solo las 100 reglas
        columnas = session.get('columnas')
        return render_template('asociacion.html', columnas=columnas, reglas=reglas_mostrar)

    except Exception as e:
        flash(f'Error al generar reglas: {str(e)}')
        return redirect(url_for('asociacion'))

        # ============================================================
# RUTA PARA DESCARGAR REGLAS EN CSV (RF4)
# ============================================================
@app.route('/descargar_reglas', methods=['POST'])
def descargar_reglas():
    # Recupero los datos del formulario oculto
    reglas_json = request.form.get('reglas_json')
    if not reglas_json:
        flash('No hay reglas para descargar.')
        return redirect(url_for('asociacion'))

    import json
    reglas = json.loads(reglas_json)

    # Genero el texto del CSV
    csv_data = "Antecedente,Consecuente,Soporte (%),Confianza (%),Lift\n"
    for r in reglas:
        csv_data += f'"{r["antecedentes"]}","{r["consecuentes"]}",{r["soporte"]},{r["confianza"]},{r["lift"]}\n'

    # Devuelvo el archivo para que el navegador lo descargue
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=reglas_asociacion.csv"}
    )
# ============================================================
# RUTA PARA EL DASHBOARD (RF6)
# ============================================================
@app.route('/dashboard')
def dashboard():
    """Muestra los gráficos interactivos."""
    cleaned_filepath = session.get('cleaned_filepath')
    if not cleaned_filepath or not os.path.exists(cleaned_filepath):
        flash('Primero debes subir un archivo CSV.')
        return redirect(url_for('index'))

    try:
        # Leo el CSV limpio
        df_limpio = pd.read_csv(cleaned_filepath)
        
        # Genero los gráficos llamando a mi módulo
        graficos = generar_graficos(df_limpio)
        
        return render_template('dashboard.html', graficos=graficos)
        
    except Exception as e:
        flash(f'Error al generar el dashboard: {str(e)}')
        return redirect(url_for('index'))

# RUTA PARA DESCARGAR EL INFORME EN HTML (RF5)
# ============================================================
# RUTAS PARA EL INFORME (RF5)
# ============================================================

# 1. Ruta para VER el informe en el navegador
@app.route('/informe')
def informe():
    """Muestra el informe en pantalla."""
    cleaned_filepath = session.get('cleaned_filepath')
    if not cleaned_filepath or not os.path.exists(cleaned_filepath):
        flash('Primero debes subir un archivo CSV.')
        return redirect(url_for('index'))

    try:
        df = pd.read_csv(cleaned_filepath)
        info_dataset = {
            'filas': len(df),
            'columnas': len(df.columns),
            'nombres_columnas': list(df.columns),
            'nulos_restantes': int(df.isnull().sum().sum())
        }
        resumen_limpieza = session.get('resumen', {})

        return render_template('informe.html', 
                               info_dataset=info_dataset, 
                               resumen=resumen_limpieza,
                               filename=session.get('filename'))

    except Exception as e:
        flash(f'Error al generar el informe: {str(e)}')
        return redirect(url_for('index'))


# 2. Ruta para DESCARGAR el informe en HTML
@app.route('/descargar_informe')
def descargar_informe():
    """Descarga el archivo HTML del informe."""
    cleaned_filepath = session.get('cleaned_filepath')
    if not cleaned_filepath or not os.path.exists(cleaned_filepath):
        flash('Primero debes subir un archivo CSV.')
        return redirect(url_for('index'))

    try:
        df = pd.read_csv(cleaned_filepath)
        info_dataset = {
            'filas': len(df),
            'columnas': len(df.columns),
            'nombres_columnas': list(df.columns),
            'nulos_restantes': int(df.isnull().sum().sum())
        }
        resumen_limpieza = session.get('resumen', {})

        # Renderizamos el HTML a texto y lo enviamos como descarga
        html_content = render_template('informe.html', 
                                       info_dataset=info_dataset, 
                                       resumen=resumen_limpieza,
                                       filename=session.get('filename'))

        from flask import Response
        return Response(
            html_content,
            mimetype="text/html",
            headers={"Content-Disposition": "attachment; filename=Informe_Mineria.html"}
        )

    except Exception as e:
        flash(f'Error al descargar el informe: {str(e)}')
        return redirect(url_for('index'))
# ------------------------------------------------------------
# PUNTO DE ENTRADA
# ------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)