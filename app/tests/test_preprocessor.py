"""
test_preprocessor.py — TESTS DEL PREPROCESSOR DEL MODELO ML

El preprocessor convierte el dict de variables en el DataFrame EXACTO
que el modelo espera. Errores aquí = predicciones incorrectas en silencio.
Por eso se prueban: orden de columnas, validación de faltantes y rangos.
"""
import pandas as pd
import pytest

from app.ml.preprocessor import preprocess, FEATURE_COLUMNS

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


def test_preprocess_lanza_error_si_salud_general_fuera_de_rango():
    data = {**DATOS_VALIDOS, "salud_general": 9}
    with pytest.raises(ValueError, match="Salud general fuera de rango"):
        preprocess(data)
