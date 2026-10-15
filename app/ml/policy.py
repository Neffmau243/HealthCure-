"""Política de bandas académicas: se selecciona en validación y se congela."""
import numpy as np
from sklearn.metrics import precision_recall_curve
from app.ml.experiment import elegir_umbral

RULES_VERSION = "bandas-academicas-3.0.0"


def seleccionar_bandas(y_validation, scores_validation):
    scores = np.round(np.asarray(scores_validation), 6)
    _, recall, cuts = precision_recall_curve(y_validation, scores)
    low = float(cuts[np.flatnonzero(recall[:-1] >= .90)[-1]])
    high = elegir_umbral(y_validation, scores)["umbral"]
    if not 0 < low < high < 1:
        raise ValueError("No se pueden construir tres bandas con los criterios fijados")
    return {
        "reglas_version": RULES_VERSION,
        "semantica_score": "calibracion_sigmoid_interna",
        "umbrales": {"bajo_max": low, "moderado_max": high},
        "seleccionado_en": "validation BRFSS 2015; nunca test ni datos externos",
        "criterios": {"bajo_max": "mayor umbral con recall validation >=0.90",
                      "moderado_max": "max F1 validation; empate mayor umbral"},
        "decimales_score": 6,
    }
