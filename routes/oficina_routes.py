from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import login_required, current_user
from models import (
    Oficina,
    OficinaDia,
    Evento,
    Checkin,
    Inscricao,
    MaterialOficina,
    RelatorioOficina,
    InscricaoTipo,
    Feedback,
)
from models.user import Ministrante, Cliente
from extensions import db
import logging
from datetime import datetime
from utils import obter_estados  # ou de onde essa função vem
from sqlalchemy import text


oficina_routes = Blueprint('oficina_routes', __name__, template_folder="../templates/oficina")

@oficina_routes.route('/oficina/<int:oficina_id>/participantes')
@login_required
def lista_participantes(oficina_id):
    """
    Exibe uma página com a lista de participantes de uma oficina específica.
    Substitui o modal que era usado anteriormente.
    """
    if current_user.tipo not in ['admin', 'cliente']:
        flash("Acesso não autorizado!", "danger")
        return redirect(url_for('dashboard_routes.dashboard'))
        
    # Busca a oficina com seus inscritos
    oficina = Oficina.query.get_or_404(oficina_id)
    
    # Verificar se a oficina pertence ao cliente atual
    if current_user.tipo == 'cliente' and oficina.cliente_id != current_user.id:
        flash("Você não tem permissão para acessar esta oficina!", "danger")
        return redirect(url_for('dashboard_routes.dashboard'))
    
    return render_template(
        'oficina/lista_participantes.html',
        oficina=oficina
    )

