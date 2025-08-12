import os
from app import create_app

# Por defecto usa ProdConfig cuando se ejecuta bajo WSGI
# (puedes cambiarlo a DevConfig si lo prefieres)
os.environ.setdefault("FLASK_CONFIG", "ProdConfig")

# Objeto WSGI que servirán Waitress/Gunicorn/etc.
app = create_app()
