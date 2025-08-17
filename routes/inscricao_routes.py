from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from utils.security import sanitize_input
from flask_login import login_required, current_user
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

    Evento, Oficina, Inscricao, Usuario, LinkCadastro,
    LoteInscricao, EventoInscricaoTipo, LoteTipoInscricao,
    CampoPersonalizadoCadastro, RespostaCampo, RespostaFormulario, Formulario, RegraInscricaoEvento,
    Patrocinador, Ministrante, InscricaoTipo, ConfiguracaoCliente, ConfiguracaoEvento, Cliente
)
import os
from mp_fix_patch import fix_mp_notification_url, create_mp_preference
import uuid
import logging
from dateutil import parser

# Configuração de logging
logger = logging.getLogger(__name__)
from sqlalchemy import func, or_, and_
from services.lote_service import lote_disponivel
from utils import external_url, preco_com_taxa, gerar_comprovante_pdf, enviar_email
from forms import RegraInscricaoEventoForm


class LoteEsgotadoError(RuntimeError):
    """Lançada quando o lote escolhido não possui mais vagas."""
    pass

inscricao_routes = Blueprint('inscricao_routes', __name__)


@inscricao_routes.route("/inscricao/<identifier>", methods=["GET", "POST"])
def cadastro_participante(identifier: str | None = None):
    """Realiza o cadastro de um participante em um evento."""

    from services.mp_service import get_sdk

    # ------------------------------------------------------------------
    # 1) Localiza o link e o evento relacionados
    # ------------------------------------------------------------------
    link = LinkCadastro.query.filter(
        (LinkCadastro.token == identifier) |
        (LinkCadastro.slug_customizado == identifier)
    ).first()

    evento = None
    cliente_id = None

    if link:
        evento = link.evento
        cliente_id = link.cliente_id
    else:
        if identifier.isdigit():
            evento = Evento.query.get(int(identifier))
            if evento and evento.publico and evento.status == "ativo" and not evento.requer_aprovacao:
                cliente_id = evento.cliente_id
            else:
                evento = None
        else:
            flash("Link de inscrição inválido.", "danger")
            return redirect(url_for("evento_routes.home"))

    if not evento:
        flash("Evento não encontrado.", "danger")
        return redirect(url_for("evento_routes.home"))

    # ------------------------------------------------------------------
    # 2) Determina lote vigente e tipos de inscrição
    # ------------------------------------------------------------------
    lote_vigente = None
    lotes_ativos = []
    if evento.habilitar_lotes:
        lotes_ativos = LoteInscricao.query.filter_by(evento_id=evento.id, ativo=True).all()
        now = datetime.utcnow()
        for lote in lotes_ativos:
            valido = True
            if lote.data_inicio and lote.data_fim:
                valido = lote.data_inicio <= now <= lote.data_fim
            if valido and lote.tipos_inscricao:
                lote_vigente = lote
                break

    tipos_inscricao = EventoInscricaoTipo.query.filter_by(evento_id=evento.id).all()

    # ------------------------------------------------------------------
    # 3) Processamento do POST
    # ------------------------------------------------------------------
    if request.method == "POST":
        nome = sanitize_input(request.form.get("nome", "").strip())
        cpf = sanitize_input(request.form.get("cpf", "").strip())
        email = sanitize_input(request.form.get("email", "").strip())
        senha = sanitize_input(request.form.get("senha"))
        formacao = sanitize_input(request.form.get("formacao", ""))
        estados = [sanitize_input(e) for e in request.form.getlist("estados[]")]
        cidades = [sanitize_input(c) for c in request.form.getlist("cidades[]")]
        lote_id = request.form.get("lote_id")
        lote_tipo_id = request.form.get("lote_tipo_inscricao_id")
        tipo_insc_id = request.form.get("tipo_inscricao_id")

        try:
            config_cli = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()

            def obrig(attr):
                return getattr(config_cli, attr) if config_cli else True

            total_insc = Inscricao.query.filter_by(cliente_id=cliente_id).count()
            if config_cli and config_cli.limite_inscritos is not None and total_insc >= config_cli.limite_inscritos:
                flash('Limite de inscritos atingido.', 'danger')
                return _render_form(link=link, evento=evento, lote_vigente=lote_vigente,
                                   lotes_ativos=lotes_ativos, cliente_id=cliente_id)

            if (
                (obrig("obrigatorio_nome") and not nome) or
                (obrig("obrigatorio_cpf") and not cpf) or
                (obrig("obrigatorio_email") and not email) or
                (obrig("obrigatorio_senha") and not senha) or
                (obrig("obrigatorio_formacao") and not formacao)
            ):
                raise ValueError("Preencha todos os campos obrigatórios.")

            duplicado = Usuario.query.filter(
                (Usuario.email == email) | (Usuario.cpf == cpf)
            ).first()

            usuario = None
            if duplicado:
                if not check_password_hash(duplicado.senha, senha):
                    flash("Senha incorreta. Faça login.", "warning")
                    return redirect(url_for("auth_routes.login"))
                usuario = duplicado
                inscr_existente = Inscricao.query.filter_by(
                    usuario_id=duplicado.id, evento_id=evento.id
                ).first()
                if inscr_existente:
                    flash("Você já possui inscrição neste evento. Faça login.", "warning")
                    return redirect(url_for("auth_routes.login"))

            resolved_tipo = None
            if lote_tipo_id:
                lt = LoteTipoInscricao.query.get(lote_tipo_id)
                if not lt:
                    raise ValueError("Tipo de inscrição inválido.")
                resolved_tipo = lt.tipo_inscricao_id
                lote_id = lt.lote_id
            elif tipo_insc_id:
                resolved_tipo = int(tipo_insc_id)

            if lote_id:
                _reservar_vaga(int(lote_id))

            if not usuario:
                usuario = Usuario(
                    nome=nome,
                    cpf=cpf,
                    email=email,
                    senha=generate_password_hash(senha),
                    formacao=formacao,
                    tipo="participante",
                    cliente_id=cliente_id,
                    evento_id=evento.id,
                    tipo_inscricao_id=resolved_tipo,
                    estados=",".join(estados) if estados else None,
                    cidades=",".join(cidades) if cidades else None,
                )
                db.session.add(usuario)
                db.session.flush()
            else:
                if usuario.evento_id != evento.id:
                    usuario.evento_id = evento.id
                    if current_user.is_authenticated and current_user.id == usuario.id:
                        current_user.evento_id = evento.id

            cliente_obj = Cliente.query.get(cliente_id)
            if cliente_obj and cliente_obj not in usuario.clientes:
                usuario.clientes.append(cliente_obj)

            inscricao = Inscricao(
                usuario_id=usuario.id,
                evento_id=evento.id,
                cliente_id=cliente_id,
                lote_id=lote_id if lote_id else None,
                tipo_inscricao_id=resolved_tipo,
            )
            db.session.add(inscricao)

            _salvar_campos_personalizados(usuario.id, cliente_id, request.form)

            preco, titulo = _calcular_preco(evento, lote_tipo_id, tipo_insc_id, lote_vigente)
            sdk = get_sdk()
            if preco > 0 and sdk:
                url_pagamento = _criar_preferencia_mp(sdk, preco, titulo, inscricao, usuario)
                db.session.commit()
                return redirect(url_pagamento)

            inscricao.status_pagamento = "approved"
            db.session.commit()
            if duplicado:
                flash("Conta já existente. Utilize seus dados para acessar.", "info")
            else:
                flash("Inscrição realizada com sucesso!", "success")
            return redirect(url_for("auth_routes.login"))

        except LoteEsgotadoError:
            db.session.rollback()
            flash("Lote esgotado. Escolha outro tipo de inscrição.", "danger")
            return redirect(url_for("inscricao_routes.cadastro_participante", identifier=identifier))
        except Exception as e:
            logging.exception("Erro no cadastro de participante")
            db.session.rollback()
            flash(str(e), "danger")
            return _render_form(link=link, evento=evento, lote_vigente=lote_vigente,
                               lotes_ativos=lotes_ativos, cliente_id=cliente_id)

    # ------------------------------------------------------------------
    # 4) GET - apenas renderiza o formulário
    # ------------------------------------------------------------------
    return _render_form(link=link, evento=evento, lote_vigente=lote_vigente,
                        lotes_ativos=lotes_ativos, cliente_id=cliente_id)




