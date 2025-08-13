import os
import json
import random
import string
import ipaddress
import secrets
from typing import Optional
from flask import request, current_app
from werkzeug.utils import secure_filename
from .models import db, ActivityLog

# -------------------------
# Utilidades generales
# -------------------------

def gen_code(length: int = 6) -> str:
    """Genera un código alfanumérico en mayúsculas."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))

def allowed_image(filename) -> bool:
    """Valida extensión de imagen según configuración."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    allowed_cfg = current_app.config.get("ALLOWED_IMAGE_EXTENSIONS")
    avatar_allowed = current_app.config.get("AVATAR_ALLOWED_EXT")
    allowed = set()
    if isinstance(allowed_cfg, (set, list, tuple)): 
        allowed |= set(allowed_cfg)
    if isinstance(avatar_allowed, (set, list, tuple)): 
        allowed |= set(avatar_allowed)
    if not allowed:
        allowed = {"png", "jpg", "jpeg", "webp", "gif"}
    return ext in allowed

def save_avatar(file_storage, user_id: int) -> Optional[str]:
    """
    Guarda el avatar en /static/uploads/avatars y devuelve la URL pública (/static/...).
    Devuelve None si no se guardó (extensión/tamaño inválidos, etc.).
    """
    if not file_storage or file_storage.filename == "":
        return None

    # Directorio destino (con valor por defecto robusto)
    upload_dir = current_app.config.get("AVATAR_UPLOAD_DIR")
    if not upload_dir:
        upload_dir = os.path.join(current_app.root_path, "static", "uploads", "avatars")

    max_size = int(current_app.config.get("AVATAR_MAX_SIZE", 2 * 1024 * 1024))

    # Tamaño: usa content_length si está disponible; si no, calcula con stream
    size = getattr(file_storage, "content_length", None)
    if not size:
        try:
            pos = file_storage.stream.tell()
        except Exception:
            pos = 0
        try:
            file_storage.stream.seek(0, os.SEEK_END)
            size = file_storage.stream.tell()
            file_storage.stream.seek(pos)
        except Exception:
            size = 0

    if size and size > max_size:
        return None

    if not allowed_image(file_storage.filename):
        return None

    fname = secure_filename(file_storage.filename)
    ext = fname.rsplit(".", 1)[-1].lower()
    rand = secrets.token_hex(6)
    new_name = f"user{user_id}_{rand}.{ext}"
    abs_path = os.path.join(upload_dir, new_name)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    file_storage.save(abs_path)

    # URL pública (no usamos url_for aquí para no exigir contexto)
    #return f"/static/uploads/avatars/{new_name}"
# ... dentro de save_avatar(...)
    return f"/media/avatars/{new_name}"


# -------------------------
# Auditoría / logs
# -------------------------

def log_action(user, action: str, entity: str, entity_id: int, detail: str = ""):
    """
    Guarda una línea de auditoría en ActivityLog.
    Compatibilidad:
      - Si el modelo tiene (actor_id, meta), guardamos JSON con ip/ua/detalle.
      - Si no, intentamos con (user_id, detail, ip, user_agent).
    """
    ip = get_client_ip(request) or (request.remote_addr if request else None)
    ua = request.headers.get("User-Agent") if request else None
    meta = {"detail": detail, "ip": ip, "user_agent": ua}

    try:
        # Modelo moderno (actor_id + meta JSON string)
        entry = ActivityLog(
            actor_id=(user.id if user else None),
            action=action,
            entity=entity,
            entity_id=entity_id,
            meta=json.dumps(meta, ensure_ascii=False)
        )
        db.session.add(entry)
        db.session.commit()
        return
    except TypeError:
        # Compatibilidad con modelo antiguo
        try:
            entry = ActivityLog(
                user_id=(user.id if user else None),
                action=action,
                entity=entity,
                entity_id=entity_id,
                detail=detail,
                ip=ip,
                user_agent=ua
            )
            db.session.add(entry)
            db.session.commit()
            return
        except Exception:
            db.session.rollback()
    except Exception:
        db.session.rollback()

# -------------------------
# IP real del cliente
# -------------------------

def _pick_public_ip(ip_candidates):
    """Elige la primera IP pública válida de la lista (prefiere cliente en X-Forwarded-For)."""
    for raw in ip_candidates:
        if not raw:
            continue
        ip = raw.strip()
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
    Orden: CF-Connecting-IP > X-Forwarded-For > X-Real-IP > remote_addr.
    (Activa ProxyFix en producción para fiarte de cabeceras de tu proxy.)
    """
    headers = req.headers if req else {}
    candidates = [
        headers.get("CF-Connecting-IP"),
        headers.get("X-Forwarded-For"),
        headers.get("X-Real-IP"),
        req.remote_addr if req else None,
    ]
    return _pick_public_ip(candidates)
