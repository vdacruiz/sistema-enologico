-- ============================================================
-- LABORATORIO - Parametros y Analisis
-- ============================================================

-- Parametros de referencia con rangos por tipo de vino
CREATE TABLE lab_parameters (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    wine_type wine_type_enum NOT NULL,
    min_normal NUMERIC(10,3),
    max_normal NUMERIC(10,3),
    alert_value NUMERIC(10,3),
    critical_value NUMERIC(10,3),
    alert_direction TEXT DEFAULT 'above',
    sort_order INT DEFAULT 0,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Analisis de laboratorio (cabecera)
CREATE TABLE lab_analyses (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    tank_id INT REFERENCES tanks(id),
    wine_id INT REFERENCES wines(id),
    grape_variety_id INT REFERENCES grape_varieties(id),
    wine_type wine_type_enum NOT NULL DEFAULT 'Tinto',
    stage TEXT DEFAULT 'Guarda',
    analyst TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Resultados individuales por parametro
CREATE TABLE lab_analysis_results (
    id SERIAL PRIMARY KEY,
    analysis_id INT NOT NULL REFERENCES lab_analyses(id) ON DELETE CASCADE,
    parameter_id INT NOT NULL REFERENCES lab_parameters(id),
    value NUMERIC(10,3),
    evaluation TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_lab_analyses_tank ON lab_analyses(tank_id);
CREATE INDEX idx_lab_analyses_wine ON lab_analyses(wine_id);
CREATE INDEX idx_lab_analyses_date ON lab_analyses(date);
CREATE INDEX idx_lab_analysis_results_analysis ON lab_analysis_results(analysis_id);

-- ============================================================
-- DATOS INICIALES - Parametros Tinto
-- ============================================================

INSERT INTO lab_parameters (code, name, unit, wine_type, min_normal, max_normal, alert_value, critical_value, alert_direction, sort_order) VALUES
('TINTO_GRADO', 'Grado Alcoholico', '%vol', 'Tinto', 12.5, 15.0, NULL, NULL, 'above', 1),
('TINTO_PH', 'pH', '', 'Tinto', 3.3, 3.8, NULL, NULL, 'above', 2),
('TINTO_AT', 'Acidez Total', 'g/L', 'Tinto', 4.5, 6.5, NULL, NULL, 'below', 3),
('TINTO_AV', 'Acidez Volatil', 'g/L', 'Tinto', 0, 0.4, 0.6, 0.9, 'above', 4),
('TINTO_SO2L', 'SO2 Libre', 'mg/L', 'Tinto', 20, 40, NULL, NULL, 'below', 5),
('TINTO_SO2T', 'SO2 Total', 'mg/L', 'Tinto', 0, 120, 150, 180, 'above', 6),
('TINTO_AR', 'Azucar Residual', 'g/L', 'Tinto', 0, 2, 4, 12, 'above', 7),
('TINTO_NTU', 'Turbidez', 'NTU', 'Tinto', 0, 1, 3, 5, 'above', 8),
('TINTO_CO2', 'CO2', 'mg/L', 'Tinto', 0, 800, 1200, NULL, 'above', 9),
('TINTO_COLOR', 'Color', '', 'Tinto', 5, 15, NULL, NULL, 'above', 10),
('TINTO_SO2M', 'SO2 Molecular', 'mg/L', 'Tinto', 0.5, 0.8, NULL, NULL, 'below', 11);

-- ============================================================
-- DATOS INICIALES - Parametros Blanco/Rosado
-- ============================================================

INSERT INTO lab_parameters (code, name, unit, wine_type, min_normal, max_normal, alert_value, critical_value, alert_direction, sort_order) VALUES
('BLANCO_GRADO', 'Grado Alcoholico', '%vol', 'Blanco', 11, 14, NULL, NULL, 'above', 1),
('BLANCO_PH', 'pH', '', 'Blanco', 3.0, 3.4, NULL, NULL, 'above', 2),
('BLANCO_AT', 'Acidez Total', 'g/L', 'Blanco', 5.5, 7.5, NULL, NULL, 'below', 3),
('BLANCO_AV', 'Acidez Volatil', 'g/L', 'Blanco', 0, 0.4, 0.6, 0.9, 'above', 4),
('BLANCO_SO2L', 'SO2 Libre', 'mg/L', 'Blanco', 25, 50, NULL, NULL, 'below', 5),
('BLANCO_SO2T', 'SO2 Total', 'mg/L', 'Blanco', 0, 150, 200, 250, 'above', 6),
('BLANCO_AR', 'Azucar Residual', 'g/L', 'Blanco', 0, 4, 8, 12, 'above', 7),
('BLANCO_NTU', 'Turbidez', 'NTU', 'Blanco', 0, 1, 3, 5, 'above', 8),
('BLANCO_CO2', 'CO2', 'mg/L', 'Blanco', 0, 1200, 1800, NULL, 'above', 9),
('BLANCO_COLOR', 'Color', '', 'Blanco', 1, 5, NULL, NULL, 'above', 10),
('BLANCO_SO2M', 'SO2 Molecular', 'mg/L', 'Blanco', 0.8, 1.0, NULL, NULL, 'below', 11);

-- Rosado usa mismos parametros que Blanco
INSERT INTO lab_parameters (code, name, unit, wine_type, min_normal, max_normal, alert_value, critical_value, alert_direction, sort_order) VALUES
('ROSADO_GRADO', 'Grado Alcoholico', '%vol', 'Rosado', 11, 14, NULL, NULL, 'above', 1),
('ROSADO_PH', 'pH', '', 'Rosado', 3.0, 3.4, NULL, NULL, 'above', 2),
('ROSADO_AT', 'Acidez Total', 'g/L', 'Rosado', 5.5, 7.5, NULL, NULL, 'below', 3),
('ROSADO_AV', 'Acidez Volatil', 'g/L', 'Rosado', 0, 0.4, 0.6, 0.9, 'above', 4),
('ROSADO_SO2L', 'SO2 Libre', 'mg/L', 'Rosado', 25, 50, NULL, NULL, 'below', 5),
('ROSADO_SO2T', 'SO2 Total', 'mg/L', 'Rosado', 0, 150, 200, 250, 'above', 6),
('ROSADO_AR', 'Azucar Residual', 'g/L', 'Rosado', 0, 4, 8, 12, 'above', 7),
('ROSADO_NTU', 'Turbidez', 'NTU', 'Rosado', 0, 1, 3, 5, 'above', 8),
('ROSADO_CO2', 'CO2', 'mg/L', 'Rosado', 0, 1200, 1800, NULL, 'above', 9),
('ROSADO_COLOR', 'Color', '', 'Rosado', 1, 5, NULL, NULL, 'above', 10),
('ROSADO_SO2M', 'SO2 Molecular', 'mg/L', 'Rosado', 0.8, 1.0, NULL, NULL, 'below', 11);