# ---------------------------------------------------------------------------
# Helpers (visão alta: poderiam ir para app.services)
# ---------------------------------------------------------------------------

def _reservar_vaga(lote_id: int) -> None:
    """Bloqueia linha do lote e garante que ainda têm vagas."""
    lote = (
        LoteInscricao.query.filter_by(id=lote_id)
        .with_for_update(nowait=True)
        .first()
    )
    if not lote or not lote_disponivel(lote):
        raise LoteEsgotadoError()


def _salvar_campos_personalizados(user_id: int, cliente_id: int, form):
    """Salva respostas de campos personalizados vinculadas a um RespostaFormulario."""

    # Formulário padrão para o cadastro de participante utilizado quando
    # não há um formulário específico configurado.
    formulario = Formulario.query.get(1)
    if not formulario:
        formulario = Formulario(id=1, nome="Cadastro de Participante")
        db.session.add(formulario)
        db.session.commit()

    resposta_formulario = RespostaFormulario(
        formulario_id=formulario.id,
        usuario_id=user_id,
    )
    db.session.add(resposta_formulario)
    db.session.flush()  # obtém ID para relacionar as respostas

    campos = CampoPersonalizadoCadastro.query.filter_by(cliente_id=cliente_id).all()
    for campo in campos:
        valor = form.get(f"campo_{campo.id}") or ""
        if campo.obrigatorio and not valor:
            raise ValueError(f"O campo '{campo.nome}' é obrigatório.")
        db.session.add(
            RespostaCampo(
                resposta_formulario_id=resposta_formulario.id,
                campo_id=campo.id,
                valor=valor,
            )
        )

    return resposta_formulario.id


def _calcular_preco(evento, lote_tipo_insc_id, tipo_insc_id, lote_vigente):
    preco = 0.0
    titulo = "Inscrição"

    if evento and evento.inscricao_gratuita:
        return preco, titulo

    if lote_tipo_insc_id and evento and evento.habilitar_lotes:
        lote_tipo = LoteTipoInscricao.query.get(lote_tipo_insc_id)
        if lote_tipo:
            preco = float(lote_tipo.preco)
            ti = EventoInscricaoTipo.query.get(lote_tipo.tipo_inscricao_id)
            titulo = f"Inscrição – {evento.nome} – {ti.nome} ({lote_vigente.nome})"
    elif tipo_insc_id:
        ti = EventoInscricaoTipo.query.get(tipo_insc_id)
        if ti:
            preco = float(ti.preco)
            titulo = f"Inscrição – {evento.nome} – {ti.nome}"
    return preco, titulo


