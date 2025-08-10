# app/admin.py
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from .models import db, User, Service, ServiceStatus, LoginLog, Classified, ActivityLog
from .utils import log_action

admin_bp = Blueprint("admin", __name__)

def _require_admin():
    return current_user.is_authenticated and current_user.role in ("admin", "superadmin")

@admin_bp.before_request
def _check_admin():
    if request.endpoint and request.endpoint.startswith("admin.") and not _require_admin():
        return ("Forbidden", 403)

def _is_super():
    return current_user.is_authenticated and current_user.role == "superadmin"

# ------------------------
# Dashboard (sin gráficas)
# ------------------------
@admin_bp.route("/dashboard")
@login_required
def dashboard():
    if not _require_admin():
        return ("Forbidden", 403)

    now = datetime.utcnow()
    today = now.date()

    total_users = db.session.query(User).filter_by(is_deleted=False).count()
    active_users_30d = (
        db.session.query(LoginLog.user_id)
        .filter(LoginLog.created_at >= now - timedelta(days=30))
        .distinct()
        .count()
    )
    services_pending = db.session.query(Service).filter_by(status=ServiceStatus.PENDING.value, is_deleted=False).count()
    services_active = db.session.query(Service).filter_by(status=ServiceStatus.APPROVED.value, is_active=True, is_deleted=False).count()
    classifieds_pending = db.session.query(Classified).filter_by(status=ServiceStatus.PENDING.value, is_deleted=False).count()
    classifieds_active = db.session.query(Classified).filter_by(status=ServiceStatus.APPROVED.value, is_active=True, is_deleted=False).count()
    logins_today = db.session.query(LoginLog).filter(LoginLog.created_at >= datetime.combine(today, datetime.min.time())).count()

    return render_template(
        "admin/dashboard.html",
        kpis=dict(
            total_users=total_users,
            active_users_30d=active_users_30d,
            services_pending=services_pending,
            services_active=services_active,
            classifieds_pending=classifieds_pending,
            classifieds_active=classifieds_active,
            logins_today=logins_today,
        ),
    )

# ------------------------
# Servicios
# ------------------------
@admin_bp.route("/services")
@login_required
def admin_services():
    if not _require_admin():
        return ("Forbidden", 403)
    status = request.args.get("status")
    q = Service.query.filter_by(is_deleted=False)
    if status:
        q = q.filter_by(status=status)
    items = q.order_by(Service.created_at.desc()).all()

    users_map = {u.id: u.name for u in User.query.with_entities(User.id, User.name).all()}

    return render_template("admin/services.html", items=items, ServiceStatus=ServiceStatus, users_map=users_map)

@admin_bp.route("/services/approve/<int:service_id>", methods=["POST"])
@login_required
def approve_service(service_id):
    if not _require_admin():
        return ("Forbidden", 403)
    s = Service.query.get_or_404(service_id)

    # Si fue rechazado, solo quien lo rechazó puede aprobar; superadmin puede siempre
    if s.status == ServiceStatus.REJECTED.value and not _is_super():
        if s.rejected_by and s.rejected_by != current_user.id:
            flash("Solo el administrador que rechazó este servicio puede volver a aprobarlo.", "warning")
            return redirect(url_for("admin.admin_services"))

    s.status = ServiceStatus.APPROVED.value
    s.is_active = True
    s.approved_by = current_user.id
    s.approved_at = datetime.utcnow()
    db.session.commit()
    log_action(current_user, "approve", "Service", s.id, "")
    flash("Servicio aprobado y activado.", "success")
    return redirect(url_for("admin.admin_services"))

@admin_bp.route("/services/reject/<int:service_id>", methods=["POST"])
@login_required
def reject_service(service_id):
    if not _require_admin():
        return ("Forbidden", 403)
    s = Service.query.get_or_404(service_id)
    s.status = ServiceStatus.REJECTED.value
    s.is_active = False
    s.rejected_by = current_user.id
    s.rejected_at = datetime.utcnow()
    db.session.commit()
    log_action(current_user, "reject", "Service", s.id, "")
    flash("Servicio rechazado.", "warning")
    return redirect(url_for("admin.admin_services"))

