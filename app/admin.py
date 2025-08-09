
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import db, User, Service, ServiceStatus, ActivityLog, LoginLog
from .utils import roles_required, log_action

admin_bp = Blueprint("admin", __name__)

@admin_bp.before_request
def require_admin():
    if not current_user.is_authenticated or current_user.role not in ("admin","superadmin"):
        from flask import abort
        abort(403)

@admin_bp.route("/")
def dashboard():
    total_services = Service.query.filter_by(is_deleted=False).count()
    pending = Service.query.filter_by(status=ServiceStatus.PENDING.value, is_deleted=False).count()
    approved = Service.query.filter_by(status=ServiceStatus.APPROVED.value, is_deleted=False).count()
    users = User.query.filter_by(is_deleted=False).count()
    return render_template("admin/dashboard.html", total_services=total_services, pending=pending, approved=approved, users=users)

@admin_bp.route("/services")
def admin_services():
    status = request.args.get("status")
    q = Service.query.filter_by(is_deleted=False)
    if status:
        q = q.filter_by(status=status)
    items = q.order_by(Service.created_at.desc()).all()
    return render_template("admin/services.html", items=items, ServiceStatus=ServiceStatus)

@admin_bp.route("/services/approve/<int:service_id>", methods=["POST"])
def approve_service(service_id):
    s = Service.query.get_or_404(service_id)
    s.status = ServiceStatus.APPROVED.value
    s.is_active = True
    s.approved_by = current_user.id
    s.approved_at = datetime.utcnow()
    db.session.commit()
    log_action(current_user, "approve", "Service", s.id, "Aprobado y activado")
    flash("Servicio aprobado y activado.", "success")
    return redirect(url_for("admin.admin_services"))

@admin_bp.route("/services/reject/<int:service_id>", methods=["POST"])
def reject_service(service_id):
    s = Service.query.get_or_404(service_id)
    s.status = ServiceStatus.REJECTED.value
    s.is_active = False
    db.session.commit()
    log_action(current_user, "reject", "Service", s.id, "Rechazado")
    flash("Servicio rechazado.", "warning")
    return redirect(url_for("admin.admin_services"))

@admin_bp.route("/services/toggle/<int:service_id>", methods=["POST"])
def toggle_active(service_id):
    s = Service.query.get_or_404(service_id)
    s.is_active = not s.is_active
    db.session.commit()
    log_action(current_user, "toggle", "Service", s.id, f"Activo={s.is_active}")
    flash("Estado de activación actualizado.", "info")
    return redirect(url_for("admin.admin_services"))

@admin_bp.route("/services/softdelete/<int:service_id>", methods=["POST"])
def softdelete_service(service_id):
    s = Service.query.get_or_404(service_id)
    s.is_deleted = True
    s.is_active = False
    db.session.commit()
    log_action(current_user, "soft_delete", "Service", s.id, "Soft delete por admin")
    flash("Servicio eliminado (soft delete).", "info")
    return redirect(url_for("admin.admin_services"))

@admin_bp.route("/services/harddelete/<int:service_id>", methods=["POST"])
def harddelete_service(service_id):
    if current_user.role != "superadmin":
        from flask import abort
        abort(403)
    s = Service.query.get_or_404(service_id)
    db.session.delete(s)
    db.session.commit()
    log_action(current_user, "hard_delete", "Service", s.id, "Hard delete por superadmin")
    flash("Servicio eliminado DEFINITIVAMENTE.", "danger")
    return redirect(url_for("admin.admin_services"))

@admin_bp.route("/users")
def users():
    items = User.query.filter_by(is_deleted=False).order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", items=items)

@admin_bp.route("/users/create", methods=["GET","POST"])
def create_user():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email").lower().strip()
        role = request.form.get("role","basic")
        temp_password = request.form.get("password","12345678")
        if User.query.filter_by(email=email).first():
            flash("Email ya existe.", "warning")
            return render_template("admin/user_form.html")
        u = User(name=name, email=email, role=role, is_verified=True)
        u.set_password(temp_password)
        db.session.add(u); db.session.commit()
        log_action(current_user, "create", "User", u.id, f"Creado por admin con rol {role}")
        flash("Usuario creado.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html")

@admin_bp.route("/users/reset/<int:user_id>", methods=["POST"])
def reset_user(user_id):
    u = User.query.get_or_404(user_id)
    u.is_verified = True
    u.verification_code = None
    u.set_password("12345678")
    db.session.commit()
    log_action(current_user, "reset_user", "User", u.id, "Reset a contraseña por defecto 12345678")
    flash("Usuario reseteado (contraseña 12345678).", "info")
    return redirect(url_for("admin.users"))

@admin_bp.route("/users/softdelete/<int:user_id>", methods=["POST"])
def softdelete_user(user_id):
    u = User.query.get_or_404(user_id)
    u.is_deleted = True
    db.session.commit()
    log_action(current_user, "soft_delete", "User", u.id, "Soft delete")
    flash("Usuario eliminado (soft delete).", "info")
    return redirect(url_for("admin.users"))

@admin_bp.route("/logs")
def logs():
    if current_user.role != "superadmin":
        from flask import abort
        abort(403)
    acts = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(500).all()
    logins = LoginLog.query.order_by(LoginLog.created_at.desc()).limit(500).all()
    return render_template("admin/logs.html", acts=acts, logins=logins)
