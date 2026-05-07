-- ============================================================
-- SISTEMA ENOLOGICO VDA - Schema Principal
-- ============================================================

-- Tipos ENUM
CREATE TYPE currency_type AS ENUM ('CLP', 'USD', 'EUR');
CREATE TYPE wine_type_enum AS ENUM ('Tinto', 'Blanco', 'Rosado', 'Borras', 'N/A');
CREATE TYPE movement_type AS ENUM ('Ingreso', 'Egreso');
CREATE TYPE unit_type AS ENUM ('Kg', 'Lts', 'Unidad');
CREATE TYPE tank_status AS ENUM ('Vacio', 'Ocupado', 'En proceso', 'Limpieza');

-- ============================================================
-- TABLAS DE REFERENCIA
-- ============================================================

CREATE TABLE winemaking_processes (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE grape_varieties (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    wine_type wine_type_enum NOT NULL DEFAULT 'Tinto',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE product_lines (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    sort_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE workers (
    id SERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    role TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    rut TEXT,
    contact_name TEXT,
    phone TEXT,
    email TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE supply_classifications (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE tanks (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT,
    capacity_liters NUMERIC(10,0),
    location TEXT,
    tank_type TEXT DEFAULT 'Cuba',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INSUMOS ENOLOGICOS
-- ============================================================

CREATE TABLE supplies (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    unit unit_type NOT NULL DEFAULT 'Kg',
    unit_cost NUMERIC(12,4),
    currency currency_type DEFAULT 'CLP',
    classification_id INT REFERENCES supply_classifications(id),
    default_process_id INT REFERENCES winemaking_processes(id),
    min_stock NUMERIC(12,3),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE supply_lots (
    id SERIAL PRIMARY KEY,
    supply_id INT NOT NULL REFERENCES supplies(id),
    lot_number TEXT NOT NULL,
    expiry_date DATE,
    initial_stock NUMERIC(12,3) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(supply_id, lot_number),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE supply_process_map (
    id SERIAL PRIMARY KEY,
    supply_id INT NOT NULL REFERENCES supplies(id),
    process_id INT NOT NULL REFERENCES winemaking_processes(id),
    UNIQUE(supply_id, process_id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- VINOS
-- ============================================================

CREATE TABLE wines (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    grape_variety_id INT REFERENCES grape_varieties(id),
    product_line_id INT REFERENCES product_lines(id),
    wine_type wine_type_enum NOT NULL DEFAULT 'Tinto',
    vintage_year INT,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ORDENES DE COMPRA (Recepcion de Insumos)
-- ============================================================

CREATE TABLE purchase_orders (
    id SERIAL PRIMARY KEY,
    oc_number TEXT,
    date DATE NOT NULL,
    supplier_id INT REFERENCES suppliers(id),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE purchase_order_lines (
    id SERIAL PRIMARY KEY,
    purchase_order_id INT NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    supply_id INT NOT NULL REFERENCES supplies(id),
    lot_id INT REFERENCES supply_lots(id),
    quantity NUMERIC(12,3) NOT NULL,
    movement_type movement_type NOT NULL DEFAULT 'Ingreso',
    unit unit_type NOT NULL DEFAULT 'Kg',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ORDENES DE TRABAJO (Egreso de Insumos)
-- ============================================================

CREATE TABLE work_orders (
    id SERIAL PRIMARY KEY,
    ot_number INT NOT NULL,
    date DATE NOT NULL,
    wine_id INT REFERENCES wines(id),
    grape_variety_id INT REFERENCES grape_varieties(id),
    product_line_id INT REFERENCES product_lines(id),
    wine_type wine_type_enum,
    source_tank_id INT REFERENCES tanks(id),
    dest_tank_id INT REFERENCES tanks(id),
    liters NUMERIC(12,0),
    process_id INT REFERENCES winemaking_processes(id),
    worker_id INT REFERENCES workers(id),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE work_order_lines (
    id SERIAL PRIMARY KEY,
    work_order_id INT NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
    supply_id INT NOT NULL REFERENCES supplies(id),
    lot_id INT REFERENCES supply_lots(id),
    quantity NUMERIC(12,3) NOT NULL,
    unit_cost NUMERIC(12,4),
    currency currency_type,
    cost_clp NUMERIC(14,2),
    total_cost NUMERIC(14,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- CUBAS (Estado y Movimientos)
-- ============================================================

CREATE TABLE tank_contents (
    id SERIAL PRIMARY KEY,
    tank_id INT NOT NULL REFERENCES tanks(id) UNIQUE,
    wine_id INT REFERENCES wines(id),
    grape_variety_id INT REFERENCES grape_varieties(id),
    wine_type wine_type_enum,
    product_line_id INT REFERENCES product_lines(id),
    current_liters NUMERIC(12,0) NOT NULL DEFAULT 0,
    status tank_status DEFAULT 'Vacio',
    last_operation TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE tank_movements (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    source_tank_id INT REFERENCES tanks(id),
    dest_tank_id INT REFERENCES tanks(id),
    wine_id INT REFERENCES wines(id),
    liters NUMERIC(12,0) NOT NULL,
    operation TEXT,
    work_order_id INT REFERENCES work_orders(id),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- RECEPCION DE VINO/UVA
-- ============================================================

CREATE TABLE wine_receptions (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    grape_variety_id INT REFERENCES grape_varieties(id),
    wine_id INT REFERENCES wines(id),
    supplier TEXT,
    kilos NUMERIC(12,1),
    liters NUMERIC(12,0),
    brix NUMERIC(5,2),
    ph NUMERIC(4,2),
    acidity NUMERIC(6,3),
    dest_tank_id INT REFERENCES tanks(id),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INVENTARIO FISICO
-- ============================================================

CREATE TABLE inventory_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    name TEXT NOT NULL,
    is_finalized BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE inventory_snapshot_lines (
    id SERIAL PRIMARY KEY,
    snapshot_id INT NOT NULL REFERENCES inventory_snapshots(id) ON DELETE CASCADE,
    supply_id INT NOT NULL REFERENCES supplies(id),
    lot_id INT REFERENCES supply_lots(id),
    theoretical_stock NUMERIC(12,3),
    physical_stock NUMERIC(12,3),
    difference NUMERIC(12,3),
    pct_difference NUMERIC(8,4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TIPOS DE CAMBIO
-- ============================================================

CREATE TABLE currency_rates (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    usd_to_clp NUMERIC(10,2),
    eur_to_clp NUMERIC(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- CERTIFICACIONES BRC
-- ============================================================

CREATE TABLE brc_certifications (
    id SERIAL PRIMARY KEY,
    supply_id INT NOT NULL REFERENCES supplies(id),
    supplier_id INT NOT NULL REFERENCES suppliers(id),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(supply_id, supplier_id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDICES
-- ============================================================

CREATE INDEX idx_work_order_lines_supply ON work_order_lines(supply_id);
CREATE INDEX idx_work_order_lines_lot ON work_order_lines(lot_id);
CREATE INDEX idx_work_order_lines_wo ON work_order_lines(work_order_id);
CREATE INDEX idx_purchase_order_lines_supply ON purchase_order_lines(supply_id);
CREATE INDEX idx_purchase_order_lines_lot ON purchase_order_lines(lot_id);
CREATE INDEX idx_work_orders_date ON work_orders(date);
CREATE INDEX idx_work_orders_ot ON work_orders(ot_number);
CREATE INDEX idx_purchase_orders_date ON purchase_orders(date);
CREATE INDEX idx_supply_lots_supply ON supply_lots(supply_id);
CREATE INDEX idx_supply_lots_expiry ON supply_lots(expiry_date);
CREATE INDEX idx_tank_contents_tank ON tank_contents(tank_id);
CREATE INDEX idx_wines_code ON wines(code);
