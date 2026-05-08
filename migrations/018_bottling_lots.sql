-- ============================================================
-- LOTES DE EMBOTELLADO / ENVASADO
-- Trazabilidad completa por lote de botella
-- ============================================================

CREATE TABLE IF NOT EXISTS bottling_lots (
    id SERIAL PRIMARY KEY,
    lot_number TEXT NOT NULL UNIQUE,
    wine_id INT NOT NULL REFERENCES wines(id),
    tank_id INT NOT NULL REFERENCES tanks(id),
    bottling_date DATE NOT NULL,
    liters NUMERIC(12,1) NOT NULL,
    bottles_count INT,
    bottle_format TEXT,
    grape_variety_id INT REFERENCES grape_varieties(id),
    product_line_id INT REFERENCES product_lines(id),
    wine_type wine_type_enum,
    vintage_year INT,
    alcohol_degree NUMERIC(5,2),
    ph NUMERIC(4,2),
    total_acidity NUMERIC(6,3),
    volatile_acidity NUMERIC(6,3),
    free_so2 NUMERIC(6,1),
    total_so2 NUMERIC(6,1),
    residual_sugar NUMERIC(6,2),
    ntu NUMERIC(6,2),
    notes TEXT,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bottling_lots_wine ON bottling_lots(wine_id);
CREATE INDEX IF NOT EXISTS idx_bottling_lots_lot ON bottling_lots(lot_number);
CREATE INDEX IF NOT EXISTS idx_bottling_lots_date ON bottling_lots(bottling_date);