@oficina_routes.route('/criar_oficina', methods=['GET', 'POST'])
@login_required
def criar_oficina():
    if current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    estados = obter_estados()
    ministrantes_disponiveis = (
        Ministrante.query.filter_by(cliente_id=current_user.id).all()
        if current_user.tipo == 'cliente'
        else Ministrante.query.all()
    )
    clientes_disponiveis = Cliente.query.all() if current_user.tipo == 'admin' else []
    eventos_disponiveis = (
        Evento.query.filter_by(cliente_id=current_user.id).all()
        if current_user.tipo == 'cliente'
        else Evento.query.all()
    )

    if request.method == 'POST':
        logger.debug("Dados recebidos do formulário: %s", request.form)

        # Captura os campos do formulário
        titulo = request.form.get('titulo')
        descricao = request.form.get('descricao')
        ministrante_id = request.form.get('ministrante_id') or None
        vagas = request.form.get('vagas')
        carga_horaria = request.form.get('carga_horaria')
        estado = request.form.get('estado')
        cidade = request.form.get('cidade')
        opcoes_checkin = request.form.get('opcoes_checkin')
        palavra_correta = request.form.get('palavra_correta')
        evento_id = request.form.get('evento_id')

        # Validação básica dos campos obrigatórios
        if not all([titulo, descricao, vagas, carga_horaria, estado, cidade, evento_id]):
            flash("Erro: Todos os campos obrigatórios devem ser preenchidos!", "danger")
            return render_template(
                'criar_oficina.html',
                estados=estados,
                ministrantes=ministrantes_disponiveis,
                clientes=clientes_disponiveis,
                eventos=eventos_disponiveis,
                datas=request.form.getlist('data[]'),
                horarios_inicio=request.form.getlist('horario_inicio[]'),
                horarios_fim=request.form.getlist('horario_fim[]')
            )

        # Definir o cliente da oficina
        cliente_id = (
            request.form.get('cliente_id') if current_user.tipo == 'admin' else current_user.id
        )

        # Verifica se o cliente possui habilitação de pagamento
        inscricao_gratuita = (
            True if request.form.get('inscricao_gratuita') == 'on' else False
            if current_user.habilita_pagamento else True
        )

        try:
            # Cria a nova oficina
            # Determina o tipo de inscrição com base nos dados do formulário
            tipo_inscricao = request.form.get('tipo_inscricao', 'com_inscricao_com_limite')
            
            # Obtém os valores dos novos campos tipo_oficina e tipo_oficina_outro
            tipo_oficina = request.form.get('tipo_oficina', 'Oficina')
            tipo_oficina_outro = None
            if tipo_oficina == 'outros':
                tipo_oficina_outro = request.form.get('tipo_oficina_outro')
                
            nova_oficina = Oficina(
                titulo=titulo,
                descricao=descricao,
                ministrante_id=ministrante_id,
                vagas=int(vagas),  # Este valor será ajustado no __init__ conforme o tipo_inscricao
                carga_horaria=carga_horaria,
                estado=estado,
                cidade=cidade,
                cliente_id=cliente_id,
                evento_id=evento_id,
                opcoes_checkin=opcoes_checkin,
                palavra_correta=palavra_correta,
                tipo_inscricao=tipo_inscricao,
                tipo_oficina=tipo_oficina,
                tipo_oficina_outro=tipo_oficina_outro
            )
            nova_oficina.inscricao_gratuita = inscricao_gratuita
            db.session.add(nova_oficina)
            db.session.flush()  # Garante que o ID da oficina esteja disponível
            

            # Adiciona os tipos de inscrição (se não for gratuita)
            if not inscricao_gratuita:
                nomes_tipos = request.form.getlist('nome_tipo[]')
                precos = request.form.getlist('preco_tipo[]')
                if not nomes_tipos or not precos:
                    raise ValueError("Tipos de inscrição e preços são obrigatórios para oficinas pagas.")
                for nome, preco in zip(nomes_tipos, precos):
                    novo_tipo = InscricaoTipo(
                        oficina_id=nova_oficina.id,
                        nome=nome,
                        preco=float(preco)
                    )
                    db.session.add(novo_tipo)

            # Adiciona os dias e horários
            datas = request.form.getlist('data[]')
            horarios_inicio = request.form.getlist('horario_inicio[]')
            horarios_fim = request.form.getlist('horario_fim[]')
            if not datas or len(datas) != len(horarios_inicio) or len(datas) != len(horarios_fim):
                raise ValueError("Datas e horários inconsistentes.")
            if any(d == '' for d in datas) or any(h == '' for h in horarios_inicio) or any(f == '' for f in horarios_fim):
                raise ValueError("Todos os campos de data e horário devem ser preenchidos.")
            for i in range(len(datas)):
                novo_dia = OficinaDia(
                    oficina_id=nova_oficina.id,
                    data=datetime.strptime(datas[i], '%Y-%m-%d').date(),
                    horario_inicio=horarios_inicio[i],
                    horario_fim=horarios_fim[i]
                )
                db.session.add(novo_dia)
            
                # 3) Captura lista de IDs de ministrantes extras
            ids_extras = request.form.getlist('ministrantes_ids[]')  # array
            for mid in ids_extras:
                m = Ministrante.query.get(int(mid))
                if m:
                    nova_oficina.ministrantes_associados.append(m)

            db.session.commit()
            flash('Atividade criada com sucesso!', 'success')
            return redirect(
                url_for('dashboard_routes.dashboard_cliente' if current_user.tipo == 'cliente' else 'dashboard_routes.dashboard')
            )

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar oficina: %s", str(e))
            flash(f"Erro ao criar oficina: {str(e)}", "danger")
            return render_template(
                'criar_oficina.html',
                estados=estados,
                ministrantes=ministrantes_disponiveis,
                clientes=clientes_disponiveis,
                eventos=eventos_disponiveis,
                datas=request.form.getlist('data[]'),
                horarios_inicio=request.form.getlist('horario_inicio[]'),
                horarios_fim=request.form.getlist('horario_fim[]')
            )

    return render_template(
        'criar_oficina.html',
        estados=estados,
        ministrantes=ministrantes_disponiveis,
        clientes=clientes_disponiveis,
        eventos=eventos_disponiveis
    )


