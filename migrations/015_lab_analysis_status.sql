-- Agregar estado y operario a lab_analyses
ALTER TABLE lab_analyses ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Confirmado';
ALTER TABLE lab_analyses ADD COLUMN IF NOT EXISTS worker_id INT REFERENCES workers(id);

-- Indice para buscar ultimo analisis por vino rapidamente
CREATE INDEX IF NOT EXISTS idx_lab_analyses_wine_date ON lab_analyses(wine_id, date DESC);