@admin_bp.route("/services/softdelete/<int:service_id>", methods=["POST"])
@login_required
def softdelete_service(service_id):
    if not _require_admin():
        return ("Forbidden", 403)
    s = Service.query.get_or_404(service_id)
    s.is_deleted = True
    s.is_active = False
    db.session.commit()
    log_action(current_user, "soft_delete", "Service", s.id, "")
    flash("Servicio movido a papelera.", "info")
    return redirect(url_for("admin.admin_services"))

@admin_bp.route("/services/toggle/<int:service_id>", methods=["POST"])
@login_required
def toggle_active(service_id):
    if not _require_admin():
        return ("Forbidden", 403)
    s = Service.query.get_or_404(service_id)
    if s.status != ServiceStatus.APPROVED.value:
        flash("Solo los servicios aprobados pueden activarse/desactivarse.", "warning")
        return redirect(url_for("admin.admin_services"))
    s.is_active = not bool(s.is_active)
    db.session.commit()
    action = "activate" if s.is_active else "deactivate"
    log_action(current_user, action, "Service", s.id, "")
    flash("Servicio activado." if s.is_active else "Servicio desactivado.", "success")
    return redirect(url_for("admin.admin_services"))

# ------------------------
# Clasificados
# ------------------------
@admin_bp.route("/classifieds")
@login_required
def admin_classifieds():
    if not _require_admin():
        return ("Forbidden", 403)
    status = request.args.get("status")
    q = Classified.query.filter_by(is_deleted=False)
    if status:
        q = q.filter_by(status=status)
    items = q.order_by(Classified.created_at.desc()).all()

    users_map = {u.id: u.name for u in User.query.with_entities(User.id, User.name).all()}

    return render_template("admin/classifieds.html", items=items, ServiceStatus=ServiceStatus, users_map=users_map)

@admin_bp.route("/classifieds/approve/<int:cid>", methods=["POST"])
@login_required
def approve_classified(cid):
    if not _require_admin():
        return ("Forbidden", 403)
    c = Classified.query.get_or_404(cid)
    if c.status == ServiceStatus.REJECTED.value and not _is_super():
        if c.rejected_by and c.rejected_by != current_user.id:
            flash("Solo el administrador que rechazó este clasificado puede volver a aprobarlo.", "warning")
            return redirect(url_for("admin.admin_classifieds"))
    c.status = ServiceStatus.APPROVED.value
    c.is_active = True
    c.approved_by = current_user.id
    c.approved_at = datetime.utcnow()
    db.session.commit()
    log_action(current_user, "approve", "Classified", c.id, "")
    flash("Clasificado aprobado y activado.", "success")
    return redirect(url_for("admin.admin_classifieds"))

@admin_bp.route("/classifieds/reject/<int:cid>", methods=["POST"])
@login_required
def reject_classified(cid):
    if not _require_admin():
        return ("Forbidden", 403)
    c = Classified.query.get_or_404(cid)
    c.status = ServiceStatus.REJECTED.value
    c.is_active = False
    c.rejected_by = current_user.id
    c.rejected_at = datetime.utcnow()
    db.session.commit()
    log_action(current_user, "reject", "Classified", c.id, "")
    flash("Clasificado rechazado.", "warning")
    return redirect(url_for("admin.admin_classifieds"))

# ------------------------
# Usuarios y Logs
# ------------------------
@admin_bp.route("/users")
@login_required
def users():
    if not _require_admin():
        return ("Forbidden", 403)

    if _is_super():
        items = User.query.filter_by(is_deleted=False).order_by(User.created_at.desc()).limit(1000).all()
    else:
        items = User.query.filter(
            User.is_deleted == False,
            User.role == "user"
        ).order_by(User.created_at.desc()).limit(1000).all()

    return render_template("admin/users.html", items=items)