@oficina_routes.route('/editar_oficina/<int:oficina_id>', methods=['GET', 'POST'])
@login_required
def editar_oficina(oficina_id):
    oficina = Oficina.query.get_or_404(oficina_id)

    if current_user.tipo == 'cliente' and oficina.cliente_id != current_user.id:
        flash('Você não tem permissão para editar esta atividade.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard_cliente'))

    estados = obter_estados()
    if current_user.tipo == 'cliente':
        ministrantes = Ministrante.query.filter_by(cliente_id=current_user.id).all()
        eventos_disponiveis = Evento.query.filter_by(cliente_id=current_user.id).all()
    else:
        ministrantes = Ministrante.query.all()
        eventos_disponiveis = Evento.query.all()

    clientes_disponiveis = Cliente.query.all() if current_user.tipo == 'admin' else []

    if request.method == 'POST':
        oficina.titulo = request.form.get('titulo')
        oficina.descricao = request.form.get('descricao')
        ministrante_id = request.form.get('ministrante_id') or None
        oficina.ministrante_id = ministrante_id
        oficina.carga_horaria = request.form.get('carga_horaria')
        oficina.estado = request.form.get('estado')
        oficina.cidade = request.form.get('cidade')
        oficina.opcoes_checkin = request.form.get('opcoes_checkin')
        oficina.palavra_correta = request.form.get('palavra_correta')
        oficina.evento_id = request.form.get('evento_id')  # Atualiza o evento_id
        
        # Atualiza os campos tipo_oficina e tipo_oficina_outro
        tipo_oficina = request.form.get('tipo_oficina', 'Oficina')
        oficina.tipo_oficina = tipo_oficina
        if tipo_oficina == 'outros':
            oficina.tipo_oficina_outro = request.form.get('tipo_oficina_outro')
        else:
            oficina.tipo_oficina_outro = None
        
        # Atualiza o tipo de inscrição e ajusta as vagas conforme necessário
        tipo_inscricao = request.form.get('tipo_inscricao', 'com_inscricao_com_limite')
        oficina.tipo_inscricao = tipo_inscricao
        
        # Define o valor de vagas com base no tipo de inscrição
        if tipo_inscricao == 'sem_inscricao':
            oficina.vagas = 0  # Não é necessário controlar vagas
        elif tipo_inscricao == 'com_inscricao_sem_limite':
            oficina.vagas = 9999  # Um valor alto para representar "sem limite"
        else:  # com_inscricao_com_limite
            oficina.vagas = int(request.form.get('vagas'))

        # Permitir que apenas admins alterem o cliente
        if current_user.tipo == 'admin':
            oficina.cliente_id = request.form.get('cliente_id') or None
            
        # Atualiza o campo inscricao_gratuita
        if current_user.habilita_pagamento:
            oficina.inscricao_gratuita = True if request.form.get('inscricao_gratuita') == 'on' else False
        else:
            oficina.inscricao_gratuita = True

        try:
            # Atualizar os dias e horários
            datas = request.form.getlist('data[]')
            horarios_inicio = request.form.getlist('horario_inicio[]')
            horarios_fim = request.form.getlist('horario_fim[]')
            oficina.ministrantes_associados = []  # Limpa os ministrantes associados

            # Capturar IDs dos ministrantes selecionados
            ministrantes_ids = request.form.getlist('ministrantes_ids[]')
            for mid in ministrantes_ids:
                m = Ministrante.query.get(int(mid))
                if m:
                    oficina.ministrantes_associados.append(m)

            if not datas or len(datas) != len(horarios_inicio) or len(datas) != len(horarios_fim):
                raise ValueError("Datas e horários inconsistentes.")

            # Apagar os registros antigos para evitar duplicação
            OficinaDia.query.filter_by(oficina_id=oficina.id).delete()

            for i in range(len(datas)):
                novo_dia = OficinaDia(
                    oficina_id=oficina.id,
                    data=datetime.strptime(datas[i], '%Y-%m-%d').date(),
                    horario_inicio=horarios_inicio[i],
                    horario_fim=horarios_fim[i]
                )
                db.session.add(novo_dia)
                
            # Atualiza os tipos de inscrição (se não for gratuita)
            if not oficina.inscricao_gratuita:
                # Remove os tipos de inscrição antigos
                InscricaoTipo.query.filter_by(oficina_id=oficina.id).delete()
                
                # Adiciona os novos tipos de inscrição
                nomes_tipos = request.form.getlist('nome_tipo[]')
                precos = request.form.getlist('preco_tipo[]')
                if not nomes_tipos or not precos:
                    raise ValueError("Tipos de inscrição e preços são obrigatórios para oficinas pagas.")
                for nome, preco in zip(nomes_tipos, precos):
                    novo_tipo = InscricaoTipo(
                        oficina_id=oficina.id,
                        nome=nome,
                        preco=float(preco)
                    )
                    db.session.add(novo_tipo)

            db.session.commit()
            flash('Oficina editada com sucesso!', 'success')
            return redirect(url_for('dashboard_routes.dashboard_cliente' if current_user.tipo == 'cliente' else 'dashboard_routes.dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao editar oficina: {str(e)}', 'danger')
            return render_template(
                'editar_oficina.html',
                oficina=oficina,
                estados=estados,
                ministrantes=ministrantes,
                clientes=clientes_disponiveis,
                eventos=eventos_disponiveis
            )

    return render_template(
        'editar_oficina.html',
        oficina=oficina,
        estados=estados,
        ministrantes=ministrantes,
        clientes=clientes_disponiveis,
        eventos=eventos_disponiveis
    )

@oficina_routes.route('/excluir_oficina/<int:oficina_id>', methods=['POST'])
@login_required
def excluir_oficina(oficina_id):
    oficina = Oficina.query.get_or_404(oficina_id)

    # 🚨 Cliente só pode excluir oficinas que ele criou
    if current_user.tipo == 'cliente' and oficina.cliente_id != current_user.id:
        flash('Você não tem permissão para excluir esta oficina.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard_cliente'))

    try:
        logger.debug("Excluindo oficina ID: %s", oficina_id)

        # 1️⃣ **Excluir check-ins relacionados à oficina**
        db.session.query(Checkin).filter_by(oficina_id=oficina.id).delete()
        logger.debug("Check-ins removidos.")

        # 2️⃣ **Excluir inscrições associadas à oficina**
        db.session.query(Inscricao).filter_by(oficina_id=oficina.id).delete()
        logger.debug("Inscrições removidas.")

        # 3️⃣ **Excluir registros de datas da oficina (OficinaDia)**
        db.session.query(OficinaDia).filter_by(oficina_id=oficina.id).delete()
        logger.debug("Dias da oficina removidos.")

        # 4️⃣ **Excluir materiais da oficina**
        db.session.query(MaterialOficina).filter_by(oficina_id=oficina.id).delete()
        logger.debug("Materiais da oficina removidos.")

        # 5️⃣ **Excluir relatórios associados à oficina**
        db.session.query(RelatorioOficina).filter_by(oficina_id=oficina.id).delete()
        logger.debug("Relatórios da oficina removidos.")

        # 6️⃣ **Excluir feedbacks relacionados à oficina**
        db.session.query(Feedback).filter_by(oficina_id=oficina.id).delete()
        logger.debug("Feedbacks da oficina removidos.")

        # 7️⃣ **Excluir tipos de inscrição da oficina**
        db.session.query(InscricaoTipo).filter_by(oficina_id=oficina.id).delete()
        logger.debug("Tipos de inscrição removidos.")
        # 8️⃣ **Excluir associações com ministrantes na tabela de associação**
        from sqlalchemy import text
        db.session.execute(
            text('DELETE FROM oficina_ministrantes_association WHERE oficina_id = :oficina_id'),
            {'oficina_id': oficina.id}
        )
        logger.debug("Associações com ministrantes removidas.")

        # 9️⃣ **Excluir a própria oficina**
        db.session.delete(oficina)
        db.session.commit()
        logger.info("Oficina removida com sucesso!")
        flash('Oficina excluída com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        logger.error("Erro ao excluir oficina %s: %s", oficina_id, str(e))
        flash(f'Erro ao excluir oficina: {str(e)}', 'danger')

    return redirect(url_for('dashboard_routes.dashboard_cliente' if current_user.tipo == 'cliente' else 'dashboard_routes.dashboard'))


@oficina_routes.route("/excluir_todas_oficinas", methods=["POST"])
@login_required
def excluir_todas_oficinas():
    if current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso Autorizado!', 'danger')
        

    try:
        if current_user.tipo == 'admin':
            oficinas = Oficina.query.all()
        else:  # Cliente só pode excluir suas próprias oficinas
            oficinas = Oficina.query.filter_by(cliente_id=current_user.id).all()

        if not oficinas:
            flash("Não há oficinas para excluir.", "warning")
            return redirect(url_for("dashboard_routes.dashboard_cliente" if current_user.tipo == 'cliente' else "dashboard_routes.dashboard"))

        for oficina in oficinas:
            db.session.query(Checkin).filter_by(oficina_id=oficina.id).delete()
            db.session.query(Inscricao).filter_by(oficina_id=oficina.id).delete()
            db.session.query(OficinaDia).filter_by(oficina_id=oficina.id).delete()
            db.session.query(MaterialOficina).filter_by(oficina_id=oficina.id).delete()
            db.session.query(RelatorioOficina).filter_by(oficina_id=oficina.id).delete()
            db.session.query(Feedback).filter_by(oficina_id=oficina.id).delete()
            db.session.query(InscricaoTipo).filter_by(oficina_id=oficina.id).delete()
            db.session.delete(oficina)

        db.session.commit()
        flash("Oficinas excluídas com sucesso!", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir oficinas: {str(e)}", "danger")

    return redirect(url_for("dashboard_routes.dashboard_cliente" if current_user.tipo == 'cliente' else "dashboard_routes.dashboard"))

@oficina_routes.route('/api/oficinas_mesmo_evento/<int:oficina_id>')
@login_required
def oficinas_mesmo_evento(oficina_id):
    oficina = Oficina.query.get_or_404(oficina_id)
    evento = oficina.evento
    oficinas = Oficina.query.filter(
        Oficina.evento_id == oficina.evento_id,
        Oficina.id != oficina_id
    ).all()
    return jsonify({
        'evento_nome': evento.nome if evento else 'Sem evento',
        'oficinas': [
            {
                'id': o.id,
                'titulo': o.titulo,
                'vagas': o.vagas,
                'evento_nome': evento.nome if evento else 'Sem evento'
            } for o in oficinas
        ]
    })
    
# routes.py  (ou onde ficam suas rotas API)
@oficina_routes.route('/api/eventos_com_oficinas')
@login_required
def eventos_com_oficinas():
    # ① Se for cliente, mostra só os eventos dele.  Admin vê todos.
    q = Evento.query
    if current_user.tipo == 'cliente':
        q = q.filter_by(cliente_id=current_user.id)

    eventos = q.order_by(Evento.nome).all()
    payload = []
    for ev in eventos:
        payload.append({
            'id': ev.id,
            'nome': ev.nome,
            'oficinas': [
                {'id': o.id, 'titulo': o.titulo, 'vagas': o.vagas}
                for o in ev.oficinas
            ]
        })
    return jsonify(payload)

@oficina_routes.route('/oficinas_disponiveis')
@login_required
def oficinas_disponiveis():
    oficinas = Oficina.query.filter_by(cliente_id=current_user.cliente_id).all()
    return render_template('oficinas.html', oficinas=oficinas)

# routes/links_ui.py  (ou no mesmo arquivo se preferir)
@oficina_routes.route("/links/gerar", methods=["GET"])
@login_required
def gerar_link_ui():
    """Página HTML para criar/gerenciar links – usa a API JSON existente."""
    return render_template("links/gerar.html")

@oficina_routes.route('/oficinas', methods=['GET'])
@login_required
def listar_oficinas():
    if session.get('user_type') == 'participante':
        oficinas = Oficina.query.filter_by(cliente_id=current_user.cliente_id).all()  # ✅ Mostra apenas oficinas do Cliente que registrou o usuário
    else:
        oficinas = Oficina.query.all()

    return render_template('oficinas.html', oficinas=oficinas)

