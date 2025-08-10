from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from .models import db, User, LoginLog
from .utils import gen_code, log_action, save_avatar
from .email import send_verification_email

auth_bp = Blueprint("auth", __name__)

def _ts():
    return URLSafeTimedSerializer(
        secret_key=current_app.config["SECRET_KEY"],
        salt="email-verify-salt"
    )

def _build_verify_link(token: str) -> str:
    base = current_app.config.get("APP_BASE_URL", "").rstrip("/")
    return f"{base}{url_for('auth.verify')}?token={token}"

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").lower().strip()
        phone = request.form.get("phone","").strip()
        password = request.form.get("password","")
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

        token = _ts().dumps({"uid": u.id, "code": u.verification_code})
        link = _build_verify_link(token)
        # Email real con link y código
        send_verification_email(u.email, link, code=u.verification_code)

        flash("Registro exitoso. Te enviamos un correo con el enlace de verificación.", "success")
        return redirect(url_for("auth.verify"))
    return render_template("auth/register.html")

@auth_bp.route("/verify", methods=["GET", "POST"])
def verify():
    token = request.args.get("token")
    if token:
        try:
            data = _ts().loads(token, max_age=current_app.config.get("VERIFY_TOKEN_MAX_AGE", 86400))
            u = User.query.get(int(data.get("uid")))
            if not u:
                flash("Usuario no encontrado.", "danger")
                return render_template("auth/verify.html")
            if u.is_verified:
                flash("La cuenta ya está verificada.", "info")
                return redirect(url_for("auth.login"))
            if u.verification_code and data.get("code") == u.verification_code:
                u.is_verified = True
                u.verification_code = None
                db.session.commit()
                flash("Cuenta verificada. Ahora puedes iniciar sesión.", "success")
                return redirect(url_for("auth.login"))
            flash("Token inválido o expirado.", "danger")
        except SignatureExpired:
            flash("El enlace de verificación expiró. Solicita uno nuevo.", "warning")
        except BadSignature:
            flash("Token de verificación inválido.", "danger")
        return render_template("auth/verify.html")

    if request.method == "POST":
        email = request.form.get("email","").lower().strip()
        code = request.form.get("code","").strip()
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
            flash("Cuenta verificada. Ahora puedes iniciar sesión.", "success")
            return redirect(url_for("auth.login"))
        else:
            flash("Código incorrecto.", "danger")
    return render_template("auth/verify.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").lower().strip()
        password = request.form.get("password","")
        u = User.query.filter_by(email=email, is_deleted=False).first()
        if not u or not u.check_password(password):
            flash("Credenciales inválidas.", "danger")
            return render_template("auth/login.html")
        if not u.is_verified:
            flash("Tu cuenta no está verificada. Revisa tu email o solicita un nuevo enlace.", "warning")
            return redirect(url_for("auth.verify"))
        login_user(u, remember=True)
        # IP real (respeta proxy si se configuró ProxyFix)
        ip_hdr = request.headers.get("X-Forwarded-For", request.remote_addr) or ""
        ip = ip_hdr.split(",")[0].strip() if ip_hdr else request.remote_addr
        log = LoginLog(user_id=u.id, ip=ip, user_agent=request.headers.get("User-Agent"), location="")
        db.session.add(log)
        db.session.commit()
        return redirect(url_for("main.index"))
    return render_template("auth/login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("main.index"))

@auth_bp.route("/profile", methods=["GET","POST"])
@login_required
def profile():
    if request.method == "POST":
        # Campos básicos
        current_user.name = request.form.get("name", current_user.name)
        current_user.phone = request.form.get("phone", current_user.phone)
        current_user.address = request.form.get("address", current_user.address)

        # Subida de avatar
        file = request.files.get("avatar_file")
        if file and file.filename:
            url = save_avatar(file, current_user.id)
            if url:
                current_user.avatar_url = url
                flash("Avatar actualizado.", "success")
            else:
                flash("La imagen no es válida (extensión o tamaño).", "warning")

        # Cambiar email → requiere reverificación
        email = request.form.get("email","").lower().strip()
        if email and email != current_user.email:
            # Evitar duplicados
            if User.query.filter(User.email == email, User.id != current_user.id).first():
                flash("Ese email ya está en uso por otro usuario.", "danger")
            else:
                current_user.email = email
                current_user.is_verified = False
                current_user.verification_code = gen_code(6)
                send_verification_email(current_user.email, current_user.verification_code)
                flash("Email actualizado. Verifícalo con el código que te enviamos.", "info")

        # Cambiar contraseña
        pwd = request.form.get("password","")
        if pwd:
            current_user.set_password(pwd)
            flash("Contraseña actualizada.", "success")

        db.session.commit()
        log_action(current_user, "update_profile", "User", current_user.id, "Perfil actualizado")
        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html")