from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

trabalho_routes = Blueprint(
    'trabalho_routes',
    __name__,
    template_folder="../templates/trabalho"
)


@trabalho_routes.route('/submeter_trabalho', methods=['GET', 'POST'])
@login_required
def submeter_trabalho():
    if current_user.tipo != 'participante':
        flash('Apenas participantes podem submeter trabalhos.', 'danger')
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

    if request.method == 'POST':
        titulo = request.form.get('titulo')
        resumo = request.form.get('resumo')
        area_tematica = request.form.get('area_tematica')
        arquivo = request.files.get('arquivo_pdf')

        if not all([titulo, resumo, area_tematica, arquivo]):
            flash('Todos os campos são obrigatórios!', 'danger')
            return redirect(url_for('trabalho_routes.submeter_trabalho'))

        filename = secure_filename(arquivo.filename)
        caminho_pdf = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        arquivo.save(caminho_pdf)

        trabalho = TrabalhoCientifico(
            titulo=titulo,
            resumo=resumo,
            area_tematica=area_tematica,
            arquivo_pdf=caminho_pdf,
            usuario_id=current_user.id,
            evento_id=current_user.evento_id  # opcionalmente usa o evento do usuário
        )
        db.session.add(trabalho)
        db.session.commit()

        flash("Trabalho submetido com sucesso!", "success")
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

    return render_template("submeter_trabalho.html")


@trabalho_routes.route('/avaliar_trabalhos')
@login_required
def avaliar_trabalhos():
    if current_user.tipo != 'cliente' and not current_user.is_superuser():
        flash('Apenas administradores ou avaliadores têm acesso.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    trabalhos = TrabalhoCientifico.query.filter(TrabalhoCientifico.status != 'aceito').all()
    return render_template('avaliar_trabalhos.html', trabalhos=trabalhos)

@trabalho_routes.route('/avaliar_trabalho/<int:trabalho_id>', methods=['GET', 'POST'])
@login_required
def avaliar_trabalho(trabalho_id):
    trabalho = TrabalhoCientifico.query.get_or_404(trabalho_id)

    if request.method == 'POST':
        estrelas = request.form.get('estrelas')
        nota = request.form.get('nota')
        conceito = request.form.get('conceito')
        comentario = request.form.get('comentario')

        avaliacao = AvaliacaoTrabalho(
            trabalho_id=trabalho.id,
            avaliador_id=current_user.id,
            estrelas=int(estrelas) if estrelas else None,
            nota=float(nota) if nota else None,
            conceito=conceito,
            comentario=comentario
        )
        db.session.add(avaliacao)

        trabalho.status = 'avaliado'
        db.session.commit()

        flash("Avaliação registrada!", "success")
        return redirect(url_for('trabalho_routes.avaliar_trabalhos'))

    return render_template('avaliar_trabalho.html', trabalho=trabalho)


@trabalho_routes.route('/meus_trabalhos')
@login_required
def meus_trabalhos():
    if current_user.tipo != 'participante':
        return redirect(url_for('dashboard_participante_routes.dashboard_participante'))

    trabalhos = TrabalhoCientifico.query.filter_by(usuario_id=current_user.id).all()
    return render_template('meus_trabalhos.html', trabalhos=trabalhos)

@trabalho_routes.route('/submeter_trabalho', methods=['GET', 'POST'])
@login_required
def nova_submissao():
    if current_user.tipo != 'participante':
        flash('Apenas participantes podem submeter trabalhos.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    if request.method == 'POST':
        titulo = request.form.get('titulo')
        resumo = request.form.get('resumo')
        area_tematica = request.form.get('area_tematica')
        arquivo = request.files.get('arquivo_pdf')

        if not all([titulo, resumo, area_tematica, arquivo]):
            flash('Todos os campos são obrigatórios!', 'warning')
            return redirect(url_for('trabalho_routes.nova_submissao'))

        # Garante diretório e salva o arquivo PDF
        filename = secure_filename(arquivo.filename)
        caminho_pdf = os.path.join('static/uploads/trabalhos', filename)
        os.makedirs(os.path.dirname(caminho_pdf), exist_ok=True)
        arquivo.save(caminho_pdf)

        # Registra trabalho no banco
        trabalho = TrabalhoCientifico(
            titulo=titulo,
            resumo=resumo,
            area_tematica=area_tematica,
            arquivo_pdf=caminho_pdf,
            usuario_id=current_user.id,
            evento_id=current_user.evento_id if hasattr(current_user, 'evento_id') else None
        )

        db.session.add(trabalho)
        db.session.commit()

        flash('Trabalho submetido com sucesso!', 'success')
        return redirect(url_for('trabalho_routes.meus_trabalhos'))


