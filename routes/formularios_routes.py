from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory,
    send_file,
)
import logging

logger = logging.getLogger(__name__)
from flask_login import login_required, current_user
from utils.mfa import mfa_required
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload
import os

from sqlalchemy import text
from extensions import db
from models import (
    Formulario,
    RespostaFormulario,
    RespostaCampo,
    CampoFormulario,
    FormularioTemplate,
    CampoFormularioTemplate,
    FeedbackCampo,
    Usuario,
    Inscricao,
    Oficina,
    Ministrante,
    AuditLog,
    Evento,
    ConfiguracaoCliente,
)
from services.pdf_service import gerar_pdf_respostas

formularios_routes = Blueprint(
    'formularios_routes',
    __name__,
    template_folder="../templates/formulario"
)

@formularios_routes.route('/formularios', methods=['GET'])
@login_required
def listar_formularios():
    """
    •  Superusuário   → vê todos os formulários do sistema.
    •  Demais perfis  → vê apenas formulários ligados ao seu cliente.
    Cada formulário vem com TODAS as respostas + usuário de cada resposta
    para evitar consultas N+1.
    """
    # Base query com eager-load das relações necessárias
    q = (Formulario.query
            .options(
                joinedload(Formulario.respostas)
                    .joinedload(RespostaFormulario.usuario)   # carrega o autor da resposta
            )
            .order_by(Formulario.nome)
        )

    # 1. Se o usuário for superadmin, não filtra nada
    if getattr(current_user, "tipo", None) == "superadmin":
        formularios = q.all()

    # 2. Caso contrário, mostra apenas o que pertence ao cliente dele
    else:
        cliente_id = getattr(current_user, "cliente_id", None)

        # fallback: se o modelo antigo gravou cliente_id = current_user.id
        # usa o id do usuário como último recurso
        if not cliente_id:
            cliente_id = current_user.id

        formularios = q.filter(Formulario.cliente_id == cliente_id).all()

    # Envia tudo para o novo template que lista formulários + respostas
    return render_template('formularios.html',
                           formularios=formularios)


@formularios_routes.route('/formularios/novo', methods=['GET', 'POST'])
@login_required
def criar_formulario():
    eventos_disponiveis = (
        Evento.query.filter_by(cliente_id=current_user.id).all()
        if current_user.tipo == 'cliente'
        else Evento.query.all()
    )

    config_cli = ConfiguracaoCliente.query.filter_by(cliente_id=current_user.id).first()

    if request.method == 'POST':
        count_forms = Formulario.query.filter_by(cliente_id=current_user.id).count()
        if config_cli and config_cli.limite_formularios is not None and count_forms >= config_cli.limite_formularios:
            flash('Limite de formulários atingido.', 'danger')
            return redirect(url_for('formularios_routes.listar_formularios'))
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        evento_ids = request.form.getlist('eventos')

        novo_formulario = Formulario(
            nome=nome,
            descricao=descricao,
            cliente_id=current_user.id  # Relaciona com o cliente logado
        )

        if evento_ids:
            eventos_sel = Evento.query.filter(Evento.id.in_(evento_ids)).all()
            novo_formulario.eventos = eventos_sel

        db.session.add(novo_formulario)
        db.session.commit()
        flash('Formulário criado com sucesso!', 'success')
        return redirect(url_for('formularios_routes.listar_formularios'))

    return render_template("criar_formulario.html", eventos=eventos_disponiveis)

