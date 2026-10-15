"""Ejecuta la segunda etapa offline sin reemplazar el modelo de la aplicación.

Uso: python entrenar_modelo.py [CSV] [--output experimentos_ml/NOMBRE]
     [--report-dir docs/experimentos/NOMBRE] [--bootstrap 200]

Los helpers/constantes LEGACY se conservan solo para que generar_figuras.py
reproduzca el artefacto activo v2 (split 80/20, seed 42). El experimento nuevo
usa su propio protocolo 60/15/10/15; nunca sobrescribe app/resources.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score

from app.ml.dataset import COLUMNAS, cargar_dataset  # noqa: F401
from app.ml.preprocessor import FEATURE_COLUMNS  # noqa: F401

# Exclusivas de las figuras y métricas históricas del modelo activo v2.
OUTPUT_PATH = "app/resources/modelos/2.0.0/modelo_cardiaco.joblib"
METADATA_PATH = "app/resources/modelos/2.0.0/modelo_cardiaco_metadata.json"
RANDOM_STATE = 42
TEST_SIZE = .20
CLASSIFICATION_THRESHOLDS = {"bajo_max": .30, "moderado_max": .60}


def evaluar_modelo(model, X, y, umbral):
    from app.ml.experiment import metricas
    scores = model.predict_proba(X)[:, 1]
    m = metricas(y, scores, umbral)
    return {
        "umbral": round(float(umbral), 4),
        "accuracy": round(float(accuracy_score(y, scores >= umbral)), 4),
        **{k: round(m[k], 4) for k in ("precision", "recall", "f1", "roc_auc")},
        "pr_auc": round(m["average_precision"], 4),
        "matriz_confusion": m["matriz_confusion"],
    }


def distribucion_triaje(proba, umbrales):
    scores = np.asarray(proba)
    cuts = (scores < umbrales["bajo_max"],
            (scores >= umbrales["bajo_max"]) & (scores < umbrales["moderado_max"]),
            scores >= umbrales["moderado_max"])
    return {name: {"n": int(mask.sum()), "pct": round(float(mask.mean()), 4)}
            for name, mask in zip(("bajo", "moderado", "alto"), cuts)}


def main():
    from app.ml.experiment import ejecutar, ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="?", default=str(ROOT/"heart_disease_health_indicators_BRFSS2015.csv"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    parser.add_argument("--output", default=str(ROOT/"experimentos_ml"/stamp))
    parser.add_argument("--report-dir", help="Nueva carpeta para publicar evidencia resumida, sin modelos ni filas")
    parser.add_argument("--bootstrap", type=int, default=200)
    args = parser.parse_args()
    if not Path(args.csv).is_file():
        parser.error("No existe el CSV BRFSS 2015; descárgalo de la fuente documentada")
    ejecutar(args.csv, args.output, args.report_dir, args.bootstrap)


if __name__ == "__main__":
    main()