def _criar_preferencia_mp(sdk, preco: float, titulo: str, inscricao: Inscricao, usuario: Usuario) -> str:
    """Gera preferência MP e devolve URL de pagamento."""
    # Aplicar a taxa configurada ao preço, considerando cliente_id da inscrição
    logging.info(f"Criando preferência MP: preco={preco}, titulo='{titulo}', inscricao_id={inscricao.id}, usuario_id={usuario.id}, cliente_id={inscricao.cliente_id}")
    
    try:
        preco_final = preco_com_taxa(preco, cliente_id=inscricao.cliente_id)
        logging.info(f"Preço com taxa aplicada: {preco_final}")
    except Exception as e:
        logging.exception(f"Erro ao calcular preço com taxa: {str(e)}")
        # Usar o preço original se houver erro no cálculo da taxa
        preco_final = float(preco)
        logging.info(f"Usando preço original: {preco_final}")
    # Construir as URLs para o Mercado Pago
    try:
        # Obter o hostname válido para as URLs
        app_url = os.getenv("APP_BASE_URL")
        if not app_url or not app_url.strip():
            app_url = request.host_url.rstrip('/')
            if not app_url.startswith(('http://', 'https://')):
                app_url = f"https://{app_url}"
        elif not app_url.startswith(('http://', 'https://')):
            app_url = f"https://{app_url}"
            
        logging.info(f"Base URL para Mercado Pago: {app_url}")
            
        # Gerar URLs completas e válidas
        notification_url = external_url("mercadopago_routes.webhook_mp")
        success_url = external_url("mercadopago_routes.pagamento_sucesso")
        failure_url = external_url("mercadopago_routes.pagamento_falha")
        pending_url = external_url("mercadopago_routes.pagamento_pendente")
        
        # Verificar se as URLs são válidas
        for url_name, url in [
            ("notification_url", notification_url),
            ("success_url", success_url),
            ("failure_url", failure_url),
            ("pending_url", pending_url)
        ]:
            if not url.startswith(('http://', 'https://')):
                logging.warning(f"URL inválida '{url_name}': {url} - Ajustando...")
                # Adicionar protocolo https:// se não houver
                fixed_url = f"https://{url}" if '://' not in url else url
                
                if url_name == "notification_url":
                    notification_url = fixed_url
                elif url_name == "success_url":
                    success_url = fixed_url
                elif url_name == "failure_url":
                    failure_url = fixed_url
                elif url_name == "pending_url":
                    pending_url = fixed_url
                    
        # Validar novamente todas as URLs para garantir que são URLs absolutas válidas
        for url_name, url in [
            ("notification_url", notification_url),
            ("success_url", success_url),
            ("failure_url", failure_url),
            ("pending_url", pending_url)
        ]:
            if not url.startswith(('http://', 'https://')):
                logging.error(f"URL ainda inválida para {url_name}: {url}")
                # Usar uma URL absoluta construída manualmente como fallback
                fixed_url = f"{app_url}/mercadopago/{url_name.replace('_url', '')}"
                
                if url_name == "notification_url":
                    notification_url = fixed_url.replace('notification', 'webhook')
                elif url_name == "success_url":
                    success_url = fixed_url.replace('success', 'pagamento_sucesso')
                elif url_name == "failure_url":
                    failure_url = fixed_url.replace('failure', 'pagamento_falha')
                elif url_name == "pending_url":
                    pending_url = fixed_url.replace('pending', 'pagamento_pendente')
        
        logging.info(f"URLs finais para MP: notification={notification_url}, success={success_url}, failure={failure_url}, pending={pending_url}")
    except Exception as e:
        logging.exception(f"Erro ao gerar URLs: {str(e)}")
        # Uso do fallback simples para as URLs
        base_url = os.getenv("APP_BASE_URL") or "https://sistema.evento.com"
        if not base_url.startswith(('http://', 'https://')):
            base_url = f"https://{base_url}"
        notification_url = f"{base_url}/mercadopago/webhook"
        success_url = f"{base_url}/mercadopago/sucesso"
        failure_url = f"{base_url}/mercadopago/falha"
        pending_url = f"{base_url}/mercadopago/pendente"
        logging.info(f"Usando URLs de fallback: notification={notification_url}, success={success_url}")
      # Dados para a API do Mercado Pago, garantindo formato correto
    preference_data = {
        "items": [
            {
                "id": str(inscricao.id),
                "title": titulo,
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": float(preco_final),
            }
        ],
        "payer": {"email": usuario.email, "name": usuario.nome},
        "external_reference": str(inscricao.id),
        "back_urls": {
            "success": success_url,
            "failure": failure_url,
            "pending": pending_url,
        },
        "notification_url": notification_url,
    }
      # Log detalhado dos parâmetros sendo enviados
    logging.info(f"Dados da preferência MP: {preference_data}")
    
    auto_return = os.getenv("MP_AUTO_RETURN")
    if auto_return:
        preference_data["auto_return"] = auto_return
        
    # Adicionar o campo notificaction_url para contornar possível bug no MP ou SDK
    if "notification_url" in preference_data:
        preference_data["notificaction_url"] = preference_data["notification_url"]
        logging.info("Adicionado campo notificaction_url como fallback")
    
    try:
        # Tenta criar a preferência com o SDK
        # Usar a função segura de criação de preferência

        pref = create_mp_preference(sdk, preference_data)
        logging.info(f"Preferência MP criada: {pref}")
    except Exception as exc:
        logging.exception(f"Erro ao chamar API do Mercado Pago: {str(exc)}")
        
        # Se o erro for relacionado à URL de notificação, tente com a correção
        if "notification_url" in str(exc) or "notificaction_url" in str(exc):
            logging.warning("Erro relacionado à URL de notificação. Tentando corrigir...")
            try:
                # Cria uma cópia dos dados e adiciona notificaction_url
                corrected_data = preference_data.copy()
                corrected_data["notificaction_url"] = preference_data["notification_url"]
                
                # Tenta novamente com os dados corrigidos
                pref = sdk.preference().create(corrected_data)
                logging.info(f"Preferência MP criada após correção: {pref}")
            except Exception as exc2:
                logging.exception(f"Falha na segunda tentativa: {str(exc2)}")
                if hasattr(exc2, 'response'):
                    logging.error(f"Resposta de erro do MP: {exc2.response}")
                raise RuntimeError(f"Falha ao criar preferência de pagamento após correção: {str(exc2)}") from exc2
        else:
            # Detalhando o erro para melhor diagnóstico
            if hasattr(exc, 'response'):
                logging.error(f"Resposta de erro do MP: {exc.response}")
            raise RuntimeError(f"Falha ao criar preferência de pagamento: {str(exc)}") from exc

    init_point = pref.get("response", {}).get("init_point")
    if not init_point:
        logging.error(f"Resposta inesperada do Mercado Pago: {pref}")
        raise RuntimeError("Falha ao criar preferência de pagamento: URL de redirecionamento não encontrada na resposta.")
    inscricao.payment_id = pref["response"].get("id")
    db.session.flush()
    return init_point