@formularios_routes.route('/formularios/<int:formulario_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_formulario(formulario_id):
    formulario = Formulario.query.get_or_404(formulario_id)

    if request.method == 'POST':
        formulario.nome = request.form.get('nome')
        formulario.descricao = request.form.get('descricao')
        db.session.commit()
        flash('Formulário atualizado!', 'success')
        return redirect(url_for('formularios_routes.listar_formularios'))

    return render_template('editar_formulario.html', formulario=formulario)

@formularios_routes.route('/formularios/<int:formulario_id>/deletar', methods=['POST'])
@login_required
def deletar_formulario(formulario_id):
    formulario = Formulario.query.get_or_404(formulario_id)
    db.session.delete(formulario)
    db.session.commit()
    flash('Formulário deletado com sucesso!', 'success')
    return redirect(url_for('formularios_routes.listar_formularios'))


@formularios_routes.route('/formularios/<int:formulario_id>/eventos', methods=['GET', 'POST'])
@login_required
def editar_eventos_formulario(formulario_id):
    """Permite atribuir eventos a um formulário."""
    formulario = Formulario.query.get_or_404(formulario_id)

    # Admins podem ver todos eventos, clientes apenas os seus
    if getattr(current_user, 'tipo', None) in ('admin', 'superadmin'):
        eventos = Evento.query.order_by(Evento.nome).all()
    else:
        eventos = Evento.query.filter_by(cliente_id=current_user.id).order_by(Evento.nome).all()

    if request.method == 'POST':
        selecionados = [int(eid) for eid in request.form.getlist('eventos')]
        formulario.eventos = [e for e in eventos if e.id in selecionados]
        db.session.commit()
        flash('Eventos atualizados com sucesso!', 'success')
        return redirect(url_for('formularios_routes.editar_eventos_formulario', formulario_id=formulario_id))

    return render_template('atribuir_eventos.html', formulario=formulario, eventos=eventos)

@formularios_routes.route('/formularios/<int:formulario_id>/campos', methods=['GET', 'POST'])
@login_required
def gerenciar_campos(formulario_id):
    formulario = Formulario.query.get_or_404(formulario_id)

    if request.method == 'POST':
        nome = request.form.get('nome')
        tipo = request.form.get('tipo')
        opcoes = request.form.get('opcoes', '').strip()
        obrigatorio = request.form.get('obrigatorio') == 'on'
        tamanho_max = request.form.get('tamanho_max') or None
        regex_validacao = request.form.get('regex_validacao') or None

        novo_campo = CampoFormulario(
            formulario_id=formulario.id,
            nome=nome,
            tipo=tipo,
            opcoes=opcoes if tipo in ['dropdown', 'checkbox', 'radio'] else None,
            obrigatorio=obrigatorio,
            tamanho_max=int(tamanho_max) if tamanho_max else None,
            regex_validacao=regex_validacao
        )

        db.session.add(novo_campo)
        db.session.commit()
        flash('Campo adicionado com sucesso!', 'success')

        return redirect(url_for('formularios_routes.gerenciar_campos', formulario_id=formulario.id))

    return render_template('gerenciar_campos.html', formulario=formulario)

@formularios_routes.route('/campos/<int:campo_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_campo(campo_id):
    campo = CampoFormulario.query.get_or_404(campo_id)

    if request.method == 'POST':
        campo.nome = request.form.get('nome')
        campo.tipo = request.form.get('tipo')
        campo.opcoes = request.form.get('opcoes', '').strip() if campo.tipo in ['dropdown', 'checkbox', 'radio'] else None
        campo.obrigatorio = request.form.get('obrigatorio') == 'on'
        campo.tamanho_max = request.form.get('tamanho_max') or None
        campo.regex_validacao = request.form.get('regex_validacao') or None

        db.session.commit()
        flash('Campo atualizado com sucesso!', 'success')

        return redirect(url_for('formularios_routes.gerenciar_campos', formulario_id=campo.formulario_id))

    return render_template('editar_campo.html', campo=campo)

@formularios_routes.route('/campos/<int:campo_id>/deletar', methods=['POST'])
@login_required
def deletar_campo(campo_id):
    campo = CampoFormulario.query.get_or_404(campo_id)
    formulario_id = campo.formulario_id
    db.session.delete(campo)
    db.session.commit()
    flash('Campo removido com sucesso!', 'success')

    return redirect(url_for('formularios_routes.gerenciar_campos', formulario_id=formulario_id))

@formularios_routes.route('/formularios/<int:formulario_id>/preencher', methods=['GET', 'POST'])
@login_required
def preencher_formulario(formulario_id):
    formulario = Formulario.query.get_or_404(formulario_id)

    if request.method == 'POST':
        resposta_formulario = RespostaFormulario(
            formulario_id=formulario.id,
            usuario_id=current_user.id
        )
        db.session.add(resposta_formulario)
        db.session.commit()

        for campo in formulario.campos:
            valor = request.form.get(str(campo.id))
            if campo.tipo == 'file' and 'file_' + str(campo.id) in request.files:
                arquivo = request.files['file_' + str(campo.id)]
                if arquivo.filename:
                    filename = secure_filename(arquivo.filename)
                    caminho_arquivo = os.path.join('uploads', 'respostas', filename)
                    os.makedirs(os.path.dirname(caminho_arquivo), exist_ok=True)
                    arquivo.save(caminho_arquivo)
                    valor = caminho_arquivo  # Salva o caminho do arquivo

            resposta_campo = RespostaCampo(
                resposta_formulario_id=resposta_formulario.id,
                campo_id=campo.id,
                valor=valor
            )
            db.session.add(resposta_campo)

        db.session.commit()
        flash("Formulário enviado com sucesso!", "success")
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

    return render_template('inscricao/preencher_formulario.html', formulario=formulario)


@formularios_routes.route('/formularios_participante', methods=['GET'])
@login_required
def listar_formularios_participante():
    if current_user.tipo != 'participante':
        flash("Acesso negado!", "danger")
        return redirect(url_for('dashboard_routes.dashboard'))

    # Busca apenas formulários disponíveis para o participante
    # Filtra formulários criados pelo mesmo cliente ao qual o participante está associado
    cliente_id = current_user.cliente_id
    evento_id = request.args.get('evento_id', type=int) or current_user.evento_id
    
    if not cliente_id:
        flash("Você não está associado a nenhum cliente.", "warning")
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))
        
    # Base query
    if evento_id:
        # Se um evento foi selecionado, exibe formulários associados
        # independentemente do cliente do participante
        query = Formulario.query.join(Formulario.eventos).filter(Evento.id == evento_id)
    else:
        # Mantém o comportamento atual quando nenhum evento é fornecido
        query = Formulario.query.filter_by(cliente_id=cliente_id)
    formularios = query.all()
    
    # Não há relação direta entre formulários e ministrantes no modelo atual,
    # então estamos filtrando apenas pelo cliente_id do participante

    if not formularios:
        flash("Nenhum formulário disponível no momento.", "warning")
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

    return render_template('formularios_participante.html', formularios=formularios)

