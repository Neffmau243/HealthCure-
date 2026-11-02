-- Conserva las observaciones y el aviso calculado en cada registro. NULL = legado.
ALTER TABLE evaluaciones ADD COLUMN observaciones_clinicas JSON NULL, ADD COLUMN alerta_clinica JSON NULL;
ALTER TABLE atenciones ADD COLUMN observaciones_clinicas JSON NULL, ADD COLUMN alerta_clinica JSON NULL;
