# Directorio DMV

Directorio de negocios y **clasificados** para el grupo **COLOMBIANOS EN WASHINGTON–MARYLAND–VIRGINIA**.

- Stack: Flask 3, SQLAlchemy, Flask-Login, Bootstrap 5.3, DataTables, SweetAlert2, SQLite.
- Roles: superadmin, admin, basic, searcher.
- Funciones: registro con verificación, flujo de aprobación de servicios, búsqueda pública, dark mode, panel admin, logs.

## Rápido inicio
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
pip install -r requirements.txt
python run.py
