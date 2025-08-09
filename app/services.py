
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import db, Service, ServiceStatus
from .utils import log_action

services_bp = Blueprint("services", __name__)

@services_bp.route("/create", methods=["GET","POST"])
@login_required
def create_service():
    if request.method == "POST":
        s = Service(
            owner_id=current_user.id,
            person_name=request.form.get("person_name","").strip(),
            business_name=request.form.get("business_name","").strip(),
            title=request.form.get("title","").strip(),
            description=request.form.get("description","").strip(),
            email=request.form.get("email","").strip(),
            phone=request.form.get("phone","").strip(),
            address=request.form.get("address","").strip(),
            social_link=request.form.get("social_link","").strip(),
        )
        db.session.add(s); db.session.commit()
        log_action(current_user, "create", "Service", s.id, "Creación en estado pendiente")
        flash("Servicio creado y pendiente de aprobación.", "success")
        return redirect(url_for("services.my_services"))
    return render_template("services/create.html")

@services_bp.route("/mine")
@login_required
def my_services():
    items = Service.query.filter_by(owner_id=current_user.id).order_by(Service.created_at.desc()).all()
    return render_template("services/mine.html", items=items)

@services_bp.route("/edit/<int:service_id>", methods=["GET","POST"])
@login_required
def edit_service(service_id):
    s = Service.query.get_or_404(service_id)
    if s.owner_id != current_user.id and current_user.role not in ("admin","superadmin"):
        return ("Forbidden", 403)
    if request.method == "POST":
        s.person_name = request.form.get("person_name", s.person_name)
        s.business_name = request.form.get("business_name", s.business_name)
        s.title = request.form.get("title", s.title)
        s.description = request.form.get("description", s.description)
        s.email = request.form.get("email", s.email)
        s.phone = request.form.get("phone", s.phone)
        s.address = request.form.get("address", s.address)
        s.social_link = request.form.get("social_link", s.social_link)
        db.session.commit()
        log_action(current_user, "update", "Service", s.id, "Edición")
        flash("Servicio actualizado.", "success")
        return redirect(url_for("services.my_services"))
    return render_template("services/edit.html", s=s)

@services_bp.route("/delete/<int:service_id>", methods=["POST"])
@login_required
def soft_delete(service_id):
    s = Service.query.get_or_404(service_id)
    if s.owner_id != current_user.id and current_user.role not in ("admin","superadmin"):
        return ("Forbidden", 403)
    s.is_deleted = True
    s.is_active = False
    db.session.commit()
    log_action(current_user, "soft_delete", "Service", s.id, "Eliminación lógica")
    flash("Servicio eliminado (soft delete).", "info")
    return redirect(url_for("services.my_services"))

@services_bp.route("/detail/<int:service_id>")
def detail(service_id):
    s = Service.query.get_or_404(service_id)
    if s.is_deleted:
        return ("No encontrado", 404)
    # público puede ver solo si aprobado+activo o si dueño/admin
    if s.status != ServiceStatus.APPROVED.value or not s.is_active:
        from flask_login import current_user
        if not current_user.is_authenticated or (current_user.id != s.owner_id and current_user.role not in ("admin","superadmin")):
            return ("No autorizado", 403)
    return render_template("services/detail.html", s=s)
