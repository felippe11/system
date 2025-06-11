from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from extensions import db
from models import Cliente

cliente_routes = Blueprint('cliente_routes', __name__)

@cliente_routes.route('/cadastrar_cliente', methods=['GET', 'POST'])
@login_required
def cadastrar_cliente():
    if session.get('user_type') != 'admin':  # Apenas admin pode cadastrar clientes
        abort(403)

    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        # Verifica se o e-mail já está cadastrado
        cliente_existente = Cliente.query.filter_by(email=email).first()
        if cliente_existente:
            flash("Já existe um cliente com esse e-mail!", "danger")
            return redirect(url_for('cliente_routes.cadastrar_cliente'))

        # Cria o cliente
        habilita_pagamento = True if request.form.get('habilita_pagamento') == 'on' else False
        novo_cliente = Cliente(
            nome=request.form['nome'],
            email=request.form['email'],
            senha=request.form['senha'],
            habilita_pagamento=habilita_pagamento
        )


        db.session.add(novo_cliente)
        db.session.commit()

        flash("Cliente cadastrado com sucesso!", "success")
        return redirect(url_for('cliente_routes.dashboard'))

    return render_template("auth/cadastrar_cliente.html")



@cliente_routes.route('/editar_cliente/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(cliente_id):
    if current_user.tipo != 'admin':
        flash('Acesso negado!', 'danger')
        return redirect(url_for('cliente_routes.dashboard'))

    cliente = Cliente.query.get_or_404(cliente_id)
    if request.method == 'POST':
        cliente.nome = request.form.get('nome')
        cliente.email = request.form.get('email')
        nova_senha = request.form.get('senha')
        if nova_senha:  # Só atualiza a senha se fornecida
            cliente.senha = generate_password_hash(nova_senha)
        
        # Debug: exibe o valor recebido do checkbox
        debug_checkbox = request.form.get('habilita_pagamento')
        print("DEBUG: Valor recebido do checkbox 'habilita_pagamento':", debug_checkbox)
        # Se você tiver um logger configurado, pode usar:
        # logger.debug("Valor recebido do checkbox 'habilita_pagamento': %s", debug_checkbox)
        
        cliente.habilita_pagamento = True if debug_checkbox == 'on' else False
        
        # Debug: exibe o valor que está sendo salvo
        print("DEBUG: Valor salvo em cliente.habilita_pagamento:", cliente.habilita_pagamento)
        # logger.debug("Valor salvo em cliente.habilita_pagamento: %s", cliente.habilita_pagamento)

        try:
            db.session.commit()
            flash("Cliente atualizado com sucesso!", "success")
        except Exception as e:
            db.session.rollback()
            print("DEBUG: Erro ao atualizar cliente:", e)
            # logger.error("Erro ao atualizar cliente: %s", e, exc_info=True)
            flash(f"Erro ao atualizar cliente: {str(e)}", "danger")
        return redirect(url_for('cliente_routes.dashboard'))
    
    return render_template('auth/editar_cliente.html', cliente=cliente)


@cliente_routes.route('/excluir_cliente/<int:cliente_id>', methods=['POST'])
@login_required
def excluir_cliente(cliente_id):
    if current_user.tipo != 'admin':
        flash("Apenas administradores podem excluir clientes.", "danger")
        return redirect(url_for('cliente_routes.dashboard'))

    cliente = Cliente.query.get_or_404(cliente_id)

    try:
        from sqlalchemy import or_, text
        from models import (
            Usuario, Oficina, OficinaDia, Checkin, Inscricao, MaterialOficina, RelatorioOficina,
            Ministrante, Evento, Patrocinador, CampoPersonalizadoCadastro, LinkCadastro,
            ConfiguracaoCliente, CertificadoTemplate, Feedback, RespostaCampo, RespostaFormulario,
            ConfiguracaoAgendamento, HorarioVisitacao, SalaVisitacao
        )

        # ===============================
        # 1️⃣ PARTICIPANTES
        # ===============================
        participantes = Usuario.query.filter_by(cliente_id=cliente.id).all()

        with db.session.no_autoflush:
            for usuario in participantes:
                Checkin.query.filter_by(usuario_id=usuario.id).delete()
                Inscricao.query.filter_by(usuario_id=usuario.id).delete()
                Feedback.query.filter_by(usuario_id=usuario.id).delete()
                RespostaCampo.query.filter_by(resposta_formulario_id=usuario.id).delete()
                RespostaFormulario.query.filter_by(usuario_id=usuario.id).delete()

        Usuario.query.filter_by(cliente_id=cliente.id).delete()

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

            db.session.execute(
                text('DELETE FROM oficina_ministrantes_association WHERE oficina_id = :oficina_id'),
                {'oficina_id': oficina.id}
            )

            db.session.delete(oficina)

        # ===============================
        # 3️⃣ MINISTRANTES
        # ===============================
        Ministrante.query.filter_by(cliente_id=cliente.id).delete()

        # ===============================
        # 4️⃣ EVENTOS E DEPENDÊNCIAS
        # ===============================
        eventos = Evento.query.filter(
            or_(Evento.cliente_id == cliente.id, Evento.cliente_id == None)
        ).all()

        for evento in eventos:
            with db.session.no_autoflush:
                HorarioVisitacao.query.filter_by(evento_id=evento.id).delete()
                ConfiguracaoAgendamento.query.filter_by(evento_id=evento.id).delete()
                Patrocinador.query.filter_by(evento_id=evento.id).delete()
                SalaVisitacao.query.filter_by(evento_id=evento.id).delete()  # ✅ NOVO

                db.session.delete(evento)

        # ===============================
        # 5️⃣ CONFIGURAÇÕES E VINCULAÇÕES
        # ===============================
        CertificadoTemplate.query.filter_by(cliente_id=cliente.id).delete()
        CampoPersonalizadoCadastro.query.filter_by(cliente_id=cliente.id).delete()
        LinkCadastro.query.filter_by(cliente_id=cliente.id).delete()
        ConfiguracaoCliente.query.filter_by(cliente_id=cliente.id).delete()

        # ===============================
        # 6️⃣ EXCLUI O CLIENTE
        # ===============================
        db.session.delete(cliente)
        db.session.commit()

        flash('Cliente e todos os dados vinculados foram excluídos com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir cliente: {str(e)}", 'danger')

    return redirect(url_for('cliente_routes.dashboard'))
