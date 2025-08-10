# app/services.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from .models import db, Service, ServiceStatus, User
from .utils import log_action

services_bp = Blueprint("services", __name__)

def _is_admin():
    return current_user.is_authenticated and current_user.role in ("admin","superadmin")

@services_bp.route("/my")
@login_required
def my_services():
    items = (
        Service.query
        .filter_by(owner_id=current_user.id, is_deleted=False)
        .order_by(Service.created_at.desc())
        .all()
    )
    # Indicador para la plantilla: ¿existe la ruta de edición?
    can_edit = "services.edit" in current_app.view_functions
    return render_template("services/my.html", items=items, can_edit_route=can_edit)

@services_bp.route("/create", methods=["GET","POST"])
@login_required
def create_service():
    if request.method == "POST":
        title = request.form.get("title","").strip()
        description = request.form.get("description","").strip()
        website = request.form.get("website","").strip()
        social = request.form.get("social","").strip()
        address = request.form.get("address","").strip()

        owner_id = current_user.id
        if _is_admin():
            owner_id = int(request.form.get("owner_id", current_user.id))

        if _is_admin():
            contact_name = request.form.get("contact_name","").strip()
            contact_email = request.form.get("contact_email","").lower().strip()
            contact_phone = request.form.get("contact_phone","").strip()
        else:
            contact_name = current_user.name
            contact_email = current_user.email
            contact_phone = current_user.phone

        if not title:
            flash("El título es obligatorio.", "danger")
            return render_template(
                "services/create.html",
                is_admin=_is_admin(),
                users=User.query.filter_by(is_deleted=False).all()
            )

        s = Service(
            title=title,
            description=description,
            website=website,
            social=social,
            address=address,
            owner_id=owner_id,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            status=ServiceStatus.PENDING.value,
            is_active=False
        )
        db.session.add(s); db.session.commit()
        log_action(current_user, "create", "Service", s.id, "")
        flash("Servicio creado. Quedó pendiente de aprobación.", "success")
        return redirect(url_for("services.my_services"))

    return render_template(
        "services/create.html",
        is_admin=_is_admin(),
        users=User.query.filter_by(is_deleted=False).all()
    )

@services_bp.route("/detail/<int:service_id>")
def detail(service_id):
    s = Service.query.get_or_404(service_id)
    # público solo si aprobado y activo; el dueño/adm pueden verlo igual
    if not s.is_deleted and (s.is_active and s.status==ServiceStatus.APPROVED.value or (current_user.is_authenticated and (current_user.id==s.owner_id or _is_admin()))):
        return render_template("services/detail.html", s=s)
    flash("Servicio no disponible.", "warning")
    return redirect(url_for("main.index"))
