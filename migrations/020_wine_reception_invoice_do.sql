-- ============================================================
-- FACTURA, DO y campos adicionales en wine_receptions
-- Para trazabilidad contable: Recibido → Facturado → DO Liberada → Aprobada
-- ============================================================

ALTER TABLE wine_receptions ADD COLUMN IF NOT EXISTS invoice_number TEXT;
ALTER TABLE wine_receptions ADD COLUMN IF NOT EXISTS invoice_date DATE;
ALTER TABLE wine_receptions ADD COLUMN IF NOT EXISTS invoice_amount NUMERIC(14,2);
ALTER TABLE wine_receptions ADD COLUMN IF NOT EXISTS do_number TEXT;
ALTER TABLE wine_receptions ADD COLUMN IF NOT EXISTS do_date DATE;
ALTER TABLE wine_receptions ADD COLUMN IF NOT EXISTS do_released BOOLEAN DEFAULT FALSE;
ALTER TABLE wine_receptions ADD COLUMN IF NOT EXISTS approved_date DATE;
ALTER TABLE wine_receptions ADD COLUMN IF NOT EXISTS approved_by TEXT;
ALTER TABLE wine_receptions ADD COLUMN IF NOT EXISTS vintage_year INT;
ALTER TABLE wine_receptions ADD COLUMN IF NOT EXISTS litros_guia NUMERIC(12,0);
