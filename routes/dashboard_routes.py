from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    abort,
    request,
    current_app,
    jsonify
)
from flask_login import login_required, current_user, login_user
from utils.taxa_service import calcular_taxa_cliente, calcular_taxas_clientes
from services.template_service import TemplateService
from utils import endpoints

dashboard_routes = Blueprint(
    'dashboard_routes',
    __name__,
    template_folder="../templates/dashboard"
)
# ────────────────────────────────────────
# DASHBOARD GERAL (admin, cliente, participante, professor)
# ────────────────────────────────────────
@dashboard_routes.route('/dashboard')
@login_required
def dashboard():
    tipo = getattr(current_user, "tipo", None)

    if tipo == "admin":
        return redirect(url_for(endpoints.DASHBOARD_ADMIN))

    elif tipo == "cliente":
        return redirect(url_for(endpoints.DASHBOARD_CLIENTE))

    elif tipo == "participante":
        return redirect(
            url_for("dashboard_participante_routes.dashboard_participante")
        )

    elif tipo == "ministrante":
        return redirect(
            url_for("formador_routes.dashboard_formador")
        )

    elif tipo == "professor":
        return redirect(url_for("dashboard_professor.dashboard_professor"))

    elif tipo == "superadmin":
        return redirect(url_for(endpoints.DASHBOARD_SUPERADMIN))

    abort(403)

@dashboard_routes.route("/dashboard_admin")
@login_required
def dashboard_admin():
    """Renderiza o dashboard do administrador com estatísticas do sistema."""
    from flask import current_app, abort

    # Se o login não está desabilitado e o usuário logado não é admin → 403
    if not current_app.config.get("LOGIN_DISABLED") and getattr(current_user, "tipo", None) != "admin":
        abort(403)


    from models import (
        Evento,
        Oficina,
        Inscricao,
        Cliente,
        Configuracao,
        Proposta,
        EventoInscricaoTipo,
        LoteTipoInscricao,
    )
    from extensions import db

    total_eventos = Evento.query.count()
    total_oficinas = Oficina.query.count()
    total_inscricoes = Inscricao.query.count()

    # Calculo de vagas oferecidas considerando o tipo de inscrição
    oficinas = Oficina.query.options(db.joinedload(Oficina.inscritos)).all()
    total_vagas = 0
    for of in oficinas:
        if of.tipo_inscricao == "com_inscricao_com_limite":
            total_vagas += of.vagas
        elif of.tipo_inscricao == "com_inscricao_sem_limite":
            total_vagas += len(of.inscritos)

    percentual_adesao = (total_inscricoes / total_vagas) * 100 if total_vagas > 0 else 0    # Obter todos os clientes com suas configurações (para taxas diferenciadas)
    clientes = Cliente.query.options(db.joinedload(Cliente.configuracao)).all()
    propostas = Proposta.query.order_by(Proposta.data_criacao.desc()).all()
    configuracao = Configuracao.query.first()
    
    # Garantir que todos os clientes tenham uma configuração
    for cliente in clientes:
        if not hasattr(cliente, 'configuracao') or cliente.configuracao is None:
            from models import ConfiguracaoCliente
            nova_config = ConfiguracaoCliente(cliente_id=cliente.id)
            db.session.add(nova_config)
            db.session.commit()
            cliente.configuracao = nova_config    # ------------------------------------------------------------------
    # Dados financeiros gerais
    # ------------------------------------------------------------------
    taxa_geral = float(configuracao.taxa_percentual_inscricao or 0) if configuracao else 0.0

    inscricoes_pagas = (
        Inscricao.query
        .join(Evento)
        .filter(
            Inscricao.status_pagamento == "approved",
            Evento.inscricao_gratuita.is_(False)
        )
        .options(db.joinedload(Inscricao.evento))
        .all()
    )

    financeiro_clientes = {}
    for ins in inscricoes_pagas:
        evento = ins.evento
        if not evento:
            continue
        cliente = evento.cliente
        cinfo = financeiro_clientes.setdefault(
            cliente.id,
            {
                "nome": cliente.nome,
                "receita_total": 0.0,
                "taxas": 0.0,
                "eventos": {},
            },
        )

        preco = 0.0
        if ins.lote_id and evento.habilitar_lotes:
            lti = LoteTipoInscricao.query.filter_by(
                lote_id=ins.lote_id,
                tipo_inscricao_id=ins.tipo_inscricao_id,
            ).first()
            if lti:
                preco = float(lti.preco)
        else:
            eit = EventoInscricaoTipo.query.get(ins.tipo_inscricao_id)
            if eit:
                preco = float(eit.preco)
        einfo = cinfo["eventos"].setdefault(
            evento.id,
            {"nome": evento.nome, "quantidade": 0, "receita": 0.0},
        )
        einfo["quantidade"] += 1
        einfo["receita"] += preco
        cinfo["receita_total"] += preco
      # Aplicar o cálculo de taxas utilizando o serviço centralizado    calcular_taxas_clientes(clientes, financeiro_clientes, taxa_geral)

    total_eventos_receita = sum(len(c["eventos"]) for c in financeiro_clientes.values())
    receita_total = sum(c["receita_total"] for c in financeiro_clientes.values())
    receita_taxas = sum(c["taxas"] for c in financeiro_clientes.values())

    estado_filter = request.args.get("estado")
    cidade_filter = request.args.get("cidade")

    return render_template(
        "dashboard/dashboard_admin.html",
        total_eventos=total_eventos,
        total_oficinas=total_oficinas,
        total_inscricoes=total_inscricoes,
        percentual_adesao=percentual_adesao,
        clientes=clientes,
        propostas=propostas,
        configuracao=configuracao,
        finance_clientes=list(financeiro_clientes.values()),
        total_eventos_receita=total_eventos_receita,
        receita_total=receita_total,
        receita_taxas=receita_taxas,
        estado_filter=estado_filter,
        cidade_filter=cidade_filter,
    )


