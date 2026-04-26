# Portal de Inventario de Equipos

Aplicación web en Flask para control de inventario de equipos con autenticación de usuarios.

## Funcionalidades

- Registro e inicio de sesión con contraseñas hasheadas (Werkzeug).
- CRUD completo de equipos: alta, edición y eliminación.
- Listado con búsqueda por nombre/serie/área y filtro por estado.
- Persistencia en SQLite (`inventario.db`) creado automáticamente al arrancar.

## Requisitos

- Python 3.10+

## Ejecutar en local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Opcional: define una clave secreta estable para mantener la sesión entre reinicios
export INVENTARIO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"

python app.py
```

Luego abre: `http://127.0.0.1:5000`

## Variables de entorno

| Variable                  | Descripción                                                                  |
| ------------------------- | ---------------------------------------------------------------------------- |
| `INVENTARIO_SECRET_KEY`   | Clave para firmar la sesión. Si no se define, se genera una aleatoria al inicio (las sesiones se invalidan al reiniciar). |

Hay un archivo `.env.example` de referencia.

## Primer uso

1. Ve a `/register` y crea tu usuario.
2. Inicia sesión en `/login`.
3. Desde el panel principal podrás dar de alta, editar, filtrar y eliminar equipos.

## Estados de equipo

`Disponible`, `En uso`, `Mantenimiento`, `Baja`.
