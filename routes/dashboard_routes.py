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
from utils.taxa_service import calcular_taxas_clientes
from sqlalchemy import func
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


@dashboard_routes.route('/api/alertas-orcamento')
@login_required
def api_alertas_orcamento():
    """API para obter alertas orçamentários do cliente."""
    from services.alerta_orcamento_service import AlertaOrcamentoService
    
    if current_user.tipo != 'cliente':
        return jsonify({'error': 'Acesso negado'}), 403
    
    ano = request.args.get('ano', type=int)
    alertas = AlertaOrcamentoService.obter_alertas_cliente(current_user.id, ano)
    
    return jsonify(alertas)


@dashboard_routes.route('/api/resumo-orcamentario')
@login_required
def api_resumo_orcamentario():
    """API para obter resumo orçamentário do cliente."""
    from services.alerta_orcamento_service import AlertaOrcamentoService
    
    if current_user.tipo != 'cliente':
        return jsonify({'error': 'Acesso negado'}), 403
    
    ano = request.args.get('ano', type=int)
    resumo = AlertaOrcamentoService.obter_resumo_orcamentario(current_user.id, ano)
    
    return jsonify(resumo)


@dashboard_routes.route('/api/verificar-disponibilidade-orcamentaria')
@login_required
def api_verificar_disponibilidade():
    """API para verificar disponibilidade orçamentária."""
    from services.alerta_orcamento_service import AlertaOrcamentoService
    
    if current_user.tipo != 'cliente':
        return jsonify({'error': 'Acesso negado'}), 403
    
    valor = request.args.get('valor', type=float)
    tipo_gasto = request.args.get('tipo_gasto', 'total')
    
    if not valor:
        return jsonify({'error': 'Valor é obrigatório'}), 400
    
    resultado = AlertaOrcamentoService.verificar_disponibilidade_orcamentaria(
        current_user.id, valor, tipo_gasto
    )
    
    return jsonify(resultado)

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

    estado_filter = (request.args.get("estado") or "").strip().upper()
    cidade_filter = (request.args.get("cidade") or "").strip()
    cidade_filter_upper = cidade_filter.upper()

    # Mapear localidades a partir das oficinas existentes
    from collections import defaultdict

    oficina_locais = db.session.query(
        Oficina.cliente_id, Oficina.estado, Oficina.cidade
    ).all()

    cidades_por_estado = defaultdict(set)
    estados_disponiveis = set()
    for cliente_id, estado, cidade in oficina_locais:
        if estado:
            estados_disponiveis.add(estado.upper())
            if cidade:
                cidades_por_estado[estado.upper()].add(cidade)
        elif cidade:
            cidades_por_estado[""].add(cidade)

    estados_opcoes = sorted(estados_disponiveis)
    cidades_por_estado_map = {
        uf: sorted(cidades)
        for uf, cidades in cidades_por_estado.items()
    }
    if estado_filter and estado_filter in cidades_por_estado_map:
        cidades_opcoes_iniciais = list(cidades_por_estado_map[estado_filter])
    else:
        cidades_opcoes_iniciais = sorted(
            {cidade for cidades in cidades_por_estado_map.values() for cidade in cidades}
        )

    cliente_query = Cliente.query.options(db.joinedload(Cliente.configuracao))
    if estado_filter or cidade_filter_upper:
        cliente_query = cliente_query.join(Oficina, Oficina.cliente_id == Cliente.id)
        if estado_filter:
            cliente_query = cliente_query.filter(func.upper(Oficina.estado) == estado_filter)
        if cidade_filter_upper:
            cliente_query = cliente_query.filter(func.upper(Oficina.cidade) == cidade_filter_upper)
        cliente_query = cliente_query.distinct()

    clientes = cliente_query.all()
    propostas = Proposta.query.order_by(Proposta.data_criacao.desc()).all()
    configuracao = Configuracao.query.first()

    # Garantir que todos os clientes tenham uma configuração
    for cliente in clientes:
        if not getattr(cliente, "configuracao", None):
            from models import ConfiguracaoCliente

            nova_config = ConfiguracaoCliente(cliente_id=cliente.id)
            db.session.add(nova_config)
            db.session.commit()
            cliente.configuracao = nova_config

    # Dados financeiros gerais
    # ------------------------------------------------------------------
    taxa_geral = float(configuracao.taxa_percentual_inscricao or 0) if configuracao else 0.0

    cliente_ids = [cliente.id for cliente in clientes]

    if cliente_ids:
        evento_query = Evento.query.filter(Evento.cliente_id.in_(cliente_ids))
        oficinas_query = Oficina.query.options(db.joinedload(Oficina.inscritos)).filter(
            Oficina.cliente_id.in_(cliente_ids)
        )
        inscricoes_query = Inscricao.query.join(Evento).filter(
            Evento.cliente_id.in_(cliente_ids)
        )
        inscricoes_pagas_query = (
            Inscricao.query
            .join(Evento)
            .filter(
                Inscricao.status_pagamento == "approved",
                Evento.inscricao_gratuita.is_(False),
                Evento.cliente_id.in_(cliente_ids),
            )
            .options(db.joinedload(Inscricao.evento))
        )
        inscricoes_pagas = inscricoes_pagas_query.all()
        oficinas = oficinas_query.all()
        total_eventos = evento_query.count()
        total_oficinas = len(oficinas)
        total_inscricoes = inscricoes_query.count()
    else:
        inscricoes_pagas = []
        oficinas = []
        total_eventos = 0
        total_oficinas = 0
        total_inscricoes = 0

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
                "usando_taxa_diferenciada": False,
                "taxa_aplicada": taxa_geral,
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

    if financeiro_clientes:
        calcular_taxas_clientes(clientes, financeiro_clientes, taxa_geral)

    total_eventos_receita = sum(len(c["eventos"]) for c in financeiro_clientes.values())
    receita_total = sum(c["receita_total"] for c in financeiro_clientes.values())
    receita_taxas = sum(c["taxas"] for c in financeiro_clientes.values())

    total_vagas = 0
    for of in oficinas:
        if of.tipo_inscricao == "com_inscricao_com_limite":
            total_vagas += of.vagas
        elif of.tipo_inscricao == "com_inscricao_sem_limite":
            total_vagas += len(of.inscritos)

    percentual_adesao = (
        (total_inscricoes / total_vagas) * 100 if total_vagas > 0 else 0
    )

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
        estados_opcoes=estados_opcoes,
        cidades_opcoes=cidades_opcoes_iniciais,
        cidades_por_estado=cidades_por_estado_map,
    )


