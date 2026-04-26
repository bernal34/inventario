from __future__ import annotations

import os
import secrets
from functools import wraps
from typing import Any, Callable

import psycopg
from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from psycopg.rows import dict_row
from werkzeug.security import check_password_hash, generate_password_hash

EQUIPMENT_STATUSES = ("Disponible", "En uso", "Mantenimiento", "Baja")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("INVENTARIO_SECRET_KEY") or secrets.token_hex(32)


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL no está configurada. Define la cadena de conexión "
            "Postgres (por ejemplo, la del pooler de Supabase)."
        )
    return url


def get_db() -> psycopg.Connection:
    if "db" not in g:
        g.db = psycopg.connect(_database_url(), row_factory=dict_row, autocommit=False)
    return g.db


@app.teardown_appcontext
def close_db(_: Any) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS equipment (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    serial_number TEXT NOT NULL,
    area TEXT NOT NULL,
    status TEXT NOT NULL,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"""


@app.cli.command("init-db")
def init_db_command() -> None:
    """Crea las tablas en la base de datos configurada en DATABASE_URL."""
    with psycopg.connect(_database_url()) as conn:
        conn.execute(SCHEMA_SQL)
    print("Tablas creadas/verificadas correctamente.")


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
@login_required
def index() -> str:
    query = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()

    sql = (
        "SELECT id, name, serial_number, area, status, created_at, updated_at "
        "FROM equipment WHERE 1=1"
    )
    params: list[Any] = []

    if query:
        sql += " AND (name ILIKE %s OR serial_number ILIKE %s OR area ILIKE %s)"
        like = f"%{query}%"
        params.extend([like, like, like])

    if status_filter and status_filter in EQUIPMENT_STATUSES:
        sql += " AND status = %s"
        params.append(status_filter)

    sql += " ORDER BY updated_at DESC, id DESC"

    rows = get_db().execute(sql, params).fetchall()
    return render_template(
        "dashboard.html",
        equipment=rows,
        username=session.get("username"),
        statuses=EQUIPMENT_STATUSES,
        query=query,
        status_filter=status_filter,
    )


@app.route("/register", methods=["GET", "POST"])
def register() -> str:
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Usuario y contraseña son obligatorios.", "error")
            return render_template("register.html")

        if len(password) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "error")
            return render_template("register.html")

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, generate_password_hash(password)),
            )
            db.commit()
            flash("Usuario creado con éxito. Inicia sesión.", "success")
            return redirect(url_for("login"))
        except psycopg.errors.UniqueViolation:
            db.rollback()
            flash("El usuario ya existe.", "error")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login() -> str:
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT id, username, password_hash FROM users WHERE username = %s",
            (username,),
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Credenciales inválidas.", "error")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout() -> str:
    session.clear()
    return redirect(url_for("login"))


def _read_equipment_form() -> tuple[str, str, str, str]:
    name = request.form.get("name", "").strip()
    serial_number = request.form.get("serial_number", "").strip()
    area = request.form.get("area", "").strip()
    status = request.form.get("status", "Disponible").strip()
    return name, serial_number, area, status


@app.route("/equipment/add", methods=["POST"])
@login_required
def add_equipment() -> str:
    name, serial_number, area, status = _read_equipment_form()

    if not all([name, serial_number, area, status]):
        flash("Todos los campos del equipo son obligatorios.", "error")
        return redirect(url_for("index"))

    if status not in EQUIPMENT_STATUSES:
        flash("Estado de equipo no válido.", "error")
        return redirect(url_for("index"))

    db = get_db()
    db.execute(
        """
        INSERT INTO equipment (name, serial_number, area, status, created_by)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (name, serial_number, area, status, session["user_id"]),
    )
    db.commit()
    flash("Equipo agregado correctamente.", "success")
    return redirect(url_for("index"))


@app.route("/equipment/<int:equipment_id>/edit", methods=["GET", "POST"])
@login_required
def edit_equipment(equipment_id: int) -> str:
    db = get_db()
    item = db.execute(
        "SELECT id, name, serial_number, area, status FROM equipment WHERE id = %s",
        (equipment_id,),
    ).fetchone()

    if item is None:
        flash("Equipo no encontrado.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        name, serial_number, area, status = _read_equipment_form()

        if not all([name, serial_number, area, status]):
            flash("Todos los campos del equipo son obligatorios.", "error")
            return render_template(
                "edit_equipment.html", item=item, statuses=EQUIPMENT_STATUSES
            )

        if status not in EQUIPMENT_STATUSES:
            flash("Estado de equipo no válido.", "error")
            return render_template(
                "edit_equipment.html", item=item, statuses=EQUIPMENT_STATUSES
            )

        db.execute(
            """
            UPDATE equipment
               SET name = %s, serial_number = %s, area = %s, status = %s,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = %s
            """,
            (name, serial_number, area, status, equipment_id),
        )
        db.commit()
        flash("Equipo actualizado.", "success")
        return redirect(url_for("index"))

    return render_template("edit_equipment.html", item=item, statuses=EQUIPMENT_STATUSES)


@app.route("/equipment/<int:equipment_id>/delete", methods=["POST"])
@login_required
def delete_equipment(equipment_id: int) -> str:
    db = get_db()
    result = db.execute("DELETE FROM equipment WHERE id = %s", (equipment_id,))
    db.commit()

    if result.rowcount == 0:
        flash("Equipo no encontrado.", "error")
    else:
        flash("Equipo eliminado.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
