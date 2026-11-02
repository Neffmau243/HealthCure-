"""Casos de deterioro actual: no pueden quedar ocultos tras una banda ML baja."""
from datetime import date, datetime, timedelta
from io import BytesIO
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from pypdf import PdfReader
from sqlalchemy import create_engine, inspect, text

from app.schemas.clinica import ObservacionesClinicas
from app.services.alerta_clinica_service import evaluar_alertas, VERSION_REGLAS
from app.models.atencion import Atencion
from app.models.evaluacion import Evaluacion
from scripts.migrar_alertas_clinicas import migrar

BASE = dict(presion_sistolica=120, presion_diastolica=80, frecuencia_cardiaca=80,
            frecuencia_respiratoria=16, saturacion_o2=98, temperatura_c=36.5, sintomas=[])


@pytest.mark.parametrize("cambios,nivel", [
    ({"saturacion_o2":75},"inmediata"), ({"saturacion_o2":91},"inmediata"),
    ({"saturacion_o2":92},"prioritaria"), ({"saturacion_o2":95},"prioritaria"),
    ({"saturacion_o2":96},"sin_criterios_detectados"),
    ({"presion_sistolica":80,"presion_diastolica":50},"inmediata"),
    ({"presion_sistolica":90,"presion_diastolica":60},"inmediata"),
    ({"presion_sistolica":200,"presion_diastolica":130},"prioritaria"),
    ({"presion_sistolica":180,"presion_diastolica":100},"prioritaria"),
    ({"presion_sistolica":179,"presion_diastolica":120},"prioritaria"),
    ({"presion_sistolica":200,"presion_diastolica":120,"sintomas":["alteraciones_visuales"]},"inmediata"),
    ({"presion_sistolica":200,"presion_diastolica":120,"sintomas":["cefalea_intensa"]},"inmediata"),
    ({"frecuencia_cardiaca":0},"inmediata"), ({"frecuencia_cardiaca":40},"inmediata"),
    ({"frecuencia_cardiaca":41},"prioritaria"), ({"frecuencia_cardiaca":131},"inmediata"),
    ({"frecuencia_cardiaca":130},"prioritaria"),
    ({"frecuencia_respiratoria":0},"inmediata"), ({"frecuencia_respiratoria":8},"inmediata"),
    ({"frecuencia_respiratoria":25},"inmediata"), ({"frecuencia_respiratoria":24},"prioritaria"),
    ({"temperatura_c":35},"inmediata"), ({"temperatura_c":40},"prioritaria"),
    ({"sintomas":["dolor_toracico"]},"inmediata"),
    ({"sintomas":["dificultad_respiratoria"]},"inmediata"),
    ({"sintomas":["alteracion_conciencia"]},"inmediata"),
    ({"sintomas":["convulsiones"]},"inmediata"),
    ({"sintomas":["deficit_neurologico"]},"inmediata"),
    ({"sintomas":["sangrado_abundante"]},"inmediata"),
])
def test_casos_y_fronteras_adultos(cambios,nivel):
    alerta = evaluar_alertas(ObservacionesClinicas(**{**BASE,**cambios}),30)
    assert alerta["nivel"] == nivel
    assert alerta["version_reglas"] == VERSION_REGLAS
    if nivel in ("inmediata","prioritaria"):
        assert alerta["motivos"]
        assert "rutinari" in alerta["accion"]


@pytest.mark.parametrize("condicion", ["gestante","puerpera"])
@pytest.mark.parametrize("cambios", [
    {"presion_sistolica":160,"presion_diastolica":100},
    {"presion_sistolica":150,"presion_diastolica":110},
    {"temperatura_c":38}, {"sintomas":["cefalea_intensa"]},
    {"sintomas":["alteraciones_visuales"]}, {"sintomas":["sangrado_abundante"]},
])
def test_casos_maternos_separados_del_modelo(condicion,cambios):
    obs = ObservacionesClinicas(**{**BASE,**cambios})
    assert evaluar_alertas(obs,30,condicion)["nivel"] == "inmediata"


@pytest.mark.parametrize("edad", [0,7,17])
def test_pediatria_no_usa_tablas_adultas_ni_promete_normalidad(edad):
    alerta = evaluar_alertas(ObservacionesClinicas(**{**BASE,"frecuencia_cardiaca":135}),edad)
    assert alerta["nivel"] == "valoracion_especifica"
    for campo,valor in [("saturacion_o2",75),("frecuencia_cardiaca",0),("frecuencia_respiratoria",0),("sintomas",["convulsiones"]),("sintomas",["incapacidad_beber"])]:
        assert evaluar_alertas(ObservacionesClinicas(**{**BASE,campo:valor}),edad)["nivel"] == "inmediata"


