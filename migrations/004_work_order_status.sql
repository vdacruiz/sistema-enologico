-- Agregar estados y prioridad a ordenes de trabajo
ALTER TABLE work_orders ADD COLUMN status TEXT NOT NULL DEFAULT 'Pendiente';
ALTER TABLE work_orders ADD COLUMN priority TEXT NOT NULL DEFAULT 'Normal';
ALTER TABLE work_orders ADD COLUMN observations TEXT;
ALTER TABLE work_orders ADD COLUMN started_at TIMESTAMPTZ;
ALTER TABLE work_orders ADD COLUMN completed_at TIMESTAMPTZ;

-- Lineas: cantidad planificada vs cantidad real
ALTER TABLE work_order_lines ADD COLUMN planned_quantity NUMERIC(12,3);
ALTER TABLE work_order_lines ADD COLUMN observations TEXT;

-- Indice para filtrar por estado y operario
CREATE INDEX idx_work_orders_status ON work_orders(status);
CREATE INDEX idx_work_orders_worker ON work_orders(worker_id);
