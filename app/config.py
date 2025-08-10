
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Email (for demo, we'll print to console)
    MAIL_FROM = os.environ.get("MAIL_FROM", "no-reply@example.com")
    # Toggle console email vs SMTP later
    USE_CONSOLE_EMAIL = True
    UPLOAD_FOLDER = "app/static/uploads/avatars"
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
