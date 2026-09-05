"""
paciente.py — MODELO: TABLA DE PACIENTES

Almacena los datos ADMINISTRATIVOS de cada paciente:
  - Identidad: tipo de documento, documento, historia clínica
  - Nombres: apellido paterno, apellido materno, nombres (formato peruano)
  - Contacto: teléfono, dirección, distrito, localidad
  - Seguro: tipo de seguro + código de afiliación
  - Control: quién lo registró, si está activo

IMPORTANTE: Este modelo NO tiene nada que ver con el modelo de ML.
Las variables predictoras (presión alta, colesterol, etc.) van en
la tabla Evaluacion, porque CADA evaluación es una instantánea
clínica diferente del mismo paciente.

Distritos y localidades vienen de catálogos que gestiona el admin
(ver models/distrito.py y models/localidad.py). El médico solo
ELIGE las opciones disponibles — no las crea.
"""
from sqlalchemy import (
    Column, BigInteger, String, Enum, Date, Numeric, Boolean,
    DateTime, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Paciente(Base):
    """
    Representa la tabla 'pacientes' en MySQL.
    Un paciente puede tener MÚLTIPLES evaluaciones cardíacas a lo largo del tiempo.
    """
    __tablename__ = "pacientes"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # ============================================================
    # IDENTIDAD
    # ============================================================
    tipo_documento = Column(
        Enum("DNI", "CE", "Pasaporte", name="tipo_documento_enum"),
        nullable=False,
        default="DNI"
    )
    # DNI = Documento Nacional de Identidad (Perú)
    # CE = Carné de Extranjería
    # Pasaporte = para extranjeros sin CE

    documento_identidad = Column(String(30), nullable=False, unique=True, index=True)
    # El número en sí (ej: "1032456789")
    # unique + index = no se puede duplicar y las búsquedas son rápidas

    numero_historia_clinica = Column(String(30), nullable=True, unique=True, index=True)
    # Número de historia clínica del hospital (ej: "72769512")
    # unique=True → una historia clínica no puede estar en dos pacientes

    # ============================================================
    # NOMBRES (formato peruano: apellidos + nombres)
    # ============================================================
    apellido_paterno = Column(String(100), nullable=False)
    apellido_materno = Column(String(100), nullable=True)
    nombres = Column(String(100), nullable=False)

    fecha_nacimiento = Column(Date, nullable=False)
    # Se usa para calcular la edad cuando se hace la evaluación

    sexo = Column(Enum("M", "F", name="sexo_enum"), nullable=False)
    # M = Masculino, F = Femenino

    # ============================================================
    # CONTACTO Y UBICACIÓN
    # ============================================================
    telefono = Column(String(20), nullable=True)
    # Ej: "987654321"

    direccion = Column(String(200), nullable=True)
    # Ej: "Av. Principal 123"

    distrito_id = Column(BigInteger, ForeignKey("distritos.id"), nullable=True)
    # FK → distritos.id. Es un CATÁLOGO gestionado por el admin.
    # El médico elige de la lista desplegable.

    localidad_id = Column(BigInteger, ForeignKey("localidades.id"), nullable=True)
    # FK → localidades.id. Depende del distrito elegido.

    # ============================================================
    # SEGURO DE SALUD
    # ============================================================
    tipo_seguro = Column(
        Enum("SIS", "EsSalud", "Privado", "Otro", name="tipo_seguro_enum"),
        nullable=False,
        default="SIS"
    )
    # SIS = Seguro Integral de Salud (Perú)
    # EsSalud = Seguro social
    # Privado = EPS/aseguradora privada

    codigo_afiliacion_seguro = Column(String(50), nullable=True)
    # Código de afiliación (ej: "040-2-1032456789")

    # ============================================================
    # CONTROL
    # ============================================================
    usuario_creador_id = Column(BigInteger, nullable=True, index=True)
    # Guarda qué usuario (médico/enfermera) registró este paciente.
    # Se usa para permisos: solo el creador o un admin puede editar.
    # nullable=True para compatibilidad con datos existentes del seed.

    activo = Column(Boolean, nullable=False, default=True)
    # Soft delete del paciente: False = paciente dado de baja,
    # pero sus evaluaciones e historial siguen existiendo para auditoría.

    # --- Mediciones físicas (opcionales, se pueden llenar después) ---
    talla_cm = Column(Numeric(5, 1), nullable=True)
    # Numeric(5,1) = hasta 999.9 cm (ej: 175.5 cm)

    peso_kg = Column(Numeric(5, 1), nullable=True)
    # Numeric(5,1) = hasta 999.9 kg (ej: 72.3 kg)

    # --- Timestamps ---
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # --- Relaciones ---
    evaluaciones = relationship("Evaluacion", back_populates="paciente")
    # Un paciente puede tener MUCHAS evaluaciones cardíacas

    distrito = relationship("Distrito")
    # Para acceder a paciente.distrito.nombre en la respuesta

    localidad = relationship("Localidad")
    # Para acceder a paciente.localidad.nombre en la respuesta

    @property
    def nombre_completo(self) -> str:
        """
        Nombre completo en formato peruano: "APELLIDO PATERNO Apellido materno, Nombres"
        Ejemplo: "PEREZ RODRIGUEZ, Juan"
        Usado por el frontend para mostrar el paciente en listas/búsquedas.
        """
        apellidos = " ".join(
            p for p in [self.apellido_paterno, self.apellido_materno] if p
        )
        return f"{apellidos}, {self.nombres}".strip(", ")