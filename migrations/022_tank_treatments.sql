-- ============================================================
-- TRATAMIENTOS aplicados al vino en cada cuba
-- Dato historico (carga manual) + actualizado por OTs
-- _ots guarda numeros de OT separados por coma (se acumulan en mezclas)
-- ============================================================

ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS has_enzima BOOLEAN DEFAULT FALSE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS enzima_date DATE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS enzima_ots TEXT;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS has_gelatina BOOLEAN DEFAULT FALSE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS gelatina_date DATE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS gelatina_ots TEXT;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS has_bentonita BOOLEAN DEFAULT FALSE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS bentonita_date DATE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS bentonita_ots TEXT;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS has_frio BOOLEAN DEFAULT FALSE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS frio_date DATE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS frio_ots TEXT;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS has_meta BOOLEAN DEFAULT FALSE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS meta_date DATE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS meta_ots TEXT;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS has_cmc BOOLEAN DEFAULT FALSE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS cmc_date DATE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS cmc_ots TEXT;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS has_bic BOOLEAN DEFAULT FALSE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS bic_date DATE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS bic_ots TEXT;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS has_tangencial BOOLEAN DEFAULT FALSE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS tangencial_date DATE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS tangencial_ots TEXT;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS has_trasiego BOOLEAN DEFAULT FALSE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS trasiego_date DATE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS trasiego_ots TEXT;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS has_placas BOOLEAN DEFAULT FALSE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS placas_date DATE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS placas_ots TEXT;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS has_sulfirex BOOLEAN DEFAULT FALSE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS sulfirex_date DATE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS sulfirex_ots TEXT;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS has_goma BOOLEAN DEFAULT FALSE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS goma_date DATE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS goma_ots TEXT;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS has_sorbato BOOLEAN DEFAULT FALSE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS sorbato_date DATE;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS sorbato_ots TEXT;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS sorbato_dosis TEXT;
