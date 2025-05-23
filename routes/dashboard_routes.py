
from flask import Blueprint, render_template, redirect, url_for, flash, session
from flask_login import login_required, current_user

dashboard_routes = Blueprint('dashboard_routes', __name__)
# ────────────────────────────────────────
# DASHBOARD GERAL (admin, cliente, participante, professor)
# ────────────────────────────────────────
@dashboard_routes.route('/dashboard')
@login_required
def dashboard():
    tipo = getattr(current_user, "tipo", None)

    if tipo == "admin":
        return redirect(url_for("routes.dashboard_admin"))
    elif tipo == "cliente":
        return redirect(url_for("routes.dashboard_cliente"))
    elif tipo == "participante":
        return redirect(url_for("routes.dashboard_participante"))
    elif tipo == "professor":
        return redirect(url_for("routes.dashboard_professor"))
    else:
        abort(403)