@formularios_routes.route('/respostas/<int:resposta_id>', methods=['GET'])
@login_required
def visualizar_resposta(resposta_id):
    resposta = RespostaFormulario.query.get_or_404(resposta_id)

    # Se quiser, confira se o current_user é o dono da resposta
    if resposta.usuario_id != current_user.id:
        flash("Você não tem permissão para ver esta resposta.", "danger")
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

    return render_template('visualizar_resposta.html', resposta=resposta)


    
    
@formularios_routes.route('/formularios/<int:formulario_id>/exportar_csv')
@login_required
def exportar_csv(formulario_id):
    import csv
    import io
    import pytz
    from flask import Response, stream_with_context

    formulario = Formulario.query.get_or_404(formulario_id)
    respostas = RespostaFormulario.query.filter_by(formulario_id=formulario.id).all()

    csv_filename = f"respostas_{formulario.id}.csv"
    
    # Função para converter datetime para o fuso de Brasília
    def convert_to_brasilia(dt):
        brasilia_tz = pytz.timezone("America/Sao_Paulo")
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.utc)
        return dt.astimezone(brasilia_tz)

    # Função geradora que cria o CSV linha a linha
    def generate():
        output = io.StringIO()
        writer = csv.writer(output, delimiter=',')
        
        # Cabeçalho do CSV: Usuário, Data de Envio e os nomes dos campos do formulário
        header = ["Usuário", "Data de Envio"] + [campo.nome for campo in formulario.campos]
        writer.writerow(header)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
        
        # Preenche as linhas com as respostas
        for resposta in respostas:
            usuario_nome = resposta.usuario.nome if resposta.usuario else "N/A"
            data_envio = convert_to_brasilia(resposta.data_submissao).strftime('%d/%m/%Y %H:%M')
            row = [usuario_nome, data_envio]
            for campo in formulario.campos:
                valor = next((resp.valor for resp in resposta.respostas_campos if resp.campo_id == campo.id), "")
                row.append(valor)
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return Response(
        stream_with_context(generate()),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={csv_filename}"}
    )


