from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


def cliente_required(f):
    """
    Decorator para verificar se o usuário atual é um cliente.
    Redireciona para login se não autenticado ou para dashboard se não for cliente.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Você precisa estar logado para acessar esta página.', 'error')
            return redirect(url_for('auth.login'))
            
        # Verificar se o usuário é um cliente
        if not hasattr(current_user, 'tipo') or current_user.tipo != 'cliente':
            flash('Acesso negado. Esta área é restrita a clientes.', 'error')
            return redirect(url_for('dashboard.index'))
            
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator para verificar se o usuário atual é um administrador.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Você precisa estar logado para acessar esta página.', 'error')
            return redirect(url_for('auth.login'))
            
        # Verificar se o usuário é um administrador
        if not hasattr(current_user, 'tipo') or current_user.tipo != 'admin':
            flash('Acesso negado. Esta área é restrita a administradores.', 'error')
            return redirect(url_for('dashboard.index'))
            
        return f(*args, **kwargs)
    return decorated_function


def revisor_required(f):
    """
    Decorator para verificar se o usuário atual é um revisor.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Você precisa estar logado para acessar esta página.', 'error')
            return redirect(url_for('auth.login'))
            
        # Verificar se o usuário é um revisor
        if not hasattr(current_user, 'tipo') or current_user.tipo != 'revisor':
            flash('Acesso negado. Esta área é restrita a revisores.', 'error')
            return redirect(url_for('dashboard.index'))
            
        return f(*args, **kwargs)
    return decorated_function