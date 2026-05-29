-- ============================================================================
-- 🍽️ BASE DE DATOS: Do Eat — Restaurant App
-- ============================================================================
-- Motor:       MySQL 8.0+
-- Charset:     utf8mb4 (soporte completo de Unicode / emojis)
-- Collation:   utf8mb4_unicode_ci (comparaciones case-insensitive)
-- Normalización: Tercera Forma Normal (3NF)
--
-- Diseño basado en el diagrama entidad-relación manuscrito del proyecto.
-- Adaptado para producción con mejores prácticas de MySQL.
-- ============================================================================

-- ────────────────────────────────────────────────────────────────────────────
-- 0. CREACIÓN Y SELECCIÓN DE LA BASE DE DATOS
-- ────────────────────────────────────────────────────────────────────────────

DROP DATABASE IF EXISTS do_eat_restaurant;

CREATE DATABASE do_eat_restaurant
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE do_eat_restaurant;

-- ────────────────────────────────────────────────────────────────────────────
-- 1. TABLA: categorias
-- ────────────────────────────────────────────────────────────────────────────
-- Almacena las categorías de productos del menú.
-- Relación: Una categoría tiene muchos productos (1:N → productos).
-- Decisión: Tabla independiente en lugar de ENUM para permitir que
--           el administrador agregue/modifique categorías sin alterar el schema.
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE categorias (
    id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    nombre      VARCHAR(100)    NOT NULL,
    descripcion TEXT            NULL,
    activa      BOOLEAN         NOT NULL DEFAULT TRUE
        COMMENT 'Permite desactivar categorías sin eliminarlas (soft-delete)',
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    -- Evita categorías duplicadas
    CONSTRAINT uq_categorias_nombre UNIQUE (nombre)

) ENGINE=InnoDB
  COMMENT='Categorías del menú (entrada, plato fuerte, postre, bebida, etc.)';

-- ────────────────────────────────────────────────────────────────────────────
-- 2. TABLA: usuarios
-- ────────────────────────────────────────────────────────────────────────────
-- Almacena los usuarios del sistema: clientes y administradores/staff.
-- Decisión: Se usa un campo `rol` con ENUM en lugar de un booleano `es_admin`
--           para soportar tres niveles de acceso (admin, staff, user),
--           lo cual es más flexible y ya está implementado en la API.
-- Decisión: `carnet` (student_id) es único e indexado porque es el
--           identificador principal del estudiante en la universidad.
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE usuarios (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    nombre              VARCHAR(100)    NOT NULL,
    apellido            VARCHAR(100)    NOT NULL,
    email               VARCHAR(255)    NOT NULL,
    username            VARCHAR(100)    NOT NULL,
    password_hash       VARCHAR(255)    NOT NULL
        COMMENT 'Hash bcrypt de la contraseña — nunca almacenar en texto plano',
    rol                 ENUM('admin', 'staff', 'user')
                        NOT NULL DEFAULT 'user'
        COMMENT 'Nivel de acceso: admin (CRUD total), staff (gestión menú/órdenes), user (cliente)',
    activo              BOOLEAN         NOT NULL DEFAULT TRUE
        COMMENT 'Desactivar cuenta sin eliminar datos (soft-delete)',

    -- Campos universitarios
    carnet              VARCHAR(50)     NOT NULL
        COMMENT 'Carnet universitario único del estudiante (ej: UNI-2024-001)',
    fecha_nacimiento    DATE            NULL
        COMMENT 'Utilizada para descuento automático de cumpleaños (20%)',

    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    -- Restricciones de unicidad
    CONSTRAINT uq_usuarios_email    UNIQUE (email),
    CONSTRAINT uq_usuarios_username UNIQUE (username),
    CONSTRAINT uq_usuarios_carnet   UNIQUE (carnet),

    -- Índices para búsquedas frecuentes
    INDEX idx_usuarios_rol        (rol),
    INDEX idx_usuarios_activo     (activo)

) ENGINE=InnoDB
  COMMENT='Usuarios del sistema (clientes universitarios y personal)';

