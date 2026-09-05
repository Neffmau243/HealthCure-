"""
test_preprocessor.py — TESTS DEL PREPROCESSOR DEL MODELO ML

El preprocessor convierte el dict de variables en el DataFrame EXACTO
que el modelo espera. Errores aquí = predicciones incorrectas en silencio.
Por eso se prueban: orden de columnas, validación de faltantes y rangos.
"""
import pandas as pd
import pytest

from app.ml.preprocessor import preprocess, FEATURE_COLUMNS, mapear_edad_cdc

DATOS_VALIDOS = {
    "edad": 55,
    "presion_alta": 1,
    "colesterol_alto": 1,
    "tabaquismo": 0,
    "actividad_fisica": 1,
    "antecedente_acv": 0,
    "diabetes": 1,
    "salud_general": 3,
    "dificultad_para_caminar": 0,
}


def test_preprocess_retorna_dataframe_de_una_fila():
    df = preprocess(DATOS_VALIDOS)
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (1, 9)  # 1 evaluación × 9 variables


def test_preprocess_mantiene_el_orden_exacto_de_columnas():
    """El modelo fue entrenado con FEATURE_COLUMNS en ESTE orden."""
    df = preprocess(DATOS_VALIDOS)
    assert list(df.columns) == FEATURE_COLUMNS


def test_preprocess_descarta_campos_extra():
    """Campos administrativos (paciente_id, etc.) no deben llegar al modelo."""
    data = {**DATOS_VALIDOS, "paciente_id": 999, "comentario": "hola"}
    df = preprocess(data)
    assert list(df.columns) == FEATURE_COLUMNS
    assert df.shape[1] == 9


def test_preprocess_lanza_error_si_falta_una_variable():
    data = {k: v for k, v in DATOS_VALIDOS.items() if k != "diabetes"}
    with pytest.raises(ValueError, match="diabetes"):
        preprocess(data)


def test_preprocess_lanza_error_si_edad_fuera_de_rango():
    data = {**DATOS_VALIDOS, "edad": 200}
    with pytest.raises(ValueError, match="Edad fuera de rango"):
        preprocess(data)


# ============================================================
# mapear_edad_cdc (años reales -> codigo 1-13 del BRFSS)
# ============================================================

def test_mapear_edad_cdc_fronteras():
    """Límites exactos de cada rango CDC (ver entrenar_modelo.py)."""
    assert mapear_edad_cdc(24) == 1   # 18-24
    assert mapear_edad_cdc(25) == 2   # 25-29
    assert mapear_edad_cdc(29) == 2
    assert mapear_edad_cdc(30) == 3   # 30-34
    assert mapear_edad_cdc(54) == 7   # 50-54
    assert mapear_edad_cdc(55) == 8   # 55-59
    assert mapear_edad_cdc(79) == 12  # 75-79
    assert mapear_edad_cdc(80) == 13  # 80+
    assert mapear_edad_cdc(95) == 13


def test_preprocess_convierte_edad_a_codigo_cdc():
    """El DataFrame que ve el modelo lleva edad 1-13, no años reales."""
    df = preprocess({**DATOS_VALIDOS, "edad": 55})
    assert df.iloc[0]["edad"] == 8   # 55 años -> rango 8

    df2 = preprocess({**DATOS_VALIDOS, "edad": 30})
    assert df2.iloc[0]["edad"] == 3  # 30 años -> rango 3


def test_preprocess_lanza_error_si_salud_general_fuera_de_rango():
    data = {**DATOS_VALIDOS, "salud_general": 9}
    with pytest.raises(ValueError, match="Salud general fuera de rango"):
        preprocess(data)
