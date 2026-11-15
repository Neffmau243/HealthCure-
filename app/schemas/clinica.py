"""Observaciones actuales, separadas de las nueve variables del modelo."""
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.core.clinica import CondicionMaterna


class SintomaAlarma(str, Enum):
    dolor_toracico = "dolor_toracico"
    dificultad_respiratoria = "dificultad_respiratoria"
    alteracion_conciencia = "alteracion_conciencia"
    convulsiones = "convulsiones"
    deficit_neurologico = "deficit_neurologico"
    sangrado_abundante = "sangrado_abundante"
    cefalea_intensa = "cefalea_intensa"
    alteraciones_visuales = "alteraciones_visuales"
    dolor_abdominal_intenso = "dolor_abdominal_intenso"
    movimientos_fetales_disminuidos = "movimientos_fetales_disminuidos"
    incapacidad_beber = "incapacidad_beber"


class ObservacionesClinicas(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    presion_sistolica: float | None = Field(None, gt=0, le=350)
    presion_diastolica: float | None = Field(None, gt=0, le=250)
    frecuencia_cardiaca: float | None = Field(None, ge=0, le=300)
    frecuencia_respiratoria: float | None = Field(None, ge=0, le=100)
    saturacion_o2: float | None = Field(None, ge=0, le=100)
    temperatura_c: float | None = Field(None, ge=25, le=45)
    peso_kg: float | None = Field(None, gt=0, le=500)
    talla_cm: float | None = Field(None, gt=0, le=300)
    # None = no revisados. [] = el profesional confirmó que no están presentes.
    sintomas: list[SintomaAlarma] | None = None
    condicion_materna: CondicionMaterna | None = None

    @model_validator(mode="after")
    def validar_presion(self):
        s, d = self.presion_sistolica, self.presion_diastolica
        if (s is None) != (d is None):
            raise ValueError("Registra ambas cifras de presión o deja ambas sin registrar")
        if s is not None and d >= s:
            raise ValueError("La presión sistólica debe ser mayor que la diastólica; verifica la medición")
        return self


class AlertaClinica(BaseModel):
    nivel: Literal["inmediata", "prioritaria", "sin_criterios_detectados", "datos_insuficientes", "valoracion_especifica"]
    titulo: str
    accion: str
    motivos: list[str]
    datos_faltantes: list[str]
    limitaciones: list[str]
    version_reglas: str
    origen_evaluacion_id: int | None = None


class RevisionClinicaCreate(BaseModel):
    paciente_id: int = Field(..., gt=0)
    observaciones_clinicas: ObservacionesClinicas | None = None