-- ────────────────────────────────────────────────────────────────────────────
-- 3. TABLA: productos
-- ────────────────────────────────────────────────────────────────────────────
-- Almacena los productos/platos del menú.
-- Relación: Cada producto pertenece a una categoría (N:1 → categorias).
-- Decisión: Se incluyen flags `disponible`, `destacado` y `es_nuevo`
--           para control de visibilidad en el menú sin eliminación.
-- Nota del diseño: "Productos incluirá tanto individuales como combos/menús"
--     → El campo `es_combo` permite diferenciar productos individuales de combos.
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE productos (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    categoria_id    INT UNSIGNED    NOT NULL
        COMMENT 'FK → categorias.id — cada producto pertenece a exactamente una categoría',
    nombre          VARCHAR(200)    NOT NULL,
    descripcion     TEXT            NULL,
    precio          DECIMAL(10,2)   NOT NULL
        COMMENT 'DECIMAL para precisión monetaria — evita errores de redondeo de FLOAT',
    imagen_url      VARCHAR(500)    NULL
        COMMENT 'URL de imagen del producto (preparado para cloud storage)',
    disponible      BOOLEAN         NOT NULL DEFAULT TRUE
        COMMENT 'Controla si el producto aparece en el menú activo',
    destacado       BOOLEAN         NOT NULL DEFAULT FALSE
        COMMENT 'Productos destacados/recomendados que aparecen primero',
    es_nuevo        BOOLEAN         NOT NULL DEFAULT FALSE,
    es_combo        BOOLEAN         NOT NULL DEFAULT FALSE
        COMMENT 'Diferencia productos individuales de combos/menús',

    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    -- FK: Producto → Categoría (1:N)
    CONSTRAINT fk_productos_categoria
        FOREIGN KEY (categoria_id) REFERENCES categorias(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
        -- RESTRICT: No permitir eliminar una categoría que tenga productos asociados

    -- Índices
    INDEX idx_productos_categoria   (categoria_id),
    INDEX idx_productos_nombre      (nombre),
    INDEX idx_productos_disponible  (disponible),

    -- Validación: precio debe ser positivo
    CONSTRAINT chk_productos_precio CHECK (precio > 0)

) ENGINE=InnoDB
  COMMENT='Productos/platos del menú del restaurante';

-- ────────────────────────────────────────────────────────────────────────────
-- 4. TABLA: descuentos
-- ────────────────────────────────────────────────────────────────────────────
-- Almacena los diferentes tipos de descuentos disponibles.
-- Relación: Descuentos ↔ Productos es N:M (tabla intermedia: descuento_producto).
-- Decisión: Tabla separada para descuentos permite gestionar promociones
--           de forma independiente y reutilizable (ej: "2x1", "20% cumpleaños",
--           "descuento de temporada", etc.).
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE descuentos (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    nombre          VARCHAR(150)    NOT NULL
        COMMENT 'Nombre descriptivo del descuento (ej: "Descuento cumpleaños")',
    descripcion     TEXT            NULL,
    porcentaje      DECIMAL(5,2)    NOT NULL
        COMMENT 'Porcentaje de descuento a aplicar (ej: 20.00 = 20%)',
    activo          BOOLEAN         NOT NULL DEFAULT TRUE,
    fecha_inicio    DATETIME        NULL
        COMMENT 'Inicio de vigencia — NULL = sin fecha de inicio (siempre válido)',
    fecha_fin       DATETIME        NULL
        COMMENT 'Fin de vigencia — NULL = sin fecha de expiración',

    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    -- Validaciones
    CONSTRAINT chk_descuentos_porcentaje CHECK (porcentaje > 0 AND porcentaje <= 100),
    CONSTRAINT chk_descuentos_fechas     CHECK (fecha_fin IS NULL OR fecha_inicio IS NULL OR fecha_fin >= fecha_inicio)

) ENGINE=InnoDB
  COMMENT='Descuentos y promociones aplicables a productos';

-- ────────────────────────────────────────────────────────────────────────────
-- 5. TABLA: descuento_producto (Tabla intermedia N:M)
-- ────────────────────────────────────────────────────────────────────────────
-- Tabla de unión para la relación muchos-a-muchos entre descuentos y productos.
-- Un descuento puede aplicarse a muchos productos, y un producto puede tener
-- múltiples descuentos activos simultáneamente.
-- Decisión: Se usa clave compuesta (descuento_id, producto_id) para evitar
--           duplicados y optimizar JOINs.
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE descuento_producto (
    descuento_id    INT UNSIGNED    NOT NULL,
    producto_id     INT UNSIGNED    NOT NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Clave primaria compuesta: garantiza unicidad de la combinación
    PRIMARY KEY (descuento_id, producto_id),

    -- FK: → descuentos
    CONSTRAINT fk_dp_descuento
        FOREIGN KEY (descuento_id) REFERENCES descuentos(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
        -- CASCADE: Si se elimina un descuento, se eliminan sus asociaciones

    -- FK: → productos
    CONSTRAINT fk_dp_producto
        FOREIGN KEY (producto_id) REFERENCES productos(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
        -- CASCADE: Si se elimina un producto, se eliminan sus asociaciones de descuento

    -- Índice inverso para búsquedas "¿qué descuentos tiene este producto?"
    INDEX idx_dp_producto (producto_id)

) ENGINE=InnoDB
  COMMENT='Relación N:M entre descuentos y productos';

-- ────────────────────────────────────────────────────────────────────────────
-- 6. TABLA: pedidos
-- ────────────────────────────────────────────────────────────────────────────
-- Almacena las órdenes/pedidos realizados por los usuarios.
-- Relación: Un usuario tiene muchos pedidos (1:N).
-- Relación: Un pedido tiene un ticket único (1:1 → ticket_unico).
-- Decisión: `estado` como ENUM con flujo definido:
--           pending → confirmed → preparing → ready → delivered
--           En cualquier momento → cancelled
-- Decisión: `precio_total` se almacena como campo desnormalizado para
--           rendimiento en consultas de analytics (evita SUM en cada query).
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE pedidos (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    usuario_id      INT UNSIGNED    NOT NULL
        COMMENT 'FK → usuarios.id — usuario que realizó el pedido',
    fecha           DATE            NOT NULL DEFAULT (CURRENT_DATE)
        COMMENT 'Fecha del pedido (separada de hora para facilitar reportes diarios)',
    hora            TIME            NOT NULL DEFAULT (CURRENT_TIME)
        COMMENT 'Hora del pedido (separada para consultas por rango horario)',
    precio_total    DECIMAL(10,2)   NOT NULL DEFAULT 0.00
        COMMENT 'Total calculado del pedido (campo desnormalizado para rendimiento)',
    estado          ENUM('pending', 'confirmed', 'preparing', 'ready', 'delivered', 'cancelled')
                    NOT NULL DEFAULT 'pending'
        COMMENT 'Flujo: pending→confirmed→preparing→ready→delivered | →cancelled',
    notas           TEXT            NULL
        COMMENT 'Instrucciones especiales del cliente',
    hora_programada DATETIME        NULL
        COMMENT 'Para pedidos diferidos: hora a la que se desea recoger',

    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    -- FK: Pedido → Usuario (N:1)
    CONSTRAINT fk_pedidos_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
        -- CASCADE: Si se elimina un usuario, se eliminan sus pedidos

    -- Índices para consultas frecuentes
    INDEX idx_pedidos_usuario    (usuario_id),
    INDEX idx_pedidos_estado     (estado),
    INDEX idx_pedidos_fecha      (fecha),

    -- Validación
    CONSTRAINT chk_pedidos_precio CHECK (precio_total >= 0)

) ENGINE=InnoDB
  COMMENT='Pedidos/órdenes realizados por los usuarios';

-- ────────────────────────────────────────────────────────────────────────────
-- 7. TABLA: detalles_pedido
-- ────────────────────────────────────────────────────────────────────────────
-- Líneas de detalle de cada pedido (qué productos se pidieron).
-- Relación: Un pedido tiene muchos detalles (1:N) — ver nota abajo.
-- Relación: Cada detalle referencia un producto (N:1 → productos).
--
-- ⚠️ CORRECCIÓN respecto al diseño original:
--   El diagrama indica "Pedido → Detalles Pedido: 1:1", pero esto debería
--   ser 1:N (un pedido puede contener múltiples productos). Se corrige aquí
--   porque un pedido con un solo producto sería una limitación severa.
--
-- Decisión: Se almacena `nombre_producto` y `precio_unitario` como snapshot
--           al momento del pedido, para que el historial sea inmutable incluso
--           si el producto cambia de nombre o precio después.
-- Decisión: `descuento_aplicado` almacena el porcentaje de descuento que se
--           aplicó en el momento de la compra (0.00 si no hubo descuento).
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE detalles_pedido (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    pedido_id           INT UNSIGNED    NOT NULL
        COMMENT 'FK → pedidos.id — pedido al que pertenece este detalle',
    producto_id         INT UNSIGNED    NULL
        COMMENT 'FK → productos.id — NULL si el producto fue eliminado del catálogo',
    nombre_producto     VARCHAR(200)    NOT NULL
        COMMENT 'Snapshot del nombre del producto al momento del pedido (inmutable)',
    cantidad            INT UNSIGNED    NOT NULL DEFAULT 1,
    precio_unitario     DECIMAL(10,2)   NOT NULL
        COMMENT 'Snapshot del precio unitario al momento del pedido',
    descuento_aplicado  DECIMAL(5,2)    NOT NULL DEFAULT 0.00
        COMMENT 'Porcentaje de descuento aplicado (ej: 20.00 = 20%)',
    subtotal            DECIMAL(10,2)   GENERATED ALWAYS AS (
                            cantidad * precio_unitario * (1 - descuento_aplicado / 100)
                        ) STORED
        COMMENT 'Columna calculada: cantidad × precio × (1 - descuento%) — STORED para rendimiento',

    PRIMARY KEY (id),

    -- FK: Detalle → Pedido (N:1)
    CONSTRAINT fk_detalles_pedido
        FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    -- FK: Detalle → Producto (N:1)
    CONSTRAINT fk_detalles_producto
        FOREIGN KEY (producto_id) REFERENCES productos(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
        -- SET NULL: Si se elimina un producto, el historial se mantiene
        -- con nombre_producto y precio_unitario como snapshot

    -- Índices
    INDEX idx_detalles_pedido    (pedido_id),
    INDEX idx_detalles_producto  (producto_id),

    -- Validaciones
    CONSTRAINT chk_detalles_cantidad    CHECK (cantidad > 0),
    CONSTRAINT chk_detalles_precio      CHECK (precio_unitario > 0),
    CONSTRAINT chk_detalles_descuento   CHECK (descuento_aplicado >= 0 AND descuento_aplicado <= 100)

) ENGINE=InnoDB
  COMMENT='Líneas de detalle de cada pedido (productos, cantidades, precios)';

-- ────────────────────────────────────────────────────────────────────────────
-- 8. TABLA: tickets
-- ────────────────────────────────────────────────────────────────────────────
-- Ticket único asociado a cada pedido (comprobante / recibo).
-- Relación: Un pedido tiene exactamente un ticket (1:1).
-- Decisión: `codigo_qr` almacena el contenido/datos para generar el QR
--           (no la imagen en sí). Puede ser un UUID o hash único.
-- Decisión: `numero_ticket` es un identificador legible para el cliente
--           (ej: "TCK-20260519-0042").
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE tickets (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    pedido_id       INT UNSIGNED    NOT NULL
        COMMENT 'FK → pedidos.id — relación 1:1 con el pedido',
    numero_ticket   VARCHAR(50)     NOT NULL
        COMMENT 'Número legible del ticket (ej: TCK-20260519-0042)',
    codigo_qr       VARCHAR(500)    NOT NULL
        COMMENT 'Contenido del código QR (UUID o hash para escaneo)',

    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    -- 1:1 con pedidos — cada pedido tiene exactamente un ticket
    CONSTRAINT uq_tickets_pedido    UNIQUE (pedido_id),
    CONSTRAINT uq_tickets_numero    UNIQUE (numero_ticket),
    CONSTRAINT uq_tickets_qr        UNIQUE (codigo_qr),

    -- FK: Ticket → Pedido (1:1)
    CONSTRAINT fk_tickets_pedido
        FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE

) ENGINE=InnoDB
  COMMENT='Ticket único / comprobante de cada pedido con código QR';

-- ────────────────────────────────────────────────────────────────────────────
-- 9. TABLA: carritos (Existente en el proyecto, no en el diseño manuscrito)
-- ────────────────────────────────────────────────────────────────────────────
-- Carrito de compras — uno por usuario (1:1).
-- Decisión: Se mantiene del diseño actual del proyecto porque es necesario
--           para la funcionalidad de agregar productos antes de confirmar un pedido.
-- No estaba en el diseño manuscrito, pero es necesario para el flujo completo.
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE carritos (
    id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    usuario_id  INT UNSIGNED    NOT NULL
        COMMENT 'FK → usuarios.id — un carrito por usuario (1:1)',

    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    -- 1:1 con usuarios
    CONSTRAINT uq_carritos_usuario UNIQUE (usuario_id),

    -- FK: Carrito → Usuario (1:1)
    CONSTRAINT fk_carritos_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE

) ENGINE=InnoDB
  COMMENT='Carrito de compras — uno por usuario';

-- ────────────────────────────────────────────────────────────────────────────
-- 10. TABLA: carrito_items
-- ────────────────────────────────────────────────────────────────────────────
-- Líneas de detalle del carrito (productos agregados).
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE carrito_items (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    carrito_id      INT UNSIGNED    NOT NULL
        COMMENT 'FK → carritos.id',
    producto_id     INT UNSIGNED    NOT NULL
        COMMENT 'FK → productos.id',
    cantidad        INT UNSIGNED    NOT NULL DEFAULT 1,

    PRIMARY KEY (id),

    -- FK: Item → Carrito
    CONSTRAINT fk_citems_carrito
        FOREIGN KEY (carrito_id) REFERENCES carritos(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    -- FK: Item → Producto
    CONSTRAINT fk_citems_producto
        FOREIGN KEY (producto_id) REFERENCES productos(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    -- Un producto solo puede aparecer una vez por carrito (se actualiza la cantidad)
    CONSTRAINT uq_carrito_producto UNIQUE (carrito_id, producto_id),

    -- Validación
    CONSTRAINT chk_citems_cantidad CHECK (cantidad > 0)

) ENGINE=InnoDB
  COMMENT='Productos dentro del carrito de compras';

-- ────────────────────────────────────────────────────────────────────────────
-- 11. TABLA: reservaciones (Existente en el proyecto, no en el diseño manuscrito)
-- ────────────────────────────────────────────────────────────────────────────
-- Reservaciones de mesa/espacio en el restaurante.
-- Se mantiene del proyecto actual por completitud funcional.
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE reservaciones (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    usuario_id      INT UNSIGNED    NOT NULL
        COMMENT 'FK → usuarios.id — usuario que hizo la reserva',
    fecha_hora      DATETIME        NOT NULL
        COMMENT 'Fecha y hora de la reservación',
    num_personas    INT UNSIGNED    NOT NULL
        COMMENT 'Cantidad de personas',
    estado          ENUM('pending', 'confirmed', 'cancelled', 'completed')
                    NOT NULL DEFAULT 'pending',
    notas           TEXT            NULL,

    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    -- FK: Reservación → Usuario (N:1)
    CONSTRAINT fk_reservaciones_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    -- Índices
    INDEX idx_reservaciones_usuario     (usuario_id),
    INDEX idx_reservaciones_fecha       (fecha_hora),
    INDEX idx_reservaciones_estado      (estado),

    -- Validación
    CONSTRAINT chk_reservaciones_personas CHECK (num_personas > 0)

) ENGINE=InnoDB
  COMMENT='Reservaciones de mesa/espacio en el restaurante';


-- ============================================================================
-- DATOS DE PRUEBA (SEED)
-- ============================================================================
-- Los mismos usuarios de prueba que usa el proyecto actualmente.
-- Las contraseñas son hashes bcrypt (generados por la aplicación en runtime).
-- Aquí se insertan como placeholder — la app los reemplaza al hacer seed.
-- ============================================================================

-- Categorías iniciales
INSERT INTO categorias (nombre, descripcion) VALUES
    ('Entrada',          'Aperitivos y entradas'),
    ('Plato fuerte',     'Platos principales'),
    ('Postre',           'Postres y dulces'),
    ('Bebida',           'Bebidas frías y calientes'),
    ('Acompañamiento',   'Guarniciones y acompañamientos'),
    ('Especial del día', 'Platos especiales rotativos');

-- Descuentos base
INSERT INTO descuentos (nombre, descripcion, porcentaje, activo) VALUES
    ('Descuento cumpleaños',    'Descuento automático del 20% el día de tu cumpleaños',  20.00, TRUE),
    ('Descuento estudiante',    'Descuento especial para estudiantes regulares',          10.00, TRUE),
    ('Promoción de temporada',  'Descuento por temporada en productos seleccionados',     15.00, FALSE);


-- ============================================================================
-- VISTAS ÚTILES (OPCIONAL — para analytics y consultas frecuentes)
-- ============================================================================

-- ────────────────────────────────────────────────────────────────────────────
-- Vista: Resumen de pedidos con información del usuario
-- ────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW v_resumen_pedidos AS
SELECT
    p.id                AS pedido_id,
    p.fecha,
    p.hora,
    p.estado,
    p.precio_total,
    u.id                AS usuario_id,
    u.username,
    u.nombre,
    u.apellido,
    u.carnet,
    t.numero_ticket,
    t.codigo_qr
FROM pedidos p
    INNER JOIN usuarios u   ON p.usuario_id = u.id
    LEFT  JOIN tickets t    ON p.id = t.pedido_id;

-- ────────────────────────────────────────────────────────────────────────────
-- Vista: Productos con su categoría y descuentos activos
-- ────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW v_productos_completos AS
SELECT
    p.id                AS producto_id,
    p.nombre            AS producto,
    p.descripcion,
    p.precio,
    p.disponible,
    p.destacado,
    p.es_combo,
    c.nombre            AS categoria,
    GROUP_CONCAT(
        CONCAT(d.nombre, ' (', d.porcentaje, '%)')
        SEPARATOR ', '
    )                   AS descuentos_activos
FROM productos p
    INNER JOIN categorias c         ON p.categoria_id = c.id
    LEFT  JOIN descuento_producto dp ON p.id = dp.producto_id
    LEFT  JOIN descuentos d          ON dp.descuento_id = d.id AND d.activo = TRUE
GROUP BY p.id, p.nombre, p.descripcion, p.precio, p.disponible, p.destacado, p.es_combo, c.nombre;
