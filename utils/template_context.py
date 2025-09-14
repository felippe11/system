from datetime import datetime
from flask_login import current_user
from utils.auth import (
    has_permission, 
    get_current_user_role, 
    is_admin, 
    is_superadmin, 
    is_cliente, 
    is_ministrante, 
    is_participante,
    can_access_resource
)

def inject_auth_context():
    """Injeta funções de autorização no contexto dos templates."""
    return {
        'has_permission': has_permission,
        'get_current_user_role': get_current_user_role,
        'is_admin': is_admin,
        'is_superadmin': is_superadmin,
        'is_cliente': is_cliente,
        'is_ministrante': is_ministrante,
        'is_participante': is_participante,
        'can_access_resource': can_access_resource,
        'current_user_authenticated': current_user.is_authenticated if current_user else False,
        'now': datetime.utcnow
    }

def register_template_context(app):
    """Registra o contexto de autorização na aplicação Flask."""
    app.context_processor(inject_auth_context)
