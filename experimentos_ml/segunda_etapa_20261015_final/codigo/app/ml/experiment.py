"""Experimento offline: cuatro particiones, calibración y auditoría reproducible.

Nunca escribe en app/resources ni modifica la base de datos. Los parámetros se
fijan antes de mirar el nuevo test, pero proceden de trabajo previo con este CSV:
esta reevaluación interna no equivale a una cohorte externa nunca observada.
"""
import hashlib
import json
import platform
import shutil
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score, brier_score_loss, confusion_matrix, f1_score,
    log_loss, precision_recall_curve, roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from app.ml.dataset import preparar_dataframe
from app.ml.preprocessor import FEATURE_COLUMNS

ROOT = Path(__file__).resolve().parents[2]
ROLES = ("train", "calibration", "validation", "test")
SEED = 20261015
PARAMS = dict(n_estimators=400, max_depth=3, learning_rate=0.05,
              subsample=0.8, colsample_bytree=0.8)
SCENARIOS = ("filas", "perfiles", "sin_duplicados_completos")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def guardar_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2,
                                    allow_nan=False) + "\n", encoding="utf-8")


def grupos_perfil(X):
    # Sin target ni sexo: todo input idéntico del modelo permanece junto.
    # Factorize evita colisiones de un hash de perfiles.
    return pd.factorize(pd.MultiIndex.from_frame(X[FEATURE_COLUMNS]), sort=True)[0]


def particionar(y, groups, modo="perfiles", seed=SEED):
    """60/15/10/15; por grupos las proporciones son aproximadas por filas."""
    y, groups = np.asarray(y), np.asarray(groups)
    if modo == "filas":
        indices = np.arange(len(y))
        resto, test = train_test_split(indices, test_size=.15, stratify=y, random_state=seed)
        resto, val = train_test_split(resto, test_size=10/85, stratify=y[resto], random_state=seed+1)
        train, cal = train_test_split(resto, test_size=.20, stratify=y[resto], random_state=seed+2)
        return dict(zip(ROLES, (train, cal, val, test)))
    if modo != "perfiles":
        raise ValueError("Modo de partición desconocido")
    # Asignación por ID de perfil aleatoria y sin consultar etiquetas.
    unique = np.unique(groups)
    shuffled = np.random.default_rng(seed).permutation(unique)
    n = len(unique)
    conjuntos = np.split(shuffled, [int(.60*n), int(.75*n), int(.85*n)])
    return {role: np.flatnonzero(np.isin(groups, ids)) for role, ids in zip(ROLES, conjuntos)}


def auditar_particiones(parts, y, groups, exigir_grupos=True):
    unidos = np.concatenate(list(parts.values()))
    if len(unidos) != len(y) or not np.array_equal(np.sort(unidos), np.arange(len(y))):
        raise ValueError("Las particiones omiten o repiten filas")
    estadisticas = {}
    for role, idx in parts.items():
        if len(np.unique(np.asarray(y)[idx])) != 2:
            raise ValueError(f"{role} debe contener ambas clases")
        estadisticas[role] = {
            "n": len(idx), "positivos": int(np.asarray(y)[idx].sum()),
            "prevalencia": float(np.asarray(y)[idx].mean()),
            "perfiles": len(np.unique(np.asarray(groups)[idx])),
        }
    overlaps = {}
    for a, b in combinations(ROLES, 2):
        comunes = np.intersect1d(np.asarray(groups)[parts[a]], np.asarray(groups)[parts[b]])
        overlaps[f"{a}__{b}"] = len(comunes)
        if exigir_grupos and len(comunes):
            raise ValueError(f"Perfiles compartidos: {a}/{b}")
    return {"particiones": estadisticas, "perfiles_compartidos": overlaps}


