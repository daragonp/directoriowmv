from datetime import datetime
from enum import Enum
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login_manager

class Role(Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    BASIC = "basic"
    SEARCHER = "searcher"

class ServiceStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(50))
    address = db.Column(db.String(200))
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default=Role.BASIC.value, nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(6), nullable=True)
    avatar_url = db.Column(db.String(255))
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Servicios creados/propiedad del usuario
    services = db.relationship(
        "Service",
        backref="owner",
        lazy=True,
        foreign_keys="Service.owner_id",
    )

    # Servicios que este usuario aprobó (si es admin/superadmin)
    approved_services = db.relationship(
        "Service",
        backref="approver",
        lazy=True,
        foreign_keys="Service.approved_by",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    person_name = db.Column(db.String(120), nullable=False)
    business_name = db.Column(db.String(140))
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    address = db.Column(db.String(200))
    social_link = db.Column(db.String(200))
    status = db.Column(db.String(20), default=ServiceStatus.PENDING.value, nullable=False)
    is_active = db.Column(db.Boolean, default=False)  # requires approval; active toggle
    is_deleted = db.Column(db.Boolean, default=False)
    approved_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LoginLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    ip = db.Column(db.String(64))
    user_agent = db.Column(db.String(255))
    location = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    action = db.Column(db.String(50))  # create_service, update_service, approve_service, etc.
    entity = db.Column(db.String(50))  # Service/User
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