@dashboard_routes.route("/dashboard_superadmin")
@login_required
def dashboard_superadmin():
    """Painel reservado ao superadministrador."""
    if not current_app.config.get("LOGIN_DISABLED") and getattr(current_user, "tipo", None) != "superadmin":
        abort(403)

    from models import Cliente
    clientes = Cliente.query.all()

    return render_template(
        "dashboard/dashboard_superadmin.html",
        clientes=clientes,
    )


@dashboard_routes.route('/inicializar_templates/<int:cliente_id>', methods=['POST'])
@login_required
def inicializar_templates(cliente_id: int):
    """Inicializa templates pré-definidos para um cliente."""
    if current_user.tipo not in {'admin', 'superadmin'}:
        abort(403)
    
    try:
        from models import Cliente
        cliente = Cliente.query.get_or_404(cliente_id)
        
        resultado = TemplateService.inicializar_templates_cliente(cliente_id)
        
        flash(f'Templates inicializados com sucesso! {resultado["certificados"]} templates de certificados e {resultado["declaracoes"]} templates de declarações criados.', 'success')
        
        return jsonify({
            'success': True,
            'message': f'Templates inicializados com sucesso!',
            'certificados': resultado['certificados'],
            'declaracoes': resultado['declaracoes']
        })
    
    except Exception as e:
        flash(f'Erro ao inicializar templates: {str(e)}', 'error')
        return jsonify({
            'success': False,
            'message': f'Erro ao inicializar templates: {str(e)}'
        }), 500

@dashboard_routes.route('/login_as_cliente/<int:cliente_id>')
@login_required
def login_as_cliente(cliente_id: int):
    """Permite que um admin assuma a sessão de um cliente."""
    if current_user.tipo not in {'admin', 'superadmin'}:
        abort(403)

    from models import Cliente, Usuario
    admin_id = current_user.get_id()
    session['impersonator_id'] = admin_id
    session['impersonator_type'] = current_user.tipo

    cliente = Cliente.query.get_or_404(cliente_id)

    login_user(cliente)
    session['user_type'] = 'cliente'

    return redirect(url_for(endpoints.DASHBOARD_CLIENTE))


@dashboard_routes.route('/login_as_usuario/<int:usuario_id>')
@login_required
def login_as_usuario(usuario_id: int):
    """Permite que um admin assuma a sessão de um usuário comum."""
    if current_user.tipo not in {'admin', 'superadmin'}:
        abort(403)

    from models import Usuario

    admin_id = current_user.get_id()
    session['impersonator_id'] = admin_id
    session['impersonator_type'] = current_user.tipo

    usuario = Usuario.query.get_or_404(usuario_id)

    login_user(usuario)
    session['user_type'] = usuario.tipo

    return redirect(url_for(endpoints.DASHBOARD))


@dashboard_routes.route('/encerrar_impersonacao')
@login_required
def encerrar_impersonacao():
    """Retorna o usuário logado ao modo administrador."""
    impersonator_id = session.get('impersonator_id')
    impersonator_type = session.get('impersonator_type', 'admin')

    if not impersonator_id:
        return redirect(url_for(endpoints.DASHBOARD))

    from models import Usuario
    admin = Usuario.query.get_or_404(int(impersonator_id))

    login_user(admin)
    session['user_type'] = impersonator_type

    session.pop('impersonator_id', None)
    session.pop('impersonator_type', None)

    return redirect(url_for(endpoints.DASHBOARD_ADMIN))
