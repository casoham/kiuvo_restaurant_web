-- Kiuvo Restaurant — Esquema inicial para Supabase PostgreSQL
-- Ejecutar en SQL Editor o: supabase db push

-- ── Tipos enumerados ────────────────────────────────────────
CREATE TYPE user_role AS ENUM ('admin', 'staff', 'user');
CREATE TYPE order_status AS ENUM (
  'pending', 'confirmed', 'preparing', 'ready', 'delivered', 'cancelled'
);
CREATE TYPE menu_category AS ENUM (
  'appetizer', 'main_course', 'dessert', 'beverage', 'side', 'special'
);
CREATE TYPE reservation_status AS ENUM (
  'pending', 'confirmed', 'cancelled', 'completed'
);

-- ── Usuarios ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  username VARCHAR(100) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role user_role NOT NULL DEFAULT 'user',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  student_id VARCHAR(50) NOT NULL UNIQUE,
  birth_date DATE,
  sparks INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_student_id ON users (student_id);

-- ── Menú ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS menu_items (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  description TEXT,
  price DOUBLE PRECISION NOT NULL,
  category menu_category NOT NULL,
  image_url VARCHAR(500),
  is_available BOOLEAN NOT NULL DEFAULT TRUE,
  is_featured BOOLEAN NOT NULL DEFAULT FALSE,
  is_new BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_menu_items_category ON menu_items (category);
CREATE INDEX IF NOT EXISTS idx_menu_items_name ON menu_items (name);

-- ── Carritos ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS carts (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL UNIQUE REFERENCES users (id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cart_items (
  id BIGSERIAL PRIMARY KEY,
  cart_id BIGINT NOT NULL REFERENCES carts (id) ON DELETE CASCADE,
  menu_item_id BIGINT NOT NULL REFERENCES menu_items (id) ON DELETE CASCADE,
  quantity INTEGER NOT NULL DEFAULT 1
);

-- ── Órdenes ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  total_price DOUBLE PRECISION NOT NULL DEFAULT 0,
  status order_status NOT NULL DEFAULT 'pending',
  notes TEXT,
  scheduled_time TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders (user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);
CREATE INDEX IF NOT EXISTS idx_orders_scheduled_time ON orders (scheduled_time)
  WHERE scheduled_time IS NOT NULL;

CREATE TABLE IF NOT EXISTS order_items (
  id BIGSERIAL PRIMARY KEY,
  order_id BIGINT NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
  menu_item_id BIGINT REFERENCES menu_items (id) ON DELETE SET NULL,
  quantity INTEGER NOT NULL DEFAULT 1,
  unit_price DOUBLE PRECISION NOT NULL,
  item_name VARCHAR(200) NOT NULL
);

-- ── Reservas ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reservations (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  scheduled_time TIMESTAMPTZ NOT NULL,
  people_count INTEGER NOT NULL,
  status reservation_status NOT NULL DEFAULT 'pending',
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reservations_user_id ON reservations (user_id);

-- ── Row Level Security (defensa en profundidad) ─────────────
-- El backend FastAPI usa conexión directa (service role / postgres).
-- RLS bloquea acceso vía Data API con claves anon/authenticated.

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE menu_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE carts ENABLE ROW LEVEL SECURITY;
ALTER TABLE cart_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE reservations ENABLE ROW LEVEL SECURITY;

-- Menú: lectura pública de items disponibles
CREATE POLICY menu_items_read_available ON menu_items
  FOR SELECT
  USING (is_available = TRUE);

-- Usuarios autenticados (auth.uid() vía Supabase Auth en el futuro):
-- Por ahora sin políticas INSERT/UPDATE para anon — solo backend.

-- Política de lectura propia si se integra Supabase Auth (app_metadata.role)
-- CREATE POLICY users_read_own ON users FOR SELECT USING (auth.uid()::text = id::text);

-- Revocar acceso directo anon por defecto (opcional, refuerzo)
REVOKE ALL ON users FROM anon, authenticated;
REVOKE ALL ON carts FROM anon, authenticated;
REVOKE ALL ON cart_items FROM anon, authenticated;
REVOKE ALL ON orders FROM anon, authenticated;
REVOKE ALL ON order_items FROM anon, authenticated;
REVOKE ALL ON reservations FROM anon, authenticated;
-- menu_items: SELECT permitido vía policy anterior

-- ── Trigger updated_at ──────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER menu_items_updated_at
  BEFORE UPDATE ON menu_items
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER carts_updated_at
  BEFORE UPDATE ON carts
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER orders_updated_at
  BEFORE UPDATE ON orders
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
