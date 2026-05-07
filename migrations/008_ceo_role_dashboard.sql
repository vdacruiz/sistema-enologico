-- Agregar permiso dashboard a roles existentes
UPDATE app_roles SET permissions = permissions || '{"dashboard": {"ver": true}}'::jsonb
WHERE name IN ('Administrador', 'Enologia');

-- Rol CEO: solo ve metricas (dashboard, stock, cubas)
INSERT INTO app_roles (name, description, permissions) VALUES
('CEO', 'Gerencia - vista de metricas y reportes, solo lectura', '{
    "dashboard": {"ver": true},
    "ordenes_trabajo": {},
    "ejecutar_ot": {},
    "recepcion_insumos": {},
    "recepcion_vino": {},
    "stock_insumos": {"ver": true},
    "stock_cubas": {"ver": true},
    "laboratorio": {"ver": true},
    "configuracion": {},
    "admin": {}
}');
