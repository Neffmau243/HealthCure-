-- ============================================================
-- HealthCure - CardioPredict
-- MIGRACIÓN 001: Triaje clínico en evaluaciones
-- ============================================================
-- Aplica SOLO si tu base de datos ya existe (creada con el schema.sql viejo).
-- Si la BD es nueva (vas a correr schema.sql actualizado), NO necesitas esto.
--
-- Ejecutar en MySQL:
--   mysql -u tu_usuario -p healthcure_db < app/resources/migrations/001_triaje_clinico.sql
-- ============================================================

ALTER TABLE evaluaciones
    ADD COLUMN nivel_alerta VARCHAR(100) NULL AFTER modelo_version,
    ADD COLUMN codigo_color VARCHAR(20) NULL AFTER nivel_alerta,
    ADD COLUMN accion_sugerida TEXT NULL AFTER codigo_color,
    ADD COLUMN factores_riesgo_detectados JSON NULL AFTER accion_sugerida,
    ADD COLUMN factores_protectores JSON NULL AFTER factores_riesgo_detectados,
    ADD COLUMN recomendaciones_medicas JSON NULL AFTER factores_protectores;