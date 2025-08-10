import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

# Carpeta de estáticos y avatares
STATIC_DIR = os.path.join(BASE_DIR, "app", "static")
AVATAR_UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads", "avatars")
os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True)

def _normalize_sqlite_url(url: str) -> str:
    """
    Si DATABASE_URL es sqlite y la ruta es relativa (p.ej. sqlite:///instance/app.db),
    conviértela a absoluta bajo BASE_DIR/instance para evitar 'unable to open database file'.
    """
    if not url:
        return f"sqlite:///{os.path.join(INSTANCE_DIR, 'app.db')}"
    if not url.lower().startswith("sqlite"):
        return url
    raw = url[len("sqlite:///"):]
    if os.path.isabs(raw):
        return f"sqlite:///{raw.replace(os.sep, '/')}"
    abs_path = os.path.abspath(os.path.join(BASE_DIR, raw))
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    return f"sqlite:///{abs_path.replace(os.sep, '/')}"

class BaseConfig:
    # SECURITY
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-please-change-me")
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # DB
    _RAW_DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(INSTANCE_DIR, 'app.db')}")
    SQLALCHEMY_DATABASE_URI = _normalize_sqlite_url(_RAW_DB_URL)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # MAIL
    MAIL_ENABLED = os.getenv("MAIL_ENABLED", "false").lower() == "true"
    MAIL_FROM = os.getenv("MAIL_FROM", "no-reply@example.com")
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"

    # VERIFICATION
    VERIFY_TOKEN_MAX_AGE = int(os.getenv("VERIFY_TOKEN_MAX_AGE", "86400"))  # 24h
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5000")

    # Proxy / headers reales (cuando hay Nginx/Load Balancer delante)
    USE_PROXYFIX = os.getenv("USE_PROXYFIX", "false").lower() == "true"
    PROXYFIX_X_FOR = int(os.getenv("PROXYFIX_X_FOR", "1"))
    PROXYFIX_X_PROTO = int(os.getenv("PROXYFIX_X_PROTO", "1"))
    PROXYFIX_X_HOST = int(os.getenv("PROXYFIX_X_HOST", "1"))
    PROXYFIX_X_PORT = int(os.getenv("PROXYFIX_X_PORT", "1"))
    PROXYFIX_X_PREFIX = int(os.getenv("PROXYFIX_X_PREFIX", "0"))

    # Avatares
    AVATAR_UPLOAD_DIR = AVATAR_UPLOAD_DIR
    AVATAR_MAX_SIZE = 2 * 1024 * 1024  # 2MB
    AVATAR_ALLOWED_EXT = {"png", "jpg", "jpeg", "webp"}

class DevConfig(BaseConfig):
    DEBUG = True

class ProdConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"  # o "None" si usas cookies cross-site bajo HTTPS
