from functools import wraps
from collections.abc import Iterable
from flask import session, redirect, url_for, flash, abort, request, jsonify
from flask_login import current_user, login_required as flask_login_required
import logging
from utils import endpoints

logger = logging.getLogger(__name__)

# =======================================
# Decorators de Autenticação
# =======================================

def login_required(f):
    """Decorator que exige que o usuário esteja logado."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            # Debug logging
            print(f"DEBUG: Path: {request.path}")
            print(f"DEBUG: Accept header: {request.headers.get('Accept', '')}")
            print(f"DEBUG: Content-Type header: {request.headers.get('Content-Type', '')}")
            print(f"DEBUG: request.is_json: {request.is_json}")
            
            # Check if request expects JSON (either Content-Type or Accept header)
            is_json_request = (request.is_json or 
                             'application/json' in request.headers.get('Accept', '') or
                             request.path.startswith('/api/'))
            print(f"DEBUG: is_json_request: {is_json_request}")
            
            if is_json_request:
                print("DEBUG: Returning JSON error")
                return jsonify({'error': 'Autenticação necessária'}), 401
            print("DEBUG: Redirecting to login")
            return redirect(url_for('auth_routes.login'))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    """Decorator que exige privilégios de administrador."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json:
                return jsonify({'error': 'Autenticação necessária'}), 401
            return redirect(url_for('auth_routes.login'))
        
        user_type = getattr(current_user, 'tipo', None)
        session_type = session.get('user_type')
        
        if user_type not in ('admin', 'superadmin') and session_type not in ('admin', 'superadmin'):
            if request.is_json:
                return jsonify({'error': 'Acesso negado - privilégios de administrador necessários'}), 403
            flash('Acesso negado - privilégios de administrador necessários!', 'danger')
            return redirect(url_for(endpoints.DASHBOARD))
        
        return f(*args, **kwargs)
    return wrapper


def superadmin_required(f):
    """Decorator que exige privilégios de super administrador."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json:
                return jsonify({'error': 'Autenticação necessária'}), 401
            return redirect(url_for('auth_routes.login'))
        
        user_type = getattr(current_user, 'tipo', None)
        session_type = session.get('user_type')
        
        if user_type != 'superadmin' and session_type != 'superadmin':
            if request.is_json:
                return jsonify({'error': 'Acesso negado - privilégios de super administrador necessários'}), 403
            flash('Acesso negado - privilégios de super administrador necessários!', 'danger')
            return redirect(url_for(endpoints.DASHBOARD))
        
        return f(*args, **kwargs)
    return wrapper


def cliente_required(f):
    """Decorator que exige que o usuário seja um cliente."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json:
                return jsonify({'error': 'Autenticação necessária'}), 401
            return redirect(url_for('auth_routes.login'))
        
        user_type = getattr(current_user, 'tipo', None)
        session_type = session.get('user_type')
        
        if user_type != 'cliente' and session_type != 'cliente':
            if request.is_json:
                return jsonify({'error': 'Acesso negado - acesso restrito a clientes'}), 403
            flash('Acesso negado - acesso restrito a clientes!', 'danger')
            return redirect(url_for(endpoints.DASHBOARD))
        
        return f(*args, **kwargs)
    return wrapper


def ministrante_required(f):
    """Decorator que exige que o usuário seja um ministrante."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json:
                return jsonify({'error': 'Autenticação necessária'}), 401
            return redirect(url_for('auth_routes.login'))
        
        user_type = getattr(current_user, 'tipo', None)
        session_type = session.get('user_type')
        
        if user_type != 'ministrante' and session_type != 'ministrante':
            if request.is_json:
                return jsonify({'error': 'Acesso negado - acesso restrito a ministrantes'}), 403
            flash('Acesso negado - acesso restrito a ministrantes!', 'danger')
            return redirect(url_for(endpoints.DASHBOARD))
        
        return f(*args, **kwargs)
    return wrapper


def participante_required(f):
    """Decorator que exige que o usuário seja um participante."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json:
                return jsonify({'error': 'Autenticação necessária'}), 401
            return redirect(url_for('auth_routes.login'))
        
        user_type = getattr(current_user, 'tipo', None)
        session_type = session.get('user_type')
        
        if user_type != 'participante' and session_type != 'participante':
            if request.is_json:
                return jsonify({'error': 'Acesso negado - acesso restrito a participantes'}), 403
            flash('Acesso negado - acesso restrito a participantes!', 'danger')
            return redirect(url_for(endpoints.DASHBOARD))
        
        return f(*args, **kwargs)
    return wrapper


