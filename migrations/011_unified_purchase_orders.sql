-- ============================================================
-- ORDENES DE COMPRA UNIFICADAS
-- ============================================================

-- Agregar tipo y campos adicionales a purchase_orders existente
ALTER TABLE purchase_orders ADD COLUMN purchase_type TEXT NOT NULL DEFAULT 'Insumos';
ALTER TABLE purchase_orders ADD COLUMN grape_variety_id INT REFERENCES grape_varieties(id);
ALTER TABLE purchase_orders ADD COLUMN product_line_id INT REFERENCES product_lines(id);
ALTER TABLE purchase_orders ADD COLUMN wine_type wine_type_enum;
ALTER TABLE purchase_orders ADD COLUMN expected_liters NUMERIC(12,0);
ALTER TABLE purchase_orders ADD COLUMN expected_kilos NUMERIC(12,1);
ALTER TABLE purchase_orders ADD COLUMN price_per_liter NUMERIC(12,4);
ALTER TABLE purchase_orders ADD COLUMN price_per_kilo NUMERIC(12,4);
ALTER TABLE purchase_orders ADD COLUMN total_price NUMERIC(14,2);
ALTER TABLE purchase_orders ADD COLUMN currency currency_type DEFAULT 'CLP';
ALTER TABLE purchase_orders ADD COLUMN invoice_number TEXT;
ALTER TABLE purchase_orders ADD COLUMN invoice_date DATE;
ALTER TABLE purchase_orders ADD COLUMN do_number TEXT;
ALTER TABLE purchase_orders ADD COLUMN do_date DATE;
ALTER TABLE purchase_orders ADD COLUMN acceptance_date DATE;
ALTER TABLE purchase_orders ADD COLUMN status TEXT NOT NULL DEFAULT 'Pedido';

CREATE INDEX idx_purchase_orders_type ON purchase_orders(purchase_type);
CREATE INDEX idx_purchase_orders_status ON purchase_orders(status);

-- Recepciones de vino vinculadas a OC
ALTER TABLE wine_purchase_deliveries ADD COLUMN purchase_order_id INT REFERENCES purchase_orders(id);

-- Recepciones de uva vinculadas a OC
CREATE TABLE grape_reception_deliveries (
    id SERIAL PRIMARY KEY,
    purchase_order_id INT NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    guia_despacho TEXT,
    kilos NUMERIC(12,1) NOT NULL,
    brix NUMERIC(5,2),
    ph NUMERIC(4,2),
    acidity NUMERIC(6,3),
    temperature NUMERIC(5,1),
    dest_tank_id INT REFERENCES tanks(id),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_grape_reception_deliveries_po ON grape_reception_deliveries(purchase_order_id);
