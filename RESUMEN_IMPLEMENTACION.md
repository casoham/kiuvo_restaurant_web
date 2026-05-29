# Kiuvo Restaurant — Resumen de implementación

Proyecto FastAPI + SQLAlchemy + Supabase PostgreSQL, listo para producción.

## Contenido del ZIP

- Código fuente (`api/`, `cli/`, `src/`, `config/`)
- Schema Supabase + RLS: `supabase/migrations/20260101000000_initial_schema.sql`
- Configuración: `.env.example`, `requirements.txt`, `Procfile`, `render.yaml`
- Tests: `tests/` (81 pruebas)
- Documentación: `README.md`

**No incluido:** `venv/`, `.env` (credenciales), cachés.

## Instalación local

```powershell
cd kiuvo_restaurant_app
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m cli.main --seed
python run_api.py
```

Docs: http://127.0.0.1:8000/docs

## Supabase (producción)

1. Crear proyecto en https://supabase.com
2. Ejecutar en SQL Editor: `supabase/migrations/20260101000000_initial_schema.sql`
3. Configurar `.env`:

```env
DATABASE_URL=postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
APP_ENV=production
SECRET_KEY=...
JWT_SECRET_KEY=...
```

4. Verificar: `GET /health`

## Endpoints principales

| Método | Ruta |
|--------|------|
| POST | `/api/v1/auth/register/client` |
| POST | `/api/v1/auth/register/staff` |
| POST | `/api/v1/auth/forgot-password` |
| POST | `/api/v1/auth/reset-password` |
| GET | `/api/v1/orders/slots` |

## Reglas de negocio

- Email cliente: `nombre.apellido@keyinstitute.edu.sv`
- Carnet: `Key_xxxxxx` (6 caracteres alfanuméricos)
- Contraseña: mín. 6, mayúscula y minúscula
- Pedidos programados: 6:00–17:00, máx. 15 por franja de 15 min
- Sparks al entregar: `int(total_price) * 2`

## Usuarios seed

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| admin | Admin123 | admin |
| maria_lopez | Staff123 | staff |
| juan_perez | User1234 | user |

## Tests

```powershell
python -m pytest tests/ -v
```

## Despliegue

- **Render:** usar `render.yaml`
- **Heroku:** `Procfile` → `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