@formularios_routes.route('/formularios/<int:formulario_id>/exportar_xlsx')
@login_required
def exportar_xlsx(formulario_id):
    formulario = Formulario.query.get_or_404(formulario_id)
    respostas = RespostaFormulario.query.filter_by(formulario_id=formulario.id).all()

    try:
        import xlsxwriter
        from io import BytesIO
    except ImportError:
        flash('Biblioteca XLSXWriter não disponível', 'warning')
        return redirect(url_for('formularios_routes.exportar_csv', formulario_id=formulario_id))

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    sheet = workbook.add_worksheet('Respostas')

    headers = ['Usuário', 'Data de Envio'] + [c.nome for c in formulario.campos]
    for col, h in enumerate(headers):
        sheet.write(0, col, h)

    for row_idx, resposta in enumerate(respostas, start=1):
        usuario_nome = resposta.usuario.nome if resposta.usuario else 'N/A'
        data_envio = resposta.data_submissao.strftime('%d/%m/%Y %H:%M')
        row_data = [usuario_nome, data_envio]
        for campo in formulario.campos:
            valor = next((r.valor for r in resposta.respostas_campos if r.campo_id == campo.id), '')
            row_data.append(valor)
        for col_idx, val in enumerate(row_data):
            sheet.write(row_idx, col_idx, val)

    workbook.close()
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='respostas.xlsx')


@formularios_routes.route('/formularios/<int:formulario_id>/gerar_pdf_respostas')
@login_required
def gerar_pdf_respostas_route(formulario_id):
    """Gera um PDF contendo todas as respostas do formulário."""
    resultado = gerar_pdf_respostas(formulario_id)
    if isinstance(resultado, tuple):
        _, mensagem = resultado
        flash(mensagem, 'warning')
        return redirect(request.referrer or url_for('formularios_routes.listar_respostas'))
    return resultado


@formularios_routes.route('/respostas/<path:filename>')
@login_required
@mfa_required
def get_resposta_file(filename):
    logger.debug("get_resposta_file foi chamado com: %s", filename)
    uploads_folder = os.path.join('uploads', 'respostas')
    uid = current_user.id if hasattr(current_user, 'id') else None
    log = AuditLog(user_id=uid, submission_id=None, event_type='download')
    db.session.add(log)
    db.session.commit()
    return send_from_directory(uploads_folder, filename)


@formularios_routes.route('/formularios/<int:formulario_id>/excluir', methods=['POST'])
@login_required
def excluir_formulario(formulario_id):
    formulario = Formulario.query.get_or_404(formulario_id)

    try:
        # 1️⃣ Exclui FeedbackCampo associados às respostas do formulário (SQL textual corrigido)
        db.session.execute(text('''
            DELETE FROM feedback_campo
            WHERE resposta_campo_id IN (
                SELECT id FROM respostas_campo
                WHERE resposta_formulario_id IN (
                    SELECT id FROM respostas_formulario
                    WHERE formulario_id = :fid
                )
            );
        '''), {'fid': formulario_id})

        # 2️⃣ Exclui RespostaCampo
        RespostaCampo.query.filter(
            RespostaCampo.resposta_formulario_id.in_(
                db.session.query(RespostaFormulario.id).filter_by(formulario_id=formulario_id)
            )
        ).delete(synchronize_session=False)

        # 3️⃣ Exclui RespostaFormulario
        RespostaFormulario.query.filter_by(formulario_id=formulario_id).delete()

        # 4️⃣ Exclui o Formulário
        formulario = Formulario.query.get_or_404(formulario_id)
        db.session.delete(formulario)

        db.session.commit()

        flash("Formulário e todos os dados relacionados excluídos com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir formulário: {str(e)}", "danger")

    return redirect(url_for('formularios_routes.listar_formularios'))