def elegir_umbral(y_validation, scores_validation):
    """Maximiza F1 solo en validación; empate: mayor umbral (menos alertas)."""
    y, scores = np.asarray(y_validation), np.asarray(scores_validation)
    if len(np.unique(y)) != 2 or not np.isfinite(scores).all():
        raise ValueError("Validación requiere ambas clases y scores finitos")
    precision, recall, cuts = precision_recall_curve(y, scores)
    denom = precision[:-1] + recall[:-1]
    f1 = np.divide(2*precision[:-1]*recall[:-1], denom,
                   out=np.zeros_like(denom), where=denom > 0)
    best = np.flatnonzero(f1 == f1.max())[-1]
    return {"umbral": float(cuts[best]), "f1_validation": float(f1[best]),
            "seleccionado_en": "validation", "criterio": "max F1; empate mayor umbral"}


def tabla_calibracion(y, scores, bins=10):
    y, scores = np.asarray(y), np.asarray(scores)
    ids = np.minimum((scores*bins).astype(int), bins-1)
    result = []
    for i in range(bins):
        mask = ids == i
        if mask.any():
            result.append({"bin": i, "n": int(mask.sum()),
                           "score_medio": float(scores[mask].mean()),
                           "fraccion_positiva": float(y[mask].mean())})
    return result


def bandas_referencia(y, scores):
    """Solo sensibilidad descriptiva; estos cortes no se adoptan para el candidato."""
    y, scores = np.asarray(y), np.asarray(scores)
    masks = (scores < .3, (scores >= .3) & (scores < .6), scores >= .6)
    return {name: {"n": int(mask.sum()), "fraccion": float(mask.mean()),
                   "positivos": int(y[mask].sum())}
            for name, mask in zip(("bajo", "moderado", "alto"), masks)}


def metricas(y, scores, threshold):
    y, scores = np.asarray(y), np.asarray(scores)
    pred = scores >= threshold
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    both = len(np.unique(y)) == 2
    bins = tabla_calibracion(y, scores)
    return {
        "n": len(y), "positivos": int(y.sum()), "prevalencia": float(y.mean()),
        "umbral": float(threshold),
        "roc_auc": float(roc_auc_score(y, scores)) if both else None,
        "average_precision": float(average_precision_score(y, scores)) if both else None,
        "precision": float(tp/(tp+fp)) if tp+fp else 0.,
        "recall": float(tp/(tp+fn)) if tp+fn else None,
        "specificity": float(tn/(tn+fp)) if tn+fp else None,
        "f1": float(f1_score(y, pred, zero_division=0)),
        "alert_rate": float(pred.mean()),
        "brier": float(brier_score_loss(y, scores)),
        "log_loss": float(log_loss(y, scores, labels=[0, 1])),
        "ece_10_uniform": sum(b["n"]*abs(b["score_medio"]-b["fraccion_positiva"])
                              for b in bins)/len(y),
        "matriz_confusion": [[int(tn), int(fp)], [int(fn), int(tp)]],
        "aviso": "Una sola clase; AUC/AP no definidos" if not both else None,
    }


def intervalo_wilson(success, total):
    if total == 0:
        return [None, None]
    p, z = success/total, 1.959963984540054
    center = (p+z*z/(2*total))/(1+z*z/total)
    half = z*np.sqrt(p*(1-p)/total + z*z/(4*total*total))/(1+z*z/total)
    return [float(center-half), float(center+half)]


def subgrupos(y, scores, threshold, sex, age):
    sex, age = np.asarray(sex), np.asarray(age)
    masks = {"sexo_0_mujer": sex == 0, "sexo_1_hombre": sex == 1,
             "edad_18_44": age <= 5, "edad_45_64": (age >= 6) & (age <= 9),
             "edad_65_mas": age >= 10}
    # Intersecciones predefinidas; sexo se usa solo para auditoría, no predictor.
    for s in ("sexo_0_mujer", "sexo_1_hombre"):
        for a in ("edad_18_44", "edad_45_64", "edad_65_mas"):
            masks[f"{s}__{a}"] = masks[s] & masks[a]
    result = []
    for name, mask in masks.items():
        if not mask.any():
            result.append({"grupo": name, "n": 0, "aviso": "Sin casos"})
            continue
        m = metricas(np.asarray(y)[mask], np.asarray(scores)[mask], threshold)
        tn, fp = m["matriz_confusion"][0]
        fn, tp = m["matriz_confusion"][1]
        m.update(grupo=name, recall_ic95_wilson=intervalo_wilson(tp, tp+fn),
                 fpr_ic95_wilson=intervalo_wilson(fp, fp+tn),
                 positivos_insuficientes=m["positivos"] < 30)
        result.append(m)
    return result


