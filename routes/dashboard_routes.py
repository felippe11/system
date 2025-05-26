from flask import Blueprint, render_template, redirect, url_for, flash, session
from flask_login import login_required, current_user

dashboard_routes = Blueprint(
    'dashboard_routes',
    __name__,
    template_folder="dashboard"
)
# ────────────────────────────────────────
# DASHBOARD GERAL (admin, cliente, participante, professor)
# ────────────────────────────────────────
@dashboard_routes.route('/dashboard')
@login_required
def dashboard():
    tipo = getattr(current_user, "tipo", None)

    if tipo == "admin":
        return redirect(url_for("dashboard_routes.dashboard_admin"))

    elif tipo == "cliente":
        return redirect(url_for("dashboard_routes.dashboard_cliente"))

    elif tipo == "participante":
        return redirect(
            url_for("dashboard_participante_routes.dashboard_participante")
        )

    elif tipo == "ministrante":
        return redirect(
            url_for("dashboard_ministrante_routes.dashboard_ministrante")
        )

    elif tipo == "professor":
        return redirect(url_for("dashboard_professor.dashboard_professor"))

    abort(403)

@dashboard_routes.route("/dashboard_admin")
@login_required
def dashboard_admin():
    if current_user.tipo != "admin":
        abort(403)
    return render_template("dashboard/dashboard_admin.html")


@dashboard_routes.route("/dashboard_cliente")
@login_required
def dashboard_cliente():
    if current_user.tipo != "cliente":
        abort(403)
    return render_template("dashboard/dashboard_cliente.html")
