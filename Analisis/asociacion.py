# ============================================================
# MÓDULO DE REGLAS DE ASOCIACIÓN (Usando FP-Growth)
# ============================================================

import pandas as pd
# Cambiamos Apriori por FP-Growth, que es mucho más rápido y estable
from mlxtend.frequent_patterns import fpgrowth, association_rules
from mlxtend.preprocessing import TransactionEncoder

def generar_reglas(df, min_support=0.05, min_confidence=0.5):
    """
    Toma el DataFrame limpio, convierte los números en categorías
    (Alto/Bajo) y aplica el algoritmo FP-Growth para encontrar reglas.
    """
    
    df_cat = df.copy()

    for col in df_cat.columns:
        if df_cat[col].dtype in ['int64', 'float64']:
            if df_cat[col].nunique() > 10:
                mediana = df_cat[col].median()
                df_cat[col] = df_cat[col].apply(lambda x: f"{col}_Alto" if x > mediana else f"{col}_Bajo")
            else:
                df_cat[col] = df_cat[col].astype(str).apply(lambda x: f"{col}_{x}")

    df_cat = df_cat.astype(str)

    # Convertimos a dummies (0 y 1)
    df_dummies = pd.get_dummies(df_cat)
    
    # OBLIGATORIO PARA MLXTEND: Asegurarnos de que los datos sean booleanos (True/False)
    # Si no hacemos esto, a veces lanza errores silenciosos o consume mucha memoria.
    df_dummies = df_dummies.astype(bool)

    # Ejecutamos FP-Growth (es casi idéntico a Apriori, pero por debajo usa árboles)
    frequent_itemsets = fpgrowth(df_dummies, min_support=min_support, use_colnames=True)

    if frequent_itemsets.empty:
        return []

    reglas = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence)

    reglas_formateadas = []
    for _, row in reglas.iterrows():
        antecedentes = ", ".join(list(row['antecedents']))
        consecuentes = ", ".join(list(row['consequents']))
        
        reglas_formateadas.append({
            'antecedentes': antecedentes,
            'consecuentes': consecuentes,
            'soporte': round(row['support'] * 100, 2),
            'confianza': round(row['confidence'] * 100, 2),
            'lift': round(row['lift'], 2)
        })

    reglas_formateadas = sorted(reglas_formateadas, key=lambda x: x['lift'], reverse=True)
    return reglas_formateadas