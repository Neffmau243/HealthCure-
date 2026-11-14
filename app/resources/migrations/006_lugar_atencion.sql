-- Lugar de atención del FUA por visita (INTRAMURAL / EXTRAMURAL).
-- Las atenciones anteriores conservan NULL y el formulario imprime Intramural.
ALTER TABLE atenciones ADD COLUMN lugar_atencion VARCHAR(20) NULL;
