-- Agregar tipo de OT: Insumos (uso de insumos) o Movimiento (movimiento de vino entre cubas)
ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS ot_type TEXT DEFAULT 'Insumos';
