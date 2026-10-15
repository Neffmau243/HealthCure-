-- Una sola ejecución. Alternativa idempotente: python scripts/aplicar_migracion_004.py
ALTER TABLE evaluaciones ADD COLUMN politica_modelo JSON NULL;