def test_faltantes_no_equivalen_a_signos_normales():
    assert evaluar_alertas(None,30)["nivel"] == "datos_insuficientes"
    assert evaluar_alertas(ObservacionesClinicas(**{**BASE,"sintomas":None}),30)["nivel"] == "datos_insuficientes"
    assert evaluar_alertas(ObservacionesClinicas(saturacion_o2=75),30)["nivel"] == "inmediata"
    assert evaluar_alertas(ObservacionesClinicas(**BASE),30,"gestante")["nivel"] == "valoracion_especifica"
    assert evaluar_alertas(ObservacionesClinicas(**BASE),30,sexo="F")["nivel"] == "datos_insuficientes"


def test_fiebre_lactante_usa_edad_en_meses_y_no_edad_del_modelo():
    from app.core.clinica import calcular_edad_meses
    assert calcular_edad_meses(date(2026,7,25),date(2026,10,24)) == 2
    assert calcular_edad_meses(date(2026,7,24),date(2026,10,24)) == 3
    obs = ObservacionesClinicas(temperatura_c=38)
    assert evaluar_alertas(obs,0,edad_meses=2)["nivel"] == "inmediata"
    assert evaluar_alertas(obs,0,edad_meses=3)["nivel"] == "valoracion_especifica"


@pytest.mark.parametrize("cambios", [
    {"saturacion_o2":101},{"saturacion_o2":-1},{"presion_sistolica":0},
    {"presion_sistolica":120,"presion_diastolica":130},{"presion_diastolica":None},
    {"frecuencia_cardiaca":-1},{"temperatura_c":50},{"temperatura_c":float('nan')},
    {"frecuencia_respiratoria":float('inf')},{"sintomas":["inventado"]},
])
def test_datos_imposibles_no_producen_salida_tranquilizadora(cambios):
    with pytest.raises(ValidationError):
        ObservacionesClinicas(**{**BASE,**cambios})


def _pdf_text(resp):
    assert resp.status_code == 200, resp.text
    return " ".join(" ".join(p.extract_text() for p in PdfReader(BytesIO(resp.content)).pages).split())


def _preparar(env, usuarios_base, edad=30, sexo="M"):
    doctor = usuarios_base["doctor"]
    p = usuarios_base["paciente_doctor"]
    with env.new_session() as db:
        from app.models.paciente import Paciente
        paciente = db.get(Paciente,p.id)
        paciente.fecha_nacimiento = date(date.today().year-edad,1,1)
        paciente.sexo = sexo
        db.commit()
    return p.id, env.auth_header(doctor.id,"usuario")


def test_e2e_critico_ml_bajo_alerta_roja_historial_y_ambos_pdf(env,usuarios_base):
    pid,h = _preparar(env,usuarios_base)
    # Los nueve predictores son idénticos entre el control y el caso crítico.
    datos = {"paciente_id":pid,"edad":30,"salud_general":1,"actividad_fisica":True}
    normal = env.client.post('/api/v1/evaluaciones/',headers=h,json={**datos,"observaciones_clinicas":BASE})
    criticos = {**BASE,"presion_sistolica":80,"presion_diastolica":50,"frecuencia_cardiaca":160,"saturacion_o2":75,"temperatura_c":40,"sintomas":["dolor_toracico","dificultad_respiratoria"]}
    r = env.client.post('/api/v1/evaluaciones/',headers=h,json={**datos,"observaciones_clinicas":criticos})
    assert r.status_code == normal.status_code == 201
    ev = r.json()
    assert ev['clasificacion'] == 'bajo'
    assert ev['probabilidad'] == normal.json()['probabilidad']
    assert ev['alerta_clinica']['nivel'] == 'inmediata'
    assert len(ev['alerta_clinica']['motivos']) >= 5
    assert ev['triaje_clinico']['codigo_color'] == 'rojo'
    assert 'RUTINA' not in ev['triaje_clinico']['nivel_alerta']
    assert ev['observaciones_clinicas']['saturacion_o2'] == 75
    assert env.client.get(f'/api/v1/evaluaciones/{ev["id"]}',headers=h).json() == ev
    pdf_ev = _pdf_text(env.client.get(f'/api/v1/evaluaciones/{ev["id"]}/fua',headers=h))
    assert 'VALORACION' in pdf_ev.upper().replace('Ó','O')
    assert '75%' in pdf_ev
    assert '15 a 30' not in pdf_ev
    a = env.client.post('/api/v1/atenciones/',headers=h,json={"paciente_id":pid,"evaluacion_id":ev['id'],"tipo_atencion":"emergencia","usar_observaciones_evaluacion":True,"diagnostico":"Valoración clínica de prueba","tratamiento":"Actuación del profesional de prueba"})
    assert a.status_code == 201,a.text
    at = a.json()
    assert at['alerta_clinica']['nivel'] == 'inmediata'
    assert at['alerta_clinica']['origen_evaluacion_id'] == ev['id']
    assert at['observaciones_clinicas'] == {**ev['observaciones_clinicas'],"condicion_materna":"ninguna"}
    assert env.client.get(f'/api/v1/atenciones/by-paciente/{pid}',headers=h).json()[0] == at
    pdf_at = _pdf_text(env.client.get(f'/api/v1/atenciones/{at["id"]}/fua',headers=h))
    for contenido in ['Signos de alarma: valoración inmediata','75 %','160 lpm','40 °C','Emergencia','Dolor torácico']:
        assert contenido in pdf_at
    assert '15 a 30' not in pdf_at
    with env.new_session() as db:
        assert db.get(Atencion,at['id']).alerta_clinica['nivel'] == 'inmediata'


