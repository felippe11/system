from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash
import logging

from extensions import db
from models import ConfiguracaoCliente
from models.user import Cliente

cliente_routes = Blueprint("cliente_routes", __name__)
logger = logging.getLogger(__name__)


def _admin_required():
    """Verifica se o usuário corrente possui privilégios de administrador."""
    user_type = getattr(current_user, "tipo", None)
    session_type = session.get("user_type")
    if user_type not in ("admin", "superadmin") and session_type not in (
        "admin",
        "superadmin",
    ):
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))
    return None


@cliente_routes.route("/cadastrar_cliente", methods=["GET", "POST"])
@login_required
def cadastrar_cliente():
    if session.get("user_type") != "admin":  # Apenas admin pode cadastrar clientes
        abort(403)

    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]

        # Verifica se o e-mail já está cadastrado
        cliente_existente = Cliente.query.filter_by(email=email).first()
        if cliente_existente:
            flash("Já existe um cliente com esse e-mail!", "danger")
            return redirect(url_for("cliente_routes.cadastrar_cliente"))

        # Cria o cliente com pagamento habilitado por padrão
        novo_cliente = Cliente(
            nome=nome,
            email=email,
            senha=generate_password_hash(senha),
            habilita_pagamento=True,
        )

        db.session.add(novo_cliente)
        db.session.commit()

        flash("Cliente cadastrado com sucesso!", "success")
        return redirect(url_for("dashboard_routes.dashboard"))

    return render_template("auth/cadastrar_cliente.html")


