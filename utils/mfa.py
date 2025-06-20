from functools import wraps
from flask import session, redirect, url_for
from flask_login import current_user


def mfa_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if (
            current_user.is_authenticated
            and getattr(current_user, 'mfa_enabled', False)
            and not session.get('mfa_authenticated')
        ):
            session['pre_mfa_user_id'] = current_user.id
            session['pre_mfa_user_type'] = session.get('user_type')
            return redirect(url_for('auth_routes.mfa'))
        return f(*args, **kwargs)
    return wrapper
