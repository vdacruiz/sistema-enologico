-- ============================================================
-- CORRELATIVO para analisis de laboratorio
-- Mismo patron que ot_number en work_orders
-- ============================================================

ALTER TABLE lab_analyses ADD COLUMN IF NOT EXISTS analysis_number INT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_lab_analyses_number ON lab_analyses(analysis_number) WHERE analysis_number IS NOT NULL;
