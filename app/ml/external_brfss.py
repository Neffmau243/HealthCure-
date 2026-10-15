"""Adaptación explícita de BRFSS 2017 según layout/codebook del CDC."""
import numpy as np
import pandas as pd
from app.ml.preprocessor import FEATURE_COLUMNS

# Columnas 1-based publicadas por CDC; ninguna respuesta desconocida se imputa.
LAYOUT = {"GENHLTH": (90, 1), "BPHIGH4": (101, 1), "TOLDHI2": (104, 1),
          "CVDSTRK3": (108, 1), "DIABETE3": (117, 1), "SEX": (125, 1),
          "DIFFWALK": (195, 1), "SMOKE100": (198, 1), "EXERANY2": (233, 1),
          "_MICHD": (1953, 1), "_AGEG5YR": (2028, 2)}
VALID = {k: {1, 2} for k in LAYOUT}
VALID.update(GENHLTH=set(range(1, 6)), BPHIGH4={1, 2, 3, 4},
             DIABETE3={1, 2, 3, 4}, _AGEG5YR=set(range(1, 14)))


def adaptar(raw):
    flags = {col: raw[col].isin(VALID[col]) for col in LAYOUT}
    keep = np.logical_and.reduce([s.to_numpy() for s in flags.values()])
    clean = raw.loc[keep]
    X = pd.DataFrame({
        "edad": clean._AGEG5YR.astype(int), "presion_alta": (clean.BPHIGH4 == 1).astype(int),
        "colesterol_alto": (clean.TOLDHI2 == 1).astype(int),
        "tabaquismo": (clean.SMOKE100 == 1).astype(int),
        "actividad_fisica": (clean.EXERANY2 == 1).astype(int),
        "antecedente_acv": (clean.CVDSTRK3 == 1).astype(int),
        "diabetes": clean.DIABETE3.isin([1, 4]).astype(int),
        "salud_general": clean.GENHLTH.astype(int),
        "dificultad_para_caminar": (clean.DIFFWALK == 1).astype(int),
    })[FEATURE_COLUMNS]
    return X, (clean._MICHD == 1).astype(int), (clean.SEX == 1).astype(int), {
        "filas_origen": len(raw), "incluidas": len(clean), "excluidas": int((~keep).sum()),
        "invalidas_por_variable_no_excluyentes": {col: int((~mask).sum()) for col, mask in flags.items()},
    }
