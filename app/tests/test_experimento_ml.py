"""Guardas de independencia, calibración congelada y contrato experimental."""
import numpy as np
import pandas as pd
import pytest
from sklearn.tree import DecisionTreeClassifier

from app.ml.dataset import preparar_dataframe
from app.ml.experiment import (
    auditar_particiones, bootstrap_perfiles, calibrar, elegir_umbral,
    ejecutar, entrenar_candidatos, grupos_perfil, metricas, particionar, subgrupos, ROOT,
)
from app.ml.preprocessor import FEATURE_COLUMNS


def datos():
    rng = np.random.default_rng(16)
    X = pd.DataFrame(rng.integers(0, 2, size=(500, 9)), columns=FEATURE_COLUMNS)
    X["edad"] = rng.integers(1, 14, len(X))
    X["salud_general"] = rng.integers(1, 6, len(X))
    # Repite perfiles, con etiquetas potencialmente distintas.
    X = pd.concat([X, X.iloc[:100]], ignore_index=True)
    y = pd.Series(rng.binomial(1, .3, len(X)))
    return X, y


def test_perfiles_y_todas_las_filas_se_conservan_sin_fuga():
    X, y = datos()
    groups = grupos_perfil(X)
    assert groups[0] == groups[500]
    parts = particionar(y, groups)
    audit = auditar_particiones(parts, y, groups)
    assert sum(x["n"] for x in audit["particiones"].values()) == len(X)
    assert not any(audit["perfiles_compartidos"].values())
    repetido = particionar(y, groups)
    for key in parts:
        np.testing.assert_array_equal(parts[key], repetido[key])
    # Ninguna etiqueta interviene en la asignación por perfiles.
    alterado = particionar(1-y, groups)
    for key in parts:
        np.testing.assert_array_equal(parts[key], alterado[key])


def test_auditoria_rechaza_omision_y_solapamiento():
    X, y = datos()
    groups = grupos_perfil(X)
    parts = particionar(y, groups)
    parts["test"] = np.r_[parts["test"], parts["train"][:1]]
    with pytest.raises(ValueError, match="omiten o repiten"):
        auditar_particiones(parts, y, groups)


def test_umbral_en_validacion_se_evalua_fijo_en_test():
    choice = elegir_umbral([0, 0, 1, 1], [.1, .4, .6, .8])
    assert choice["umbral"] == .6
    assert choice["seleccionado_en"] == "validation"
    m = metricas([1, 1, 0, 0], [.1, .4, .6, .8], choice["umbral"])
    assert m["f1"] == 0  # El test no puede mover el umbral para mejorar F1.
    assert m["umbral"] == .6


def test_calibracion_no_reentrena_estimador_base_y_score_valido():
    X, y = datos()
    parts = particionar(y, grupos_perfil(X))
    model = DecisionTreeClassifier(max_depth=2, random_state=1)
    model.fit(X.iloc[parts["train"]], y.iloc[parts["train"]])
    before = model.predict_proba(X).copy()
    calibrated = calibrar(model, X.iloc[parts["calibration"]], y.iloc[parts["calibration"]])
    np.testing.assert_array_equal(before, model.predict_proba(X))
    scores = calibrated.predict_proba(X.iloc[parts["test"]])[:, 1]
    assert np.isfinite(scores).all() and ((scores >= 0) & (scores <= 1)).all()


def test_cambiar_etiquetas_test_no_cambia_modelos_umbrales_o_eleccion():
    X, y = datos()
    parts = particionar(y, grupos_perfil(X))
    small = dict(n_estimators=8, max_depth=2, learning_rate=.1)
    models, choices = entrenar_candidatos(X, y, parts, params=small)
    changed = y.copy()
    changed.iloc[parts["test"]] = 1 - changed.iloc[parts["test"]]
    other_models, other_choices = entrenar_candidatos(X, changed, parts, params=small)
    assert choices == other_choices
    for name in models:
        np.testing.assert_array_equal(models[name].predict_proba(X), other_models[name].predict_proba(X))


def test_subgrupos_usan_umbral_global_y_admiten_una_clase():
    result = subgrupos([0, 0, 1, 1], [.1, .8, .3, .7], .6,
                      [0, 0, 1, 1], [1, 1, 12, 12])
    women = next(r for r in result if r["grupo"] == "sexo_0_mujer")
    assert women["umbral"] == .6 and women["roc_auc"] is None
    assert women["recall_ic95_wilson"] == [None, None]
    assert women["matriz_confusion"] == [[1, 1], [0, 0]]


def test_bootstrap_reproducible_por_perfiles():
    y, scores, groups = [0, 0, 1, 1, 0, 1], [.1, .2, .4, .9, .6, .8], [0, 0, 1, 1, 2, 3]
    a = bootstrap_perfiles(y, scores, .5, groups, repeats=20)
    assert a == bootstrap_perfiles(y, scores, .5, groups, repeats=20)
    assert a["replicas_validas"] > 0
    assert all(0 <= lo <= hi <= 1 for lo, hi in a["intervalos"].values())


@pytest.mark.parametrize("column,value", [("Age", 55), ("Diabetes", 3), ("Sex", np.nan)])
def test_dataset_rechaza_codificaciones_incompatibles(column, value):
    row = dict(Age=8, HighBP=0, HighChol=0, Smoker=0, PhysActivity=1,
               Stroke=0, Diabetes=1, GenHlth=3, DiffWalk=0, HeartDiseaseorAttack=0, Sex=1)
    row[column] = value
    with pytest.raises(ValueError):
        preparar_dataframe(pd.DataFrame([row]))


def test_dataset_prediabetes_se_agrupa_sin_sexo_como_predictor():
    row = dict(Age=8, HighBP=0, HighChol=0, Smoker=0, PhysActivity=1,
               Stroke=0, Diabetes=1, GenHlth=3, DiffWalk=0, HeartDiseaseorAttack=0, Sex=1)
    X, _, sex = preparar_dataframe(pd.DataFrame([row]))
    assert X.columns.tolist() == FEATURE_COLUMNS and X.diabetes.iloc[0] == 1
    assert sex.iloc[0] == 1


def test_experimento_no_puede_escribir_modelo_activo():
    with pytest.raises(ValueError, match="experimentos_ml"):
        ejecutar("no_se_lee.csv", ROOT / "app" / "resources")
