# app/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse, urljoin
from werkzeug.utils import secure_filename
from .models import db, User, LoginLog
from .utils import gen_code, log_action, allowed_image
from .email import send_verification_email
import os
import time

auth_bp = Blueprint("auth", __name__)

def is_safe_url(target: str) -> bool:
    """Evita open redirects verificando que el host coincida."""
    if not target:
        return False
    ref = urlparse(request.host_url)
    test = urlparse(urljoin(request.host_url, target))
    return test.scheme in ("http", "https") and ref.netloc == test.netloc

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").lower().strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Nombre, email y contraseña son obligatorios.", "danger")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            flash("Ese email ya está registrado.", "warning")
            return render_template("auth/register.html")

        u = User(name=name, email=email, phone=phone)
        u.set_password(password)
        u.verification_code = gen_code(6)
        db.session.add(u)
        db.session.commit()

        # Enviar código y registrar actividad
        send_verification_email(u.email, u.verification_code)
        log_action(u, "register", "User", u.id, "Registro y envío de código")

        flash("Registro exitoso. Revisa tu email para el código de verificación.", "success")
        return redirect(url_for("auth.verify"))
    return render_template("auth/register.html")

@auth_bp.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        code = request.form.get("code", "").strip()

        u = User.query.filter_by(email=email).first()
        if not u:
            flash("Usuario no encontrado.", "danger")
            return render_template("auth/verify.html")

        if u.is_verified:
            flash("La cuenta ya está verificada. Puedes iniciar sesión.", "info")
            return redirect(url_for("auth.login"))

        if u.verification_code == code:
            u.is_verified = True
            u.verification_code = None
            db.session.commit()
            log_action(u, "verify_account", "User", u.id, "Cuenta verificada")
            flash("Cuenta verificada. Ahora puedes iniciar sesión.", "success")
            return redirect(url_for("auth.login"))
        else:
            flash("Código incorrecto.", "danger")
    return render_template("auth/verify.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        u = User.query.filter_by(email=email, is_deleted=False).first()
        if not u or not u.check_password(password):
            flash("Credenciales inválidas.", "danger")
            return render_template("auth/login.html")

        if not u.is_verified:
            flash("Tu cuenta no está verificada. Verifícala primero.", "warning")
            return redirect(url_for("auth.verify"))

        login_user(u, remember=remember)

        # Log de ingreso (LoginLog + ActivityLog)
        log = LoginLog(
            user_id=u.id,
            ip=request.headers.get("X-Forwarded-For", request.remote_addr),
            user_agent=request.headers.get("User-Agent"),
            location=""
        )
        db.session.add(log)
        db.session.commit()
        log_action(u, "login", "User", u.id, "Inicio de sesión")

        # Volver a la URL protegida si venía de allí
        next_url = request.args.get("next")
        if next_url and is_safe_url(next_url):
            return redirect(next_url)
        return redirect(url_for("main.index"))
    return render_template("auth/login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    log_action(current_user, "logout", "User", current_user.id, "Cierre de sesión")
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("main.index"))

@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        # Campos básicos
        current_user.name = request.form.get("name", current_user.name)
        current_user.phone = request.form.get("phone", current_user.phone)
        current_user.address = request.form.get("address", current_user.address)

        # Avatar por URL (opcional)
        avatar_url = request.form.get("avatar_url", "").strip()
        if avatar_url:
            current_user.avatar_url = avatar_url

        # Cambio de email -> requiere nueva verificación
        email = request.form.get("email", "").lower().strip()
        if email and email != current_user.email:
            current_user.email = email
            current_user.is_verified = False
            current_user.verification_code = gen_code(6)
            send_verification_email(current_user.email, current_user.verification_code)
            flash("Email actualizado. Verifícalo con el código que te enviamos.", "info")

        # Cambio de contraseña (opcional)
        pwd = request.form.get("password", "")
        if pwd:
            current_user.set_password(pwd)
            flash("Contraseña actualizada.", "success")

        # Subida de avatar (archivo)
        file = request.files.get("avatar_file")
        if file and allowed_image(file.filename, current_app):
            filename = secure_filename(f"{current_user.id}_{int(time.time())}_{file.filename}")
            upload_dir = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_dir, exist_ok=True)
            path = os.path.join(upload_dir, filename)
            file.save(path)
            current_user.avatar_url = f"/static/uploads/avatars/{filename}"
            flash("Avatar actualizado.", "success")

        db.session.commit()
        log_action(current_user, "update_profile", "User", current_user.id, "Perfil actualizado")

        # PRG pattern
        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html")
