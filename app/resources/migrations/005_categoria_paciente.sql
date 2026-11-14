-- Ejecutar una vez, o usar python -m scripts.migrar_categoria_paciente (idempotente).
ALTER TABLE pacientes ADD COLUMN contexto_atencion JSON NULL;
