from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_required, current_user
import pandas as pd
from extensions import db
from models import Submission, Assignment, RevisorCandidatura, Usuario, Evento
from werkzeug.security import generate_password_hash

import uuid
from sqlalchemy.orm import joinedload

from models import Submission, WorkMetadata, Usuario
from sqlalchemy.exc import DataError

importar_trabalhos_routes = Blueprint(
    "importar_trabalhos_routes", __name__
)


importar_trabalhos_routes = Blueprint('importar_trabalhos_routes', __name__)

@importar_trabalhos_routes.route('/importar_trabalhos', methods=['POST'])
@login_required
def importar_trabalhos():
    if current_user.tipo != 'cliente':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard'))

    arquivo = request.files.get('arquivo_trabalhos')
    evento_id = request.form.get('evento_id')

    if not arquivo or not evento_id:
        flash('Arquivo ou evento não selecionado.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard_cliente'))


    if not arquivo.filename.endswith('.xlsx'):
        flash('Formato de arquivo inválido. Por favor, envie um arquivo .xlsx.', 'danger')
        return redirect(url_for('dashboard_routes.dashboard_cliente'))


    try:

        df = pd.read_excel(arquivo)

        required_columns = ['titulo', 'categoria', 'Rede de Ensino', 'Etapa de Ensino', 'URL do PDF']
        if not all(col in df.columns for col in required_columns):
            flash(f'O arquivo Excel deve conter as seguintes colunas: {", ".join(required_columns)}', 'danger')
            return redirect(url_for('dashboard_routes.dashboard_cliente'))

        revisores = Usuario.query.options(joinedload(Usuario.revisor_candidaturas))\
            .join(RevisorCandidatura, Usuario.email == RevisorCandidatura.email)\
            .filter(RevisorCandidatura.status == 'aprovado').all()

        if not revisores:
            flash('Nenhum revisor aprovado encontrado para atribuir os trabalhos.', 'warning')
            return redirect(url_for('dashboard_routes.dashboard_cliente'))

        submissions = []
        for index, row in df.iterrows():
            submission = Submission(
                title=row['titulo'],
                file_path=row['URL do PDF'],
                attributes={
                    'categoria': row['categoria'],
                    'rede_ensino': row['Rede de Ensino'],
                    'etapa_ensino': row['Etapa de Ensino']
                },
                evento_id=evento_id,
                code_hash=generate_password_hash(str(uuid.uuid4()))
            )
            submissions.append(submission)
            db.session.add(submission)

        db.session.flush()

        for i, submission in enumerate(submissions):
            revisor = revisores[i % len(revisores)]
            assignment = Assignment(
                submission_id=submission.id,
                reviewer_id=revisor.id
            )
            db.session.add(assignment)


        db.session.commit()
        flash(f'{len(submissions)} trabalhos importados e atribuídos com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Ocorreu um erro ao importar os trabalhos: {e}', 'danger')

    return redirect(url_for('dashboard_routes.dashboard_cliente'))
