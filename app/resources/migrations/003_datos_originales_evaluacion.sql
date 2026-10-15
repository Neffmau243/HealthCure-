-- Ejecutar una sola vez en bases existentes, antes de iniciar esta versión.
-- No inferir categorías históricas: el booleano no distingue prediabetes.
ALTER TABLE evaluaciones
    ADD COLUMN estado_diabetes VARCHAR(20) NULL,
    ADD COLUMN presion_sistolica SMALLINT NULL,
    ADD COLUMN presion_diastolica SMALLINT NULL;