def monitor_required(f):
    """Decorator que exige que o usuário seja um monitor."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json:
                return jsonify({'error': 'Autenticação necessária'}), 401
            return redirect(url_for('auth_routes.login'))
        
        user_type = getattr(current_user, 'tipo', None)
        session_type = session.get('user_type')
        
        if user_type != 'monitor' and session_type != 'monitor':
            if request.is_json:
                return jsonify({'error': 'Acesso negado - acesso restrito a monitores'}), 403
            flash('Acesso negado - acesso restrito a monitores!', 'danger')
            return redirect(url_for(endpoints.DASHBOARD))
        
        return f(*args, **kwargs)
    return wrapper


def role_required(*allowed_roles):
    """Decorator que permite acesso apenas para roles específicos."""

    def _normalize_roles(roles):
        normalized = []
        for role in roles:
            if isinstance(role, str):
                normalized.append(role)
            elif isinstance(role, Iterable):
                normalized.extend(r for r in role if isinstance(r, str))
            else:
                normalized.append(str(role))
        return tuple(dict.fromkeys(normalized))  # remove duplicates mantendo ordem

    normalized_roles = _normalize_roles(allowed_roles)

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            is_json_request = (
                request.is_json
                or request.path.startswith('/api/')
                or 'application/json' in request.headers.get('Accept', '')
            )

            if not current_user.is_authenticated:
                if is_json_request:
                    return jsonify({'error': 'Autenticação necessária'}), 401
                return redirect(url_for('auth_routes.login'))

            user_type = getattr(current_user, 'tipo', None)
            session_type = session.get('user_type')

            current_role = user_type or session_type

            if current_role not in normalized_roles:
                if is_json_request:
                    return jsonify({
                        'error': 'Acesso negado',
                        'roles_permitidos': list(normalized_roles),
                    }), 403
                roles_txt = ", ".join(normalized_roles) if normalized_roles else 'Nenhum'
                flash(f'Acesso negado - roles permitidos: {roles_txt}!', 'danger')
                return redirect(url_for(endpoints.DASHBOARD))

            return f(*args, **kwargs)

        return wrapper

    return decorator


# =======================================
# Funções de Verificação de Permissões
# =======================================

def has_permission(permission_name, resource_id=None):
    """Verifica se o usuário atual tem uma permissão específica."""
    if not current_user.is_authenticated:
        return False
    
    user_type = getattr(current_user, 'tipo', None)
    session_type = session.get('user_type')
    current_role = user_type or session_type
    
    # Super admin tem todas as permissões
    if current_role == 'superadmin':
        return True
    
    # Mapeamento de permissões por role
    permissions_map = {
        'admin': {
            'certificados.view', 'certificados.create', 'certificados.edit', 'certificados.delete',
            'certificados.generate', 'certificados.bulk_generate', 'certificados.export',
            'declaracoes.view', 'declaracoes.create', 'declaracoes.edit', 'declaracoes.delete',
            'declaracoes.generate', 'declaracoes.bulk_generate', 'declaracoes.export',
            'templates.view', 'templates.create', 'templates.edit', 'templates.delete',
            'templates.activate', 'templates.deactivate',
            'ai.use', 'ai.configure', 'ai.view_stats',
            'eventos.view', 'eventos.create', 'eventos.edit', 'eventos.delete',
            'usuarios.view', 'usuarios.create', 'usuarios.edit', 'usuarios.delete',
            'relatorios.view', 'relatorios.export',
            'configuracoes.view', 'configuracoes.edit',
            # Dashboard Analytics Permissions
            'dashboard.view', 'dashboard.export', 'dashboard.drill_down',
            'dashboard.temporal_comparison', 'dashboard.advanced_filters',
            'dashboard.kpis.all', 'dashboard.visoes.all',
            'dashboard.audit.view', 'dashboard.audit.export'
        },
        'cliente': {
            'certificados.view', 'certificados.create', 'certificados.edit',
            'certificados.generate', 'certificados.export',
            'declaracoes.view', 'declaracoes.create', 'declaracoes.edit',
            'declaracoes.generate', 'declaracoes.export',
            'templates.view', 'templates.create', 'templates.edit',
            'templates.activate', 'templates.deactivate',
            'ai.use', 'ai.configure',
            'eventos.view', 'eventos.create', 'eventos.edit',
            'formadores.view', 'formadores.create', 'formadores.edit', 'formadores.delete',
            'relatorios.view', 'relatorios.export',
            'configuracoes.view', 'configuracoes.edit',
            # Dashboard Analytics Permissions (Limited)
            'dashboard.view', 'dashboard.export', 'dashboard.drill_down',
            'dashboard.temporal_comparison', 'dashboard.advanced_filters',
            'dashboard.kpis.own_events', 'dashboard.visoes.own_events'
        },
        'ministrante': {
            'certificados.view', 'certificados.generate',
            'declaracoes.view', 'declaracoes.generate',
            'templates.view',
            'eventos.view',
            'relatorios.view',
            # Dashboard Analytics Permissions (Very Limited)
            'dashboard.view', 'dashboard.kpis.own_events', 'dashboard.visoes.basic'
        },
        'participante': {
            'certificados.view', 'certificados.download',
            'declaracoes.view', 'declaracoes.download',
            'eventos.view',
            # Dashboard Analytics Permissions (Read-only)
            'dashboard.view', 'dashboard.kpis.own_participation'
        }
    }
    
    user_permissions = permissions_map.get(current_role, set())
    return permission_name in user_permissions


def require_permission(permission_name, resource_id=None):
    """Decorator que exige uma permissão específica."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json:
                    return jsonify({'error': 'Autenticação necessária'}), 401
                return redirect(url_for('auth_routes.login'))
            
            if not has_permission(permission_name, resource_id):
                if request.is_json:
                    return jsonify({
                        'error': f'Permissão negada - {permission_name} necessária'
                    }), 403
                flash(f'Permissão negada - {permission_name} necessária!', 'danger')
                return redirect(url_for(endpoints.DASHBOARD))
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