def _render_form(*, link, evento, lote_vigente, lotes_ativos, cliente_id):
    """Coleta dados de contexto e renderiza template."""
    from collections import defaultdict

    if evento:
        query = Oficina.query.filter(
            or_(
                Oficina.evento_id == evento.id,
                and_(
                    Oficina.evento_id.is_(None),
                    or_(
                        Oficina.cliente_id == evento.cliente_id,
                        Oficina.cliente_id.is_(None)
                    )
                )
            )
        )
        oficinas = query.all()
    else:
        oficinas = []

    # Coleta ministrantes associados ao evento tanto diretamente quanto via
    # relacionamento many-to-many. Utiliza um set para evitar duplicidade
    # quando o mesmo ministrante participa de mais de uma oficina.
    ministrantes_set = set()
    if evento:
        for ofi in oficinas:
            if ofi.ministrante_obj:
                ministrantes_set.add(ofi.ministrante_obj)
            if hasattr(ofi, "ministrantes_associados"):
                ministrantes_set.update(ofi.ministrantes_associados.all())
    ministrantes = sorted(ministrantes_set, key=lambda m: m.nome)

    grouped_oficinas: dict[str, list] = defaultdict(list)
    for oficina in oficinas:
        for dia in getattr(oficina, "dias", []):
            data_str = dia.data.strftime("%d/%m/%Y")
            grouped_oficinas[data_str].append(
                {
                    "oficina": oficina,
                    "titulo": oficina.titulo,
                    "descricao": oficina.descricao,
                    "ministrante": oficina.ministrante_obj,
                    "horario_inicio": dia.horario_inicio,
                    "horario_fim": dia.horario_fim,
                }
            )
    sorted_keys = sorted(grouped_oficinas.keys(), key=lambda d: parser.parse(d, dayfirst=True))

    campos_personalizados = CampoPersonalizadoCadastro.query.filter_by(cliente_id=cliente_id).all()
    patrocinadores = Patrocinador.query.filter_by(evento_id=evento.id).all() if evento else []

    # Tipos de inscrição
    if evento and evento.habilitar_lotes and lote_vigente:
        tipos_inscricao = lote_vigente.tipos_inscricao
    elif evento:
        tipos_inscricao = (
            EventoInscricaoTipo.query.filter_by(evento_id=evento.id).order_by(EventoInscricaoTipo.nome).all()
        )
    else:
        tipos_inscricao = []

    config_cli = ConfiguracaoCliente.query.filter_by(cliente_id=cliente_id).first()
    config_evento = (
        ConfiguracaoEvento.query.filter_by(evento_id=evento.id).first() if evento else None
    )

    def _cfg(field: str, default: bool = True) -> bool:
        if config_evento and getattr(config_evento, field) is not None:
            return getattr(config_evento, field)
        if config_cli and getattr(config_cli, field) is not None:
            return getattr(config_cli, field)
        return default

    mostrar_taxa = _cfg("mostrar_taxa", True)
    obrigatorio_nome = _cfg("obrigatorio_nome", True)
    obrigatorio_cpf = _cfg("obrigatorio_cpf", True)
    obrigatorio_email = _cfg("obrigatorio_email", True)
    obrigatorio_senha = _cfg("obrigatorio_senha", True)
    obrigatorio_formacao = _cfg("obrigatorio_formacao", True)

    # Estatísticas do lote vigente
    lote_stats = None
    if lote_vigente:
        count = (
            db.session.query(func.count(Inscricao.id))
            .filter(
                Inscricao.evento_id == evento.id,
                Inscricao.lote_id == lote_vigente.id,
                Inscricao.status_pagamento.in_(["approved", "pending"]),
            )
            .scalar()
        )
        vagas_disp = (
            lote_vigente.qtd_maxima - count if lote_vigente.qtd_maxima else "ilimitado"
        )
        lote_stats = {
            "nome": lote_vigente.nome,
            "vagas_totais": lote_vigente.qtd_maxima or "ilimitado",
            "vagas_usadas": count,
            "vagas_disponiveis": vagas_disp,
            "data_inicio": lote_vigente.data_inicio.strftime("%d/%m/%Y") if lote_vigente.data_inicio else "Imediato",
            "data_fim": lote_vigente.data_fim.strftime("%d/%m/%Y") if lote_vigente.data_fim else "Não definido",
        }

    token = link.token if link else str(evento.id)
    
    return render_template("auth/cadastro_participante.html",
        token=token,
        evento=evento,
        sorted_keys=sorted_keys,
        grouped_oficinas=grouped_oficinas,
        ministrantes=ministrantes,
        patrocinadores=patrocinadores,
        campos_personalizados=campos_personalizados,
        lote_vigente=lote_vigente,
        lote_stats=lote_stats,
        lotes_ativos=lotes_ativos,
        tipos_inscricao=tipos_inscricao,
        mostrar_taxa=mostrar_taxa,
        preco_com_taxa=preco_com_taxa,
        cliente_id=cliente_id,
        obrigatorio_nome=obrigatorio_nome,
        obrigatorio_cpf=obrigatorio_cpf,
        obrigatorio_email=obrigatorio_email,
        obrigatorio_senha=obrigatorio_senha,
        obrigatorio_formacao=obrigatorio_formacao
    )

@inscricao_routes.route('/editar_participante', methods=['GET', 'POST'])
@inscricao_routes.route('/editar_participante/<int:usuario_id>/<int:oficina_id>', methods=['GET', 'POST'])
@login_required
def editar_participante(usuario_id=None, oficina_id=None):
    # Caso o cliente esteja editando um usuário
    if usuario_id:
        if not hasattr(current_user, 'tipo') or current_user.tipo != 'cliente':
            flash('Acesso negado!', 'danger')
            return redirect(url_for('dashboard_routes.dashboard'))

        usuario = Usuario.query.get_or_404(usuario_id)
        oficina = Oficina.query.get_or_404(oficina_id)
    else:
        # Participante editando a si mesmo
        if not hasattr(current_user, 'tipo') or current_user.tipo != 'participante':
            flash('Acesso negado!', 'danger')
            return redirect(url_for('dashboard_routes.dashboard'))
        usuario = current_user
        oficina = None  # Não necessário nesse caso

    if request.method == 'POST':
        usuario.nome = sanitize_input(request.form.get('nome'))
        usuario.cpf = sanitize_input(request.form.get('cpf'))
        usuario.email = sanitize_input(request.form.get('email'))
        usuario.formacao = sanitize_input(request.form.get('formacao'))
        usuario.estados = ','.join(sanitize_input(e) for e in request.form.getlist('estados[]') or [])
        usuario.cidades = ','.join(sanitize_input(c) for c in request.form.getlist('cidades[]') or [])

        nova_senha = sanitize_input(request.form.get('senha'))
        if nova_senha:
            usuario.senha = generate_password_hash(nova_senha)

        try:
            db.session.commit()
            flash("Perfil atualizado com sucesso!", "success")
            if usuario_id:
                return redirect(url_for('inscricao_routes.editar_participante', usuario_id=usuario.id, oficina_id=oficina_id))
            return redirect(url_for('dashboard_participante_routes.dashboard_participante'))
        except Exception as e:
            db.session.rollback()
            flash("Erro ao atualizar o perfil: " + str(e), "danger")

    return render_template('editar_participante.html', usuario=usuario, oficina=oficina)




