
# Directorio DMV (Flask + SQLite)

Directorio de negocios/servicios para el grupo **COLOMBIANOS EN WASHINGTON–MARYLAND–VIRGINIA**.

## Requisitos
- Python 3.10+

## Instalación
```bash
python -m venv .venv
. .venv/bin/activate  # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## Acceso
- Ir a http://localhost:5000
- Regístrate, verifica tu email (código se imprime en consola en modo demo).
- Para crear un superadmin, usa SQLite y cambia el campo `role` del usuario a `superadmin`.