def can_access_resource(resource_type, resource_id, action='view'):
    """Verifica se o usuário pode acessar um recurso específico."""
    if not current_user.is_authenticated:
        return False
    
    user_type = getattr(current_user, 'tipo', None)
    session_type = session.get('user_type')
    current_role = user_type or session_type
    
    # Super admin pode acessar tudo
    if current_role == 'superadmin':
        return True
    
    # Admin pode acessar tudo
    if current_role == 'admin':
        return True
    
    # Cliente pode acessar apenas seus próprios recursos
    if current_role == 'cliente':
        if resource_type in ['certificado', 'declaracao', 'template', 'evento']:
            # Verificar se o recurso pertence ao cliente
            from models import Cliente, Evento, CertificadoTemplateAvancado
            
            if resource_type == 'evento':
                evento = Evento.query.get(resource_id)
                return evento and evento.cliente_id == current_user.id
            
            elif resource_type == 'template':
                template = CertificadoTemplateAvancado.query.get(resource_id)
                return template and template.cliente_id == current_user.id
            
            # Para certificados e declarações, verificar através do evento
            # Implementar conforme necessário
            
        return False
    
    # Ministrante pode acessar apenas recursos relacionados aos seus eventos
    if current_role == 'ministrante':
        if action in ['view', 'download']:
            # Implementar verificação de acesso para ministrantes
            return True
        return False
    
    # Participante pode acessar apenas seus próprios certificados/declarações
    if current_role == 'participante':
        if action in ['view', 'download']:
            # Implementar verificação de acesso para participantes
            return True
        return False
    
    return False


