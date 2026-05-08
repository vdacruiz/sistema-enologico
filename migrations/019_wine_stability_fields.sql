-- ============================================================
-- CAMPOS DE ESTABILIDAD Y TESTS en tank_contents
-- Tests puntuales que no encajan como analisis de laboratorio
-- ============================================================

ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS test_color_4 BOOLEAN DEFAULT FALSE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS test_color_4_date DATE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS test_tartarica_neg4 BOOLEAN DEFAULT FALSE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS test_tartarica_neg4_date DATE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS fecha_ac DATE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS control_mensual_date DATE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS blend_notes TEXT;
