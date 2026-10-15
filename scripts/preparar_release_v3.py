"""Congela el candidato y su política. --activar instala una release ya preparada."""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import joblib
import numpy as np
import pandas as pd
from app.ml.dataset import preparar_dataframe
from app.ml.experiment import ROOT, sha256, guardar_json, metricas, grupos_perfil, particionar
from app.ml.policy import seleccionar_bandas
from app.ml.preprocessor import FEATURE_COLUMNS

SOURCE = ROOT / "experimentos_ml/segunda_etapa_20261015_final"
RELEASE = ROOT / "app/resources/modelos/3.0.0"
ACTIVE = ROOT / "app/resources/modelo_cardiaco.joblib"


def preparar():
    RELEASE.mkdir(parents=True, exist_ok=False)
    results = json.loads((SOURCE/"resultados.json").read_text(encoding="utf-8"))
    model_source = SOURCE/"perfiles/xgb_sigmoid.joblib"
    assert sha256(model_source) == results["escenarios"]["perfiles"]["test"]["xgb_sigmoid"]["artefacto_sha256"]
    csv = ROOT/"heart_disease_health_indicators_BRFSS2015.csv"
    assert sha256(csv) == results["protocolo"]["dataset_sha256"]
    model = joblib.load(model_source)
    X, y, _ = preparar_dataframe(pd.read_csv(csv))
    parts = particionar(y, grupos_perfil(X))
    validation = parts["validation"]
    scores_val = np.round(model.predict_proba(X.iloc[validation])[:, 1], 6)
    policy = seleccionar_bandas(y.iloc[validation], scores_val)
    # Congela política antes de evaluar cualquier cohorte externa.
    guardar_json(RELEASE/"politica.json", policy)
    shutil.copy2(model_source, RELEASE/ACTIVE.name)
    val_metrics = {name: metricas(y.iloc[validation], scores_val, cut)
                   for name, cut in policy["umbrales"].items()}
    test = parts["test"]
    scores = np.round(model.predict_proba(X.iloc[test])[:, 1], 6)
    meta = {
        "model_version": "3.0.0", "algoritmo": "XGBoost+sigmoid",
        "entrenado_en": results["protocolo"]["fecha_utc"],
        "release_en": datetime.now(timezone.utc).isoformat(),
        "artifact_sha256": sha256(RELEASE/ACTIVE.name),
        "features": FEATURE_COLUMNS, "target": "Antecedente declarado de CHD o infarto; no futuro",
        "dataset": {**results["duplicados"], "n_rows": len(X), "n_features": 9,
                    "positive_rate": float(y.mean()), "sha256": sha256(csv),
                    "particiones": results["escenarios"]["perfiles"]["particiones"]},
        "hiperparametros": results["protocolo"]["parametros_xgb_fijos"],
        "validacion": "Train/calibration/validation/test por perfiles disjuntos 60/15/10/15",
        "calibracion": "sigmoid; estimador congelado; solo calibration",
        "politica_modelo": policy,
        "umbrales_clasificacion_clinica": policy["umbrales"],  # Clave histórica API.
        "metricas_validation_bandas": val_metrics,
        "metricas_test_umbral_0.50": metricas(y.iloc[test], scores, .5),
        "metricas_test_bandas": {name: metricas(y.iloc[test], scores, cut)
                                 for name, cut in policy["umbrales"].items()},
        "librerias": results["protocolo"]["librerias"],
        "limites": ["Calibración interna, sin validación clínica ni local",
                    "CSV e hiperparámetros previamente explorados; test interno",
                    "Recall varía por edad y sexo; no criterio de urgencia"],
    }
    guardar_json(RELEASE/"modelo_cardiaco_metadata.json", meta)
    print(json.dumps(policy, ensure_ascii=False, indent=2))


def activar():
    meta_path = RELEASE/"modelo_cardiaco_metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if sha256(RELEASE/ACTIVE.name) != meta["artifact_sha256"]:
        raise ValueError("Release corrupta")
    active_meta = ACTIVE.with_name("modelo_cardiaco_metadata.json")
    old = json.loads(active_meta.read_text(encoding="utf-8"))
    if old["model_version"] == meta["model_version"]:
        if sha256(ACTIVE) != meta["artifact_sha256"]:
            raise ValueError("Modelo activo no corresponde a la versión declarada")
        print("[RELEASE] Ya activa")
        return
    archive = ACTIVE.parent/"modelos"/old["model_version"]
    archive.mkdir(parents=True, exist_ok=False)
    shutil.copy2(ACTIVE, archive/ACTIVE.name)
    shutil.copy2(active_meta, archive/active_meta.name)
    for source, destination in ((RELEASE/ACTIVE.name, ACTIVE), (meta_path, active_meta)):
        temp = destination.with_suffix(destination.suffix+".tmp")
        shutil.copy2(source, temp)
        temp.replace(destination)
    print("[RELEASE] 3.0.0 activa; referencia anterior archivada. Reiniciar servidor y ambas cachés.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activar", action="store_true")
    args = parser.parse_args()
    activar() if args.activar else preparar()
