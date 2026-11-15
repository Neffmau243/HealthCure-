"""
generar_figuras.py — FIGURAS DE EVALUACIÓN DEL MODELO (EVIDENCIA PARA LA SUSTENTACIÓN)

Genera las figuras que respaldan las métricas del modelo versionado:

  01_curva_roc.png            → capacidad de discriminación (ROC AUC)
  02_curva_precision_recall.png → rendimiento con clases desbalanceadas (PR AUC)
  03_matriz_confusion.png      → tipos de error (falsos negativos / positivos)
  04_curva_calibracion.png     → ¿la probabilidad significa lo que dice? (Brier)
  05_importancia_features.png  → qué variables pesan (gain de XGBoost)
  06_barrido_umbral.png        → precision/recall/F1 vs umbral + bandas clínicas
  07_distribucion_riesgo.png   → dónde caen los pacientes en las 3 bandas

NO reentrena el modelo (eso tarda varios minutos y ya está versionado):
carga el .joblib existente y reconstruye EXACTAMENTE el mismo 20% de test
que usó `entrenar_modelo.py`, importando de allí sus constantes
(RANDOM_STATE, TEST_SIZE, CLASSIFICATION_THRESHOLDS) y su cargador de datos.
Así no hay dos definiciones del split que puedan divergir.

Además VERIFICA la integridad: recalcula las métricas y las compara contra
la ficha técnica (`modelo_cardiaco_metadata.json`). Si no coinciden, el
script termina con código 1 — señal de que el .joblib y su ficha se
desincronizaron.

USO (desde la raíz del proyecto, con el venv activo):
    python scripts/generar_figuras.py
    python scripts/generar_figuras.py ruta/al/otro.csv

REQUISITOS: matplotlib (está en requirements-dev.txt).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np

import matplotlib

matplotlib.use("Agg")  # Backend sin ventana: solo escribe PNG (sirve en servidor/CI)
import matplotlib.pyplot as plt  # noqa: E402

from sklearn.calibration import calibration_curve  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split  # noqa: E402

# La raíz del proyecto debe estar en sys.path para importar entrenar_modelo
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import entrenar_modelo as em  # noqa: E402  (constantes únicas del experimento)

FIG_DIR = RAIZ / "docs" / "figuras"
DPI = 150

# Paleta alineada con el frontend (Tailwind emerald / amber / rose).
COLOR = {
    "bajo": "#059669",
    "moderado": "#f59e0b",
    "alto": "#e11d48",
    "acento": "#1d4ed8",
    "gris": "#64748b",
}


# ══════════════════════════════════════════════════════════════════════════
# UTILIDADES
# ══════════════════════════════════════════════════════════════════════════
def _guardar(fig, nombre: str) -> Path:
    """Guarda la figura en docs/figuras/ y reporta el tamaño del PNG."""
    destino = FIG_DIR / nombre
    fig.savefig(destino, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[FIG] {nombre:<32} {destino.stat().st_size / 1024:6.0f} KB")
    return destino


def _importancias(model, features: list[str]) -> np.ndarray:
    """
    Importancia por 'gain' (mejora media de la pérdida al usar la variable).
    Se usa la API del booster porque es explícita; si el booster no devuelve
    nombres, se cae a `feature_importances_`.
    """
    try:
        score = model.get_booster().get_score(importance_type="gain")
    except Exception:
        score = {}

    if score:
        valores = []
        for i, nombre in enumerate(features):
            # XGBoost nombra las variables f0, f1... salvo si entrenó con DataFrame
            valor = score.get(nombre, score.get(f"f{i}", 0.0))
            valores.append(float(valor))
        return np.array(valores)

    return np.asarray(model.feature_importances_, dtype=float)


# ══════════════════════════════════════════════════════════════════════════
# FIGURAS
# ══════════════════════════════════════════════════════════════════════════
def fig_roc(y_test, proba) -> Path:
    fpr, tpr, _ = roc_curve(y_test, proba)
    auc = float(roc_auc_score(y_test, proba))

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(fpr, tpr, color=COLOR["acento"], lw=2.2, label=f"Modelo (ROC AUC = {auc:.4f})")
    ax.plot([0, 1], [0, 1], "--", color=COLOR["gris"], lw=1.2, label="Azar (AUC = 0.50)")
    ax.fill_between(fpr, tpr, alpha=0.08, color=COLOR["acento"])
    ax.set_xlabel("Tasa de falsos positivos (1 - especificidad)")
    ax.set_ylabel("Tasa de verdaderos positivos (sensibilidad)")
    ax.set_title("Curva ROC — discriminación del modelo\nHeart Disease Health Indicators (CDC/BRFSS 2015)")
    ax.legend(loc="lower right", frameon=False)
    ax.grid(alpha=0.25)
    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(-0.01, 1.01)
    return _guardar(fig, "01_curva_roc.png")


def fig_precision_recall(y_test, proba) -> Path:
    precision, recall, _ = precision_recall_curve(y_test, proba)
    pr_auc = float(average_precision_score(y_test, proba))
    linea_base = float(np.mean(y_test))

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(recall, precision, color=COLOR["alto"], lw=2.2,
            label=f"Modelo (PR AUC = {pr_auc:.4f})")
    ax.axhline(linea_base, ls="--", color=COLOR["gris"], lw=1.2,
               label=f"Azar = prevalencia ({linea_base:.4f})")
    ax.fill_between(recall, precision, linea_base, where=(precision >= linea_base),
                    alpha=0.10, color=COLOR["alto"])
    ax.set_xlabel("Recall (sensibilidad)")
    ax.set_ylabel("Precision (valor predictivo positivo)")
    ax.set_title(
        "Curva Precision-Recall — clases desbalanceadas\n"
        f"Positivos en test: {linea_base * 100:.2f}% (clase minoritaria)"
    )
    ax.legend(loc="upper right", frameon=False)
    ax.grid(alpha=0.25)
    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(0, 1.05)
    return _guardar(fig, "02_curva_precision_recall.png")


def fig_matriz_confusion(y_test, proba, umbral: float = 0.50) -> Path:
    cm = confusion_matrix(y_test, (proba >= umbral).astype(int))
    tn, fp, fn, tp = cm.ravel()

    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    ax.imshow(cm, cmap="Blues", alpha=0.85)
    etiquetas = ["No enfermo", "Enfermo"]
    ax.set_xticks([0, 1], labels=etiquetas)
    ax.set_yticks([0, 1], labels=etiquetas)
    ax.set_xlabel("Predicción del modelo")
    ax.set_ylabel("Realidad (BRFSS)")
    ax.set_title(f"Matriz de confusión (umbral de decisión = {umbral:.2f})")

    total = cm.sum()
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{cm[i, j]:,}\n{cm[i, j] / total * 100:.1f}%",
                    ha="center", va="center", fontsize=12,
                    color="white" if cm[i, j] > cm.max() / 2 else "#0f172a")

    fig.text(0.5, -0.04,
             f"Falsos negativos (FN) = {fn:,} → pacientes enfermos no detectados\n"
             f"Falsos positivos (FP) = {fp:,} · Verdaderos positivos (TP) = {tp:,}",
             ha="center", fontsize=9, color="#334155")
    return _guardar(fig, "03_matriz_confusion.png")


def fig_calibracion(y_test, proba) -> Path:
    """
    Curva de calibración (reliability diagram).

    Un modelo calibrado cumple: de los pacientes a los que les asignó 0.40,
    aproximadamente el 40% está enfermo. Con PONDERACIÓN DE CLASES
    (scale_pos_weight) las probabilidades se inflan a propósito, así que se
    espera ver la curva POR ENCIMA de la diagonal. Consecuencia de producto:
    las probabilidades sirven para ORDENAR riesgo y aplicar bandas de triaje,
    pero NO deben leerse como probabilidad clínica absoluta de enfermedad.
    """
    n_bins = 10
    frac_pos, media_pred = calibration_curve(
        y_test, proba, n_bins=n_bins, strategy="quantile"
    )
    brier = float(brier_score_loss(y_test, proba))
    brier_base = float(brier_score_loss(y_test, np.full_like(proba, np.mean(y_test))))

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot([0, 1], [0, 1], "--", color=COLOR["gris"], lw=1.2,
            label="Calibración perfecta")
    ax.plot(media_pred, frac_pos, "o-", color=COLOR["moderado"], lw=2,
            ms=6, label=f"Modelo (Brier = {brier:.4f})")
    ax.axhline(np.mean(y_test), ls=":", color=COLOR["gris"], lw=1,
               label=f"Prevalencia real ({np.mean(y_test):.4f})")
    ax.set_xlabel("Probabilidad predicha (media por intervalo)")
    ax.set_ylabel("Fracción real de positivos")
    ax.set_title("Curva de calibración — ¿la probabilidad es interpretable?\n"
                 "Por encima de la diagonal = sobreestima el riesgo (intencional)")
    ax.legend(loc="upper left", frameon=False)
    ax.grid(alpha=0.25)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    fig.text(0.5, -0.02,
             f"Brier del modelo = {brier:.4f} · Brier de predecir siempre la prevalencia = {brier_base:.4f}",
             ha="center", fontsize=9, color="#334155")
    return _guardar(fig, "04_curva_calibracion.png")


def fig_importancia(model, features: list[str]) -> Path:
    importancias = _importancias(model, features)
    orden = np.argsort(importancias)[::-1]
    nombres = [features[i].replace("_", " ") for i in orden]
    valores = importancias[orden]
    total = valores.sum() or 1.0

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.barh(nombres[::-1], valores[::-1], color=COLOR["acento"], alpha=0.85)
    for i, v in enumerate(valores[::-1]):
        ax.text(v, i, f"  {v / total * 100:.1f}%", va="center", fontsize=9, color="#0f172a")
    ax.set_xlabel("Ganancia media (gain) — reducción de la pérdida al usar la variable")
    ax.set_title("Importancia de variables (XGBoost, importance_type='gain')")
    ax.grid(axis="x", alpha=0.25)
    ax.margins(x=0.15)
    return _guardar(fig, "05_importancia_features.png")


def fig_barrido_umbral(y_test, proba, umbral_optimo: float) -> Path:
    """Precision/Recall/F1 en función del umbral, con las bandas clínicas."""
    umbrales = np.arange(0.05, 0.96, 0.01)
    precision, recall, f1 = [], [], []
    for u in umbrales:
        pred = (proba >= u).astype(int)
        tp = int(((pred == 1) & (y_test == 1)).sum())
        fp = int(((pred == 1) & (y_test == 0)).sum())
        fn = int(((pred == 0) & (y_test == 1)).sum())
        precision.append(tp / (tp + fp) if (tp + fp) else 0.0)
        recall.append(tp / (tp + fn) if (tp + fn) else 0.0)
        f1.append(2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0)

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.plot(umbrales, precision, color=COLOR["acento"], lw=2, label="Precision")
    ax.plot(umbrales, recall, color=COLOR["alto"], lw=2, label="Recall (sensibilidad)")
    ax.plot(umbrales, f1, color=COLOR["moderado"], lw=2, label="F1")

    ax.axvline(umbral_optimo, color=COLOR["gris"], ls="--", lw=1.4,
               label=f"Umbral óptimo F1 = {umbral_optimo:.3f}")
    ax.axvline(em.CLASSIFICATION_THRESHOLDS["bajo_max"], color=COLOR["bajo"], ls=":", lw=1.4)
    ax.axvline(em.CLASSIFICATION_THRESHOLDS["moderado_max"], color=COLOR["alto"], ls=":", lw=1.4)
    ax.axvspan(0, em.CLASSIFICATION_THRESHOLDS["bajo_max"], color=COLOR["bajo"], alpha=0.07)
    ax.axvspan(em.CLASSIFICATION_THRESHOLDS["bajo_max"], em.CLASSIFICATION_THRESHOLDS["moderado_max"],
               color=COLOR["moderado"], alpha=0.07)
    ax.axvspan(em.CLASSIFICATION_THRESHOLDS["moderado_max"], 1.0, color=COLOR["alto"], alpha=0.07)

    ax.text(em.CLASSIFICATION_THRESHOLDS["bajo_max"] / 2, 0.04, "banda\nBAJO",
            ha="center", fontsize=8, color=COLOR["bajo"])
    ax.text((em.CLASSIFICATION_THRESHOLDS["bajo_max"] + em.CLASSIFICATION_THRESHOLDS["moderado_max"]) / 2,
            0.04, "banda MODERADO", ha="center", fontsize=8, color="#b45309")
    ax.text((em.CLASSIFICATION_THRESHOLDS["moderado_max"] + 1.0) / 2, 0.04, "banda\nALTO",
            ha="center", fontsize=8, color=COLOR["alto"])

    ax.set_xlabel("Umbral de decisión sobre la probabilidad del modelo")
    ax.set_ylabel("Valor de la métrica")
    ax.set_title("Compromiso precision/recall según el umbral\n"
                 "Las bandas 0.30 / 0.60 son reglas de negocio del triaje, no el umbral de screening")
    ax.legend(loc="center right", frameon=False, fontsize=9)
    ax.grid(alpha=0.25)
    ax.set_xlim(0.05, 0.95)
    ax.set_ylim(0, 1.05)
    return _guardar(fig, "06_barrido_umbral.png")


def fig_distribucion_riesgo(y_test, proba) -> Path:
    """Dónde caen los 50.736 pacientes de test respecto a las bandas de triaje."""
    distribucion = em.distribucion_triaje(proba, em.CLASSIFICATION_THRESHOLDS)

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.hist(proba, bins=60, color=COLOR["gris"], alpha=0.60)
    for limite, color, etiqueta in (
        (em.CLASSIFICATION_THRESHOLDS["bajo_max"], COLOR["bajo"], "0.30"),
        (em.CLASSIFICATION_THRESHOLDS["moderado_max"], COLOR["alto"], "0.60"),
    ):
        ax.axvline(limite, color=color, ls="--", lw=1.6)
        ax.text(limite, ax.get_ylim()[1] * 0.92, f" {etiqueta}", color=color, fontsize=9)

    bajo_pct = distribucion["bajo"]["pct"] * 100
    mod_pct = distribucion["moderado"]["pct"] * 100
    alto_pct = distribucion["alto"]["pct"] * 100
    ax.set_xlabel("Probabilidad de enfermedad asignada por el modelo")
    ax.set_ylabel("Número de pacientes (test)")
    ax.set_title(
        "Distribución de riesgo y reparto en las 3 bandas de triaje\n"
        f"BAJO {bajo_pct:.1f}% · MODERADO {mod_pct:.1f}% · ALTO {alto_pct:.1f}%  "
        "(guardrail: ninguna banda queda vacía)"
    )
    ax.grid(alpha=0.25)
    return _guardar(fig, "07_distribucion_riesgo.png")


# ══════════════════════════════════════════════════════════════════════════
# VERIFICACIÓN DE INTEGRIDAD
# ══════════════════════════════════════════════════════════════════════════
def verificar_contra_ficha(metricas: dict, ficha: dict) -> bool:
    """
    Compara las métricas recalculadas con las guardadas en la ficha técnica.
    Devuelve False si el .joblib y su ficha se desincronizaron.
    """
    esperado = ficha.get("metricas_test_umbral_0.50", {})
    campos = ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]
    print("\n[VERIF] Métricas recalculadas vs ficha técnica (umbral 0.50):")
    ok = True
    for campo in campos:
        e, r = esperado.get(campo), metricas.get(campo)
        coincide = e is not None and r is not None and abs(float(e) - float(r)) < 1e-9
        ok &= coincide
        print(f"  {'OK ' if coincide else 'DIF'} {campo:<10} ficha={e}  recalculado={r}")

    cm_esperada = esperado.get("matriz_confusion")
    coincide_cm = cm_esperada == metricas.get("matriz_confusion")
    ok &= coincide_cm
    print(f"  {'OK ' if coincide_cm else 'DIF'} matriz_confusion ficha={cm_esperada} "
          f"recalculado={metricas.get('matriz_confusion')}")
    return ok


# ══════════════════════════════════════════════════════════════════════════
# PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════
def main(csv_path: str) -> int:
    if not Path(csv_path).exists():
        print(f"[ERROR] No se encontró el CSV: {csv_path}")
        print("Descárgalo de Kaggle: "
              "https://www.kaggle.com/datasets/alexteboul/heart-disease-health-indicators-dataset")
        return 1

    # 1) Reconstruir el MISMO split del entrenamiento (mismas constantes)
    X, y, _ = em.cargar_dataset(csv_path)
    _, X_test, _, y_test = train_test_split(
        X, y, test_size=em.TEST_SIZE, random_state=em.RANDOM_STATE, stratify=y
    )

    # 2) Cargar el modelo versionado (NO se reentrena)
    model = joblib.load(RAIZ / em.OUTPUT_PATH)
    proba = model.predict_proba(X_test)[:, 1]
    print(f"[FIG] Modelo cargado: {em.OUTPUT_PATH} · test = {len(y_test):,} filas")

    # 3) Leer la ficha técnica (umbral óptimo y métricas esperadas)
    with open(RAIZ / em.METADATA_PATH, encoding="utf-8") as f:
        ficha = json.load(f)
    umbral_optimo = float(ficha.get("umbral_decision", {}).get("f1_optimo", 0.50))

    # 4) Figuras
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig_roc(y_test, proba)
    fig_precision_recall(y_test, proba)
    fig_matriz_confusion(y_test, proba, 0.50)
    fig_calibracion(y_test, proba)
    fig_importancia(model, list(em.FEATURE_COLUMNS))
    fig_barrido_umbral(y_test, proba, umbral_optimo)
    fig_distribucion_riesgo(y_test, proba)

    # 5) Verificación de integridad modelo ↔ ficha técnica
    metricas = em.evaluar_modelo(model, X_test, y_test, 0.50)
    ok = verificar_contra_ficha(metricas, ficha)

    print(f"\n[FIG] Figuras en: {FIG_DIR.relative_to(RAIZ)}")
    if ok:
        print("[FIG] OK: el modelo reproduce exactamente las métricas de su ficha técnica.")
        return 0
    print("[FIG] ERROR: las métricas NO coinciden con la ficha técnica. "
          "El .joblib y el metadata están desincronizados: reentrena el modelo.")
    return 1


if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else str(RAIZ / "heart_disease_health_indicators_BRFSS2015.csv")
    sys.exit(main(ruta))