def bootstrap_perfiles(y, scores, threshold, groups, repeats=200, seed=SEED):
    """IC percentil 95%, remuestreo de perfiles completos; modelo/umbral fijos."""
    y, scores = np.asarray(y), np.asarray(scores)
    unique, inverse = np.unique(groups, return_inverse=True)
    rng = np.random.default_rng(seed)
    values = {key: [] for key in ("roc_auc", "average_precision", "f1", "brier", "recall")}
    for _ in range(repeats):
        weights = np.bincount(rng.integers(0, len(unique), len(unique)), minlength=len(unique))[inverse]
        if weights[y == 1].sum() == 0 or weights[y == 0].sum() == 0:
            continue
        pred = scores >= threshold
        tp = weights[(y == 1) & pred].sum()
        fn = weights[(y == 1) & ~pred].sum()
        fp = weights[(y == 0) & pred].sum()
        values["roc_auc"].append(roc_auc_score(y, scores, sample_weight=weights))
        values["average_precision"].append(average_precision_score(y, scores, sample_weight=weights))
        values["f1"].append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.)
        values["brier"].append(np.average((y-scores)**2, weights=weights))
        values["recall"].append(tp/(tp+fn))
    return {"metodo": "percentil 95%, bootstrap por perfil; modelo y umbral fijos",
            "repeticiones": repeats, "replicas_validas": len(values["f1"]),
            "intervalos": {k: np.quantile(v, [.025, .975]).tolist() if v else [None, None]
                           for k, v in values.items()}}


def calibrar(model, X_cal, y_cal):
    calibrated = CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid")
    return calibrated.fit(X_cal, y_cal)


def entrenar_candidatos(X, y, parts, params=None):
    train, cal, val = (parts[r] for r in ROLES[:3])
    y_train = y.iloc[train]
    weight = float((y_train == 0).sum()/(y_train == 1).sum())
    model = XGBClassifier(**(params or PARAMS), scale_pos_weight=weight, random_state=SEED,
                          n_jobs=2, tree_method="hist", eval_metric="logloss")
    model.fit(X.iloc[train], y_train)
    calibrated = calibrar(model, X.iloc[cal], y.iloc[cal])
    logistic = make_pipeline(StandardScaler(), LogisticRegression(C=1., max_iter=1000))
    logistic.fit(X.iloc[train], y_train)
    models = {"xgb_raw": model, "xgb_sigmoid": calibrated, "logistic": logistic}
    scores_val = {name: m.predict_proba(X.iloc[val])[:, 1] for name, m in models.items()}
    decisions = {name: elegir_umbral(y.iloc[val], s) for name, s in scores_val.items()}
    briers = {name: float(brier_score_loss(y.iloc[val], scores_val[name]))
              for name in ("xgb_raw", "xgb_sigmoid")}
    selected = min(briers, key=briers.get)  # Regla fijada en protocolo antes del test.
    return models, {"umbrales": decisions, "brier_validation": briers,
                    "variante_xgb_seleccionada": selected,
                    "scale_pos_weight_train": weight,
                    "baseline_prevalencia_train": float(y_train.mean())}


def diagnostico_duplicados(df, X, y):
    group = grupos_perfil(X)
    targets = pd.DataFrame({"group": group, "y": y.to_numpy()}).groupby("group").y.nunique()
    return {
        "filas": len(df), "duplicados_completos_excedentes": int(df.duplicated().sum()),
        "filas_en_grupos_completos_repetidos": int(df.duplicated(keep=False).sum()),
        "perfiles_9_features_unicos": len(np.unique(group)),
        "perfiles_9_features_con_ambas_etiquetas": int((targets > 1).sum()),
        "nota": "Coincidencia de respuestas no identifica encuestados; no hay ID de persona.",
    }


