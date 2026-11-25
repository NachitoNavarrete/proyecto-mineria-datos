# ============================================================
# MÓDULO DE DASHBOARD (Gráficos Interactivos)
# ============================================================
# ¿Qué hace este archivo?
#   Toma el DataFrame limpio y genera gráficos interactivos
#   usando Plotly, que luego se inyectan en el HTML.
# ============================================================

import pandas as pd
import plotly.express as px
import plotly.io as pio

def generar_graficos(df):
    """
    Genera los gráficos en formato HTML para inyectarlos en la web.
    """
    graficos = {}

    # 1. Busco las columnas numéricas y categóricas para saber qué graficar
    cols_numericas = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
    cols_categoricas = df.select_dtypes(include=['object']).columns.tolist()

    # 2. GRÁFICO 1: Distribución (Histograma) de la primera columna numérica
    if cols_numericas:
        col_num = cols_numericas[0]
        fig1 = px.histogram(df, x=col_num, title=f"Distribución de {col_num}", 
                            color_discrete_sequence=['#0d6efd'], marginal="box")
        # Lo convierto a HTML para inyectarlo en Jinja2 sin guardar archivos en disco
        graficos['histograma'] = pio.to_html(fig1, full_html=False)

    # 3. GRÁFICO 2: Correlación (Mapa de calor) si hay más de 2 numéricas
    if len(cols_numericas) >= 2:
        matriz_corr = df[cols_numericas].corr()
        fig2 = px.imshow(matriz_corr, text_auto=True, aspect="auto", 
                         title="Matriz de Correlación (Pearson)",
                         color_continuous_scale='RdBu_r')
        graficos['correlacion'] = pio.to_html(fig2, full_html=False)

    # 4. GRÁFICO 3: Conteo de la primera columna categórica (Gráfico de barras)
    if cols_categoricas:
        col_cat = cols_categoricas[0]
        conteo = df[col_cat].value_counts().reset_index()
        conteo.columns = [col_cat, 'Cantidad']
        fig3 = px.bar(conteo, x=col_cat, y='Cantidad', title=f"Frecuencia de {col_cat}",
                      color='Cantidad', color_continuous_scale='Viridis')
        graficos['barras'] = pio.to_html(fig3, full_html=False)

    return graficos