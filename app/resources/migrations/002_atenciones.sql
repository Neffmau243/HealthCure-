-- ============================================================
-- HealthCure - CardioPredict
-- MIGRACIÓN 002: Tabla de atenciones (consultorio)
-- ============================================================
-- Aplica SOLO si tu base de datos ya existe (creada con un schema.sql previo).
-- Si la BD es nueva (vas a correr schema.sql actualizado), NO necesitas esto.
--
-- Ejecutar en MySQL:
--   mysql -u tu_usuario -p healthcure_db < app/resources/migrations/002_atenciones.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS atenciones (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    paciente_id     BIGINT       NOT NULL,
    evaluacion_id   BIGINT       NULL,
    usuario_id      BIGINT       NOT NULL,

    diagnostico     TEXT         NOT NULL,
    tratamiento     TEXT         NOT NULL,
    indicaciones    TEXT         NULL,

    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_atencion_paciente
        FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_atencion_evaluacion
        FOREIGN KEY (evaluacion_id) REFERENCES evaluaciones(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_atencion_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON DELETE RESTRICT,

    INDEX ix_atenciones_paciente_id (paciente_id),
    INDEX ix_atenciones_created_at (created_at)
);
