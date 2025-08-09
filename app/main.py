# app/main.py
from flask import Blueprint, render_template, request
from .models import Service, ServiceStatus

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    q = request.args.get("q","").strip()
    items = []
    if q:
        base = Service.query.filter_by(
            is_deleted=False,
            status=ServiceStatus.APPROVED.value,
            is_active=True
        )
        like = f"%{q}%"
        base = base.filter(
            (Service.title.ilike(like))
            | (Service.description.ilike(like))
            | (Service.business_name.ilike(like))
            | (Service.person_name.ilike(like))
        )
        items = base.order_by(Service.created_at.desc()).limit(100).all()
    return render_template("index.html", items=items, q=q)

