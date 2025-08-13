# scripts/init_db.py
"""
Recrea la base de datos y crea todas las tablas de app.models.
Opcionalmente siembra un superadmin inicial.

Uso (Windows):
(.venv) > python scripts/init_db.py

Variables de entorno opcionales:
  SEED_SUPERADMIN_NAME=Super Admin
  SEED_SUPERADMIN_EMAIL=admin@example.com
  SEED_SUPERADMIN_PHONE=555-0000
  SEED_SUPERADMIN_PASSWORD=ChangeMe123!
"""

import os
import sys

# Asegura que el proyecto esté en sys.path
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Fuerza configuración de desarrollo por defecto (cámbialo si quieres Prod)
os.environ.setdefault("FLASK_CONFIG", "DevConfig")

from app import create_app, db  # noqa: E402
from app.models import (      # noqa: E402
    User, Service, Classified, LoginLog, ActivityLog, ServiceStatus
)

def seed_superadmin():
    """Crea un superadmin si no existe."""
    name = os.getenv("SEED_SUPERADMIN_NAME", "Colombianos en WMV - Administrador")
    email = os.getenv("SEED_SUPERADMIN_EMAIL", "superadmin@local").lower()
    phone = os.getenv("SEED_SUPERADMIN_PHONE", "2401000000")
    password = os.getenv("SEED_SUPERADMIN_PASSWORD", "Jacobo2505*+")

    existing = User.query.filter_by(email=email).first()
    if existing:
        print(f"[seed] Ya existe superadmin con email {email} (id={existing.id})")
        return existing

    u = User(
        name=name,
        email=email,
        phone=phone,
        role="superadmin",
        is_verified=True,
        is_deleted=False,
    )
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    print(f"[seed] Superadmin creado: {email} / (id={u.id})")
    return u

def maybe_remove_sqlite():
    """Si la base es SQLite (instance/app.db), elimínala para recrear limpia."""
    from flask import current_app
    uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if uri.startswith("sqlite:///"):
        # sqlite: ruta absoluta detrás del esquema
        abs_path = uri.replace("sqlite:///", "", 1)
        try:
            if os.path.exists(abs_path):
                os.remove(abs_path)
                print(f"[init] SQLite eliminado: {abs_path}")
        except Exception as e:
            print(f"[warn] No se pudo eliminar {abs_path}: {e}")

def main():
    app = create_app()
    with app.app_context():
        # Si es SQLite local, eliminar archivo para recrear
        maybe_remove_sqlite()

        print("[init] Creando tablas…")
        db.drop_all()
        db.create_all()
        db.session.commit()
        print("[init] Tablas creadas correctamente.")

        # Semilla mínima (opcional)
        seed_superadmin()

        print("[ok] Base de datos lista.")

if __name__ == "__main__":
    main()
