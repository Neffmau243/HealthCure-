"""Cinco repeticiones por perfiles; no elige una semilla ganadora ni toca runtime."""
import sys
from pathlib import Path
import json
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ml.dataset import preparar_dataframe
from app.ml.experiment import (ROOT, guardar_json, sha256, grupos_perfil, particionar,
                               auditar_particiones, entrenar_candidatos, metricas, subgrupos)
from app.ml.policy import seleccionar_bandas

SEEDS = [20261016, 20261017, 20261018, 20261019, 20261020]
OUT = ROOT/"docs/experimentos/estabilidad_v3"


def recall_cluster_ci(y, score, cut, groups, seed, repeats=200):
    y, score = np.asarray(y), np.asarray(score)
    _, inverse = np.unique(groups, return_inverse=True)
    n = int(inverse.max())+1
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(repeats):
        weights = np.bincount(rng.integers(n, size=n), minlength=n)[inverse]
        denom = weights[y == 1].sum()
        if denom:
            values.append(float(weights[(y == 1) & (score >= cut)].sum()/denom))
    return np.quantile(values, [.025, .975]).tolist() if values else [None, None]


def ejecutar():
    OUT.mkdir(parents=True, exist_ok=False)
    csv = ROOT/"heart_disease_health_indicators_BRFSS2015.csv"
    protocol = {"semillas": SEEDS, "unidad": "perfil nueve features sin target ni sexo",
                "seleccion_semilla": "Ninguna; todas se reportan; candidato original ya congelado",
                "bandas": "En validation de cada repetición: recall>=0.90 / máximo F1",
                "dataset_sha256": sha256(csv), "script_sha256": sha256(__file__),
                "intervalos": "Recall por bootstrap de perfiles, 200 réplicas, modelo/umbral fijos"}
    guardar_json(OUT/"protocolo.json", protocol)
    X, y, sex = preparar_dataframe(pd.read_csv(csv))
    groups = grupos_perfil(X)
    results, rows = [], []
    for seed in SEEDS:
        print(f"[ESTABILIDAD] {seed}", flush=True)
        parts = particionar(y, groups, seed=seed)
        audit = auditar_particiones(parts, y, groups)
        models, decisions = entrenar_candidatos(X, y, parts, seed=seed)
        # Siempre sigmoid, fijado para la release antes de estas repeticiones.
        model = models["xgb_sigmoid"]
        val = parts["validation"]
        policy = seleccionar_bandas(y.iloc[val], model.predict_proba(X.iloc[val])[:, 1])
        guardar_json(OUT/f"decisiones_{seed}.json", {"politica": policy, "decisiones": decisions})
        test = parts["test"]
        yt = y.iloc[test].to_numpy()
        scores = np.round(model.predict_proba(X.iloc[test])[:, 1], 6)
        case = {"seed": seed, **audit, "politica": policy, "metricas": {}}
        for band, cut in policy["umbrales"].items():
            m = metricas(yt, scores, cut)
            case["metricas"][band] = m
            subs = subgrupos(yt, scores, cut, sex.iloc[test], X.iloc[test].edad)
            for row in subs:
                row.update(seed=seed, corte=band)
                # Intervalos por perfiles para los cinco subgrupos principales.
                masks = {"sexo_0_mujer": sex.iloc[test].to_numpy() == 0,
                         "sexo_1_hombre": sex.iloc[test].to_numpy() == 1,
                         "edad_18_44": X.iloc[test].edad.to_numpy() <= 5,
                         "edad_45_64": X.iloc[test].edad.between(6, 9).to_numpy(),
                         "edad_65_mas": X.iloc[test].edad.to_numpy() >= 10}
                if row["grupo"] in masks:
                    mask = masks[row["grupo"]]
                    row["recall_ic95_perfiles"] = recall_cluster_ci(yt[mask], scores[mask], cut, groups[test][mask], seed)
                rows.append(row)
            # Descomposición descriptiva por edad para investigar la diferencia de sexo.
            by_age = {}
            sex_test = sex.iloc[test].to_numpy()
            for age_name, mask in {"18_44": X.iloc[test].edad.to_numpy() <= 5,
                                   "45_64": X.iloc[test].edad.between(6, 9).to_numpy(),
                                   "65_mas": X.iloc[test].edad.to_numpy() >= 10}.items():
                by_age[age_name] = {"positivos_total": int(yt[mask].sum()), "sexos": {}}
                for s in (0, 1):
                    by_age[age_name]["sexos"][str(s)] = metricas(yt[mask & (sex_test == s)],
                                                                scores[mask & (sex_test == s)], cut)
            weights = {a: b["positivos_total"]/int(yt.sum()) for a, b in by_age.items()}
            standardized = {str(s): sum(weights[a]*b["sexos"][str(s)]["recall"] for a,b in by_age.items())
                            for s in (0, 1)}
            case.setdefault("recall_sexo_estandarizado_edad", {})[band] = {
                "pesos": weights, "recall": standardized,
                "nota": "Misma composición de edad entre positivos; asociación descriptiva, no causal"}
        results.append(case)
        guardar_json(OUT/"resultados.json", {"protocolo": protocol, "repeticiones": results})
    pd.DataFrame(rows).to_csv(OUT/"subgrupos.csv", index=False)
    print("[ESTABILIDAD] Completa", flush=True)


if __name__ == "__main__":
    ejecutar()