def require_resource_access(resource_type, resource_id_param='id', action='view'):
    """Decorator que exige acesso a um recurso específico."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json:
                    return jsonify({'error': 'Autenticação necessária'}), 401
                return redirect(url_for('auth_routes.login'))
            
            # Obter o ID do recurso dos argumentos da função ou da URL
            resource_id = kwargs.get(resource_id_param)
            if not resource_id and resource_id_param in request.view_args:
                resource_id = request.view_args[resource_id_param]
            
            if not can_access_resource(resource_type, resource_id, action):
                if request.is_json:
                    return jsonify({
                        'error': f'Acesso negado ao {resource_type} {resource_id}'
                    }), 403
                flash(f'Acesso negado ao {resource_type}!', 'danger')
                return redirect(url_for(endpoints.DASHBOARD))
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


# =======================================
# Funções Auxiliares
# =======================================

def get_current_user_role():
    """Retorna o role do usuário atual."""
    if not current_user.is_authenticated:
        return None
    
    user_type = getattr(current_user, 'tipo', None)
    session_type = session.get('user_type')
    return user_type or session_type


def is_admin():
    """Verifica se o usuário atual é admin ou superadmin."""
    role = get_current_user_role()
    return role in ('admin', 'superadmin')


def is_superadmin():
    """Verifica se o usuário atual é superadmin."""
    role = get_current_user_role()
    return role == 'superadmin'


def is_cliente():
    """Verifica se o usuário atual é cliente."""
    role = get_current_user_role()
    return role == 'cliente'


def is_ministrante():
    """Verifica se o usuário atual é ministrante."""
    role = get_current_user_role()
    return role == 'ministrante'


def is_participante():
    """Verifica se o usuário atual é participante."""
    role = get_current_user_role()
    return role == 'participante'


def is_monitor():
    """Verifica se o usuário atual é monitor."""
    role = get_current_user_role()
    return role == 'monitor'


def log_access_attempt(action, resource_type=None, resource_id=None, success=True):
    """Registra tentativas de acesso para auditoria."""
    user_id = current_user.id if current_user.is_authenticated else None
    user_role = get_current_user_role()
    
    log_data = {
        'user_id': user_id,
        'user_role': user_role,
        'action': action,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'success': success,
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent')
    }
    
    if success:
        logger.info(f"Acesso autorizado: {log_data}")
    else:
        logger.warning(f"Acesso negado: {log_data}")


# =======================================
# Dashboard-Specific Access Control
# =======================================

def dashboard_access_required(_func=None, *, view_type='basic'):
    """Decorator que controla acesso às diferentes visões do dashboard.

    Pode ser usado com ou sem parâmetros:
    - @dashboard_access_required
    - @dashboard_access_required()
    - @dashboard_access_required(view_type='advanced')
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                log_access_attempt('dashboard_access', 'dashboard', view_type, False)
                if request.is_json:
                    return jsonify({'error': 'Autenticação necessária'}), 401
                return redirect(url_for('auth_routes.login'))

            # Verificar permissão básica de dashboard
            if not has_permission('dashboard.view'):
                log_access_attempt('dashboard_access', 'dashboard', view_type, False)
                if request.is_json:
                    return jsonify({'error': 'Acesso negado ao dashboard'}), 403
                flash('Acesso negado ao dashboard!', 'danger')
                return redirect(url_for(endpoints.DASHBOARD))

            # Verificar permissões específicas por tipo de visão
            current_role = get_current_user_role()

            if view_type == 'advanced' and current_role not in (
                'admin', 'superadmin', 'cliente'
            ):
                log_access_attempt('dashboard_advanced_access', 'dashboard', view_type, False)
                if request.is_json:
                    return jsonify({'error': 'Acesso negado às funcionalidades avançadas'}), 403
                flash('Acesso negado às funcionalidades avançadas!', 'danger')
                return redirect(url_for(endpoints.DASHBOARD))

            if view_type == 'audit' and not has_permission('dashboard.audit.view'):
                log_access_attempt('dashboard_audit_access', 'dashboard', view_type, False)
                if request.is_json:
                    return jsonify({'error': 'Acesso negado à auditoria'}), 403
                flash('Acesso negado à auditoria!', 'danger')
                return redirect(url_for(endpoints.DASHBOARD))

            log_access_attempt('dashboard_access', 'dashboard', view_type, True)
            return f(*args, **kwargs)

        return wrapper

    # Suporte a uso sem parâmetros: @dashboard_access_required
    if _func is None:
        return decorator
    else:
        return decorator(_func)