@inscricao_routes.route('/admin/evento/<int:evento_id>/inscritos')
@login_required
def listar_inscritos_evento(evento_id):
    if current_user.tipo != 'cliente':
        flash("Acesso restrito.", "danger")
        return redirect(url_for('dashboard_routes.dashboard'))

    evento = Evento.query.get_or_404(evento_id)
    inscricoes = Inscricao.query.filter_by(evento_id=evento.id).all()

    return render_template("evento/listar_inscritos_evento.html", evento=evento, inscricoes=inscricoes)



# ===========================
# INSCRIÇÃO EM OFICINAS - PARTICIPANTE
# ===========================
@inscricao_routes.route('/inscrever/<int:oficina_id>', methods=['POST'])
@login_required
def inscrever(oficina_id):
    if current_user.tipo != 'participante':
        return jsonify({
            'success': False,
            'message': 'Apenas participantes podem se inscrever.'
        })

    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        return jsonify({
            'success': False,
            'message': 'Oficina não encontrada!'
        })

    # Verifica disponibilidade de vagas com base no tipo de inscrição
    if oficina.tipo_inscricao == 'sem_inscricao':
        # Não é necessário verificar vagas para oficinas sem inscrição
        pass
    elif oficina.tipo_inscricao == 'com_inscricao_sem_limite':
        # Não há limite de vagas
        pass
    elif oficina.vagas <= 0:
        return jsonify({
            'success': False,
            'message': 'Esta oficina está lotada!'
        })

    # Evita duplicidade
    if Inscricao.query.filter_by(usuario_id=current_user.id, oficina_id=oficina.id).first():
        return jsonify({
            'success': False,
            'message': 'Você já está inscrito nesta oficina!'
        })
    
    # Verificar regras de inscrição baseadas no tipo de inscrição do participante
    if oficina.evento_id and current_user.tipo_inscricao_id:
        # Buscar regras para o tipo de inscrição do participante
        regra = RegraInscricaoEvento.query.filter_by(
            evento_id=oficina.evento_id,
            tipo_inscricao_id=current_user.tipo_inscricao_id
        ).first()
        
        if regra:
            # Verificar se esta oficina está na lista de oficinas permitidas
            oficinas_permitidas = regra.get_oficinas_permitidas_list()
            if oficinas_permitidas and oficina.id not in oficinas_permitidas:
                return jsonify({
                    'success': False,
                    'message': 'Seu tipo de inscrição não permite acesso a esta oficina.'
                })
            
            # Verificar se o participante já atingiu o limite de oficinas
            if regra.limite_oficinas > 0:
                # Contar quantas oficinas o participante já está inscrito neste evento
                inscricoes_evento = Inscricao.query.join(Oficina).filter(
                    Inscricao.usuario_id == current_user.id,
                    Oficina.evento_id == oficina.evento_id
                ).count()
                
                if inscricoes_evento >= regra.limite_oficinas:
                    return jsonify({
                        'success': False,
                        'message': f'Você já atingiu o limite de {regra.limite_oficinas} oficinas para seu tipo de inscrição.'
                    })

    # Decrementa vagas se for uma oficina com inscrição limitada
    if oficina.tipo_inscricao == 'com_inscricao_com_limite':
        oficina.vagas -= 1
    
    # No formulário de inscrição, capture o id do tipo de inscrição escolhido:
    tipo_inscricao_id = request.form.get('tipo_inscricao_id')  # Pode ser None se for gratuita
      # Criar a inscrição
    inscricao = Inscricao(
        usuario_id=current_user.id,
        oficina_id=oficina.id,
        cliente_id=current_user.cliente_id,
        evento_id=oficina.evento_id,  # Importante: associar ao evento da oficina
        tipo_inscricao_id=tipo_inscricao_id if tipo_inscricao_id else None,
    )
    
    try:
        db.session.add(inscricao)
        
        # IMPORTANTE: Se o usuário não estiver associado a nenhum evento ainda,
        # associar este usuário ao evento da oficina para manter compatibilidade com o sistema
        if not current_user.evento_id and oficina.evento_id:
            current_user.evento_id = oficina.evento_id
        
        # Verificar se a oficina é paga e processar pagamento
        if not oficina.inscricao_gratuita and tipo_inscricao_id:
            # Recuperar o tipo de inscrição
            tipo_inscricao = InscricaoTipo.query.get(tipo_inscricao_id)
            if tipo_inscricao:
                # Importar SDK do Mercado Pago
                from services.mp_service import get_sdk
                sdk = get_sdk()
                
                if sdk:
                    # Fazer flush para gerar o ID da inscrição
                    db.session.flush()
                    
                    # Criar título para o pagamento
                    titulo = f"Inscrição - {oficina.titulo} - {tipo_inscricao.nome}"
                    
                    # Criar preferência e redirecionar para pagamento
                    url_pagamento = _criar_preferencia_mp(
                        sdk=sdk, 
                        preco=float(tipo_inscricao.preco), 
                        titulo=titulo,
                        inscricao=inscricao, 
                        usuario=current_user
                    )
                    
                    # Confirmar a transação
                    db.session.commit()
                    
                    # Retornar URL de pagamento
                    return jsonify({
                        'success': True,
                        'redirect': True,
                        'payment_url': url_pagamento,
                        'message': 'Redirecionando para o pagamento...'
                    })
            
        # Se chegou aqui, é porque a inscrição é gratuita ou não precisa de pagamento
        inscricao.status_pagamento = "approved"
        db.session.commit()

        # Gera o comprovante
        try:
            pdf_path = gerar_comprovante_pdf(current_user, oficina, inscricao)

            assunto = f"Confirmação de Inscrição - {oficina.titulo}"
            corpo_texto = (
                f"Olá {current_user.nome},\n\n"
                f"Você se inscreveu na oficina '{oficina.titulo}'.\n"
                "Segue o comprovante de inscrição em anexo."
            )

            corpo_html = render_template(
                'emails/confirmacao_inscricao_oficina.html',
                participante_nome=current_user.nome,
                oficina=oficina,
            )

        enviar_email(
            destinatario=current_user.email,
            nome_participante=current_user.nome,
            nome_oficina=oficina.titulo,
            assunto=assunto,
            corpo_texto=corpo_texto,
            anexo_path=pdf_path,
            corpo_html=corpo_html,
        )
    except Exception as e:
        logger.exception("❌ ERRO ao enviar e-mail: %s", e)
        # Continuamos mesmo se houver erro no e-mail, pois a inscrição já foi concluída
            
        return jsonify({
            'success': True,
            'message': 'Inscrição realizada com sucesso!',
            'pdf_url': url_for('comprovante_routes.baixar_comprovante', oficina_id=oficina.id)
        })
        
    except Exception as e:
        db.session.rollback()
        logger.exception("❌ ERRO ao realizar inscrição: %s", e)
        return jsonify({
            'success': False,
            'message': f'Erro ao realizar inscrição: {str(e)}'
        })

