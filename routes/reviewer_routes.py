from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models.review import ReviewerApplication

reviewer_routes = Blueprint(
    'reviewer_routes', __name__, template_folder="../templates/reviewer"
)


@reviewer_routes.route('/reviewer_applications/new', methods=['GET', 'POST'])
@login_required
def new_reviewer_application():
    existing_app = ReviewerApplication.query.filter_by(usuario_id=current_user.id).first()
    if existing_app:
        flash('Sua candidatura já foi registrada.', 'info')
        return redirect(url_for('reviewer_routes.application_confirmation'))
    if request.method == 'POST':
        app_obj = ReviewerApplication(usuario_id=current_user.id)
        db.session.add(app_obj)
        db.session.commit()
        return redirect(url_for('reviewer_routes.application_confirmation'))
    return render_template('reviewer/application_form.html')


@reviewer_routes.route('/reviewer_applications/confirmation')
@login_required
def application_confirmation():
    return render_template('reviewer/confirmation.html')
