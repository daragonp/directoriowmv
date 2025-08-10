from datetime import date
from flask import Blueprint, render_template, request
from sqlalchemy import or_, and_
from .models import Service, Classified, ServiceStatus

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    """
    Home pública: solo muestra resultados si hay búsqueda (q).
    """
    q = (request.args.get("q") or "").strip()
    items = []
    if q:
        like = f"%{q}%"
        base = Service.query.filter(
            Service.is_deleted == False,
            Service.is_active == True,
            Service.status == ServiceStatus.APPROVED.value
        )
        conds = []
        if hasattr(Service, "title"):
            conds.append(Service.title.ilike(like))
        if hasattr(Service, "description"):
            conds.append(Service.description.ilike(like))
        if conds:
            base = base.filter(or_(*conds))
        items = base.order_by(Service.created_at.desc()).limit(24).all()

    return render_template("index.html", items=items, q=q)

@main_bp.route("/privacy")
def privacy():
    return render_template("legal/privacy.html")

@main_bp.route("/terms")
def terms():
    return render_template("legal/terms.html")

@main_bp.route("/clasificados/")
def classifieds_public():
    """
    Listado público de clasificados (aprobados, activos y dentro de fechas).
    """
    today = date.today()
    q = Classified.query.filter(
        Classified.is_deleted == False,
        Classified.is_active == True,
        Classified.status == ServiceStatus.APPROVED.value,
        and_(
            (Classified.start_date == None) | (Classified.start_date <= today),
            (Classified.end_date == None) | (Classified.end_date >= today),
        )
    ).order_by(Classified.start_date.desc().nullslast(), Classified.created_at.desc())

    items = q.limit(50).all()
    return render_template("public/classifieds_cards.html", items=items)