@admin_bp.route("/users/create", methods=["GET", "POST"])
@login_required
def create_user():
    if not _require_admin():
        return ("Forbidden", 403)
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").lower().strip()
        phone = request.form.get("phone","").strip()
        role = request.form.get("role","user").strip()
        if current_user.role != "superadmin":
            role = "user"
        password = request.form.get("password","").strip()
        if not name or not email:
            flash("Nombre y email son obligatorios.", "danger")
            return render_template("admin/create_user.html")
        if User.query.filter_by(email=email).first():
            flash("Ese email ya está registrado.", "warning")
            return render_template("admin/create_user.html")
        if not password:
            password = "Temp-" + email.split("@")[0]
        u = User(name=name, email=email, phone=phone, role=role, is_verified=True)
        u.password_hash = generate_password_hash(password)
        db.session.add(u); db.session.commit()
        log_action(current_user, "create_user", "User", u.id, f"Rol {role}")
        flash("Usuario creado.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/create_user.html")

@admin_bp.route("/users/edit/<int:uid>", methods=["GET", "POST"])
@login_required
def edit_user(uid):
    if not _require_admin():
        return ("Forbidden", 403)
    u = User.query.get_or_404(uid)
    if current_user.role != "superadmin" and u.role != "user":
        flash("No autorizado.", "danger")
        return redirect(url_for("admin.users"))
    if request.method == "POST":
        u.name = request.form.get("name", u.name).strip()
        u.email = request.form.get("email", u.email).lower().strip()
        u.phone = request.form.get("phone", u.phone).strip()
        db.session.commit()
        log_action(current_user, "edit_user", "User", u.id, "Datos básicos")
        flash("Usuario actualizado.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/edit_user.html", u=u)

@admin_bp.route("/users/reset_password/<int:uid>", methods=["POST"])
@login_required
def reset_password(uid):
    if not _require_admin():
        return ("Forbidden", 403)
    u = User.query.get_or_404(uid)
    if current_user.role != "superadmin" and u.role != "user":
        flash("No autorizado.", "danger")
        return redirect(url_for("admin.users"))
    temp = f"Temp-{u.id}-{int(datetime.utcnow().timestamp())}"
    u.password_hash = generate_password_hash(temp)
    db.session.commit()
    log_action(current_user, "reset_password", "User", u.id, "")
    flash(f"Contraseña temporal: {temp}", "info")
    return redirect(url_for("admin.users"))

@admin_bp.route("/users/softdelete/<int:uid>", methods=["POST"])
@login_required
def softdelete_user(uid):
    if not _require_admin():
        return ("Forbidden", 403)
    u = User.query.get_or_404(uid)
    if (current_user.role != "superadmin" and u.role != "user") or (u.id == current_user.id):
        flash("No autorizado.", "danger")
        return redirect(url_for("admin.users"))
    u.is_deleted = True
    db.session.commit()
    log_action(current_user, "soft_delete", "User", u.id, "")
    flash("Usuario movido a papelera.", "info")
    return redirect(url_for("admin.users"))

@admin_bp.route("/users/change_role/<int:uid>", methods=["POST"])
@login_required
def change_role(uid):
    if not (_require_admin() and _is_super()):
        return ("Forbidden", 403)
    u = User.query.get_or_404(uid)
    new_role = request.form.get("role", "").strip()
    if new_role not in ("user", "admin", "superadmin"):
        flash("Rol inválido.", "danger")
        return redirect(url_for("admin.users"))
    if u.role == "superadmin" and new_role in ("admin", "user"):
        remaining = User.query.filter_by(role="superadmin", is_deleted=False).count()
        if remaining <= 1:
            flash("Debe quedar al menos un superadmin activo.", "warning")
            return redirect(url_for("admin.users"))
    u.role = new_role
    db.session.commit()
    log_action(current_user, "change_role", "User", u.id, f"{new_role}")
    flash("Rol actualizado.", "success")
    return redirect(url_for("admin.users"))

@admin_bp.route("/logs")
@login_required
def logs():
    if not (_require_admin()):
        return ("Forbidden", 403)
    activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(500).all()
    logins = LoginLog.query.order_by(LoginLog.created_at.desc()).limit(500).all()
    return render_template("admin/logs.html", activities=activities, logins=logins)
