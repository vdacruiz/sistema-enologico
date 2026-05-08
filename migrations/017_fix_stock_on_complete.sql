-- Fix: solo descontar insumos de OTs completadas
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
    SELECT wol.lot_id, SUM(wol.quantity) AS total_out
    FROM work_order_lines wol
    JOIN work_orders wo ON wo.id = wol.work_order_id
    WHERE wo.status = 'Completada'
    GROUP BY wol.lot_id
) exits ON exits.lot_id = sl.id
WHERE sl.is_active = TRUE;