def figura_calibracion(y, scores, destination):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for name, s in scores.items():
        observed, predicted = calibration_curve(y, s, n_bins=10, strategy="quantile")
        axes[0].plot(predicted, observed, "o-", label=name)
        axes[1].hist(s, bins=np.linspace(0, 1, 31), histtype="step", label=name)
    axes[0].plot([0, 1], [0, 1], "--", color="gray")
    axes[0].set(xlabel="Score medio por bin (cuantiles)", ylabel="Fracción positiva observada",
                title="Test agrupado: calibración interna")
    axes[1].set(xlabel="Score", ylabel="Casos", title="Cambio de escala tras calibrar")
    for ax in axes:
        ax.legend(fontsize=8)
        ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(destination, dpi=160)
    plt.close(fig)


def ejecutar(csv_path, output, report_dir=None, bootstrap=200):
    if bootstrap < 20:
        raise ValueError("Usa al menos 20 réplicas bootstrap (200 por defecto)")
    output = Path(output).resolve()
    # El experimento no puede tomar como destino el runtime ni el repositorio entero.
    safe = (ROOT / "experimentos_ml").resolve()
    if not output.is_relative_to(safe) or output == safe:
        raise ValueError("El destino debe ser una carpeta nueva dentro de experimentos_ml/")
    if report_dir and Path(report_dir).resolve().exists():
        raise FileExistsError("El directorio del informe ya existe; usa otro para conservar evidencia")
    output.mkdir(parents=True, exist_ok=False)
    live = [ROOT/"app/resources/modelo_cardiaco.joblib",
            ROOT/"app/resources/modelo_cardiaco_metadata.json"]
    live_hashes = {str(p.relative_to(ROOT)): sha256(p) for p in live}
    snapshot_files = ("app/ml/experiment.py", "app/ml/dataset.py",
                      "app/ml/preprocessor.py", "entrenar_modelo.py")
    for name in snapshot_files:
        destination = output/"codigo"/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/name, destination)
    reference = output/"referencia_activa"
    reference.mkdir()
    for path in live:
        shutil.copy2(path, reference/path.name)
    protocol = {
        "version": "3.0.0-experimental", "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "seed": SEED, "fracciones_objetivo": dict(zip(ROLES, [.60, .15, .10, .15])),
        "primario": "perfiles", "escenarios": list(SCENARIOS),
        "features": FEATURE_COLUMNS, "parametros_xgb_fijos": PARAMS,
        "origen_parametros": "Configuración v2 previamente explorada en este mismo CSV; sin nueva búsqueda",
        "calibracion": "sigmoid en calibration, con estimador congelado; sin reentrenar después",
        "eleccion_variante_xgb": "menor Brier en validation; empate xgb_raw",
        "eleccion_umbral": "máximo F1 en validation, empate mayor umbral; sin criterio clínico",
        "bandas_app": "Sin cambios; 0.30/0.60 no se trasladan al candidato calibrado",
        "bootstrap": bootstrap, "bootstrap_unidad": "perfil 9 features",
        "subgrupos": "sexo, edades 18-44/45-64/65+, e intersecciones; umbral global fijo",
        "dataset_sha256": sha256(csv_path), "runtime_sha256": live_hashes,
        "codigo_sha256": {name: sha256(ROOT/name) for name in snapshot_files},
        "librerias": {"python": platform.python_version(), "sklearn": sklearn.__version__,
                      "xgboost": xgboost.__version__, "pandas": pd.__version__,
                      "numpy": np.__version__, "joblib": joblib.__version__},
        "limite": "Reevaluación interna de datos ya estudiados, no test externo prospectivo.",
    }
    guardar_json(output/"protocolo.json", protocol)  # Antes de entrenar/evaluar.
    df = pd.read_csv(csv_path)
    X, y, sex = preparar_dataframe(df)
    results = {"protocolo": protocol, "duplicados": diagnostico_duplicados(df, X, y), "escenarios": {}}
    for scenario in SCENARIOS:
        print(f"[EXPERIMENTO] {scenario}: preparar particiones y entrenar", flush=True)
        source_rows = np.flatnonzero(~df.duplicated()) if scenario == SCENARIOS[2] else np.arange(len(df))
        Xi, yi = X.iloc[source_rows].reset_index(drop=True), y.iloc[source_rows].reset_index(drop=True)
        si = sex.iloc[source_rows].reset_index(drop=True)
        groups = grupos_perfil(Xi)
        parts = particionar(yi, groups, "filas" if scenario == "filas" else "perfiles")
        audit = auditar_particiones(parts, yi, groups, scenario != "filas")
        directory = output/scenario
        directory.mkdir()
        assignment = pd.DataFrame({"csv_row_zero_based": source_rows, "profile_id": groups, "role": ""})
        for role, idx in parts.items():
            assignment.loc[idx, "role"] = role
        assignment.to_csv(directory/"particiones.csv.gz", index=False)
        models, decisions = entrenar_candidatos(Xi, yi, parts)
        guardar_json(directory/"decisiones_antes_test.json", decisions)
        # Ningún dato del test se entrega a entrenamiento, calibración o selección.
        test = parts["test"]
        yt = yi.iloc[test].to_numpy()
        scores = {name: model.predict_proba(Xi.iloc[test])[:, 1] for name, model in models.items()}
        scores["prevalencia_train"] = np.full(len(test), decisions["baseline_prevalencia_train"])
        case = {**audit, "decisiones": decisions, "test": {}}
        subgroup_rows = []
        for name, s in scores.items():
            cutoff = decisions["umbrales"][name]["umbral"] if name in decisions["umbrales"] else .5
            entry = {"umbral_validation": metricas(yt, s, cutoff),
                     "umbral_0_5": metricas(yt, s, .5), "calibracion_bins": tabla_calibracion(yt, s),
                     "bandas_referencia_0_30_0_60": bandas_referencia(yt, s)}
            if scenario == "perfiles" and name in ("xgb_raw", "xgb_sigmoid", "logistic"):
                print(f"[EXPERIMENTO] IC y subgrupos: {name}", flush=True)
                entry["ic95"] = bootstrap_perfiles(yt, s, cutoff, groups[test], repeats=bootstrap)
                entry["subgrupos"] = subgrupos(yt, s, cutoff, si.iloc[test], Xi.iloc[test].edad)
                subgroup_rows.extend({"modelo": name, **row} for row in entry["subgrupos"])
            case["test"][name] = entry
            if name in models:
                path = directory/f"{name}.joblib"
                joblib.dump(models[name], path)
                entry["artefacto_sha256"] = sha256(path)
                # Verifica la deserialización con el contrato de nueve columnas.
                loaded = joblib.load(path)
                np.testing.assert_allclose(loaded.predict_proba(Xi.iloc[test[:20]])[:, 1], s[:20])
        if subgroup_rows:
            pd.DataFrame(subgroup_rows).to_csv(output/"subgrupos.csv", index=False)
            figura_calibracion(yt, {k: scores[k] for k in ("xgb_raw", "xgb_sigmoid", "logistic")},
                               output/"calibracion.png")
        pd.DataFrame({"csv_row_zero_based": source_rows[test], "target": yt, **scores}).to_csv(
            directory/"predicciones_test.csv.gz", index=False)
        results["escenarios"][scenario] = case
        guardar_json(output/"resultados.json", results)
    if any(sha256(p) != live_hashes[str(p.relative_to(ROOT))] for p in live):
        raise RuntimeError("Cambió un artefacto activo durante el experimento")
    results["runtime_intacto"] = True
    results["artefactos"] = {str(p.relative_to(output)): sha256(p) for p in output.rglob("*")
                            if p.is_file() and p.name != "resultados.json"}
    guardar_json(output/"resultados.json", results)
    if report_dir:
        report_dir = Path(report_dir)
        report_dir.mkdir(parents=True, exist_ok=False)
        for name in ("protocolo.json", "resultados.json", "subgrupos.csv", "calibracion.png"):
            shutil.copy2(output/name, report_dir/name)
    print(f"[EXPERIMENTO] Finalizado: {output}. Runtime intacto.", flush=True)
    return results