@dashboard_routes.route("/dashboard_admin/ordenar_atividades", methods=["GET", "POST"])
@login_required
def ordenar_atividades_admin():
    """Permite ordenar a exibição de atividades por data no link de cadastro."""
    if not current_app.config.get("LOGIN_DISABLED") and getattr(current_user, "tipo", None) != "admin":
        abort(403)

    from collections import defaultdict
    from models import Evento, Oficina, OficinaDia
    from extensions import db

    evento_id = request.args.get("evento_id", type=int) or request.form.get("evento_id", type=int)
    eventos = Evento.query.order_by(Evento.data_inicio.desc().nullslast(), Evento.nome.asc()).all()
    evento = Evento.query.get(evento_id) if evento_id else None

    grouped_dias = {}
    if evento:
        oficina_dias = (
            OficinaDia.query.join(Oficina, Oficina.id == OficinaDia.oficina_id)
            .filter(Oficina.evento_id == evento.id)
            .all()
        )

        if request.method == "POST":
            atualizados = 0
            for dia in oficina_dias:
                campo = f"ordem_{dia.id}"
                if campo not in request.form:
                    continue
                valor = request.form.get(campo, "").strip()
                if valor == "":
                    dia.ordem_exibicao = None
                    atualizados += 1
                    continue
                try:
                    dia.ordem_exibicao = int(valor)
                    atualizados += 1
                except ValueError:
                    continue
            db.session.commit()
            flash(f"Ordem atualizada para {atualizados} atividades.", "success")
            return redirect(
                url_for("dashboard_routes.ordenar_atividades_admin", evento_id=evento.id)
            )

        agrupado = defaultdict(list)
        for dia in oficina_dias:
            data_str = dia.data.strftime("%d/%m/%Y")
            agrupado[data_str].append(dia)
        grouped_dias = dict(agrupado)
        for data_key, itens in grouped_dias.items():
            itens.sort(
                key=lambda item: (
                    item.ordem_exibicao if item.ordem_exibicao is not None else 9999,
                    item.horario_inicio or "",
                    item.oficina.titulo.lower(),
                )
            )

    return render_template(
        "dashboard/ordenar_atividades.html",
        eventos=eventos,
        evento=evento,
        grouped_dias=grouped_dias,
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
