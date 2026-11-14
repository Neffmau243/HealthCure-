"""Datos administrativos de salud materna del FUA; no son variables del modelo ML."""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.clinica import CondicionMaterna


class DatosMaternos(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    fecha_probable_parto: date | None = None
    edad_gestacional_semanas: float | None = Field(None, ge=0)
    numero_control_prenatal: int | None = Field(None, ge=1)
    altura_uterina_cm: float | None = Field(None, ge=0)
    fecha_parto: date | None = None
    numero_control_puerperal: int | None = Field(None, ge=1)


CAMPOS_GESTANTE = {"fecha_probable_parto", "edad_gestacional_semanas", "numero_control_prenatal", "altura_uterina_cm"}
CAMPOS_PUERPERA = {"fecha_parto", "numero_control_puerperal"}


class ContextoPaciente(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condicion_materna: CondicionMaterna = CondicionMaterna.ninguna
    datos_maternos: DatosMaternos | None = None

    @model_validator(mode="after")
    def validar_categoria(self):
        datos = self.datos_maternos.model_dump(exclude_none=True) if self.datos_maternos else {}
        permitidos = {"gestante": CAMPOS_GESTANTE, "puerpera": CAMPOS_PUERPERA}.get(self.condicion_materna, set())
        if datos.keys() - permitidos:
            raise ValueError("Los datos maternos no corresponden a la categoría de esta visita")
        if datos.get("fecha_parto") and datos["fecha_parto"] > date.today():
            raise ValueError("La fecha de parto no puede ser futura")
        if not datos:
            self.datos_maternos = None
        return self

    def validar_sexo(self, sexo):
        if self.condicion_materna != CondicionMaterna.ninguna and sexo != "F":
            raise ValueError("Gestante o puérpera requiere sexo femenino registrado")
