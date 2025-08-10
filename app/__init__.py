import os
from flask import Flask
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from markupsafe import Markup, escape

# --- Selección de .env según FLASK_CONFIG ---
flask_config = os.getenv("FLASK_CONFIG", "DevConfig")
env_file = ".env.dev" if flask_config == "DevConfig" else ".env.prod"
if os.path.exists(env_file):
    load_dotenv(env_file)
    print(f"⚙️ Cargando variables desde {env_file}")
else:
    print(f"⚠️ No se encontró {env_file}, usando variables del sistema")

# --- Extensiones a nivel de módulo (para evitar import circular) ---
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = "auth.login"

# --- Config classes ---
from .config import DevConfig, ProdConfig  # noqa: E402


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Cargar configuración
    if flask_config == "ProdConfig":
        app.config.from_object(ProdConfig)
    else:
        app.config.from_object(DevConfig)

    # Crear carpeta instance si no existe
    os.makedirs(app.instance_path, exist_ok=True)

    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # ProxyFix (para IP real detrás de Nginx/ELB)
    if app.config.get("USE_PROXYFIX"):
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=app.config.get("PROXYFIX_X_FOR", 1),
            x_proto=app.config.get("PROXYFIX_X_PROTO", 1),
            x_host=app.config.get("PROXYFIX_X_HOST", 1),
            x_port=app.config.get("PROXYFIX_X_PORT", 1),
            x_prefix=app.config.get("PROXYFIX_X_PREFIX", 0),
        )

    # Filtro nl2br para Jinja
    def nl2br(value):
        if not value:
            return ""
        return Markup("<br>".join(escape(value).splitlines()))
    app.jinja_env.filters["nl2br"] = nl2br

    # Cargar modelos para el user_loader (evita import circular)
    from .models import User  # noqa: WPS433

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Blueprints
    from .main import main_bp
    from .services import services_bp
    from .classifieds import classifieds_bp
    from .admin import admin_bp
    from .auth import auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(services_bp, url_prefix="/services")
    app.register_blueprint(classifieds_bp)  # ya define /clasificados dentro
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(auth_bp)

    return app
