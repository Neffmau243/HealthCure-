"""Revisión previa de signos y síntomas: sin ML y sin guardar una consulta."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.clinica import calcular_edad, calcular_edad_meses
from app.api.deps import get_current_user
from app.repositories.paciente_repository import PacienteRepository
from app.schemas.clinica import RevisionClinicaCreate, AlertaClinica
from app.services.alerta_clinica_service import evaluar_alertas

router = APIRouter(prefix="/clinica", tags=["Alertas clínicas"])


@router.post("/revisar", response_model=AlertaClinica)
def revisar(data: RevisionClinicaCreate, db: Session = Depends(get_db), _user: dict = Depends(get_current_user)):
    paciente = PacienteRepository(db).get_by_id(data.paciente_id)
    if paciente is None:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    obs = data.observaciones_clinicas
    if obs and obs.condicion_materna in ("gestante", "puerpera") and paciente.sexo != "F":
        raise HTTPException(status_code=400, detail="La condición materna requiere sexo femenino registrado")
    try:
        return evaluar_alertas(obs, calcular_edad(paciente.fecha_nacimiento), sexo=paciente.sexo, edad_meses=calcular_edad_meses(paciente.fecha_nacimiento))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
