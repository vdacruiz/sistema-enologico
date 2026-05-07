-- ============================================================
-- AUTENTICACION - Roles y Usuarios
-- ============================================================

CREATE TABLE app_roles (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    permissions JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE app_users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role_id INT NOT NULL REFERENCES app_roles(id),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_app_users_username ON app_users(username);
CREATE INDEX idx_app_users_role ON app_users(role_id);

-- ============================================================
-- ROLES INICIALES
-- ============================================================

INSERT INTO app_roles (name, description, permissions) VALUES
('Administrador', 'Acceso total al sistema, gestion de usuarios y roles', '{
    "ordenes_trabajo": {"ver": true, "crear": true, "editar": true, "eliminar": true},
    "ejecutar_ot": {"ver": true, "ejecutar": true},
    "recepcion_insumos": {"ver": true, "crear": true},
    "recepcion_vino": {"ver": true, "crear": true},
    "stock_insumos": {"ver": true},
    "stock_cubas": {"ver": true},
    "laboratorio": {"ver": true, "crear": true},
    "configuracion": {"ver": true, "editar": true},
    "admin": {"ver": true, "crear": true, "editar": true, "eliminar": true}
}'),
('Enologia', 'Enologo o asistente - crea OTs, recepciones, ve stock y lab', '{
    "ordenes_trabajo": {"ver": true, "crear": true, "editar": true, "eliminar": true},
    "ejecutar_ot": {"ver": true},
    "recepcion_insumos": {"ver": true, "crear": true},
    "recepcion_vino": {"ver": true, "crear": true},
    "stock_insumos": {"ver": true},
    "stock_cubas": {"ver": true},
    "laboratorio": {"ver": true},
    "configuracion": {"ver": true, "editar": true},
    "admin": {}
}'),
('Laboratorio', 'Analista de laboratorio - analisis y consulta de stock', '{
    "ordenes_trabajo": {"ver": true},
    "ejecutar_ot": {},
    "recepcion_insumos": {"ver": true},
    "recepcion_vino": {"ver": true},
    "stock_insumos": {"ver": true},
    "stock_cubas": {"ver": true},
    "laboratorio": {"ver": true, "crear": true},
    "configuracion": {},
    "admin": {}
}'),
('Operario', 'Operario de bodega - ejecuta OTs y recibe insumos', '{
    "ordenes_trabajo": {"ver": true},
    "ejecutar_ot": {"ver": true, "ejecutar": true},
    "recepcion_insumos": {"ver": true, "crear": true},
    "recepcion_vino": {},
    "stock_insumos": {"ver": true},
    "stock_cubas": {"ver": true},
    "laboratorio": {},
    "configuracion": {},
    "admin": {}
}');

-- ============================================================
-- USUARIO ADMINISTRADOR INICIAL
-- ============================================================

INSERT INTO app_users (username, password, full_name, role_id)
VALUES ('admin', 'vda2024', 'Cristian Ruiz', (SELECT id FROM app_roles WHERE name = 'Administrador'));
