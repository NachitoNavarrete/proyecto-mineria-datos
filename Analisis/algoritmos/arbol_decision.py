# MÓDULO DE ÁRBOL DE DECISIÓN (05-11-2026)
# ¿Qué hace este archivo?
#   Toma un DataFrame (los datos limpios), entrena un modelo de 
#   árbol de decisión y devuelve las métricas y una imagen.

import base64
import io

import matplotlib

import numpy as np
import pandas as pd

# Le digo a matplotlib que use el backend 'Agg' (sin interfaz gráfica).
# Esto es OBLIGATORIO en Flask, si no, se cae el servidor al dibujar.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.preprocessing import LabelEncoder


def entrenar_arbol(df, variable_objetivo, variables_predictoras, profundidad, test_size):
    """
    Entrena el árbol y devuelve un diccionario con todo lo necesario.
    """

    # 1. Separar los datos en X (predictoras) e y (lo que queremos predecir)
    X = df[variables_predictoras].copy()
    y = df[variable_objetivo].copy()

    # 2. Scikit-learn no entiende texto, solo números.
    # get_dummies convierte columnas de texto (ej: Ciudad: "Santiago") en columnas de 0 y 1.
    X = pd.get_dummies(X, drop_first=True)

    # LabelEncoder convierte la respuesta (ej: "Rojo", "Azul") a números (0, 1).
    le = LabelEncoder()
    y = le.fit_transform(y)

        # 3. División de entrenamiento y prueba (Train/Test split)
    # Agrego stratify=y para asegurar que haya una proporción justa de clases en la prueba
        # [CAMBIO 25-11-2026] Quito stratify=y porque la clase '3' tiene solo 1 vino y lanza error [winecsv]
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=42,
    )

    # 4. Crear y entrenar el modelo
    # max_depth controla qué tan profundo es el árbol (evita que se memorice todo).
    modelo = DecisionTreeClassifier(max_depth=profundidad, criterion='gini', random_state=42)
    modelo.fit(X_train, y_train)

    # 5. Hacer predicciones con el examen (X_test)
    y_pred = modelo.predict(X_test)

    # 6. Calcular métricas de evaluación
    exactitud = accuracy_score(y_test, y_pred)
        # [CAMBIO 25-11-2026] Le paso 'labels' para que la matriz siempre tenga el tamaño correcto
    matriz = confusion_matrix(
        y_test,
        y_pred,
        labels=range(len(le.classes_)),
    ).tolist()  # tolist() para enviarlo al HTML

       # 7. GENERAR LA IMAGEN DEL ÁRBOL
    # Hago la imagen más grande (16x10) para que las ramas no se vean apretadas
    fig, ax = plt.subplots(figsize=(16, 10))
    
    plot_tree(modelo, 
              feature_names=X.columns, 
              class_names=[str(c) for c in le.classes_], 
              filled=True, 
              rounded=True, 
              fontsize=10,       # Tamaño de letra legible
              proportion=False,
              ax=ax)
    
    # Ajusto los márgenes para que el árbol ocupe todo el espacio
    plt.tight_layout()

    img_buffer = io.BytesIO()
    # Le doy un fondo blanco y mejor resolución (dpi=150)
    fig.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150, facecolor='white')
    img_buffer.seek(0)
    
    img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
    plt.close(fig) # Cierro la figura para liberar memoria

    # 8. Empaquetar todo y devolverlo a app.py
    return {
        'exactitud': round(exactitud * 100, 2), # Lo pasamos a porcentaje (ej: 85.5)
        'matriz_confusion': matriz,
        'imagen_base64': img_base64,
        'clases': list(le.classes_)
    }