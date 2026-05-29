# Kiuvo Restaurant API

API REST y CLI para el sistema de restaurante universitario **Do Eat / Kiuvo**, construido con **FastAPI**, **SQLAlchemy** y **Supabase PostgreSQL**.

## Estructura del proyecto

```
kiuvo_restaurant_app/
├── api/                    # Capa REST FastAPI
│   ├── main.py             # Aplicación y health check
│   ├── dependencies.py     # Inyección de BD y JWT
│   ├── exception_handlers.py
│   └── routers/            # auth, users, menu, cart, orders, analytics
├── cli/                    # Interfaz de línea de comandos (Rich)
│   ├── main.py             # Menú principal y seed
│   ├── auth_cli.py         # Login, registro bifurcado, recuperación
│   └── order_cli.py        # Pedidos y selección de slots
├── config/
│   ├── settings.py         # Variables de entorno
│   └── database.py         # SQLAlchemy engine (SQLite / Postgres)
├── src/
│   ├── models/             # ORM (users, menu, orders, cart, reservations)
│   ├── repositories/       # Acceso a datos
│   ├── services/           # Lógica de negocio
│   ├── dto/schemas.py      # Pydantic request/response
│   ├── integrations/       # Cliente Supabase
│   └── utils/              # JWT, seguridad, excepciones
├── supabase/migrations/    # Schema SQL + RLS para Supabase
├── scripts/                # Migraciones locales (ej. sparks)
├── tests/                  # pytest (servicios + API)
├── .env.example
├── requirements.txt
├── Procfile                # Heroku / Render
├── render.yaml             # Blueprint Render
└── run_api.py              # Arranque de la API
```

## Requisitos

- Python 3.11+ (probado en 3.13)
- Cuenta [Supabase](https://supabase.com) (producción)
- Opcional: SMTP para correos de recuperación de contraseña

## Instalación local

```bash
# 1. Clonar y entrar al directorio
cd kiuvo_restaurant_app

# 2. Entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Variables de entorno
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS
# Editar .env con tus valores

# 5. Inicializar BD local (SQLite por defecto)
python -m cli.main --seed

# 6. API
python run_api.py
# Docs: http://127.0.0.1:8000/docs
```

## Configuración Supabase

### 1. Crear proyecto

1. [supabase.com](https://supabase.com) → New project.
2. En **Settings → Database**, copia la **Connection string** (modo **Transaction**, puerto **6543**).
3. En **Settings → API**, copia `URL`, `anon key` y `service_role key`.

### 2. Aplicar schema

En el **SQL Editor** de Supabase, ejecuta el contenido de:

`supabase/migrations/20260101000000_initial_schema.sql`

O con Supabase CLI:

```bash
supabase link --project-ref YOUR_PROJECT_REF
supabase db push
```

### 3. Variables en `.env`

```env
DATABASE_URL=postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
APP_ENV=production
APP_DEBUG=false
SECRET_KEY=genera-un-secreto-largo
JWT_SECRET_KEY=otro-secreto-largo
```

### 4. Verificar

```bash
python run_api.py
curl http://127.0.0.1:8000/health
```

La respuesta incluye el estado de conexión Supabase.

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/auth/register/client` | Registro cliente (email institucional) |
| POST | `/api/v1/auth/register/staff` | Registro staff |
| POST | `/api/v1/auth/login` | JWT access + refresh |
| POST | `/api/v1/auth/forgot-password` | Código de recuperación |
| POST | `/api/v1/auth/reset-password` | Restablecer contraseña |
| GET | `/api/v1/orders/slots` | Franjas horarias y cupo |
| GET | `/health` | Estado del servicio |

Documentación interactiva: `/docs`

## Reglas de negocio

- **Email cliente:** `nombre.apellido@keyinstitute.edu.sv`
- **Carnet / ID:** formato `Key_xxxxxx` (6 caracteres alfanuméricos)
- **Contraseña:** mínimo 6 caracteres, mayúscula y minúscula
- **Pedidos programados:** 6:00–17:00, máximo **15** pedidos por franja de 15 min
- **Sparks:** al marcar orden como `delivered` → `int(total_price) * 2`

## Despliegue

### Render.com

1. Conecta el repositorio en [Render](https://render.com).
2. Usa `render.yaml` o crea un **Web Service** Python.
3. **Build:** `pip install -r requirements.txt`
4. **Start:** `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
5. Configura las variables de `.env.example` en el panel de Render.

### Heroku

```bash
heroku create kiuvo-restaurant-api
heroku config:set DATABASE_URL=... SUPABASE_URL=... SECRET_KEY=...
git push heroku main
```

El `Procfile` ya define el comando web.

## Tests

```bash
python -m pytest tests/ -v
```

## CLI

```bash
python -m cli.main          # Menú interactivo
python -m cli.main --seed   # Datos de prueba
```

Usuarios seed (contraseñas con mayúscula/minúscula):

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| admin | Admin123 | admin |
| maria_lopez | Staff123 | staff |
| juan_perez | User1234 | user |

## Licencia

Proyecto académico — Key Institute.
