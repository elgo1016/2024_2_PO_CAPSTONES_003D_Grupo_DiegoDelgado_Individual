PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS negocios (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    descripcion TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sagas (
    id INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('cliente', 'admin'))
);
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY,
    usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id),
    nombre TEXT NOT NULL,
    telefono TEXT NOT NULL DEFAULT '',
    saga_id INTEGER REFERENCES sagas(id)
);
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY,
    negocio_id INTEGER NOT NULL REFERENCES negocios(id),
    saga_id INTEGER NOT NULL REFERENCES sagas(id),
    nombre TEXT NOT NULL,
    precio INTEGER NOT NULL CHECK (precio > 0),
    stock INTEGER NOT NULL CHECK (stock >= 0),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);
CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    fecha TEXT NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('pendiente_pago', 'cancelado')),
    referencia_demo TEXT UNIQUE CHECK (referencia_demo IN ('A', 'B', 'C')),
    clave_solicitud TEXT NOT NULL,
    huella_solicitud TEXT NOT NULL,
    UNIQUE (cliente_id, clave_solicitud)
);
CREATE TABLE IF NOT EXISTS detalle_pedido (
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id),
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario INTEGER NOT NULL CHECK (precio_unitario > 0),
    PRIMARY KEY (pedido_id, producto_id)
);
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY,
    negocio_id INTEGER NOT NULL REFERENCES negocios(id),
    nombre TEXT NOT NULL,
    fecha TEXT NOT NULL,
    ubicacion TEXT NOT NULL,
    detalle TEXT NOT NULL DEFAULT '',
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);
CREATE TABLE IF NOT EXISTS publicaciones_instagram (
    id INTEGER PRIMARY KEY,
    negocio_id INTEGER NOT NULL REFERENCES negocios(id),
    titulo TEXT NOT NULL,
    enlace TEXT NOT NULL,
    descripcion TEXT NOT NULL DEFAULT '',
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    creado_en TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sesiones (
    token_hash TEXT PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    vence INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_pedidos_cliente ON pedidos(cliente_id);
CREATE INDEX IF NOT EXISTS ix_sesiones_vence ON sesiones(vence);

CREATE TABLE IF NOT EXISTS boletin (
 email TEXT PRIMARY KEY COLLATE NOCASE,
 codigo TEXT NOT NULL UNIQUE,
 vence INTEGER NOT NULL,
 consentido_en TEXT NOT NULL,
 ultimo_envio INTEGER NOT NULL,
 pedido_id INTEGER UNIQUE REFERENCES pedidos(id)
);
CREATE TABLE IF NOT EXISTS descuentos_pedido (
 pedido_id INTEGER PRIMARY KEY REFERENCES pedidos(id),
 monto INTEGER NOT NULL CHECK(monto >= 0)
);

CREATE TABLE IF NOT EXISTS imagenes_producto (
 producto_id INTEGER PRIMARY KEY REFERENCES productos(id) ON DELETE CASCADE,
 contenido BLOB NOT NULL,
 version TEXT NOT NULL
);
