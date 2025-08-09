
import random, string
from functools import wraps
from flask import request
from .models import ActivityLog
from . import db

def gen_code(n=6):
    return ''.join(random.choices(string.digits, k=n))

def log_action(actor, action, entity, entity_id, details=""):
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    entry = ActivityLog(actor_id=actor.id if actor else None, action=action, entity=entity, entity_id=entity_id, details=details, ip=ip)
    db.session.add(entry)
    db.session.commit()

def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from flask_login import current_user
            if not current_user.is_authenticated or current_user.role not in roles:
                from flask import abort
                return abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