def dashboard_export_required(f):
    """Decorator que controla acesso às funcionalidades de exportação do dashboard."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            log_access_attempt('dashboard_export', 'dashboard', 'export', False)
            if request.is_json:
                return jsonify({'error': 'Autenticação necessária'}), 401
            return redirect(url_for('auth_routes.login'))
        
        if not has_permission('dashboard.export'):
            log_access_attempt('dashboard_export', 'dashboard', 'export', False)
            if request.is_json:
                return jsonify({'error': 'Acesso negado à exportação'}), 403
            flash('Acesso negado à exportação!', 'danger')
            return redirect(url_for(endpoints.DASHBOARD))
        
        log_access_attempt('dashboard_export', 'dashboard', 'export', True)
        return f(*args, **kwargs)
    return wrapper


def dashboard_drill_down_required(f):
    """Decorator que controla acesso às funcionalidades de drill-down."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            log_access_attempt('dashboard_drill_down', 'dashboard', 'drill_down', False)
            if request.is_json:
                return jsonify({'error': 'Autenticação necessária'}), 401
            return redirect(url_for('auth_routes.login'))
        
        if not has_permission('dashboard.drill_down'):
            log_access_attempt('dashboard_drill_down', 'dashboard', 'drill_down', False)
            if request.is_json:
                return jsonify({'error': 'Acesso negado ao drill-down'}), 403
            flash('Acesso negado ao drill-down!', 'danger')
            return redirect(url_for(endpoints.DASHBOARD))
        
        log_access_attempt('dashboard_drill_down', 'dashboard', 'drill_down', True)
        return f(*args, **kwargs)
    return wrapper


def can_access_dashboard_data(data_type, event_id=None):
    """Verifica se o usuário pode acessar dados específicos do dashboard."""
    if not current_user.is_authenticated:
        return False
    
    current_role = get_current_user_role()
    
    # Super admin e admin podem acessar todos os dados
    if current_role in ('superadmin', 'admin'):
        return True
    
    # Cliente pode acessar apenas dados de seus próprios eventos
    if current_role == 'cliente':
        if event_id:
            from models import Evento
            evento = Evento.query.get(event_id)
            return evento and evento.cliente_id == current_user.id
        return has_permission('dashboard.kpis.own_events')
    
    # Ministrante pode acessar apenas dados de eventos onde é instrutor
    if current_role == 'ministrante':
        if event_id:
            from models import Evento, EventoMinistrante
            evento_ministrante = EventoMinistrante.query.filter_by(
                evento_id=event_id,
                ministrante_id=current_user.id
            ).first()
            return evento_ministrante is not None
        return has_permission('dashboard.kpis.own_events')
    
    # Participante pode acessar apenas dados de sua própria participação
    if current_role == 'participante':
        if event_id:
            from models import Inscricao
            inscricao = Inscricao.query.filter_by(
                evento_id=event_id,
                participante_id=current_user.id
            ).first()
            return inscricao is not None
        return has_permission('dashboard.kpis.own_participation')
    
    return False


def get_dashboard_data_filter():
    """Retorna filtros de dados baseados no role do usuário."""
    if not current_user.is_authenticated:
        return None
    
    current_role = get_current_user_role()
    
    # Super admin e admin podem ver todos os dados
    if current_role in ('superadmin', 'admin'):
        return {}
    
    # Cliente pode ver apenas seus próprios eventos
    if current_role == 'cliente':
        return {'cliente_id': current_user.id}
    
    # Ministrante pode ver apenas eventos onde é instrutor
    if current_role == 'ministrante':
        from models import EventoMinistrante
        eventos_ids = [em.evento_id for em in EventoMinistrante.query.filter_by(
            ministrante_id=current_user.id
        ).all()]
        return {'evento_id__in': eventos_ids}
    
    # Participante pode ver apenas eventos onde está inscrito
    if current_role == 'participante':
        from models import Inscricao
        eventos_ids = [i.evento_id for i in Inscricao.query.filter_by(
            participante_id=current_user.id
        ).all()]
        return {'evento_id__in': eventos_ids}
    
    return None
