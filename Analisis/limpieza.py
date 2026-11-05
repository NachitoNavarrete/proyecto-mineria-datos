# ============================================================
# MODULO DE LIMPIEZA AUTOMATICA
# ============================================================
# ¿Qué hace este archivo?
#   Carga un CSV y lo prepara para análisis limpio y seguro.
#
# ¿Por qué está separado de app.py?
#   Porque la lógica de datos no debe mezclarse con la web.
#   Si mañana cambias de Flask a otra tecnología, este archivo sigue
#   siendo útil sin tocar la parte visual.
# ============================================================

import csv
import re

import pandas as pd        # Manipulación de datos tabulares
import numpy as np         # Operaciones numéricas

# ------------------------------------------------------------
# FUNCIÓN PRINCIPAL: cargar_csv
# ------------------------------------------------------------
# Cambios realizados:
# 23-10-2026
# - se agregó lectura más robusta para CSVs con BOM invisible
# - se arreglan filas que vienen entre comillas y con espacios raros
# - se corrigen columnas con nombres desordenados o vacíos
# - se convierten columnas numéricas a tipo número cuando es posible
#
# ¿Cómo funciona?
# 1) Lee el archivo en binario para conservar caracteres especiales.
# 2) Prueba varias codificaciones (UTF-8 / UTF-16 / Latin-1).
# 3) Quita el BOM y normaliza saltos de línea.
# 4) Si una fila viene como una sola cadena con comas, la divide.
# 5) Genera un DataFrame limpio y preparado para análisis.

def cargar_csv(filepath):
    """Carga un CSV robustamente aunque venga con BOM, comillas o espacios raros."""
    try:
        with open(filepath, 'rb') as f:
            raw = f.read()
    except FileNotFoundError as exc:
        raise ValueError(f'No se encontró el archivo: {filepath}') from exc

    for enc in ['utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252']:
        try:
            text = raw.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            text = None

    if text is None:
        raise ValueError('No se pudo decodificar el CSV.')

    text = text.replace('\ufeff', '').replace('\r\n', '\n').replace('\r', '\n')
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    rows = []
    for line in lines:
        try:
            parsed = next(csv.reader([line], skipinitialspace=True))
        except csv.Error:
            parsed = [line]

        if len(parsed) == 1 and ',' in parsed[0]:
            parsed = [part.strip().strip('"') for part in parsed[0].split(',')]

        rows.append([str(cell).strip().strip('"') for cell in parsed])

    if not rows:
        raise ValueError('El archivo está vacío.')

    max_cols = max(len(row) for row in rows)
    rows = [row + [''] * (max_cols - len(row)) for row in rows]
    header = rows[0]
    clean_header = []
    seen = {}
    for index, name in enumerate(header):
        base = re.sub(r'[^a-zA-Z0-9]+', ' ', str(name).strip())
        base = base.strip() or f'columna_{index + 1}'
        if base in seen:
            seen[base] += 1
            clean_header.append(f'{base}_{seen[base]}')
        else:
            seen[base] = 0
            clean_header.append(base)

    df = pd.DataFrame(rows[1:], columns=clean_header)
    df = df.replace(r'^\s*$', pd.NA, regex=True)
    for col in df.columns:
        if col.lower() not in {'nombre completo', 'ciudad'}:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception:
                pass
    return df


def limpiar_datos(df):
    """
    Aplica limpieza automática sobre un DataFrame.

    Pasos:
        1. Normaliza nombres de columnas.
        2. Elimina duplicados.
        3. Imputa valores nulos.
        4. Corrige tipos de datos.
        5. Acota outliers (IQR).

    ¿Por qué este orden?
        Primero nombres (consistencia), luego duplicados
        (no imputar filas que vamos a borrar), después
        nulos y tipos, y al final outliers (necesitan
        datos numéricos limpios).

    Devuelve:
        (df_limpio, resumen) -> tupla.
    """

    resumen = {}
    filas_antes = len(df)
    resumen['filas_antes'] = filas_antes

    # --------------------------------------------------------
    # 1. NORMALIZAR NOMBRES DE COLUMNAS
    # --------------------------------------------------------
    # "Nombre Cliente ", "nombre cliente" -> "nombre_cliente"
    # Así evitamos errores al referirnos a columnas.
    df.columns = (
        df.columns
        .str.strip()                           # Quita espacios extremos
        .str.lower()                           # Todo a minúsculas
        .str.replace(' ', '_')                 # Espacios -> _
        .str.replace(r'[^\w]', '', regex=True) # Quita símbolos raros
    )
    resumen['columnas'] = list(df.columns)

    # --------------------------------------------------------
    # 2. ELIMINAR DUPLICADOS
    # --------------------------------------------------------
    # Duplicados sesgan métricas (mismo registro contado 2 veces).
    duplicados = df.duplicated().sum()
    df = df.drop_duplicates()
    resumen['duplicados_eliminados'] = int(duplicados)

    # --------------------------------------------------------
    # 3. IMPUTAR VALORES NULOS
    # --------------------------------------------------------
    # Imputar = rellenar con un valor razonable.
    #   Numéricas: mediana (resistente a outliers).
    #   Categóricas: moda (valor más frecuente).
    nulos_antes = df.isnull().sum().sum()

    # Columnas numéricas
    for col in df.select_dtypes(include=[np.number]).columns:
        if df[col].isnull().any():
            df[col] = df[col].fillna(df[col].median())

    # Columnas de texto
    for col in df.select_dtypes(include=['object']).columns:
        if df[col].isnull().any():
            moda = df[col].mode()
            if not moda.empty:
                df[col] = df[col].fillna(moda[0])
            else:
                df[col] = df[col].fillna('desconocido')

    nulos_despues = df.isnull().sum().sum()
    resumen['nulos_antes'] = int(nulos_antes)
    resumen['nulos_despues'] = int(nulos_despues)

    # --------------------------------------------------------
    # 4. CORREGIR TIPOS DE DATOS
    # --------------------------------------------------------
    # pandas a veces lee "1234" como texto.
    # Intentamos convertir columnas de texto a número.
    # Si falla (es texto real), se queda como está.
    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                pass

    # --------------------------------------------------------
    # 5. DETECTAR Y ACOTAR OUTLIERS
    # --------------------------------------------------------
    # Outlier = valor muy alejado del resto.
    # Detección con IQR:
    #   Q1=percentil 25, Q3=percentil 75, IQR=Q3-Q1
    #   Límites: [Q1 - 1.5*IQR, Q3 + 1.5*IQR]
    # Acotamos (capping): reemplazamos outliers por el límite
    # en lugar de borrar la fila completa.
    outliers_tratados = 0
    for col in df.select_dtypes(include=[np.number]).columns:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR

        outliers = ((df[col] < lower) | (df[col] > upper)).sum()

        if outliers > 0:
            df[col] = np.where(df[col] < lower, lower, df[col])
            df[col] = np.where(df[col] > upper, upper, df[col])
            outliers_tratados += outliers

    resumen['outliers_tratados'] = int(outliers_tratados)

    # --------------------------------------------------------
    # RESUMEN FINAL
    # --------------------------------------------------------
    filas_despues = len(df)
    resumen['filas_despues'] = filas_despues
    resumen['filas_eliminadas'] = filas_antes - filas_despues

    return df, resumen