@inscricao_routes.route('/remover_inscricao/<int:oficina_id>', methods=['POST'])
@login_required
def remover_inscricao(oficina_id):
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, oficina_id=oficina_id).first()
    if not inscricao:
        flash('Você não está inscrito nesta oficina!', 'warning')
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

    oficina = Oficina.query.get(oficina_id)
    if oficina:
        oficina.vagas += 1

    db.session.delete(inscricao)
    db.session.commit()
    flash('Inscrição removida com sucesso!', 'success')
    return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

@inscricao_routes.route('/cancelar_inscricao/<int:inscricao_id>', methods=['GET','POST'])
@login_required
def cancelar_inscricao(inscricao_id):
    # Allow both admin and client access
    if current_user.tipo not in ['admin', 'cliente']:
        flash("Acesso negado!", "danger")
        return redirect(url_for('dashboard_routes.dashboard'))

    # Get inscription
    insc = Inscricao.query.get_or_404(inscricao_id)
    
    # For clients, verify they own the workshop/event
    if current_user.tipo == 'cliente':
        oficina = Oficina.query.get(insc.oficina_id)
        if oficina.cliente_id != current_user.id:
            flash("Você não tem permissão para cancelar esta inscrição!", "danger")
            return redirect(url_for('dashboard_routes.dashboard_cliente'))

    try:
        db.session.delete(insc)
        db.session.commit()
        flash("Inscrição cancelada com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao cancelar inscrição: {e}", "danger")

    # Redirect to appropriate dashboard based on user type
    if current_user.tipo == 'admin':
        return redirect(url_for('dashboard_routes.dashboard'))
    else:
        return redirect(url_for('dashboard_routes.dashboard_cliente'))
    

@inscricao_routes.route('/inscricao/token/<token>', methods=['GET', 'POST'])
def abrir_inscricao_token(token):
    """Exibe ou processa inscrição usando o token fornecido."""
    return cadastro_participante(token)

