
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from .config import Config
import os

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    @app.template_filter('nl2br')
    def nl2br(value):
        return value.replace("\n", "<br>\n") if value else ""


    from .main import main_bp
    app.register_blueprint(main_bp)


    with app.app_context():
        from . import models  # ensure models are registered
        db.create_all()

    # blueprints
    from .auth import auth_bp
    from .services import services_bp
    from .admin import admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(services_bp, url_prefix="/services")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # login view for @login_required redirects
    login_manager.login_view = "auth.login"

    @app.context_processor
    def inject_globals():
        return dict(APP_NAME="Directorio DMV", APP_ICON_URL="/static/icon.svg")

    return app