@formularios_routes.route('/formularios/<int:formulario_id>/respostas_ministrante', methods=['GET'])
@login_required
def listar_respostas_ministrante(formulario_id):
    # 1) Verifica se o current_user é ministrante
    if not isinstance(current_user, Ministrante):
        flash('Apenas ministrantes têm acesso a esta tela.', 'danger')
        return redirect(url_for('dashboard_ministrante_routes.dashboard_ministrante'))

    formulario = Formulario.query.get_or_404(formulario_id)
    # 2) Carrega as respostas
    respostas = RespostaFormulario.query.filter_by(formulario_id=formulario.id).all()

    return render_template(
        'listar_respostas_ministrante.html',
        formulario=formulario,
        respostas=respostas
    )

@formularios_routes.route(
    '/respostas/<int:resposta_id>/feedback', 
    methods=['GET', 'POST'], 
    endpoint='dar_feedback_resposta_formulario'
)
@login_required
def dar_feedback_resposta(resposta_id):
    # só Ministrantes ou Clientes
    if not (isinstance(current_user, Ministrante) or current_user.tipo == 'cliente'):
        flash('Apenas clientes e ministrantes podem dar feedback.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    resposta = RespostaFormulario.query.get_or_404(resposta_id)
    lista_campos = resposta.formulario.campos
    resposta_campos = resposta.respostas_campos

    if request.method == 'POST':
        for rc in resposta_campos:
            nome_textarea = f"feedback_{rc.id}"
            texto = request.form.get(nome_textarea, "").strip()
            if not texto:
                continue

            fb = FeedbackCampo(
                resposta_campo_id=rc.id,
                ministrante_id=current_user.id if isinstance(current_user, Ministrante) else None,
                cliente_id    =current_user.id if current_user.tipo == 'cliente' else None,
                texto_feedback=texto
            )
            db.session.add(fb)

        db.session.commit()
        flash("Feedback registrado com sucesso!", "success")
        return redirect(url_for('formularios_routes.dar_feedback_resposta_formulario', resposta_id=resposta_id))

    return render_template(
        'dar_feedback_resposta.html',
        resposta=resposta,
        lista_campos=lista_campos,
        resposta_campos=resposta_campos
    )

@formularios_routes.route('/formulario_templates', methods=['GET'])
@login_required
def listar_templates():
    if current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    # Filter by cliente if not admin
    if current_user.tipo == 'cliente':
        templates = FormularioTemplate.query.filter(
            (FormularioTemplate.cliente_id == current_user.id) | 
            (FormularioTemplate.is_default == True)
        ).all()
    else:  # Admin sees all templates
        templates = FormularioTemplate.query.all()
        
    return render_template('templates_formulario.html', templates=templates)

@formularios_routes.route('/formulario_templates/novo', methods=['GET', 'POST'])
@login_required
def criar_template():
    if current_user.tipo not in ['admin', 'cliente']:
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        categoria = request.form.get('categoria')
        is_default = request.form.get('is_default') == 'on'
        
        # Only admin can create default templates
        if current_user.tipo != 'admin' and is_default:
            is_default = False
        
        novo_template = FormularioTemplate(
            nome=nome,
            descricao=descricao,
            categoria=categoria,
            is_default=is_default,
            cliente_id=None if is_default else current_user.id
        )
        
        db.session.add(novo_template)
        db.session.commit()
        
        flash('Template criado com sucesso!', 'success')
        return redirect(url_for('formularios_routes.gerenciar_campos_template', template_id=novo_template.id))
    
    return render_template("certificado/criar_template.html")

@formularios_routes.route('/formulario_templates/<int:template_id>/campos', methods=['GET', 'POST'])
@login_required
def gerenciar_campos_template(template_id):
    template = FormularioTemplate.query.get_or_404(template_id)
    
    # Check permissions
    if current_user.tipo != 'admin' and template.cliente_id != current_user.id and not template.is_default:
        flash('Acesso negado!', 'danger')
        return redirect(url_for('formularios_routes.listar_templates'))
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        tipo = request.form.get('tipo')
        opcoes = request.form.get('opcoes', '').strip()
        obrigatorio = request.form.get('obrigatorio') == 'on'
        ordem = request.form.get('ordem', 0)
        
        novo_campo = CampoFormularioTemplate(
            template_id=template.id,
            nome=nome,
            tipo=tipo,
            opcoes=opcoes if tipo in ['dropdown', 'checkbox', 'radio'] else None,
            obrigatorio=obrigatorio,
            ordem=ordem
        )
        
        db.session.add(novo_campo)
        db.session.commit()
        
        flash('Campo adicionado com sucesso!', 'success')
        return redirect(url_for('formularios_routes.gerenciar_campos_template', template_id=template.id))
    
    return render_template('gerenciar_campos_template.html', template=template)

@formularios_routes.route('/formulario_templates/<int:template_id>/usar', methods=['GET', 'POST'])
@login_required
def usar_template(template_id):
    template = FormularioTemplate.query.get_or_404(template_id)
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        
        # Create new form from template
        novo_formulario = Formulario(
            nome=nome,
            descricao=descricao,
            cliente_id=current_user.id
        )
        db.session.add(novo_formulario)
        db.session.flush()  # Get ID before committing
        
        # Copy fields from template
        for campo_template in sorted(template.campos, key=lambda x: x.ordem):
            novo_campo = CampoFormulario(
                formulario_id=novo_formulario.id,
                nome=campo_template.nome,
                tipo=campo_template.tipo,
                opcoes=campo_template.opcoes,
                obrigatorio=campo_template.obrigatorio
            )
            db.session.add(novo_campo)
        
        db.session.commit()
        flash('Formulário criado com sucesso a partir do template!', 'success')
        return redirect(url_for('formularios_routes.listar_formularios'))
    
    return render_template('usar_template.html', template=template)

@formularios_routes.route('/respostas', methods=['GET'])
@login_required
def listar_respostas():
    # Verifica se o usuário é cliente ou ministrante
    if current_user.tipo not in ['cliente', 'ministrante']:
        flash('Acesso negado!', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    # --- Se for cliente ---
    if current_user.tipo == 'cliente':
        respostas = (
            RespostaFormulario.query
            .join(Usuario)
            .join(Formulario)
            .filter(
                Usuario.cliente_id == current_user.id,
                Formulario.cliente_id == current_user.id
            )
            .order_by(RespostaFormulario.data_submissao.desc())
            .all()
        )

    # --- Se for ministrante ---
    elif current_user.tipo == 'ministrante':
        # Você pode adaptar essa parte para buscar participantes das oficinas que ele ministra
        respostas = (
            RespostaFormulario.query
            .join(Usuario)
            .join(Inscricao, Inscricao.usuario_id == Usuario.id)
            .join(Oficina, Inscricao.oficina_id == Oficina.id)
            .filter(Oficina.ministrante_id == current_user.id)
            .order_by(RespostaFormulario.data_submissao.desc())
            .all()
        )

    # Se não houver respostas
    if not respostas:
        flash('Não há respostas disponíveis no momento.', 'info')
        return redirect(url_for('dashboard_routes.dashboard'))

    formulario = respostas[0].formulario

    return render_template(
        'listar_respostas.html',
        formulario=formulario,
        respostas=respostas
    )




@formularios_routes.route('/definir_status_inline', methods=['POST'])
@login_required
@mfa_required
def definir_status_inline():
    # 1) Pega valores do form
    resposta_id = request.form.get('resposta_id')
    novo_status = request.form.get('status_avaliacao')

    # 2) Valida
    if not resposta_id or not novo_status:
        flash("Dados incompletos!", "danger")
        return redirect(request.referrer or url_for('dashboard_routes.dashboard'))

    # 3) Busca a resposta no banco
    resposta = RespostaFormulario.query.get(resposta_id)
    if not resposta:
        flash("Resposta não encontrada!", "warning")
        return redirect(request.referrer or url_for('dashboard_routes.dashboard'))

    # 4) Atualiza
    resposta.status_avaliacao = novo_status
    db.session.commit()
    uid = current_user.id if hasattr(current_user, 'id') else None
    log = AuditLog(user_id=uid, submission_id=resposta_id, event_type='decision')
    db.session.add(log)
    db.session.commit()

    flash("Status atualizado com sucesso!", "success")

    # Redireciona para a mesma página (listar_respostas) ou usa request.referrer
    # Se estiver em /formularios/<id>/respostas_ministrante, podemos redirecionar
    return redirect(request.referrer or url_for('formularios_routes.listar_respostas',
                                                formulario_id=resposta.formulario_id))

