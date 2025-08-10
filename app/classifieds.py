# app/classifieds.py
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from .models import db, Classified, ServiceStatus
from .utils import log_action

classifieds_bp = Blueprint("classifieds", __name__, url_prefix="/clasificados")

def _is_admin():
    return current_user.is_authenticated and current_user.role in ("admin", "superadmin")

# Público: lista de clasificados activos, aprobados y vigentes
@classifieds_bp.route("/", methods=["GET"])
def public_list():
    today = date.today()
    q = Classified.query.filter(
        Classified.is_deleted == False,
        Classified.is_active == True,
        Classified.status == ServiceStatus.APPROVED.value,
    ).filter(
        (Classified.start_date == None) | (Classified.start_date <= today)
    ).filter(
        (Classified.end_date == None) | (Classified.end_date >= today)
    ).order_by(Classified.start_date.desc().nullslast())
    items = q.all()
    return render_template("classifieds/public_list.html", items=items)

# Propios del usuario
@classifieds_bp.route("/mine", methods=["GET"])
@login_required
def mine():
    items = (
        Classified.query
        .filter_by(owner_id=current_user.id, is_deleted=False)
        .order_by(Classified.created_at.desc())
        .all()
    )
    can_edit = "classifieds.edit" in current_app.view_functions
    return render_template("classifieds/mine.html", items=items, can_edit_route=can_edit)

# Crear
@classifieds_bp.route("/create", methods=["GET","POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title","").strip()
        description = request.form.get("description","").strip()
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")

        c = Classified(
            title=title,
            description=description,
            owner_id=current_user.id,
            status=ServiceStatus.PENDING.value,
            is_active=False
        )
        fmt = "%Y-%m-%d"
        if start_date:
            try: c.start_date = datetime.strptime(start_date, fmt).date()
            except: pass
        if end_date:
            try: c.end_date = datetime.strptime(end_date, fmt).date()
            except: pass

        db.session.add(c); db.session.commit()
        log_action(current_user, "create", "Classified", c.id, "")
        flash("Clasificado creado. Quedó pendiente de aprobación.", "success")
        return redirect(url_for("classifieds.mine"))

    return render_template("classifieds/create.html")

# Detalle
@classifieds_bp.route("/detail/<int:cid>")
def detail(cid):
    c = Classified.query.get_or_404(cid)
    if not c.is_deleted and (c.is_active and c.status==ServiceStatus.APPROVED.value or (current_user.is_authenticated and (current_user.id==c.owner_id or _is_admin()))):
        return render_template("classifieds/detail.html", c=c)
    flash("Clasificado no disponible.", "warning")
    return redirect(url_for("classifieds.public_list"))