@inscricao_routes.route('/configurar_regras_inscricao', methods=['GET', 'POST'])
@login_required
def configurar_regras_inscricao():
    if current_user.tipo != 'cliente':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard_cliente'))
    
    # Lista todos os eventos do cliente
    eventos = Evento.query.filter_by(cliente_id=current_user.id).all()
    
    # Evento selecionado (por padrão, None até que o usuário escolha)
    evento_id = sanitize_input(
        request.args.get('evento_id') or (request.form.get('evento_id') if request.method == 'POST' else None)
    )
    evento = None
    oficinas = []
    regras = {}
    form = RegraInscricaoEventoForm()
    
    if evento_id:
        evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first()
        if evento:
            # Carrega oficinas do evento
            oficinas = Oficina.query.filter_by(evento_id=evento.id).all()
            form = RegraInscricaoEventoForm(
                oficinas_choices=[(o.id, o.titulo) for o in oficinas]
            )

            # Carrega regras existentes
            regras_db = RegraInscricaoEvento.query.filter_by(evento_id=evento.id).all()
            for regra in regras_db:
                regras[regra.tipo_inscricao_id] = {
                    'limite_oficinas': regra.limite_oficinas,
                    'oficinas_permitidas_list': regra.get_oficinas_permitidas_list()
                }
    
    if request.method == 'POST' and evento:
        try:
            # Primeiro, remove todas as regras existentes para este evento
            RegraInscricaoEvento.query.filter_by(evento_id=evento.id).delete()
            
            # Processa cada tipo de inscrição
            for tipo in evento.tipos_inscricao_evento:
                limite_oficinas = int(request.form.get(f'limite_oficinas_{tipo.id}', 0))
                oficinas_permitidas = request.form.getlist(f'oficinas_{tipo.id}[]')
                
                # Cria nova regra
                nova_regra = RegraInscricaoEvento(
                    evento_id=evento.id,
                    tipo_inscricao_id=tipo.id,
                    limite_oficinas=limite_oficinas
                )
                
                # Define as oficinas permitidas
                nova_regra.set_oficinas_permitidas_list(oficinas_permitidas)
                
                db.session.add(nova_regra)
            
            db.session.commit()
            flash('Regras de inscrição configuradas com sucesso!', 'success')
            return redirect(url_for('dashboard_routes.dashboard_cliente'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao configurar regras: {str(e)}', 'danger')
    
    return render_template(
        "agendamento/configurar_regras_inscricao.html",
        eventos=eventos,
        evento=evento,
        oficinas=oficinas,
        regras=regras,
        form=form,
    )

@inscricao_routes.route('/inscrever_participantes_lote', methods=['POST'])
@login_required
def inscrever_participantes_lote():
    logger.debug("Iniciando processo de inscrição em lote...")

    oficina_id = request.form.get('oficina_id')
    usuario_ids = request.form.getlist('usuario_ids')

    logger.debug("Oficina selecionada: %s", oficina_id)
    logger.debug("Usuários selecionados: %s", usuario_ids)

    if not oficina_id or not usuario_ids:
        flash('Oficina ou participantes não selecionados corretamente.', 'warning')
        logger.error("Oficina ou participantes não foram selecionados corretamente.")
        return redirect(url_for('dashboard_routes.dashboard'))

    oficina = Oficina.query.get(oficina_id)
    if not oficina:
        flash('Oficina não encontrada!', 'danger')
        logger.error("Oficina não encontrada no banco de dados.")
        return redirect(url_for('dashboard_routes.dashboard'))

    inscritos_sucesso = 0
    erros = 0

    try:
        for usuario_id in usuario_ids:
            logger.debug("Tentando inscrever usuário %s na oficina %s...", usuario_id, oficina.titulo)

            ja_inscrito = Inscricao.query.filter_by(usuario_id=usuario_id, oficina_id=oficina_id).first()

            if ja_inscrito:
                logger.warning("Usuário %s já está inscrito na oficina. Pulando...", usuario_id)
                continue  # Evita duplicação

            # Verifica se há vagas disponíveis
            if oficina.vagas <= 0:
                logger.warning("Sem vagas para a oficina %s. Usuário %s não pode ser inscrito.", oficina.titulo, usuario_id)
                erros += 1
                continue

            # 🔥 SOLUÇÃO: Passando cliente_id corretamente para a Inscricao
            nova_inscricao = Inscricao(
                usuario_id=usuario_id,
                oficina_id=oficina_id,
                cliente_id=oficina.cliente_id  # Obtém o cliente_id da própria oficina
            )

            db.session.add(nova_inscricao)
            oficina.vagas -= 1  # Reduz a quantidade de vagas disponíveis

            inscritos_sucesso += 1
            logger.info("Usuário %s inscrito com sucesso!", usuario_id)

        db.session.commit()
        flash(f'{inscritos_sucesso} participantes inscritos com sucesso! {erros} não foram inscritos por falta de vagas.', 'success')
        logger.info("%s inscrições concluídas. %s falharam.", inscritos_sucesso, erros)

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao inscrever participantes em lote: {str(e)}", "danger")
        logger.exception("Erro ao inscrever participantes: %s", e)

    return redirect(url_for('dashboard_routes.dashboard'))


@inscricao_routes.route('/cancelar_inscricoes_lote', methods=['POST'])
@login_required
def cancelar_inscricoes_lote():
    # Verifica se é admin
    if current_user.tipo != 'admin':
        flash("Acesso negado!", "danger")
        return redirect(url_for('dashboard_routes.dashboard'))

    # Pega os IDs marcados
    inscricao_ids = request.form.getlist('inscricao_ids')
    if not inscricao_ids:
        flash("Nenhuma inscrição selecionada!", "warning")
        return redirect(url_for('dashboard_routes.dashboard'))

    # Converte para int
    inscricao_ids = list(map(int, inscricao_ids))

    try:
        # Busca todas as inscrições com esses IDs
        inscricoes = Inscricao.query.filter(Inscricao.id.in_(inscricao_ids)).all()
        # Cancela removendo do banco
        for insc in inscricoes:
            db.session.delete(insc)

        db.session.commit()
        flash(f"Foram canceladas {len(inscricoes)} inscrições!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao cancelar inscrições: {e}", "danger")

    return redirect(url_for('dashboard_routes.dashboard'))

from models import Inscricao, Oficina, Usuario   # ➊ certifique-se do import

@inscricao_routes.route('/inscricoes_lote', methods=['POST'])
@login_required
def inscricoes_lote():
    # ─── 0. Permissão ──────────────────────────────────────────────
    if current_user.tipo not in {'admin', 'cliente'}:
        flash("Acesso negado!", "danger")
        return redirect(url_for('dashboard_routes.dashboard'))

    # ─── 1. Dados do formulário ────────────────────────────────────
    inscricao_ids      = list(map(int, request.form.getlist('inscricao_ids')))
    oficina_destino_id = request.form.get('oficina_destino', type=int)
    acao               = request.form.get('acao', 'mover')  # mover | copiar

    if not inscricao_ids or not oficina_destino_id:
        flash("Selecione inscrições e oficina de destino.", "warning")
        return redirect(url_for('dashboard_routes.dashboard'))

    oficina_destino = Oficina.query.get_or_404(oficina_destino_id)
    inscricoes      = Inscricao.query.filter(Inscricao.id.in_(inscricao_ids)).all()

    # ─── 2. Restrições de cliente ─────────────────────────────────
    if current_user.tipo == 'cliente' and any(i.cliente_id != current_user.id for i in inscricoes):
        flash("Há inscrições de outro cliente selecionadas!", "danger")
        return redirect(url_for('dashboard_routes.dashboard'))

    # ─── 3. Verificar vagas de uma vez só ─────────────────────────
    if oficina_destino.vagas < len(inscricoes):
        flash(f"Não há vagas suficientes! "
              f"(Disponíveis: {oficina_destino.vagas}, Necessárias: {len(inscricoes)})",
              "danger")
        return redirect(url_for('dashboard_routes.dashboard'))

    # ─── 4. Processar lote ────────────────────────────────────────
    try:
        usuarios_afetados = set()          # para atualizar evento_id depois

        for insc in inscricoes:
            usuarios_afetados.add(insc.usuario_id)

            if acao == 'mover':
                # devolve vaga na origem (se houver)
                if insc.oficina:
                    insc.oficina.vagas += 1

                # ocupa vaga na destino
                oficina_destino.vagas -= 1

                # atualiza inscrição existente
                insc.oficina_id = oficina_destino.id
                insc.evento_id  = oficina_destino.evento_id

            else:  # acao == 'copiar'
                # ocupa vaga na destino
                oficina_destino.vagas -= 1

                # clona inscrição
                nova = Inscricao(
                    usuario_id       = insc.usuario_id,
                    cliente_id       = insc.cliente_id,
                    oficina_id       = oficina_destino.id,
                    evento_id        = oficina_destino.evento_id,
                    status_pagamento = insc.status_pagamento
                )
                db.session.add(nova)

        # ─── 5. Sincronizar usuario.evento_id ─────────────────────
        for uid in usuarios_afetados:
            usuario = Usuario.query.get(uid)
            # se o sistema admite apenas 1 evento corrente por usuário:
            if usuario and usuario.evento_id is None:
                usuario.evento_id = oficina_destino.evento_id

        db.session.commit()
        verbo = "movida(s)" if acao == 'mover' else "copiada(s)"
        flash(f"{len(inscricoes)} inscrição(ões) {verbo} com sucesso!", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao processar inscrições: {e}", "danger")

    return redirect(url_for('inscricao_routes.gerenciar_inscricoes'))



@inscricao_routes.route("/mover_inscricoes_lote", methods=["POST"])
@login_required
def mover_inscricoes_lote():
    # ░░░ 1. Permissão --------------------------------------------------------
    if current_user.tipo not in {"admin", "cliente"}:
        flash("Acesso negado!", "danger")
        return redirect(url_for('dashboard_routes.dashboard'))

    # ░░░ 2. Coleta de parâmetros --------------------------------------------
    inscricao_ids      = list(map(int, request.form.getlist("inscricao_ids")))
    oficina_destino_id = request.form.get("oficina_destino", type=int)

    if not inscricao_ids:
        flash("Nenhuma inscrição selecionada!", "warning")
        return redirect(url_for('dashboard_routes.dashboard'))

    if not oficina_destino_id:
        flash("Nenhuma oficina de destino selecionada!", "warning")
        return redirect(url_for('dashboard_routes.dashboard'))

    try:
        # ░░░ 3. Objetos de referência ---------------------------------------
        primeira_insc   = Inscricao.query.get_or_404(inscricao_ids[0])
        oficina_origem  = primeira_insc.oficina
        evento_id       = oficina_origem.evento_id
        oficina_destino = Oficina.query.get_or_404(oficina_destino_id)

        # 3.1 – Garantir que destino pertence ao mesmo evento
        if oficina_destino.evento_id != evento_id:
            flash("A oficina de destino deve pertencer ao mesmo evento!", "danger")
            return redirect(url_for('dashboard_routes.dashboard'))

        # 3.2 – Buscar inscrições a mover
        inscricoes = (
            Inscricao.query
            .filter(Inscricao.id.in_(inscricao_ids))
            .all()
        )

        # 3.3 – Checar se todas são do mesmo evento
        if any(insc.oficina.evento_id != evento_id for insc in inscricoes):
            flash("Todas as inscrições devem pertencer ao mesmo evento!", "danger")
            return redirect(url_for('dashboard_routes.dashboard'))

        # 3.4 – Verificar vagas
        if oficina_destino.vagas < len(inscricoes):
            flash(
                f"Não há vagas suficientes na oficina de destino! "
                f"(Disponível: {oficina_destino.vagas}, Necessário: {len(inscricoes)})",
                "danger",
            )
            return redirect(url_for('dashboard_routes.dashboard'))

        # ░░░ 4. Garante inscrição-evento para quem não tem -------------------
        usuario_ids = {insc.usuario_id for insc in inscricoes}

        existentes = (
            Inscricao.query
            .filter(
                Inscricao.evento_id == evento_id,
                Inscricao.oficina_id.is_(None),           # inscrição “geral” do evento
                Inscricao.usuario_id.in_(usuario_ids)
            )
            .with_entities(Inscricao.usuario_id)
            .all()
        )
        ja_inscritos_evento = {row.usuario_id for row in existentes}
        faltantes = usuario_ids - ja_inscritos_evento

        novas_inscricoes_evento = [
            Inscricao(
                usuario_id=u_id,
                cliente_id=primeira_insc.cliente_id,
                evento_id=evento_id,
                status_pagamento="paid"   # ajuste conforme sua regra de cobrança
            )
            for u_id in faltantes
        ]
        db.session.add_all(novas_inscricoes_evento)

        # ░░░ 5. Move as inscrições de oficina -------------------------------
        for insc in inscricoes:
            # devolve vaga na oficina de origem
            insc.oficina.vagas += 1
            # retira vaga da oficina destino
            oficina_destino.vagas -= 1
            # efetiva a troca
            insc.oficina_id = oficina_destino_id
            # (mantém vínculo com o mesmo evento pela coerência)
            insc.evento_id  = evento_id

        db.session.commit()

        flash(
            f"{len(inscricoes)} inscrição(ões) movida(s) para "
            f"“{oficina_destino.titulo}”. "
            f"{len(novas_inscricoes_evento)} inscrição(ões) de evento criadas.",
            "success"
        )

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao mover inscrições: {e}", "danger")

    return redirect(url_for("inscricao_routes.gerenciar_inscricoes"))


@inscricao_routes.route('/inscricao/<slug_customizado>', methods=['GET'])
def inscricao_personalizada(slug_customizado):
    """Redireciona slug personalizado para a rota principal de inscrição."""
    link = LinkCadastro.query.filter_by(slug_customizado=slug_customizado).first()
    if not link or not link.evento_id:
        return "Link inválido ou sem evento associado", 404

    return redirect(url_for('inscricao_routes.cadastro_participante', identifier=link.token))


@inscricao_routes.route('/admin/inscricao/<int:inscricao_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_inscricao_evento(inscricao_id):
    inscricao = Inscricao.query.get_or_404(inscricao_id)
    tipos = InscricaoTipo.query.filter_by(oficina_id=inscricao.oficina_id).all()

    if request.method == 'POST':
        tipo_id = request.form.get('tipo_inscricao_id')
        inscricao.tipo_inscricao_id = tipo_id
        db.session.commit()
        flash("Inscrição atualizada com sucesso!", "success")
        return redirect(url_for('listar_inscritos_evento', evento_id=inscricao.evento_id))

    return render_template('editar_inscricao_evento.html', inscricao=inscricao, tipos=tipos)


@inscricao_routes.route('/admin/inscricao/<int:inscricao_id>/excluir', methods=['POST'])
@login_required
def excluir_inscricao_evento(inscricao_id):
    inscricao = Inscricao.query.get_or_404(inscricao_id)
    evento_id = inscricao.evento_id
    db.session.delete(inscricao)
    db.session.commit()


@inscricao_routes.route('/gerenciar_inscricoes', methods=['GET', 'POST'])
@login_required
def gerenciar_inscricoes():
    if current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso Autorizado!', 'danger')
        
    # Se o usuário for cliente, filtra apenas as oficinas e inscrições associadas a ele
    if current_user.tipo == 'cliente':
        oficinas = Oficina.query.filter_by(cliente_id=current_user.id).all()
        inscritos = Inscricao.query.join(Oficina).filter(Oficina.cliente_id == current_user.id).all()
    else:
        # Se for admin, mostra todos os registros
        oficinas = Oficina.query.all()
        inscritos = Inscricao.query.all()
    return render_template('inscricao/gerenciar_inscricoes.html', oficinas=oficinas, inscritos=inscritos)
