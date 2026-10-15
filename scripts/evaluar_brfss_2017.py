"""Evaluación temporal externa sin ajustar modelo, calibración ni bandas."""
import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import joblib
import numpy as np
import pandas as pd
from app.ml.experiment import ROOT, sha256, guardar_json, metricas, subgrupos, grupos_perfil
from app.ml.external_brfss import LAYOUT, adaptar

ARCHIVE = ("https://topofire.dbs.umt.edu/public_data/federal_public_datasets/"
           "CDC%20Behavioral%20Risk%20Factor%20Surveillance%20System%20/"
           "2017%20Annual%20Survey%20Data/Data%20Files/LLCP2017.ASC%20")
OFFICIAL = "https://www.cdc.gov/brfss/annual_data/annual_2017.html"
DATA = ROOT/"experimentos_ml/fuentes/brfss2017"
OUT = ROOT/"docs/experimentos/externa_brfss2017_v3"
RELEASE = ROOT/"app/resources/modelos/3.0.0"


def descargar():
    from concurrent.futures import ThreadPoolExecutor
    DATA.mkdir(parents=True, exist_ok=True)
    path = DATA/"variables_2017.csv.gz"
    temp = path.with_suffix(".part")
    if path.exists():
        raise FileExistsError("Ya hay datos; evaluar sin --descargar")
    rows = 0
    prefix = None
    if temp.exists() and temp.stat().st_size:
        with gzip.open(temp, "rt") as file:
            rows = sum(1 for _ in file)-1
        prefix = {"filas_validadas": rows, "csv_parcial_sha256": sha256(temp),
                  "nota": "Prefijo conservado de descarga interrumpida; no hash del ASCII original completo"}
    else:
        with gzip.open(temp, "wt", encoding="ascii", newline="") as file:
            file.write(",".join(LAYOUT)+"\n")
    total, width, batch = 450016, 2211, 10000
    segments = []
    def fetch(bounds):
        a, b = bounds
        start, end = a*width, b*width-1
        last_error = None
        for attempt in range(3):
            try:
                request = Request(ARCHIVE, headers={"Range": f"bytes={start}-{end}", "User-Agent": "Mozilla/5.0"})
                with urlopen(request, timeout=60) as response:
                    if response.status != 206 or response.headers.get("Content-Range") != f"bytes {start}-{end}/{total*width}":
                        raise ValueError("El archivo no respeta rangos o cambió su longitud")
                    data = response.read(end-start+1)
                if len(data) != end-start+1:
                    raise ValueError("Respuesta parcial; reintentar el segmento completo")
                lines = data.splitlines()
                if len(lines) != b-a or any(len(line) != 2209 for line in lines):
                    raise ValueError(f"Formato inconsistente en filas {a}:{b}")
                selected = [",".join(line[pos-1:pos-1+w].decode("ascii").strip()
                                     for pos,w in LAYOUT.values()) for line in lines]
                return "\n".join(selected)+"\n", {"inicio_fila": a, "fin_exclusivo": b,
                         "ascii_sha256": hashlib.sha256(data).hexdigest()}
            except Exception as error:
                last_error = error
        raise last_error
    ranges = [(a, min(a+batch, total)) for a in range(rows, total, batch)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        for csv_text, segment in executor.map(fetch, ranges):
            # Cada segmento se valida completo antes de agregarlo al CSV.
            with gzip.open(temp, "at", encoding="ascii", newline="") as file:
                file.write(csv_text)
            segments.append(segment)
            rows = segment["fin_exclusivo"]
            print(f"[EXTERNA] {rows}/{total} registros validados", flush=True)
    temp.replace(path)
    guardar_json(DATA/"fuente_2017.json", {
        "url_descarga": ARCHIVE, "url_documentacion_oficial": OFFICIAL,
        "consultado_utc": datetime.now(timezone.utc).isoformat(), "filas": rows,
        "prefijo_reanudado": prefix, "segmentos_ascii_sha256": segments,
        "csv_extraido_sha256": sha256(path),
        "procedencia": "Copia archivada pública de University of Montana; CDC directo devolvió HTTP403",
        "layout_1_based": LAYOUT,
    })


def evaluar():
    OUT.mkdir(parents=True, exist_ok=False)
    meta = json.loads((RELEASE/"modelo_cardiaco_metadata.json").read_text(encoding="utf-8"))
    path = RELEASE/"modelo_cardiaco.joblib"
    assert sha256(path) == meta["artifact_sha256"]
    source = json.loads((DATA/"fuente_2017.json").read_text(encoding="utf-8"))
    csv = DATA/"variables_2017.csv.gz"
    assert sha256(csv) == source["csv_extraido_sha256"]
    guardar_json(OUT/"protocolo.json", {"fuente": source, "release_sha256": sha256(path),
                 "metadata_sha256": sha256(RELEASE/"modelo_cardiaco_metadata.json"),
                 "script_sha256": sha256(__file__), "adaptador_sha256": sha256(ROOT/"app/ml/external_brfss.py"),
                 "politica_congelada": meta["politica_modelo"],
                 "ajuste_externo": "Ninguno; solo evaluación una vez descargada la cohorte",
                 "analisis": "Casos completos de las nueve features, sexo y etiqueta; sin pesos de encuesta"})
    X, y, sex, flow = adaptar(pd.read_csv(csv))
    model = joblib.load(path)
    scores = np.round(model.predict_proba(X)[:, 1], 6)
    result = {"flujo": flow, "fuente": source, "politica": meta["politica_modelo"],
              "metricas": {}, "subgrupos": {}}
    rows = []
    for name, cut in meta["politica_modelo"]["umbrales"].items():
        result["metricas"][name] = metricas(y, scores, cut)
        result["subgrupos"][name] = subgrupos(y, scores, cut, sex, X.edad)
        rows.extend({"corte": name, **row} for row in result["subgrupos"][name])
    result["metricas"]["referencia_0_5"] = metricas(y, scores, .5)
    from scripts.evaluar_estabilidad_v3 import recall_cluster_ci
    groups = grupos_perfil(X)
    for name, cut in meta["politica_modelo"]["umbrales"].items():
        result["metricas"][name]["recall_ic95_perfiles"] = recall_cluster_ci(y, scores, cut, groups, 2017)
    # El archivo 2015 ya fue utilizado: solo describe solapamiento de patrones,
    # sin deducir identidad de personas ni eliminar perfiles de la nueva cohorte.
    from app.ml.dataset import preparar_dataframe
    oldX, _, _ = preparar_dataframe(pd.read_csv(ROOT/"heart_disease_health_indicators_BRFSS2015.csv"))
    old_profiles = pd.MultiIndex.from_frame(oldX.drop_duplicates())
    result["perfiles_compartidos_2015"] = int(pd.MultiIndex.from_frame(X).isin(old_profiles).sum())
    result["alcance"] = "Validación temporal EEUU, misma encuesta; no clínica/local, sin identificación de personas"
    guardar_json(OUT/"resultados.json", result)
    pd.DataFrame(rows).to_csv(OUT/"subgrupos.csv", index=False)
    print(json.dumps({"flujo": flow, "metricas": result["metricas"]}, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--descargar", action="store_true")
    args = parser.parse_args()
    if args.descargar:
        descargar()
    evaluar()
