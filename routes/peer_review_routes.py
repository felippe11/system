from flask import Blueprint, render_template

peer_review_routes = Blueprint(
    'peer_review_routes',
    __name__,
    template_folder="../templates/peer_review"
)

@peer_review_routes.route('/peer-review/author')
def author_dashboard():
    return render_template('peer_review/author/dashboard.html', submissions=[])

@peer_review_routes.route('/peer-review/reviewer')
def reviewer_dashboard():
    return render_template('peer_review/reviewer/dashboard.html', tasks=[])

@peer_review_routes.route('/peer-review/editor')
def editor_dashboard():
    return render_template('peer_review/editor/dashboard.html', decisions=[])
