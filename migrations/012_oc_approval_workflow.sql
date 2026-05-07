-- ============================================================
-- FLUJO DE APROBACION DE OC
-- ============================================================

-- Campos de aprobacion en purchase_orders
ALTER TABLE purchase_orders ADD COLUMN created_by INT REFERENCES app_users(id);
ALTER TABLE purchase_orders ADD COLUMN approved_by_enology INT REFERENCES app_users(id);
ALTER TABLE purchase_orders ADD COLUMN approved_by_enology_at TIMESTAMPTZ;
ALTER TABLE purchase_orders ADD COLUMN approved_by_admin INT REFERENCES app_users(id);
ALTER TABLE purchase_orders ADD COLUMN approved_by_admin_at TIMESTAMPTZ;
ALTER TABLE purchase_orders ADD COLUMN rejected_by INT REFERENCES app_users(id);
ALTER TABLE purchase_orders ADD COLUMN rejected_at TIMESTAMPTZ;
ALTER TABLE purchase_orders ADD COLUMN rejection_notes TEXT;

-- Rol Creador de OC
INSERT INTO app_roles (name, description, permissions) VALUES
('Creador OC', 'Crea ordenes de compra para aprobacion', '{
    "dashboard": {},
    "ordenes_trabajo": {"ver": true},
    "ejecutar_ot": {},
    "recepcion_insumos": {"ver": true},
    "recepcion_vino": {"ver": true, "crear": true},
    "stock_insumos": {"ver": true},
    "stock_cubas": {"ver": true},
    "laboratorio": {},
    "configuracion": {},
    "admin": {}
}');

-- Agregar permiso de aprobar OC a Enologia y Administrador
UPDATE app_roles SET permissions = permissions || '{"aprobar_oc": {"ver": true, "aprobar_enologia": true}}'::jsonb
WHERE name = 'Enologia';

UPDATE app_roles SET permissions = permissions || '{"aprobar_oc": {"ver": true, "aprobar_enologia": true, "aprobar_admin": true}}'::jsonb
WHERE name = 'Administrador';
