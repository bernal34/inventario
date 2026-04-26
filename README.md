# Portal de Inventario de Equipos

Aplicación web en Flask para control de inventario con autenticación de usuarios.

## Funcionalidades

- Registro e inicio de sesión.
- Gestión básica de equipos (alta y listado).
- Persistencia en SQLite (`inventario.db`).

## Ejecutar en local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Luego abre: `http://127.0.0.1:5000`

## Usuario inicial

Registra tu usuario desde `/register` y entra al panel principal.
