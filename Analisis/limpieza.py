# ============================================================
# MODULO DE LIMPIEZA AUTOMATICA
# ============================================================
# ¿Qué hace este archivo?
#   Carga un CSV y lo limpia automáticamente antes de
#   cualquier análisis.
#
# ¿Por qué está separado de app.py?
#   Porque la lógica de datos no debe mezclarse con la web.
#   Si cambiamos de Flask a Django, este archivo no se toca.
# ============================================================

import pandas as pd        # Manipulación de datos tabulares
import numpy as np         # Operaciones numéricas


def cargar_csv(filepath):
    """
    Carga un CSV detectando codificación y separador.

    ¿Por qué probar varias codificaciones?
        Un CSV puede venir en UTF-8, Latin-1, ISO-8859-1.
        Si no detectamos bien, los acentos salen como "MÃ©xico".

    ¿Por qué sep=None?
        Le dice a pandas que adivine el separador
        (coma, punto y coma, tabulación).

    Devuelve:
        DataFrame de pandas.
    """
    encodings = ['utf-8', 'latin-1', 'iso-8859-1']

    for enc in encodings:
        try:
            df = pd.read_csv(filepath, encoding=enc, sep=None, engine='python')
            return df
        except Exception:
            continue

    raise ValueError("No se pudo leer el CSV. Verifica codificación y separador.")


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