# app/utils.py
import os
import random
import string
import ipaddress
from typing import Optional
from flask import request
from flask_login import current_user
from .models import db, ActivityLog

# -------------------------
# Utilidades generales
# -------------------------

def gen_code(length: int = 6) -> str:
    """Genera un código alfanumérico en mayúsculas."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))

def log_action(user, action: str, entity: str, entity_id: int, detail: str = ""):
    """Guarda una línea de auditoría en ActivityLog."""
    try:
        entry = ActivityLog(
            user_id=user.id if user else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
            detail=detail,
            ip=get_client_ip(request) or request.remote_addr if request else None,
            user_agent=request.headers.get("User-Agent") if request else None
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()

def allowed_image(filename, app) -> bool:
    """Valida extensión de imagen según ALLOWED_IMAGE_EXTENSIONS en Config."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    allowed = app.config.get("ALLOWED_IMAGE_EXTENSIONS", set())
    return ext in allowed

# -------------------------
# IP real del cliente
# -------------------------

def _pick_public_ip(ip_candidates):
    """Elige la primera IP pública válida de la lista (prefiere cliente en X-Forwarded-For)."""
    for raw in ip_candidates:
        if not raw:
            continue
        ip = raw.strip()
        # Si es una lista "a, b, c", el primer elemento suele ser el cliente original
        if "," in ip:
            ip = ip.split(",")[0].strip()
        try:
            ip_obj = ipaddress.ip_address(ip)
            if not (ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved or ip_obj.is_link_local):
                return ip
        except ValueError:
            continue
    # Si no hay pública, devuelve la primera válida
    for raw in ip_candidates:
        if not raw:
            continue
        ip = raw.split(",")[0].strip()
        try:
            ipaddress.ip_address(ip)
            return ip
        except ValueError:
            continue
    return None

def get_client_ip(req) -> Optional[str]:
    """
    Obtiene la IP real del cliente considerando proxies/CDN.
    Orden: CF-Connecting-IP > X-Forwarded-For > X-Real-IP > remote_addr
    Requiere ProxyFix en app para asegurar cabeceras de confianza.
    """
    headers = req.headers if req else {}
    candidates = [
        headers.get("CF-Connecting-IP"),
        headers.get("X-Forwarded-For"),
        headers.get("X-Real-IP"),
        req.remote_addr if req else None,
    ]
    return _pick_public_ip(candidates)
