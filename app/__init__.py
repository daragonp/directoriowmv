from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from .config import Config
from datetime import datetime

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Confía en los encabezados del proxy/CDN para obtener IP real, protocolo, host, etc.
    # Ajusta x_for si tienes múltiples proxies encadenados.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"

    @app.template_filter('nl2br')
    def nl2br(value):
        return value.replace("\n", "<br>\n") if value else ""

    @app.context_processor
    def inject_globals():
        return dict(
            APP_NAME="Directorio DMV",
            APP_ICON_URL="/static/icon.svg",
            CURRENT_YEAR=datetime.utcnow().year
        )

    with app.app_context():
        from . import models  # importa modelos para que SQLAlchemy los conozca
        db.create_all()

    # Importa y registra blueprints DESPUÉS de init_app para evitar imports circulares
    from .auth import auth_bp
    from .services import services_bp
    from .admin import admin_bp
    from .main import main_bp
    from .classifieds import classifieds_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(services_bp, url_prefix="/services")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(main_bp)
    app.register_blueprint(classifieds_bp, url_prefix="/clasificados")

    return app
