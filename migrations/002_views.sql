-- ============================================================
-- VISTAS DE STOCK EN TIEMPO REAL
-- ============================================================

-- Stock por lote (detallado)
CREATE OR REPLACE VIEW v_supply_stock_by_lot AS
SELECT
    sl.id AS lot_id,
    s.id AS supply_id,
    s.name AS supply_name,
    s.code AS supply_code,
    s.unit,
    sl.lot_number,
    sl.expiry_date,
    sl.initial_stock,
    COALESCE(entries.total_in, 0) AS total_entries,
    COALESCE(exits.total_out, 0) AS total_exits,
    sl.initial_stock + COALESCE(entries.total_in, 0) - COALESCE(exits.total_out, 0) AS current_stock,
    CASE
        WHEN sl.expiry_date IS NOT NULL AND sl.expiry_date < CURRENT_DATE THEN 'VENCIDO'
        WHEN sl.expiry_date IS NOT NULL AND sl.expiry_date < CURRENT_DATE + INTERVAL '90 days' THEN 'POR VENCER'
        ELSE 'OK'
    END AS expiry_status
FROM supply_lots sl
JOIN supplies s ON s.id = sl.supply_id
LEFT JOIN (
    SELECT lot_id, SUM(quantity) AS total_in
    FROM purchase_order_lines
    WHERE movement_type = 'Ingreso'
    GROUP BY lot_id
) entries ON entries.lot_id = sl.id
LEFT JOIN (
    SELECT lot_id, SUM(quantity) AS total_out
    FROM work_order_lines
    GROUP BY lot_id
) exits ON exits.lot_id = sl.id
WHERE sl.is_active = TRUE;

-- Stock total por insumo (agregado)
CREATE OR REPLACE VIEW v_supply_stock_total AS
SELECT
    supply_id,
    supply_name,
    supply_code,
    unit,
    SUM(initial_stock) AS total_initial,
    SUM(total_entries) AS total_entries,
    SUM(total_exits) AS total_exits,
    SUM(current_stock) AS total_stock,
    COUNT(*) FILTER (WHERE current_stock > 0) AS active_lots
FROM v_supply_stock_by_lot
GROUP BY supply_id, supply_name, supply_code, unit;

-- Alertas de stock bajo
CREATE OR REPLACE VIEW v_low_stock_alerts AS
SELECT
    s.id, s.code, s.name, s.unit, s.min_stock,
    COALESCE(vst.total_stock, 0) AS current_stock,
    s.min_stock - COALESCE(vst.total_stock, 0) AS deficit
FROM supplies s
LEFT JOIN v_supply_stock_total vst ON vst.supply_id = s.id
WHERE s.min_stock IS NOT NULL
  AND s.min_stock > 0
  AND COALESCE(vst.total_stock, 0) < s.min_stock
  AND s.is_active = TRUE
ORDER BY deficit DESC;

-- Alertas de vencimiento
CREATE OR REPLACE VIEW v_expiry_alerts AS
SELECT * FROM v_supply_stock_by_lot
WHERE expiry_status IN ('VENCIDO', 'POR VENCER')
  AND current_stock > 0
ORDER BY expiry_date ASC;
