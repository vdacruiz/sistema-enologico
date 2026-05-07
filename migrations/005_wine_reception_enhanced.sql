-- Mejorar tabla de recepcion de vino para compras y vendimia
ALTER TABLE wine_receptions ADD COLUMN reception_type TEXT NOT NULL DEFAULT 'Compra Vino';
ALTER TABLE wine_receptions ADD COLUMN supplier_id INT REFERENCES suppliers(id);
ALTER TABLE wine_receptions ADD COLUMN guia_despacho TEXT;
ALTER TABLE wine_receptions ADD COLUMN oc_number TEXT;
ALTER TABLE wine_receptions ADD COLUMN price_per_liter NUMERIC(12,4);
ALTER TABLE wine_receptions ADD COLUMN total_price NUMERIC(14,2);
ALTER TABLE wine_receptions ADD COLUMN currency currency_type DEFAULT 'CLP';
ALTER TABLE wine_receptions ADD COLUMN alcohol_degree NUMERIC(5,2);
ALTER TABLE wine_receptions ADD COLUMN so2_total NUMERIC(6,2);
ALTER TABLE wine_receptions ADD COLUMN wine_type wine_type_enum;
ALTER TABLE wine_receptions ADD COLUMN product_line_id INT REFERENCES product_lines(id);
ALTER TABLE wine_receptions ADD COLUMN wine_code TEXT;
ALTER TABLE wine_receptions ADD COLUMN status TEXT NOT NULL DEFAULT 'Recibido';

CREATE INDEX idx_wine_receptions_date ON wine_receptions(date);
CREATE INDEX idx_wine_receptions_type ON wine_receptions(reception_type);
