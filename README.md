# Portal de Inventario de Equipos

Aplicación web en Flask para control de inventario de equipos con autenticación
de usuarios. Lista para desplegar como **función serverless en Vercel** usando
**Supabase (Postgres)** como base de datos.

## Funcionalidades

- Registro e inicio de sesión con contraseñas hasheadas (Werkzeug).
- CRUD completo de equipos: alta, edición y eliminación.
- Listado con búsqueda por nombre/serie/área y filtro por estado.
- Persistencia en Postgres a través de `psycopg`.

## Requisitos

- Python 3.10+
- Una instancia Postgres accesible (recomendado: Supabase free tier).

## Variables de entorno

| Variable                  | Descripción                                                                  |
| ------------------------- | ---------------------------------------------------------------------------- |
| `DATABASE_URL`            | Cadena de conexión Postgres. En Supabase usa la URL del *Transaction pooler* (puerto 6543). |
| `INVENTARIO_SECRET_KEY`   | Clave para firmar la sesión. Si no se define, se genera una aleatoria al inicio (las sesiones se invalidan al reiniciar). |

Hay un `.env.example` con el formato esperado.

## Ejecutar en local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL="postgresql://..."
export INVENTARIO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"

# Una sola vez, crea las tablas:
flask --app app init-db

python app.py
```

Luego abre: `http://127.0.0.1:5000`

## Deploy en Vercel + Supabase

### 1. Crear la base en Supabase

1. Entra a https://supabase.com y crea un proyecto (free tier).
2. **SQL Editor** → pega el contenido de `schema.sql` y ejecútalo.
3. **Settings → Database → Connection string → Transaction pooler** (puerto
   `6543`). Cópiala — esa es tu `DATABASE_URL`. Sustituye `[YOUR-PASSWORD]`
   por la contraseña que definiste al crear el proyecto.

> **Importante:** usa siempre la URL del *pooler*, no la directa. Las
> funciones serverless abren conexiones nuevas en cada invocación y agotarían
> rápido el cupo del Postgres directo.

### 2. Conectar el repo a Vercel

1. https://vercel.com → *Add New… → Project* → importa este repo de GitHub.
2. Framework preset: **Other** (Vercel detecta `vercel.json` automáticamente).
3. **Environment Variables** — añade:
   - `DATABASE_URL` con el valor del pooler de Supabase.
   - `INVENTARIO_SECRET_KEY` con una cadena aleatoria larga.
4. *Deploy*. Tras 1–2 minutos tendrás una URL `https://<proyecto>.vercel.app`.

### 3. Primer uso

1. Abre `/register` y crea tu usuario.
2. Inicia sesión en `/login`.
3. Desde el panel principal podrás dar de alta, editar, filtrar y eliminar equipos.

## Estructura

```
app.py              # Flask app (rutas, auth, CRUD)
vercel.json         # Configuración del runtime Python en Vercel
schema.sql          # DDL de Postgres (ejecutar 1 vez en Supabase)
requirements.txt    # Flask, Werkzeug, psycopg[binary]
templates/          # Jinja2 (base, login, register, dashboard, edit_equipment)
static/styles.css
```

## Estados de equipo

`Disponible`, `En uso`, `Mantenimiento`, `Baja`.

## Notas sobre el modelo serverless

- En Vercel cada request puede iniciar una instancia "fría" — la primera vez
  tarda algo más (~1-2 s) por arrancar Python e importar dependencias.
- No hay disco persistente: toda persistencia va a Supabase.
- Las sesiones de Flask viajan en cookies firmadas con `INVENTARIO_SECRET_KEY`,
  por eso es importante fijarla y mantenerla estable entre deploys.
