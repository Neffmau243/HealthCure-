-- Conserva las atenciones antiguas sin inventar su tipo ni condición materna.
ALTER TABLE atenciones
    ADD COLUMN tipo_atencion VARCHAR(20) NULL,
    ADD COLUMN grupo_etario VARCHAR(20) NULL,
    ADD COLUMN condicion_materna VARCHAR(20) NULL,
    ADD COLUMN edad_al_atender SMALLINT NULL;
