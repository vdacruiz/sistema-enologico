-- ============================================================
-- COMPRAS DE VINO (OC Vino con multiples despachos)
-- ============================================================

CREATE TABLE wine_purchases (
    id SERIAL PRIMARY KEY,
    oc_number TEXT,
    date DATE NOT NULL,
    supplier_id INT REFERENCES suppliers(id),
    grape_variety_id INT REFERENCES grape_varieties(id),
    product_line_id INT REFERENCES product_lines(id),
    wine_type wine_type_enum,
    expected_liters NUMERIC(12,0),
    price_per_liter NUMERIC(12,4),
    total_price NUMERIC(14,2),
    currency currency_type DEFAULT 'CLP',
    invoice_number TEXT,
    invoice_date DATE,
    do_number TEXT,
    do_date DATE,
    acceptance_date DATE,
    status TEXT NOT NULL DEFAULT 'Pedido',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE wine_purchase_deliveries (
    id SERIAL PRIMARY KEY,
    wine_purchase_id INT NOT NULL REFERENCES wine_purchases(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    guia_despacho TEXT,
    liters NUMERIC(12,0) NOT NULL,
    dest_tank_id INT REFERENCES tanks(id),
    alcohol_degree NUMERIC(5,2),
    so2_total NUMERIC(6,2),
    ph NUMERIC(4,2),
    temperature NUMERIC(5,1),
    wine_code TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_wine_purchases_supplier ON wine_purchases(supplier_id);
CREATE INDEX idx_wine_purchases_date ON wine_purchases(date);
CREATE INDEX idx_wine_purchases_status ON wine_purchases(status);
CREATE INDEX idx_wine_purchase_deliveries_purchase ON wine_purchase_deliveries(wine_purchase_id);
