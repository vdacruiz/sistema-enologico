-- Agregar campo de aprobacion para envasado en tank_contents
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS apto_envasado BOOLEAN DEFAULT FALSE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS apto_envasado_at TIMESTAMP;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS apto_envasado_by TEXT;
