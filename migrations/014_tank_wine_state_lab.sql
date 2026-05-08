-- Agregar estado del vino y datos de lab principales a tank_contents
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS wine_state TEXT;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS vintage_year INT;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS alcohol_degree NUMERIC(5,2);
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS ph NUMERIC(4,2);
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS total_acidity NUMERIC(6,3);
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS volatile_acidity NUMERIC(6,3);
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS free_so2 NUMERIC(6,1);
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS total_so2 NUMERIC(6,1);
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS residual_sugar NUMERIC(6,2);
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS so2_molecular NUMERIC(6,4);
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS ntu NUMERIC(6,2);
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS color NUMERIC(6,2);
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS co2 NUMERIC(8,1);
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS fml TEXT;
ALTER TABLE tank_contents ADD COLUMN IF NOT EXISTS last_analysis_date DATE;