def test_e2e_revision_previa_funciona_sin_modelo_sin_guardar(env,usuarios_base):
    pid,h = _preparar(env,usuarios_base)
    with patch('app.ml.predictor.predict',side_effect=RuntimeError('modelo no disponible')) as modelo:
        r = env.client.post('/api/v1/clinica/revisar',headers=h,json={"paciente_id":pid,"observaciones_clinicas":{"saturacion_o2":60}})
        assert r.status_code == 200
        assert r.json()['nivel'] == 'inmediata'
        modelo.assert_not_called()
    with env.new_session() as db:
        assert db.query(Evaluacion).count() == 0
        assert db.query(Atencion).count() == 0


@pytest.mark.parametrize('edad,sexo,condicion,cambios',[(7,'M','ninguna',{'sintomas':['convulsiones']}),(30,'F','gestante',{'presion_sistolica':160,'presion_diastolica':100}),(30,'F','puerpera',{'temperatura_c':38}),(75,'M','ninguna',{'frecuencia_cardiaca':35})])
def test_e2e_casos_sin_ml_hasta_el_fua(env,usuarios_base,edad,sexo,condicion,cambios):
    pid,h = _preparar(env,usuarios_base,edad,sexo)
    r = env.client.post('/api/v1/atenciones/',headers=h,json={"paciente_id":pid,"condicion_materna":condicion,"observaciones_clinicas":{**BASE,**cambios},"diagnostico":"Caso de alarma de prueba","tratamiento":"Revisión profesional de prueba"})
    assert r.status_code == 201,r.text
    a = r.json()
    assert a['evaluacion_id'] is None
    assert a['alerta_clinica']['nivel'] == 'inmediata'
    assert 'Signos de alarma: valoración inmediata' in _pdf_text(env.client.get(f'/api/v1/atenciones/{a["id"]}/fua',headers=h))


def test_e2e_observaciones_no_se_heredan_sin_verificacion_ni_desde_ayer(env,usuarios_base):
    pid,h = _preparar(env,usuarios_base)
    ev = env.client.post('/api/v1/evaluaciones/',headers=h,json={"paciente_id":pid,"edad":30,"observaciones_clinicas":{**BASE,"saturacion_o2":75}}).json()
    payload = {"paciente_id":pid,"evaluacion_id":ev['id'],"diagnostico":"Otra visita de prueba","tratamiento":"Tratamiento de prueba"}
    a = env.client.post('/api/v1/atenciones/',headers=h,json=payload)
    assert a.status_code == 201
    assert a.json()['observaciones_clinicas'] is None
    assert a.json()['alerta_clinica']['nivel'] == 'datos_insuficientes'
    with env.new_session() as db:
        db.get(Evaluacion,ev['id']).created_at = datetime.now()-timedelta(days=1)
        db.commit()
    assert env.client.post('/api/v1/atenciones/',headers=h,json={**payload,'usar_observaciones_evaluacion':True}).status_code == 400


def test_revision_valida_entradas_y_permisos(env,usuarios_base):
    pid,h = _preparar(env,usuarios_base)
    payload = {"paciente_id":pid,"observaciones_clinicas":{'saturacion_o2':150}}
    assert env.client.post('/api/v1/clinica/revisar',headers=h,json=payload).status_code == 422
    assert env.client.post('/api/v1/clinica/revisar',json={'paciente_id':pid}).status_code == 401
    assert env.client.post('/api/v1/clinica/revisar',headers=h,json={'paciente_id':99999}).status_code == 404
    assert env.client.post('/api/v1/clinica/revisar',headers=h,json={'paciente_id':pid,'observaciones_clinicas':{'condicion_materna':'gestante'}}).status_code == 400


def test_migracion_preserva_registros_y_es_idempotente():
    engine = create_engine('sqlite://')
    try:
        with engine.begin() as db:
            for tabla in ['evaluaciones','atenciones']:
                db.execute(text(f'CREATE TABLE {tabla} (id INTEGER PRIMARY KEY)'))
                db.execute(text(f'INSERT INTO {tabla} VALUES (1)'))
        migrar(engine); migrar(engine)
        with engine.connect() as db:
            for tabla in ['evaluaciones','atenciones']:
                assert len(inspect(db).get_columns(tabla)) == 3
                assert tuple(db.execute(text(f'SELECT * FROM {tabla}')).one()) == (1,None,None)
    finally:
        engine.dispose()
