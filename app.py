from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "inventario.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "cambia-esta-clave-secreta"


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_: Any) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            serial_number TEXT NOT NULL,
            area TEXT NOT NULL,
            status TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        );
        """
    )
    db.commit()


@app.before_request
def load_logged_in_user() -> None:
    init_db()


@app.route("/")
def index() -> str:
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    db = get_db()
    rows = db.execute(
        "SELECT id, name, serial_number, area, status, created_at FROM equipment ORDER BY created_at DESC"
    ).fetchall()
    return render_template("dashboard.html", equipment=rows, username=session.get("username"))


@app.route("/register", methods=["GET", "POST"])
def register() -> str:
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Usuario y contraseña son obligatorios.", "error")
            return render_template("register.html")

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            db.commit()
            flash("Usuario creado con éxito. Inicia sesión.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("El usuario ya existe.", "error")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login() -> str:
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

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


@app.route("/equipment/add", methods=["POST"])
def add_equipment() -> str:
    if "user_id" not in session:
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()
    serial_number = request.form.get("serial_number", "").strip()
    area = request.form.get("area", "").strip()
    status = request.form.get("status", "Disponible").strip()

    if not all([name, serial_number, area, status]):
        flash("Todos los campos del equipo son obligatorios.", "error")
        return redirect(url_for("index"))

    db = get_db()
    db.execute(
        """
        INSERT INTO equipment (name, serial_number, area, status, created_by)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, serial_number, area, status, session["user_id"]),
    )
    db.commit()
    flash("Equipo agregado correctamente.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
