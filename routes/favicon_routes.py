from flask import Blueprint, send_from_directory, current_app
import os

favicon_routes = Blueprint('favicon_routes', __name__)

@favicon_routes.route('/favicon.ico')
def favicon():
    """Serve o favicon na raiz do site para compatibilidade máxima."""
    return send_from_directory(
        os.path.join(current_app.root_path, 'static', 'favicon'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

@favicon_routes.route('/favicon-<int:size>.png')
def favicon_png(size):
    """Serve favicons PNG em diferentes tamanhos."""
    filename = f'favicon-{size}x{size}.png'
    return send_from_directory(
        os.path.join(current_app.root_path, 'static', 'favicon'),
        filename,
        mimetype='image/png'
    )

@favicon_routes.route('/apple-touch-icon.png')
def apple_touch_icon():
    """Serve o ícone para dispositivos Apple."""
    return send_from_directory(
        os.path.join(current_app.root_path, 'static', 'favicon'),
        'apple-touch-icon.png',
        mimetype='image/png'
    )

@favicon_routes.route('/android-chrome-<int:size>.png')
def android_chrome(size):
    """Serve ícones para Android Chrome."""
    filename = f'android-chrome-{size}x{size}.png'
    return send_from_directory(
        os.path.join(current_app.root_path, 'static', 'favicon'),
        filename,
        mimetype='image/png'
    )

@favicon_routes.route('/site.webmanifest')
def webmanifest():
    """Serve o manifest para PWA."""
    return send_from_directory(
        os.path.join(current_app.root_path, 'static', 'favicon'),
        'site.webmanifest',
        mimetype='application/manifest+json'
    )