@cliente_routes.route("/editar_cliente/<int:cliente_id>", methods=["GET", "POST"])
@login_required
def editar_cliente(cliente_id):
    if current_user.tipo != "admin":
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    cliente = Cliente.query.get_or_404(cliente_id)
    if request.method == "POST":
        cliente.nome = request.form.get("nome")
        cliente.email = request.form.get("email")
        nova_senha = request.form.get("senha")
        if nova_senha:  # Só atualiza a senha se fornecida
            cliente.senha = generate_password_hash(nova_senha)

        # Pagamento sempre habilitado para clientes
        cliente.habilita_pagamento = True

        config = ConfiguracaoCliente.query.filter_by(cliente_id=cliente.id).first()
        if not config:
            config = ConfiguracaoCliente(cliente_id=cliente.id)
            db.session.add(config)

        def _parse_int(field, default):
            try:
                return int(request.form.get(field, default))
            except (TypeError, ValueError):
                return default

        config.limite_eventos = _parse_int('limite_eventos', config.limite_eventos)
        config.limite_inscritos = _parse_int('limite_inscritos', config.limite_inscritos)
        config.limite_formularios = _parse_int('limite_formularios', config.limite_formularios)
        config.limite_revisores = _parse_int('limite_revisores', config.limite_revisores)

        try:
            db.session.commit()
            flash("Cliente atualizado com sucesso!", "success")
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao atualizar cliente: %s", e, exc_info=True)
            flash(f"Erro ao atualizar cliente: {str(e)}", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    return render_template("auth/editar_cliente.html", cliente=cliente)


@cliente_routes.route("/excluir_cliente/<int:cliente_id>", methods=["POST"])
@login_required
def excluir_cliente(cliente_id):
    if current_user.tipo != "admin":
        flash("Apenas administradores podem excluir clientes.", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    cliente = Cliente.query.get_or_404(cliente_id)

    try:
        from sqlalchemy import or_, text

        from models import (
            CampoPersonalizadoCadastro,
            CertificadoTemplate,
            Checkin,
            ConfiguracaoAgendamento,
            ConfiguracaoCliente,
            ConfiguracaoEvento,
            Evento,
            EventoInscricaoTipo,
            Feedback,
            HorarioVisitacao,
            InscricaoTipo,
            Inscricao,
            LinkCadastro,
            LoteInscricao,
            LoteTipoInscricao,
            MaterialOficina,
            Ministrante,
            Oficina,
            OficinaDia,
            Patrocinador,
            RegraInscricaoEvento,
            RelatorioOficina,
            RespostaCampo,
            RespostaFormulario,
            FeedbackCampo,
            SalaVisitacao,
            Formulario,
            FormularioTemplate,
            CampoFormularioTemplate,
            Sorteio,
            Pagamento,
            Usuario,
            PasswordResetToken,
            usuario_clientes,
            AgendamentoVisita,
            AlunoVisitante,
            ProfessorBloqueado,
            PasswordResetToken,
        )

        # ===============================
        # 1️⃣ PARTICIPANTES
        # ===============================
        participantes = Usuario.query.filter_by(cliente_id=cliente.id).all()
        usuario_ids = [u.id for u in participantes]

        with db.session.no_autoflush:
            for usuario in participantes:
                Checkin.query.filter_by(usuario_id=usuario.id).delete()
                Inscricao.query.filter_by(usuario_id=usuario.id).delete()
                Feedback.query.filter_by(usuario_id=usuario.id).delete()
                PasswordResetToken.query.filter_by(usuario_id=usuario.id).delete()
                resposta_ids = db.session.query(RespostaFormulario.id).filter_by(
                    usuario_id=usuario.id
                )

                db.session.execute(
                    text(
                        """
                        DELETE FROM feedback_campo
                        WHERE resposta_campo_id IN (
                            SELECT id FROM respostas_campo
                            WHERE resposta_formulario_id IN (
                                SELECT id FROM respostas_formulario
                                WHERE usuario_id = :uid
                            )
                        )
                        """
                    ),
                    {"uid": usuario.id},
                )

                RespostaCampo.query.filter(
                    RespostaCampo.resposta_formulario_id.in_(resposta_ids)
                ).delete(synchronize_session=False)

                RespostaFormulario.query.filter_by(usuario_id=usuario.id).delete()

        PasswordResetToken.query.filter(
            PasswordResetToken.usuario_id.in_(usuario_ids)
        ).delete(synchronize_session=False)

        # Remover associações entre usuários e clientes (tanto deste cliente
        # quanto outras referencias destes usuários)
        db.session.execute(
            usuario_clientes.delete().where(
                or_(
                    usuario_clientes.c.usuario_id.in_(usuario_ids),
                    usuario_clientes.c.cliente_id == cliente.id,
                )
            )
        )

        Usuario.query.filter_by(cliente_id=cliente.id).delete(synchronize_session=False)
        db.session.commit()

        # ===============================
        # 2️⃣ OFICINAS
        # ===============================
        oficinas = Oficina.query.filter_by(cliente_id=cliente.id).all()

        for oficina in oficinas:
            Checkin.query.filter_by(oficina_id=oficina.id).delete()
            Inscricao.query.filter_by(oficina_id=oficina.id).delete()
            OficinaDia.query.filter_by(oficina_id=oficina.id).delete()
            MaterialOficina.query.filter_by(oficina_id=oficina.id).delete()
            RelatorioOficina.query.filter_by(oficina_id=oficina.id).delete()
            Feedback.query.filter_by(oficina_id=oficina.id).delete()

            # Remove tipos de inscrição vinculados à oficina
            tipo_ids = db.session.query(InscricaoTipo.id).filter_by(oficina_id=oficina.id)
            Inscricao.query.filter(
                Inscricao.tipo_inscricao_id.in_(tipo_ids)
            ).delete(synchronize_session=False)
            InscricaoTipo.query.filter_by(oficina_id=oficina.id).delete()

            db.session.execute(
                text(
                    "DELETE FROM oficina_ministrantes_association WHERE oficina_id = :oficina_id"
                ),
                {"oficina_id": oficina.id},
            )

            db.session.delete(oficina)

        # ===============================
        # 3️⃣ MINISTRANTES
        # ===============================
        ministrantes = Ministrante.query.filter_by(cliente_id=cliente.id).all()
        for m in ministrantes:
            # Remove associações em oficinas de outros clientes
            db.session.execute(
                text(
                    "DELETE FROM oficina_ministrantes_association WHERE ministrante_id = :mid"
                ),
                {"mid": m.id},
            )
            # Remove vínculo direto caso alguma oficina ainda aponte para este ministrante
            Oficina.query.filter_by(ministrante_id=m.id).update(
                {"ministrante_id": None}, synchronize_session=False
            )

        Ministrante.query.filter_by(cliente_id=cliente.id).delete()

        # ===============================
        # 4️⃣ EVENTOS E DEPENDÊNCIAS
        # ===============================
        eventos = Evento.query.filter(
            or_(Evento.cliente_id == cliente.id, Evento.cliente_id == None)
        ).all()
        evento_ids = [e.id for e in eventos]

        for evento in eventos:
            with db.session.no_autoflush:
                # Limpar referências em usuários para tipos de inscrição deste evento
                Usuario.query.filter(
                    Usuario.tipo_inscricao_id.in_(
                        db.session.query(EventoInscricaoTipo.id).filter_by(
                            evento_id=evento.id
                        )
                    )
                ).update({"tipo_inscricao_id": None}, synchronize_session=False)
                agendamento_ids = (
                    db.session.query(AgendamentoVisita.id)
                    .join(HorarioVisitacao)
                    .filter(HorarioVisitacao.evento_id == evento.id)
                )

                AlunoVisitante.query.filter(
                    AlunoVisitante.agendamento_id.in_(agendamento_ids)
                ).delete(synchronize_session=False)

                AgendamentoVisita.query.filter(
                    AgendamentoVisita.id.in_(agendamento_ids)
                ).delete(synchronize_session=False)

                ProfessorBloqueado.query.filter_by(evento_id=evento.id).delete()

                HorarioVisitacao.query.filter_by(evento_id=evento.id).delete()
                ConfiguracaoAgendamento.query.filter_by(evento_id=evento.id).delete()
                Patrocinador.query.filter_by(evento_id=evento.id).delete()
                SalaVisitacao.query.filter_by(evento_id=evento.id).delete()  # ✅ NOVO

                # Remover inscrições e check-ins vinculados ao evento
                Checkin.query.filter_by(evento_id=evento.id).delete()
                Inscricao.query.filter_by(evento_id=evento.id).delete()

                # Remover dependências de inscrição do evento
                LoteTipoInscricao.query.filter(
                    LoteTipoInscricao.lote_id.in_(
                        db.session.query(LoteInscricao.id).filter_by(
                            evento_id=evento.id
                        )
                    )
                ).delete(synchronize_session=False)
                LoteInscricao.query.filter_by(evento_id=evento.id).delete()

                # Remover pagamentos do evento
                Pagamento.query.filter_by(evento_id=evento.id).delete(synchronize_session=False)

                RegraInscricaoEvento.query.filter_by(evento_id=evento.id).delete()
                EventoInscricaoTipo.query.filter_by(evento_id=evento.id).delete()

                ConfiguracaoEvento.query.filter_by(evento_id=evento.id).delete()

                db.session.delete(evento)

        # ===============================
        # 5️⃣ CONFIGURAÇÕES E VINCULAÇÕES
        # ===============================
        CertificadoTemplate.query.filter_by(cliente_id=cliente.id).delete()
        CampoPersonalizadoCadastro.query.filter_by(cliente_id=cliente.id).delete()
        LinkCadastro.query.filter_by(cliente_id=cliente.id).delete()
        ConfiguracaoCliente.query.filter_by(cliente_id=cliente.id).delete()

        # Formulários e templates vinculados ao cliente
        template_ids = db.session.query(FormularioTemplate.id).filter_by(cliente_id=cliente.id)
        CampoFormularioTemplate.query.filter(
            CampoFormularioTemplate.template_id.in_(template_ids)
        ).delete(synchronize_session=False)
        FormularioTemplate.query.filter_by(cliente_id=cliente.id).delete()
        formularios = Formulario.query.filter_by(cliente_id=cliente.id).all()
        for f in formularios:
            db.session.delete(f)  # cascades to campos and respostas

        # Sorteios e pagamentos
        Sorteio.query.filter_by(cliente_id=cliente.id).delete()
        Pagamento.query.filter(
            Pagamento.usuario_id.in_(usuario_ids)
        ).delete(synchronize_session=False)
        # Pagamentos dos eventos já foram removidos dentro do loop acima

        # ===============================
        # 6️⃣ EXCLUI O CLIENTE
        # ===============================
        db.session.delete(cliente)
        db.session.commit()

        flash(
            "Cliente e todos os dados vinculados foram excluídos com sucesso!",
            "success",
        )

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir cliente: {str(e)}", "danger")

    return redirect(url_for("dashboard_routes.dashboard"))


@cliente_routes.route("/listar_usuarios/<int:cliente_id>")
@login_required
def listar_usuarios(cliente_id: int):
    """Exibe os usuários vinculados a um cliente específico."""
    if current_user.tipo != "admin":
        flash("Acesso negado!", "danger")
        return redirect(url_for("dashboard_routes.dashboard"))

    from models import Usuario, Cliente, usuario_clientes

    cliente = Cliente.query.get_or_404(cliente_id)
    usuarios = (
        Usuario.query
        .join(usuario_clientes)
        .filter(usuario_clientes.c.cliente_id == cliente.id)
        .all()
    )

    return render_template(
        "cliente/listar_usuarios.html", cliente=cliente, usuarios=usuarios
    )

@cliente_routes.route("/restringir_clientes", methods=["POST"])
@login_required
def restringir_clientes():
    """Ativa ou bloqueia em lote os *clientes* enviados por ID (check‑box)."""
    # Somente admin
    redirect_resp = _admin_required()
    if redirect_resp:
        return redirect_resp

    ids = request.form.getlist("cliente_ids")
    if not ids:
        flash("Nenhum cliente selecionado!", "warning")
        return redirect(url_for("dashboard_routes.dashboard"))

    clientes = Cliente.query.filter(Cliente.id.in_(ids)).all()
    for cliente in clientes:
        cliente.ativo = not cliente.ativo
    db.session.commit()

    flash(f"{len(clientes)} cliente(s) atualizados com sucesso!", "success")
    return redirect(url_for("dashboard_routes.dashboard"))


@cliente_routes.route("/excluir_clientes", methods=["POST"])
@login_required
def excluir_clientes():
    """Exclui, em lote, os *clientes* enviados via formulário (checkbox)."""
    redirect_resp = _admin_required()
    if redirect_resp:
        return redirect_resp

    ids = request.form.getlist("cliente_ids")
    if not ids:
        flash("Nenhum cliente selecionado!", "warning")
        return redirect(url_for("dashboard_routes.dashboard"))

    for cid in ids:
        excluir_cliente(int(cid))

    flash(f"{len(ids)} cliente(s) excluídos!", "success")
    return redirect(url_for("dashboard_routes.dashboard"))


# ---------------------------------------------------------------------------
# Rota de (des)ativação ⇢ Usuário específico
# ---------------------------------------------------------------------------

@cliente_routes.route("/toggle_usuario/<int:usuario_id>")
@login_required
def toggle_usuario(usuario_id: int):
    """Ativa ou bloqueia o acesso de um *usuário* específico."""
    from models import Usuario
    redirect_resp = _admin_required()
    if redirect_resp:
        return redirect_resp

    usuario = Usuario.query.get_or_404(usuario_id)
    usuario.ativo = not usuario.ativo
    db.session.commit()

    flash(
        f"Usuário {'bloqueado' if not usuario.ativo else 'ativado'} com sucesso!",
        "success",
    )

    # Redireciona para a lista de usuários do cliente ao qual pertence
    if usuario.cliente_id:
        return redirect(url_for("cliente_routes.listar_usuarios", cliente_id=usuario.cliente_id))
    return redirect(url_for("dashboard_routes.dashboard"))
