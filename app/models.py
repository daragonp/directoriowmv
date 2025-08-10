# app/models.py
from datetime import datetime, date
from enum import Enum
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login_manager


class ServiceStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)

    # Perfil
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    phone = db.Column(db.String(50))
    address = db.Column(db.String(255))
    avatar_url = db.Column(db.String(500))

    # Seguridad / estado
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user")  # user | admin | superadmin
    is_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(10))
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones (lazy='dynamic' para poder encadenar queries)
    services = db.relationship(
        "Service",
        backref="owner",
        lazy="dynamic",
        foreign_keys="Service.owner_id",
    )
    classifieds = db.relationship(
        "Classified",
        backref="owner",
        lazy="dynamic",
        foreign_keys="Classified.owner_id",
    )

    def set_password(self, raw: str):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    def __repr__(self):
        return f"<User {self.id} {self.email} ({self.role})>"


class Service(db.Model):
    __tablename__ = "service"

    id = db.Column(db.Integer, primary_key=True)

    # Contenido
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    website = db.Column(db.String(255))
    social = db.Column(db.String(255))
    address = db.Column(db.String(255))

    # Propietario
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Contacto (se rellenan automáticamente con datos del owner para básicos)
    contact_name = db.Column(db.String(150))
    contact_email = db.Column(db.String(255))
    contact_phone = db.Column(db.String(50))

    # Estado
    status = db.Column(db.String(20), default=ServiceStatus.PENDING.value)
    is_active = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Auditoría de flujo
    approved_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    approved_at = db.Column(db.DateTime)
    rejected_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    rejected_at = db.Column(db.DateTime)

    def __repr__(self):
        return f"<Service {self.id} {self.title} [{self.status}]>"


class Classified(db.Model):
    __tablename__ = "classified"

    id = db.Column(db.Integer, primary_key=True)

    # Contenido
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # Fechas de vigencia (opcionales)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    # Propietario
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Estado
    status = db.Column(db.String(20), default=ServiceStatus.PENDING.value)
    is_active = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Auditoría de flujo (⚠️ NUEVO)
    approved_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    approved_at = db.Column(db.DateTime)
    rejected_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    rejected_at = db.Column(db.DateTime)

    def is_currently_valid(self, today: date | None = None) -> bool:
        """Útil por si lo quieres usar en queries/plantillas."""
        today = today or date.today()
        if self.start_date and self.start_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return True

    def __repr__(self):
        return f"<Classified {self.id} {self.title} [{self.status}]>"


class LoginLog(db.Model):
    __tablename__ = "login_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    ip = db.Column(db.String(100))
    user_agent = db.Column(db.String(500))
    location = db.Column(db.String(255))  # si luego integras GeoIP
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="login_logs")


class ActivityLog(db.Model):
    __tablename__ = "activity_log"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    action = db.Column(db.String(50))           # e.g., "create", "approve", "reject", etc.
    entity = db.Column(db.String(50))           # e.g., "Service", "Classified", "User"
    entity_id = db.Column(db.Integer)
    meta = db.Column(db.Text)                   # json/extra info si la necesitas
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    actor = db.relationship("User", backref="activities")

    def __repr__(self):
        return f"<ActivityLog {self.id} {self.action} {self.entity}#{self.entity_id}>"
