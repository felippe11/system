import json
import os
import secrets
import unicodedata
import uuid
from collections import defaultdict
from datetime import datetime, time
from io import BytesIO
from utils import endpoints

import pandas as pd
import sqlalchemy as sa
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_login import current_user
from utils.auth import login_required
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from extensions import db, csrf
from models import (
    AuditLog,
    Evento,
    Formulario,
    Review,
    Submission,
    Usuario,
    WorkMetadata,
)
from models.avaliacao import AvaliacaoBarema, AvaliacaoCriterio
from models.event import RespostaCampoFormulario, RespostaFormulario
from models.review import Assignment, RevisorProcess, RevisorCandidatura
from sqlalchemy import func
from sqlalchemy.exc import DataError, SQLAlchemyError
from sqlalchemy.orm import joinedload
from services.submission_service import SubmissionService
from utils.mfa import mfa_required


trabalho_routes = Blueprint(
    "trabalho_routes",
    __name__,
    template_folder="../templates/trabalho"
)


def _user_dashboard_endpoint() -> str:
    """Return the appropriate dashboard endpoint for the logged-in user."""
    if current_user.is_authenticated and getattr(current_user, "tipo", None) == "revisor":
        return endpoints.DASHBOARD_REVISOR
    return endpoints.DASHBOARD


# ──────────────────────────────── SUBMISSÃO ──────────────────────────────── #
@trabalho_routes.route("/submeter_trabalho", methods=["GET", "POST"])
@login_required
@mfa_required
def submeter_trabalho():
    """Participante faz upload do PDF e registra o trabalho no banco."""
    if current_user.tipo not in ["participante", "ministrante"]:
        flash("Acesso negado. Apenas participantes podem submeter trabalhos.", "error")
        return redirect(url_for(_user_dashboard_endpoint()))

    config = current_user.cliente.configuracao if current_user.cliente else None
    formulario = None
    if config and config.habilitar_submissao_trabalhos:
        formulario = config.formulario_submissao
        if not formulario or not formulario.is_submission_form:
            flash("Formulário de submissão inválido.", "danger")
            return redirect(url_for(_user_dashboard_endpoint()))
        if (
            formulario.eventos
            and current_user.evento_id not in [ev.id for ev in formulario.eventos]
        ):
            flash("Formulário indisponível para seu evento.", "danger")
            return redirect(url_for(_user_dashboard_endpoint()))

    if not formulario:
        flash("Submissão de trabalhos desabilitada.", "danger")
        return redirect(url_for(_user_dashboard_endpoint()))

    if request.method == "POST":
        evento_id = getattr(current_user, "evento_id", None)
        if not evento_id:
            flash("Usuário sem evento associado.", "danger")
            return redirect(url_for("trabalho_routes.submeter_trabalho"))

        evento = Evento.query.get(evento_id)
        if not evento:
            flash("Evento não encontrado.", "danger")
            return redirect(url_for("trabalho_routes.submeter_trabalho"))
        # Submissão sempre permitida - validação removida

        resposta_formulario = RespostaFormulario(
            formulario_id=formulario.id, usuario_id=current_user.id
        )
        db.session.add(resposta_formulario)
        db.session.flush()

        allowed = "pdf"
        if current_user.cliente and current_user.cliente.configuracao:
            allowed = current_user.cliente.configuracao.allowed_file_types or "pdf"
        exts = [e.strip().lower() for e in allowed.split(",")] if allowed else []

        titulo = None
        arquivo_pdf = None

        for campo in formulario.campos:
            valor = request.form.get(str(campo.id))
            if campo.tipo == "file" and f"file_{campo.id}" in request.files:
                arquivo = request.files[f"file_{campo.id}"]
                if arquivo and arquivo.filename:
                    filename = secure_filename(arquivo.filename)
                    ext_ok = any(
                        filename.lower().endswith(f".{ext}") for ext in exts
                    )
                    if not ext_ok:
                        db.session.rollback()
                        flash("Tipo de arquivo não permitido.", "warning")
                        return redirect(url_for("trabalho_routes.submeter_trabalho"))
                    uploads_dir = current_app.config.get(
                        "UPLOAD_FOLDER", "static/uploads/trabalhos"
                    )
                    os.makedirs(uploads_dir, exist_ok=True)
                    unique_name = f"{uuid.uuid4().hex}_{filename}"
                    caminho_arquivo = os.path.join(uploads_dir, unique_name)
                    arquivo.save(caminho_arquivo)
                    valor = caminho_arquivo
                    if not arquivo_pdf:
                        arquivo_pdf = caminho_arquivo

            if campo.obrigatorio and not valor:
                db.session.rollback()
                flash(f"O campo '{campo.nome}' é obrigatório.", "warning")
                return redirect(url_for("trabalho_routes.submeter_trabalho"))

            resposta_campo = RespostaCampoFormulario(
                resposta_formulario_id=resposta_formulario.id,
                campo_id=campo.id,
                valor=valor,
            )
            db.session.add(resposta_campo)

            if not titulo and campo.tipo != "file":
                titulo = valor

        titulo = titulo or "Trabalho sem título"


        try:
            # Usar o serviço unificado para criar a submissão
            submission = SubmissionService.create_submission(
                title=titulo,
                author_id=current_user.id,
                evento_id=int(evento_id),
                file_path=arquivo_pdf
            )
            
            # Gerar código de acesso
            code = uuid.uuid4().hex[:8]
            submission.code_hash = generate_password_hash(code, method="pbkdf2:sha256")
            
            # Log de auditoria
            usuario = Usuario.query.get(getattr(current_user, "id", None))
            uid = usuario.id if usuario else None
            db.session.add(
                AuditLog(user_id=uid, submission_id=submission.id, event_type="submission")
            )
            
            db.session.commit()
            
            flash(
                "Trabalho submetido com sucesso! "
                f"Localizador: {submission.locator} Código: {code}",
                "success",
            )
            return redirect(url_for("trabalho_routes.meus_trabalhos"))
            
        except ValueError as e:
            db.session.rollback()
            flash(str(e), "error")
            return redirect(url_for("trabalho_routes.submeter_trabalho"))
        except Exception as e:
            db.session.rollback()
            flash("Erro interno. Tente novamente.", "error")
            current_app.logger.error(f"Erro na submissão: {e}")
            return redirect(url_for("trabalho_routes.submeter_trabalho"))

    return render_template("submeter_trabalho.html", formulario=formulario)


# ──────────────────────────────── MEUS TRABALHOS ─────────────────────────── #
@trabalho_routes.route("/meus_trabalhos")
@login_required
def meus_trabalhos():
    """Lista trabalhos do participante logado com informações detalhadas."""
    if current_user.tipo not in ["participante", "ministrante"]:
        return redirect(url_for(_user_dashboard_endpoint()))

    # Buscar submissões com informações relacionadas
    from sqlalchemy.orm import joinedload
    from models.review import Review, Assignment
    
    trabalhos = db.session.query(Submission).options(
        joinedload(Submission.evento),
        joinedload(Submission.author)
    ).filter_by(author_id=current_user.id).all()
    
    # Enriquecer dados dos trabalhos
    trabalhos_detalhados = []
    for trabalho in trabalhos:
        # Buscar revisões
        reviews = Review.query.filter_by(submission_id=trabalho.id).all()
        assignments = Assignment.query.filter_by(submission_id=trabalho.id).all()
        
        # Traduzir status
        status_map = {
            'submitted': 'Submetido',
            'under_review': 'Em Revisão',
            'accepted': 'Aceito',
            'rejected': 'Rejeitado',
            'pending': 'Pendente'
        }
        
        trabalho_info = {
            'submission': trabalho,
            'status_traduzido': status_map.get(trabalho.status, trabalho.status),
            'total_reviews': len(reviews),
            'completed_reviews': len([r for r in reviews if r.finished_at]),
            'pending_reviews': len([a for a in assignments if not any(r.finished_at for r in reviews if r.submission_id == a.submission_id)]),
            'evento_nome': trabalho.evento.nome if trabalho.evento else 'N/A',
            'area_nome': 'Área Geral'  # Placeholder - implementar busca de área se necessário
        }
        trabalhos_detalhados.append(trabalho_info)
    
    return render_template("meus_trabalhos.html", trabalhos=trabalhos_detalhados)


# ──────────────────────────── TRABALHOS CLIENTE ─────────────────────────── #


def get_trabalhos_form():
    """Return the 'Formulário de Trabalhos' or ``None`` if absent."""
    return Formulario.query.filter_by(nome="Formulário de Trabalhos").first()


def _normalize_key(value: str) -> str:
    """Normalize header names to compare coluna/campo names."""
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(
        ch for ch in normalized if unicodedata.category(ch) != "Mn"
    )
    normalized = normalized.lower()
    for sep in [" ", "-", "/", "\\", "."]:
        normalized = normalized.replace(sep, "_")
    normalized = "".join(ch for ch in normalized if ch.isalnum() or ch == "_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


EMPTY_FILTER_VALUE = "__EMPTY__"


def _coerce_field_value(raw_value):
    """Try to deserialize JSON-like values while preserving originals."""
    if raw_value is None:
        return None
    if isinstance(raw_value, str):
        stripped = raw_value.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                return json.loads(stripped)
            except (json.JSONDecodeError, TypeError, ValueError):
                return raw_value
        return raw_value
    return raw_value


def _stringify_field_value(value):
    """Return a user-friendly string representation for display."""
    if value is None:
        return ""
    if isinstance(value, list):
        processed = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                processed.append(text)
        return ", ".join(processed)
    if isinstance(value, dict):
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)
    return str(value)


def _sanitize_filter_value(value):
    """Convert filter values to comparable strings."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)
    return str(value).strip()


def _filter_value_key(value):
    sanitized = _sanitize_filter_value(value)
    return sanitized if sanitized else EMPTY_FILTER_VALUE


def _format_filter_label(value):
    sanitized = _sanitize_filter_value(value)
    return sanitized if sanitized else "Não informado"


def _legacy_field_key(name: str) -> str:
    if not isinstance(name, str):
        return ""
    return name.lower().replace(" ", "_")


def _build_filter_options(question_value_map):
    filter_options = []
    for question in sorted(question_value_map.keys()):
        options_map = question_value_map[question]
        sorted_options = sorted(
            options_map.items(),
            key=lambda item: (
                1 if item[0] == EMPTY_FILTER_VALUE else 0,
                item[1].lower(),
            ),
        )
        filter_options.append(
            {
                "question": question,
                "options": [
                    {"value": value_key, "label": label}
                    for value_key, label in sorted_options
                ],
            }
        )
    return filter_options


def _apply_trabalho_filters(trabalhos, filters):
    if not filters:
        return trabalhos

    filtered = []
    for trabalho in trabalhos:
        respostas = trabalho.get("respostas", {}) or {}
        include = True
        for filtro in filters:
            question = filtro.get("question")
            valores = filtro.get("values") or []
            if not question or not valores:
                continue

            resposta = respostas.get(question)
            valores_resposta = resposta if isinstance(resposta, list) else [resposta]
            normalizados = {_filter_value_key(valor) for valor in valores_resposta}

            if not any(value in normalizados for value in valores):
                include = False
                break

        if include:
            filtered.append(trabalho)

    return filtered


def _prepare_trabalhos_dataset(formulario):
    respostas = (
        RespostaFormulario.query.options(
            joinedload(RespostaFormulario.respostas_campos).joinedload(
                RespostaCampoFormulario.campo
            ),
            joinedload(RespostaFormulario.evento),
        )
        .filter_by(formulario_id=formulario.id)
        .order_by(RespostaFormulario.data_submissao.desc())
        .all()
    )

    trabalho_ids = [resposta.id for resposta in respostas]

    from models.user import Usuario

    assignments_with_reviewers = db.session.query(
        Assignment.resposta_formulario_id,
        Usuario.nome.label("reviewer_name"),
    ).join(
        Usuario, Assignment.reviewer_id == Usuario.id
    ).filter(
        Assignment.resposta_formulario_id.in_(trabalho_ids)
    ).all()

    assignment_dict: dict[int, list[str]] = defaultdict(list)
    for assignment in assignments_with_reviewers:
        assignment_dict[assignment.resposta_formulario_id].append(
            assignment.reviewer_name
        )

    question_value_labels: dict[str, dict[str, str]] = defaultdict(dict)
    trabalhos = []
    for resposta in respostas:
        trabalho = {
            "id": resposta.id,
            "data_submissao": resposta.data_submissao,
            "evento_id": resposta.evento_id,
            "evento_nome": resposta.evento.nome if resposta.evento else None,
        }

        reviewer_names = assignment_dict.get(resposta.id, [])
        trabalho["distribution_status"] = (
            "Distribuído" if reviewer_names else "Não Distribuído"
        )
        trabalho["assignment_count"] = len(reviewer_names)
        trabalho["reviewer_names"] = reviewer_names

        respostas_dict = {}
        for resposta_campo in resposta.respostas_campos:
            campo_nome = resposta_campo.campo.nome or ""
            coerced_value = _coerce_field_value(resposta_campo.valor)
            respostas_dict[campo_nome] = coerced_value

            trabalho[_legacy_field_key(campo_nome)] = _stringify_field_value(
                coerced_value
            )

            valores_iteraveis = (
                coerced_value if isinstance(coerced_value, list) else [coerced_value]
            )
            for valor in valores_iteraveis:
                value_key = _filter_value_key(valor)
                if value_key not in question_value_labels[campo_nome]:
                    question_value_labels[campo_nome][value_key] = _format_filter_label(
                        valor
                    )

        trabalho["respostas"] = respostas_dict
        trabalhos.append(trabalho)

    trabalho_filter_options = _build_filter_options(question_value_labels)

    reviewers = (
        Usuario.query.filter_by(tipo="revisor").order_by(Usuario.nome.asc()).all()
    )
    assignment_totals = dict(
        db.session.query(Assignment.reviewer_id, func.count(Assignment.id))
        .group_by(Assignment.reviewer_id)
        .all()
    )
    reviewers_without_assignments = [
        {
            "id": reviewer.id,
            "nome": reviewer.nome,
            "email": reviewer.email,
        }
        for reviewer in reviewers
        if assignment_totals.get(reviewer.id, 0) == 0
    ]

    return {
        "trabalhos": trabalhos,
        "filter_options": trabalho_filter_options,
        "reviewers_without_assignments": reviewers_without_assignments,
    }


def _build_reviewer_distribution_list(target_cliente_id: int | None = None):
    """Retorna os revisores disponíveis com metadados usados na distribuição."""

    candidaturas_query = RevisorCandidatura.query.join(
        RevisorProcess, RevisorCandidatura.process_id == RevisorProcess.id
    )

    if target_cliente_id:
        candidaturas_query = candidaturas_query.filter(
            RevisorProcess.cliente_id == target_cliente_id
        )

    candidaturas = candidaturas_query.all()
    candidaturas_por_email: dict[str, RevisorCandidatura] = {}
    for candidatura in candidaturas:
        if candidatura.email:
            candidaturas_por_email.setdefault(candidatura.email.lower(), candidatura)

    reviewers = Usuario.query.filter_by(tipo="revisor").all()

    assignment_counts = dict(
        db.session.query(Assignment.reviewer_id, func.count(Assignment.id))
        .filter(Assignment.completed == False)
        .group_by(Assignment.reviewer_id)
        .all()
    )

    reviewer_list = []
    for reviewer in reviewers:
        current_assignments = assignment_counts.get(reviewer.id, 0)

        candidatura = None
        if reviewer.email:
            candidatura = candidaturas_por_email.get(reviewer.email.lower())

        reviewer_list.append(
            {
                "id": reviewer.id,
                "nome": reviewer.nome,
                "email": reviewer.email,
                "current_assignments": current_assignments,
                "expertise": getattr(reviewer, "expertise", ""),
                "available": True,
                "respostas": (
                    candidatura.respostas
                    if candidatura and isinstance(candidatura.respostas, dict)
                    else {}
                ),
            }
        )

    return reviewer_list




def _load_assignment_table():
    metadata = sa.MetaData()
    bind = db.session.get_bind() or db.engine

    try:
        table = sa.Table(
            'assignment',
            metadata,
            autoload_with=bind,
        )
    except SQLAlchemyError:
        table = None

    if table is None:
        dialect = bind.dialect.name
        if dialect == 'sqlite':
            rows = db.session.execute(sa.text("PRAGMA table_info(assignment)")).fetchall()
            column_names = [row[1] for row in rows]
        else:
            rows = db.session.execute(
                sa.text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = :table
                      AND table_schema = current_schema()
                    ORDER BY ordinal_position
                    """
                ),
                {"table": 'assignment'},
            ).fetchall()
            column_names = [row[0] for row in rows]

        if not column_names:
            raise RuntimeError("Tabela 'assignment' não encontrada no banco de dados.")

        columns = [sa.column(name) for name in column_names]
        table = sa.table('assignment', *columns)

    resolved_columns, column_map = _detect_assignment_columns(table)
    return table, resolved_columns, column_map


def _detect_assignment_columns(assignment_table) -> tuple[dict[str, sa.Column], dict[str, sa.Column]]:
    columns = assignment_table.c
    column_map: dict[str, sa.Column] = {col.name: col for col in columns}

    def _resolve_column(candidate_names: list[str], keywords: list[str]):
        for name in candidate_names:
            col = column_map.get(name)
            if col is not None:
                return col
        lowered = {name.lower(): col for name, col in column_map.items()}
        for keyword in keywords:
            for name, col in lowered.items():
                if keyword in name:
                    return col
        return None

    resposta_column = _resolve_column(
        [
            'resposta_formulario_id',
            'submission_id',
            'work_id',
            'trabalho_id',
        ],
        ['resposta', 'submission', 'work', 'trabalho'],
    )

    reviewer_column = _resolve_column(
        [
            'reviewer_id',
            'revisor_id',
            'reviewer',
            'usuario_id',
        ],
        ['reviewer', 'revisor', 'usuario'],
    )

    if resposta_column is None or reviewer_column is None:
        available = ", ".join(sorted(column_map.keys()))
        raise RuntimeError(
            "Tabela de assignment não possui colunas esperadas para vincular revisor e trabalho. "
            f"Colunas disponíveis: {available}"
        )

    resolved = {
        'resposta': resposta_column,
        'reviewer': reviewer_column,
        'id': column_map.get('id'),
        'deadline': column_map.get('deadline'),
        'distribution_type': column_map.get('distribution_type'),
        'distribution_date': column_map.get('distribution_date'),
        'distributed_by': column_map.get('distributed_by'),
        'notes': column_map.get('notes'),
        'is_reevaluation': column_map.get('is_reevaluation'),
    }

    return resolved, column_map


def _build_export_dataframe(trabalhos):
    question_order = []
    seen_questions = set()
    for trabalho in trabalhos:
        respostas = trabalho.get("respostas") or {}
        for question in respostas.keys():
            if question not in seen_questions:
                seen_questions.add(question)
                question_order.append(question)

    base_columns = [
        "ID",
        "Título",
        "Categoria",
        "Rede de Ensino",
        "Etapa de Ensino",
        "Evento",
        "Data de Cadastro",
        "Status Distribuição",
        "Total Revisores",
        "Revisores",
    ]
    base_column_set = set(base_columns)

    rows = []
    for trabalho in trabalhos:
        respostas = trabalho.get("respostas") or {}

        data_submissao = trabalho.get("data_submissao")
        if data_submissao:
            data_formatada = data_submissao.strftime("%d/%m/%Y %H:%M")
        else:
            data_formatada = ""

        row = {
            "ID": trabalho.get("id"),
            "Título": trabalho.get("título")
            or _stringify_field_value(respostas.get("Título")),
            "Categoria": trabalho.get("categoria")
            or _stringify_field_value(respostas.get("Categoria")),
            "Rede de Ensino": trabalho.get("rede_de_ensino")
            or _stringify_field_value(respostas.get("Rede de Ensino")),
            "Etapa de Ensino": trabalho.get("etapa_de_ensino")
            or _stringify_field_value(respostas.get("Etapa de Ensino")),
            "Evento": trabalho.get("evento_nome") or "",
            "Data de Cadastro": data_formatada,
            "Status Distribuição": trabalho.get("distribution_status"),
            "Total Revisores": trabalho.get("assignment_count"),
            "Revisores": ", ".join(trabalho.get("reviewer_names") or []),
        }

        for question in question_order:
            if question in base_column_set:
                continue
            row[question] = _stringify_field_value(respostas.get(question))

        rows.append(row)

    ordered_columns = base_columns + [
        question
        for question in question_order
        if question not in base_column_set
    ]

    if not rows:
        return pd.DataFrame(columns=ordered_columns)

    df = pd.DataFrame(rows)

    # Garantir a ordem das colunas
    for column in ordered_columns:
        if column not in df.columns:
            df[column] = ""
    df = df[ordered_columns]

    return df


def _build_reviewer_filter_options(candidaturas):
    question_value_map: dict[str, dict[str, str]] = defaultdict(dict)

    for candidatura in candidaturas:
        respostas = getattr(candidatura, 'respostas', None) or {}
        if not isinstance(respostas, dict):
            continue

        for pergunta, valor in respostas.items():
            if not pergunta:
                continue

            valores = valor if isinstance(valor, list) else [valor]
            for item in valores:
                value_key = _filter_value_key(item)
                if value_key not in question_value_map[pergunta]:
                    question_value_map[pergunta][value_key] = _format_filter_label(item)

    filter_options = []
    for pergunta in sorted(question_value_map.keys()):
        options = question_value_map[pergunta]
        sorted_options = sorted(
            options.items(),
            key=lambda entry: (
                1 if entry[0] == EMPTY_FILTER_VALUE else 0,
                entry[1].lower(),
            ),
        )
        filter_options.append(
            {
                "question": pergunta,
                "options": [
                    {"value": key, "label": label}
                    for key, label in sorted_options
                ],
            }
        )

    return filter_options


def _get_reviewer_filter_options_for_user(user):
    target_cliente_id = None
    if getattr(user, 'tipo', None) == 'cliente':
        target_cliente_id = getattr(user, 'id', None)

    candidaturas_query = RevisorCandidatura.query.join(
        RevisorProcess, RevisorCandidatura.process_id == RevisorProcess.id
    )

    if target_cliente_id:
        candidaturas_query = candidaturas_query.filter(RevisorProcess.cliente_id == target_cliente_id)

    candidaturas = candidaturas_query.all()
    return _build_reviewer_filter_options(candidaturas)


def _extract_filters_from_request():
    filters_payload = request.values.get("filters")

    if filters_payload is None and request.is_json:
        body = request.get_json(silent=True) or {}
        filters_payload = body.get("filters")

    if isinstance(filters_payload, str):
        try:
            return json.loads(filters_payload)
        except json.JSONDecodeError:
            current_app.logger.warning("Não foi possível interpretar os filtros recebidos.")
            return []

    if isinstance(filters_payload, list):
        return filters_payload

    return []


@trabalho_routes.route("/trabalhos/modelo", methods=["GET"])
@login_required
def download_template_trabalhos():
    """Gera planilha modelo com as colunas do formulário de trabalhos."""
    if current_user.tipo != "cliente":
        flash("Acesso negado.", "danger")
        return redirect(url_for(_user_dashboard_endpoint()))

    formulario = get_trabalhos_form()
    if not formulario:
        flash("Formulário de trabalhos não configurado.", "warning")
        return redirect(url_for("trabalho_routes.novo_trabalho"))

    colunas = [campo.nome for campo in formulario.campos]
    if not colunas:
        colunas = ["Título"]

    df = pd.DataFrame(columns=colunas)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Trabalhos")
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="modelo_trabalhos.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@trabalho_routes.route("/trabalhos/importar", methods=["POST"])
@login_required
def importar_trabalhos_excel():
    """Importa múltiplos trabalhos a partir de uma planilha Excel."""
    if current_user.tipo != "cliente":
        flash("Acesso negado.", "danger")
        return redirect(url_for(_user_dashboard_endpoint()))

    formulario = get_trabalhos_form()
    if not formulario:
        flash("Formulário de trabalhos não configurado.", "warning")
        return redirect(url_for("trabalho_routes.novo_trabalho"))

    evento_id = request.form.get("evento_id", type=int)
    if not evento_id:
        flash("Selecione um evento para importar os trabalhos.", "warning")
        return redirect(url_for("trabalho_routes.novo_trabalho"))

    evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first()
    if not evento:
        flash("Evento inválido.", "danger")
        return redirect(url_for("trabalho_routes.novo_trabalho"))

    arquivo = request.files.get("arquivo_excel")
    if not arquivo or not arquivo.filename:
        flash("Selecione um arquivo Excel para importação.", "warning")
        return redirect(url_for("trabalho_routes.novo_trabalho"))

    filename = arquivo.filename.lower()
    if not filename.endswith((".xlsx", ".xls")):
        flash("Formato de arquivo inválido. Utilize uma planilha .xlsx ou .xls.", "danger")
        return redirect(url_for("trabalho_routes.novo_trabalho"))

    try:
        df = pd.read_excel(arquivo)
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Erro ao ler planilha de trabalhos")
        flash(f"Não foi possível ler o arquivo: {exc}", "danger")
        return redirect(url_for("trabalho_routes.novo_trabalho"))

    if df.empty:
        flash("A planilha enviada não contém dados.", "warning")
        return redirect(url_for("trabalho_routes.novo_trabalho"))

    normalized_columns = {
        _normalize_key(coluna): coluna for coluna in df.columns if coluna is not None
    }

    missing_required = [
        campo.nome
        for campo in formulario.campos
        if campo.obrigatorio and _normalize_key(campo.nome) not in normalized_columns
    ]
    if missing_required:
        flash(
            "Colunas obrigatórias ausentes na planilha: "
            + ", ".join(missing_required),
            "danger",
        )
        return redirect(url_for("trabalho_routes.novo_trabalho"))

    total_importados = 0

    usuario_autor = None
    if getattr(current_user, "id", None) is not None:
        usuario_autor = db.session.get(Usuario, current_user.id)

    try:
        with db.session.begin_nested():
            for index, row in df.iterrows():
                if row.isna().all():
                    continue

                linha_excel = index + 2  # considerar cabeçalho
                valores_campos = {}
                titulo = None

                for campo in formulario.campos:
                    coluna_key = _normalize_key(campo.nome)
                    coluna_original = normalized_columns.get(coluna_key)
                    valor_raw = row[coluna_original] if coluna_original else None
                    if pd.isna(valor_raw):
                        valor_raw = ""
                    valor = str(valor_raw).strip() if valor_raw is not None else ""

                    if campo.obrigatorio and not valor:
                        raise ValueError(
                            f"O campo '{campo.nome}' é obrigatório (linha {linha_excel})."
                        )

                    valores_campos[campo.id] = valor

                    if not titulo and valor and campo.tipo in ["text", "textarea"]:
                        titulo = valor

                if not valores_campos:
                    continue

                if all(not valor for valor in valores_campos.values()):
                    continue

                if not titulo:
                    coluna_titulo = normalized_columns.get(_normalize_key("Título"))
                    if coluna_titulo:
                        valor_titulo = row[coluna_titulo]
                        if not pd.isna(valor_titulo):
                            titulo = str(valor_titulo).strip()

                titulo = titulo or f"Trabalho importado {total_importados + 1}"

                payload_por_campo = {
                    campo.nome: valores_campos.get(campo.id, "")
                    for campo in formulario.campos
                }
                payload_normalizado = {
                    _normalize_key(chave): valor
                    for chave, valor in payload_por_campo.items()
                }

                codigo_hash = generate_password_hash(secrets.token_urlsafe(12))

                submission = Submission(
                    title=titulo,
                    author_id=usuario_autor.id if usuario_autor else None,
                    evento_id=evento.id,
                    status="submitted",
                    code_hash=codigo_hash,
                    attributes=payload_por_campo,
                )
                db.session.add(submission)
                db.session.flush()

                resposta_formulario = RespostaFormulario(
                    formulario_id=formulario.id,
                    usuario_id=usuario_autor.id if usuario_autor else None,
                    evento_id=evento.id,
                    trabalho_id=submission.id,
                )
                db.session.add(resposta_formulario)
                db.session.flush()

                for campo in formulario.campos:
                    valor = valores_campos.get(campo.id, "")
                    resposta_campo = RespostaCampoFormulario(
                        resposta_formulario_id=resposta_formulario.id,
                        campo_id=campo.id,
                        valor=valor,
                    )
                    db.session.add(resposta_campo)

                work_metadata = WorkMetadata(
                    data=payload_por_campo,
                    titulo=payload_normalizado.get("titulo"),
                    categoria=payload_normalizado.get("categoria"),
                    rede_ensino=payload_normalizado.get("rede_de_ensino"),
                    etapa_ensino=payload_normalizado.get("etapa_de_ensino"),
                    pdf_url=payload_normalizado.get("url_do_pdf")
                    or payload_normalizado.get("pdf_url"),
                    evento_id=evento.id,
                )
                db.session.add(work_metadata)

                total_importados += 1

        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
        return redirect(url_for("trabalho_routes.novo_trabalho"))
    except DataError as exc:
        db.session.rollback()
        detalhes = getattr(getattr(exc, "orig", None), "diag", None)
        if detalhes and getattr(detalhes, "column_name", None):
            mensagem = (
                "Erro ao salvar dados. Verifique o tamanho máximo do campo '"
                + detalhes.column_name
                + "'."
            )
        else:
            mensagem = "Erro ao salvar os dados importados."
        flash(mensagem, "danger")
        return redirect(url_for("trabalho_routes.novo_trabalho"))
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        current_app.logger.exception("Erro ao importar trabalhos em massa")
        flash(f"Erro ao importar trabalhos: {exc}", "danger")
        return redirect(url_for("trabalho_routes.novo_trabalho"))

    if total_importados == 0:
        flash(
            "Nenhum trabalho foi importado. Verifique se a planilha possui dados preenchidos.",
            "warning",
        )
    else:
        flash(f"{total_importados} trabalhos importados com sucesso!", "success")

    return redirect(url_for("trabalho_routes.listar_trabalhos"))


@trabalho_routes.route("/trabalhos")
@login_required
def listar_trabalhos():
    """Lista todos os trabalhos cadastrados pelo cliente."""
    if current_user.tipo not in ["cliente", "admin"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for(_user_dashboard_endpoint()))

    formulario = get_trabalhos_form()
    if not formulario:
        return render_template("trabalhos/formulario_nao_encontrado.html")
    
    dataset = _prepare_trabalhos_dataset(formulario)
    reviewer_filter_options = _get_reviewer_filter_options_for_user(current_user)

    return render_template(
        "trabalhos/listar_trabalhos.html",
        trabalhos=dataset["trabalhos"],
        trabalho_filter_options=dataset["filter_options"],
        reviewers_without_assignments=dataset["reviewers_without_assignments"],
        reviewer_filter_options=reviewer_filter_options,
    )


@trabalho_routes.route("/trabalhos/distribuicao/manual")
@login_required
def distribuicao_manual_page():
    """Exibe a página dedicada para distribuição manual de trabalhos."""

    if current_user.tipo not in ["cliente", "admin"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for(_user_dashboard_endpoint()))

    formulario = get_trabalhos_form()
    if not formulario:
        flash("Formulário de trabalhos não configurado.", "warning")
        return redirect(url_for("trabalho_routes.listar_trabalhos"))

    dataset = _prepare_trabalhos_dataset(formulario)
    reviewer_filter_options = _get_reviewer_filter_options_for_user(current_user)

    selected_ids_param = request.args.get("ids", "")
    selected_ids: list[int] = []
    for raw_id in selected_ids_param.split(","):
        raw_id = raw_id.strip()
        if not raw_id:
            continue
        try:
            selected_ids.append(int(raw_id))
        except ValueError:
            continue

    work_lookup = {work.get("id"): work for work in dataset["trabalhos"]}
    selected_work_ids = [work_id for work_id in selected_ids if work_id in work_lookup]
    selected_works = [work_lookup[work_id] for work_id in selected_work_ids]

    if not selected_works:
        flash("Selecione pelo menos um trabalho para distribuir manualmente.", "warning")
        return redirect(url_for("trabalho_routes.listar_trabalhos"))

    def _resolve_title(work: dict | None) -> str:
        if not work:
            return "Trabalho"
        respostas = work.get("respostas") or {}
        return (
            work.get("título")
            or _stringify_field_value(respostas.get("Título"))
            or f"Trabalho #{work.get('id')}"
        )

    def _resolve_category(work: dict | None) -> str:
        if not work:
            return "Sem categoria"
        respostas = work.get("respostas") or {}
        return (
            work.get("categoria")
            or _stringify_field_value(respostas.get("Categoria"))
            or "Sem categoria"
        )

    selected_work_views: list[dict[str, object]] = []
    for work in selected_works:
        selected_work_views.append(
            {
                "id": work.get("id"),
                "title": _resolve_title(work),
                "category": _resolve_category(work),
                "distribution_status": work.get("distribution_status"),
                "assignment_count": work.get("assignment_count"),
                "reviewer_names": work.get("reviewer_names") or [],
            }
        )

    assignment_rows: list = []
    if selected_work_ids:
        assignment_rows = (
            db.session.query(
                Assignment.id.label("assignment_id"),
                Assignment.resposta_formulario_id.label("resposta_formulario_id"),
                Assignment.reviewer_id.label("reviewer_id"),
                Assignment.deadline.label("deadline"),
                Assignment.completed.label("completed"),
                Assignment.distribution_type.label("distribution_type"),
                Assignment.distribution_date.label("distribution_date"),
                Assignment.notes.label("notes"),
                RespostaFormulario.trabalho_id.label("submission_id"),
                Usuario.nome.label("reviewer_name"),
                Usuario.email.label("reviewer_email"),
            )
            .outerjoin(RespostaFormulario, Assignment.resposta_formulario_id == RespostaFormulario.id)
            .outerjoin(Usuario, Assignment.reviewer_id == Usuario.id)
            .filter(Assignment.resposta_formulario_id.in_(selected_work_ids))
            .order_by(Assignment.id.desc())
            .all()
        )

    submission_ids: set[int] = set()
    reviewer_ids: set[int] = set()
    for row in assignment_rows:
        submission_id = getattr(row, "submission_id", None)
        reviewer_id = getattr(row, "reviewer_id", None)
        if submission_id:
            submission_ids.add(submission_id)
        if reviewer_id:
            reviewer_ids.add(reviewer_id)

    avaliacao_map: dict[tuple[int, int], AvaliacaoBarema] = {}
    if submission_ids and reviewer_ids:
        avaliacoes = (
            AvaliacaoBarema.query.options(joinedload(AvaliacaoBarema.revisor))
            .filter(
                AvaliacaoBarema.trabalho_id.in_(submission_ids),
                AvaliacaoBarema.revisor_id.in_(reviewer_ids),
            )
            .all()
        )
        avaliacao_map = {
            (avaliacao.trabalho_id, avaliacao.revisor_id): avaliacao
            for avaliacao in avaliacoes
        }

    assignment_views: list[dict[str, object]] = []
    for row in assignment_rows:
        work_entry = work_lookup.get(row.resposta_formulario_id)
        avaliacao_key = (
            (row.submission_id, row.reviewer_id)
            if row.submission_id and row.reviewer_id
            else None
        )
        avaliacao = avaliacao_map.get(avaliacao_key) if avaliacao_key else None

        assignment_views.append(
            {
                "id": row.assignment_id,
                "work_id": row.resposta_formulario_id,
                "work_title": _resolve_title(work_entry),
                "reviewer_id": row.reviewer_id,
                "reviewer_name": row.reviewer_name,
                "reviewer_email": row.reviewer_email,
                "deadline": row.deadline,
                "completed": row.completed,
                "submission_id": row.submission_id,
                "avaliacao_id": avaliacao.id if avaliacao else None,
                "avaliacao_nota": avaliacao.nota_final if avaliacao else None,
                "avaliacao_data": avaliacao.data_avaliacao if avaliacao else None,
            }
        )

    mode = request.args.get("mode", "assign") or "assign"
    if mode not in {"assign", "reevaluation"}:
        mode = "assign"

    next_url = request.full_path

    target_cliente_id = request.args.get("cliente_id", type=int)
    if not target_cliente_id and current_user.tipo == "cliente":
        target_cliente_id = current_user.id

    reviewers_for_page = _build_reviewer_distribution_list(target_cliente_id)

    return render_template(
        "trabalhos/distribuicao_manual.html",
        selected_works=selected_work_views,
        selected_work_ids=selected_work_ids,
        reviewer_filter_options=reviewer_filter_options,
        manual_mode=mode,
        assignments=assignment_views,
        next_url=next_url,
        reviewers=reviewers_for_page,
    )


@trabalho_routes.route("/trabalhos/avaliacoes/<int:avaliacao_id>")
@login_required
def visualizar_avaliacao_revisor(avaliacao_id: int):
    """Permite que clientes e administradores visualizem uma avaliação registrada."""

    if current_user.tipo not in ["cliente", "admin"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for(_user_dashboard_endpoint()))

    avaliacao = (
        AvaliacaoBarema.query.options(
            joinedload(AvaliacaoBarema.criterios_avaliacao),
            joinedload(AvaliacaoBarema.revisor),
            joinedload(AvaliacaoBarema.trabalho).joinedload(Submission.evento),
        )
        .get_or_404(avaliacao_id)
    )

    if current_user.tipo == "cliente":
        evento = avaliacao.trabalho.evento if avaliacao.trabalho else None
        if evento and evento.cliente_id != current_user.id:
            flash("Acesso negado.", "danger")
            return redirect(url_for("trabalho_routes.listar_trabalhos"))

    criterios = sorted(
        avaliacao.criterios_avaliacao,
        key=lambda criterio: criterio.criterio_id or "",
    )

    return render_template(
        "trabalhos/avaliacao_detalhe.html",
        avaliacao=avaliacao,
        criterios=criterios,
    )


@trabalho_routes.route(
    "/trabalhos/avaliacoes/<int:avaliacao_id>/excluir",
    methods=["POST"],
)
@login_required
def excluir_avaliacao_revisor(avaliacao_id: int):
    """Exclui uma avaliação existente e reabre os assignments associados."""

    if current_user.tipo not in ["cliente", "admin"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for(_user_dashboard_endpoint()))

    avaliacao = (
        AvaliacaoBarema.query.options(
            joinedload(AvaliacaoBarema.trabalho).joinedload(Submission.evento),
            joinedload(AvaliacaoBarema.revisor),
        )
        .get_or_404(avaliacao_id)
    )

    if current_user.tipo == "cliente":
        evento = avaliacao.trabalho.evento if avaliacao.trabalho else None
        if evento and evento.cliente_id != current_user.id:
            flash("Acesso negado.", "danger")
            return redirect(url_for("trabalho_routes.listar_trabalhos"))

    next_url = request.form.get("next") or url_for("trabalho_routes.listar_trabalhos")

    try:
        resposta = None
        if avaliacao.trabalho_id:
            resposta = (
                RespostaFormulario.query.filter_by(trabalho_id=avaliacao.trabalho_id)
                .order_by(RespostaFormulario.id.asc())
                .first()
            )

        if resposta:
            (
                Assignment.query.filter_by(
                    resposta_formulario_id=resposta.id,
                    reviewer_id=avaliacao.revisor_id,
                ).update({"completed": False}, synchronize_session=False)
            )

        db.session.delete(avaliacao)
        db.session.commit()
        flash("Avaliação excluída com sucesso.", "success")
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        current_app.logger.exception("Erro ao excluir avaliação: %s", exc)
        flash("Erro ao excluir avaliação.", "danger")

    return redirect(next_url)


@trabalho_routes.route("/trabalhos/export/xlsx")
@login_required
def exportar_trabalhos_xlsx():
    if current_user.tipo not in ["cliente", "admin"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for(_user_dashboard_endpoint()))

    formulario = get_trabalhos_form()
    if not formulario:
        flash("Formulário de trabalhos não configurado.", "warning")
        return redirect(url_for("trabalho_routes.listar_trabalhos"))

    dataset = _prepare_trabalhos_dataset(formulario)
    filtros = _extract_filters_from_request()
    trabalhos_filtrados = _apply_trabalho_filters(dataset["trabalhos"], filtros)

    dataframe = _build_export_dataframe(trabalhos_filtrados)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Trabalhos")
    buffer.seek(0)

    filename = f"trabalhos_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@trabalho_routes.route("/trabalhos/export/pdf")
@login_required
def exportar_trabalhos_pdf():
    if current_user.tipo not in ["cliente", "admin"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for(_user_dashboard_endpoint()))

    formulario = get_trabalhos_form()
    if not formulario:
        flash("Formulário de trabalhos não configurado.", "warning")
        return redirect(url_for("trabalho_routes.listar_trabalhos"))

    dataset = _prepare_trabalhos_dataset(formulario)
    filtros = _extract_filters_from_request()
    trabalhos_filtrados = _apply_trabalho_filters(dataset["trabalhos"], filtros)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    elements = [Paragraph("Relatório de Trabalhos", styles["Title"])]

    resumo_texto = f"Total de trabalhos: {len(trabalhos_filtrados)}"
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph(resumo_texto, styles["Normal"]))

    if filtros:
        filtros_legiveis = []
        options_lookup = {
            (item["question"], option["value"]): option["label"]
            for item in dataset["filter_options"]
            for option in item.get("options", [])
        }
        for filtro in filtros:
            pergunta = filtro.get("question")
            valores = filtro.get("values") or []
            if not pergunta or not valores:
                continue
            labels = [
                options_lookup.get((pergunta, valor), valor)
                for valor in valores
            ]
            filtros_legiveis.append(f"{pergunta}: {', '.join(labels)}")
        if filtros_legiveis:
            elements.append(Spacer(1, 0.2 * cm))
            elements.append(
                Paragraph(
                    "Filtros aplicados: " + " | ".join(filtros_legiveis),
                    styles["Italic"],
                )
            )

    elements.append(Spacer(1, 0.4 * cm))

    header = ["ID", "Título", "Categoria", "Rede", "Status", "Revisores"]
    tabela_dados = [header]

    if trabalhos_filtrados:
        for trabalho in trabalhos_filtrados:
            respostas = trabalho.get("respostas") or {}
            tabela_dados.append(
                [
                    trabalho.get("id") or "",
                    trabalho.get("título")
                    or _stringify_field_value(respostas.get("Título"))
                    or "",
                    trabalho.get("categoria")
                    or _stringify_field_value(respostas.get("Categoria"))
                    or "",
                    trabalho.get("rede_de_ensino")
                    or _stringify_field_value(respostas.get("Rede de Ensino"))
                    or "",
                    trabalho.get("distribution_status") or "",
                    ", ".join(trabalho.get("reviewer_names") or []),
                ]
            )
    else:
        tabela_dados.append(["-", "Sem dados disponíveis", "", "", "", ""])

    tabela = Table(
        tabela_dados,
        colWidths=[1.5 * cm, 5.5 * cm, 3.5 * cm, 3.0 * cm, 2.5 * cm, 4.5 * cm],
        repeatRows=1,
    )
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elements.append(tabela)

    doc.build(elements)
    buffer.seek(0)

    filename = f"trabalhos_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )


@trabalho_routes.route("/trabalhos/novo", methods=["GET", "POST"])
@login_required
def novo_trabalho():
    """Formulário para adicionar novo trabalho."""
    if current_user.tipo != "cliente":
        flash("Acesso negado.", "danger")
        return redirect(url_for(_user_dashboard_endpoint()))

    formulario = get_trabalhos_form()
    if not formulario:
        return render_template("trabalhos/formulario_nao_encontrado.html")
    
    # Buscar eventos disponíveis para o cliente
    eventos = Evento.query.filter_by(cliente_id=current_user.id).all()
    
    if request.method == "POST":
        current_app.logger.info(f"POST recebido para novo trabalho - Usuário: {current_user.id} ({current_user.nome})")
        current_app.logger.info(f"Dados do formulário: {dict(request.form)}")
        
        # Validar evento selecionado
        evento_id = request.form.get('evento_id')
        current_app.logger.info(f"Evento ID recebido: {evento_id}")
        if not evento_id:
            current_app.logger.warning("Evento não selecionado")
            flash("Por favor, selecione um evento.", "warning")
            return render_template("trabalhos/novo_trabalho.html", formulario=formulario, eventos=eventos)
        
        # Verificar se o evento pertence ao cliente
        current_app.logger.info(f"Verificando evento {evento_id} para cliente {current_user.id}")
        evento = Evento.query.filter_by(id=evento_id, cliente_id=current_user.id).first()
        if not evento:
            current_app.logger.error(f"Evento {evento_id} não encontrado ou não pertence ao cliente {current_user.id}")
            flash("Evento inválido.", "danger")
            return render_template("trabalhos/novo_trabalho.html", formulario=formulario, eventos=eventos)
        current_app.logger.info(f"Evento válido encontrado: {evento.nome}")
        
        # Primeiro, processar campos do formulário para obter título
        titulo = None
        campos_valores = {}
        
        for campo in formulario.campos:
            valor = request.form.get(f"campo_{campo.id}")
            
            # Validar campos obrigatórios
            if campo.obrigatorio and not valor:
                flash(f"O campo '{campo.nome}' é obrigatório.", "warning")
                return render_template("trabalhos/novo_trabalho.html", formulario=formulario, eventos=eventos)
            
            campos_valores[campo.id] = valor or ''
            
            # Capturar título (primeiro campo de texto não vazio)
            if not titulo and valor and campo.tipo in ['text', 'textarea']:
                titulo = valor
        
        # Usar título padrão se não encontrado
        titulo = titulo or "Trabalho sem título"
        
        try:
            # Log detalhado para debug
            current_app.logger.info(f"Tentando criar submissão - Título: {titulo}, Autor: {current_user.id}, Evento: {evento_id}")
            current_app.logger.info(f"Campos processados: {campos_valores}")
            
            # Permitir múltiplos trabalhos por usuário no mesmo evento
            current_app.logger.info(f"Criando nova submissão para usuário {current_user.id} no evento {evento_id}")
            
            author_usuario = db.session.get(Usuario, getattr(current_user, "id", None))
            if not author_usuario and getattr(current_user, "email", None):
                author_usuario = Usuario.query.filter_by(email=current_user.email).first()

            author_id = author_usuario.id if author_usuario else None
            submission_attributes = {}
            if not author_usuario:
                current_app.logger.info(
                    "Nenhum usuário encontrado na tabela 'usuario' para o cliente %s",
                    current_user.id,
                )
                submission_attributes = {
                    "cliente_id": current_user.id,
                    "cliente_nome": current_user.nome,
                }
                if getattr(current_user, "email", None):
                    submission_attributes["cliente_email"] = current_user.email

            # Criar submissão usando o serviço
            submission = SubmissionService.create_submission(
                title=titulo,
                author_id=author_id,
                evento_id=int(evento_id),
                attributes=submission_attributes or None,
            )

            current_app.logger.info(f"Submissão criada com sucesso - ID: {submission.id}")

            # Criar nova resposta do formulário vinculada à submissão
            resposta_formulario = RespostaFormulario(
                formulario_id=formulario.id,
                usuario_id=author_id,
                evento_id=int(evento_id),
                trabalho_id=submission.id  # Vincular à submissão criada
            )
            db.session.add(resposta_formulario)
            db.session.flush()
            
            current_app.logger.info(f"RespostaFormulario criada - ID: {resposta_formulario.id}")
            
            # Criar respostas dos campos
            for campo_id, valor in campos_valores.items():
                resposta_campo = RespostaCampoFormulario(
                    resposta_formulario_id=resposta_formulario.id,
                    campo_id=campo_id,
                    valor=valor
                )
                db.session.add(resposta_campo)
            
            db.session.commit()
            current_app.logger.info("Trabalho cadastrado com sucesso no banco de dados")
            flash("Trabalho cadastrado com sucesso!", "success")
            return redirect(url_for("trabalho_routes.listar_trabalhos"))
            
        except ValueError as e:
            db.session.rollback()
            current_app.logger.error(f"Erro de validação ao cadastrar trabalho: {e}")
            flash(str(e), "warning")
            return render_template("trabalhos/novo_trabalho.html", formulario=formulario, eventos=eventos)
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro inesperado ao cadastrar trabalho: {e}", exc_info=True)
            flash("Erro ao cadastrar trabalho. Tente novamente.", "danger")
            return render_template("trabalhos/novo_trabalho.html", formulario=formulario, eventos=eventos)
    
    return render_template("trabalhos/novo_trabalho.html", formulario=formulario, eventos=eventos)


@trabalho_routes.route("/trabalhos/<int:trabalho_id>/editar", methods=["GET", "POST"])
@login_required
def editar_trabalho(trabalho_id):
    """Editar trabalho existente."""
    if current_user.tipo not in ["cliente", "admin", "revisor"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for(_user_dashboard_endpoint()))
    
    # Buscar resposta do formulário
    if current_user.tipo == "admin":
        # Admin pode editar qualquer trabalho
        resposta = RespostaFormulario.query.get(trabalho_id)
    elif current_user.tipo == "revisor":
        # Revisor pode editar trabalhos distribuídos para ele ou seus próprios trabalhos
        resposta = RespostaFormulario.query.filter(
            db.or_(
                RespostaFormulario.usuario_id == current_user.id,
                RespostaFormulario.id.in_(
                    db.session.query(Assignment.resposta_formulario_id)
                    .filter(Assignment.reviewer_id == current_user.id)
                )
            )
        ).filter(RespostaFormulario.id == trabalho_id).first()
    else:
        # Cliente só pode editar seus próprios trabalhos
        resposta = RespostaFormulario.query.filter_by(
            id=trabalho_id,
            usuario_id=current_user.id
        ).first()
    
    if not resposta:
        flash("Trabalho não encontrado.", "danger")
        return redirect(url_for("trabalho_routes.listar_trabalhos"))
    
    formulario = resposta.formulario
    
    if request.method == "POST":
        # Atualizar evento se fornecido
        evento_id = request.form.get('evento_id')
        if evento_id:
            try:
                resposta.evento_id = int(evento_id)
            except (ValueError, TypeError):
                flash("Evento inválido selecionado.", "warning")
                # Buscar eventos para reexibir o formulário
                if current_user.tipo == "admin":
                    eventos = Evento.query.order_by(Evento.nome).all()
                else:
                    eventos = Evento.query.filter_by(cliente_id=current_user.id).order_by(Evento.nome).all()
                return render_template("trabalhos/editar_trabalho.html", 
                                     formulario=formulario, resposta=resposta, eventos=eventos)
        
        # Atualizar respostas dos campos
        for campo in formulario.campos:
            valor = request.form.get(f"campo_{campo.id}")
            
            # Validar campos obrigatórios
            if campo.obrigatorio and not valor:
                flash(f"O campo '{campo.nome}' é obrigatório.", "warning")
                return render_template("trabalhos/editar_trabalho.html", 
                                     formulario=formulario, resposta=resposta)
            
            # Buscar ou criar resposta do campo
            resposta_campo = RespostaCampoFormulario.query.filter_by(
                resposta_formulario_id=resposta.id,
                campo_id=campo.id
            ).first()
            
            if resposta_campo:
                resposta_campo.valor = valor or ''
            else:
                resposta_campo = RespostaCampoFormulario(
                    resposta_formulario_id=resposta.id,
                    campo_id=campo.id,
                    valor=valor or ''
                )
                db.session.add(resposta_campo)
        
        try:
            db.session.commit()
            flash("Trabalho atualizado com sucesso!", "success")
            return redirect(url_for("trabalho_routes.listar_trabalhos"))
        except Exception as e:
            db.session.rollback()
            flash("Erro ao atualizar trabalho. Tente novamente.", "danger")
            current_app.logger.error(f"Erro ao atualizar trabalho: {e}")
    
    # Buscar eventos do usuário logado para o select
    if current_user.tipo == "admin":
        eventos = Evento.query.order_by(Evento.nome).all()
    else:
        eventos = Evento.query.filter_by(cliente_id=current_user.id).order_by(Evento.nome).all()
    
    return render_template("trabalhos/editar_trabalho.html", 
                         formulario=formulario, resposta=resposta, eventos=eventos)


@trabalho_routes.route("/trabalhos/<int:trabalho_id>/excluir", methods=["POST"])
@login_required
def excluir_trabalho(trabalho_id):
    """Excluir trabalho."""
    if current_user.tipo not in ["cliente", "admin", "revisor"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for(_user_dashboard_endpoint()))
    
    # Buscar resposta do formulário
    if current_user.tipo == "admin":
        # Admin pode excluir qualquer trabalho
        resposta = RespostaFormulario.query.get(trabalho_id)
    elif current_user.tipo == "revisor":
        # Revisor pode excluir trabalhos distribuídos para ele ou seus próprios trabalhos
        resposta = RespostaFormulario.query.filter(
            db.or_(
                RespostaFormulario.usuario_id == current_user.id,
                RespostaFormulario.id.in_(
                    db.session.query(Assignment.resposta_formulario_id)
                    .filter(Assignment.reviewer_id == current_user.id)
                )
            )
        ).filter(RespostaFormulario.id == trabalho_id).first()
    else:
        # Cliente só pode excluir seus próprios trabalhos
        resposta = RespostaFormulario.query.filter_by(
            id=trabalho_id,
            usuario_id=current_user.id
        ).first()
    
    if not resposta:
        flash("Trabalho não encontrado.", "danger")
        return redirect(url_for("trabalho_routes.listar_trabalhos"))
    
    try:
        # Importar Assignment se não estiver importado
        from models.review import Assignment
        
        # Excluir assignments relacionados primeiro
        Assignment.query.filter_by(resposta_formulario_id=resposta.id).delete()
        
        # Excluir respostas dos campos
        RespostaCampoFormulario.query.filter_by(resposta_formulario_id=resposta.id).delete()
        
        # Excluir resposta do formulário
        db.session.delete(resposta)
        db.session.commit()
        flash("Trabalho excluído com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir trabalho: {str(e)}", "danger")
        current_app.logger.error(f"Erro ao excluir trabalho: {e}")
    
    return redirect(url_for("trabalho_routes.listar_trabalhos"))


@trabalho_routes.route("/trabalhos/<int:trabalho_id>/visualizar")
@login_required
def visualizar_trabalho(trabalho_id):
    """Visualizar detalhes do trabalho."""
    if current_user.tipo not in ["cliente", "admin", "revisor"]:
        flash("Acesso negado.", "danger")
        return redirect(url_for(_user_dashboard_endpoint()))
    
    # Buscar resposta do formulário
    if current_user.tipo == "admin":
        # Admin pode visualizar qualquer trabalho
        resposta = RespostaFormulario.query.get(trabalho_id)
    elif current_user.tipo == "revisor":
        # Revisor pode visualizar trabalhos distribuídos para ele ou seus próprios trabalhos
        resposta = RespostaFormulario.query.filter(
            db.or_(
                RespostaFormulario.usuario_id == current_user.id,
                RespostaFormulario.id.in_(
                    db.session.query(Assignment.resposta_formulario_id)
                    .filter(Assignment.reviewer_id == current_user.id)
                )
            )
        ).filter(RespostaFormulario.id == trabalho_id).first()
    else:
        # Cliente só pode visualizar seus próprios trabalhos
        resposta = RespostaFormulario.query.filter_by(
            id=trabalho_id,
            usuario_id=current_user.id
        ).first()
    
    if not resposta:
        flash("Trabalho não encontrado.", "danger")
        return redirect(url_for("trabalho_routes.listar_trabalhos"))
    
    # Obter o formulário associado
    formulario = resposta.formulario
    
    # Organizar dados do trabalho
    trabalho = {'id': resposta.id, 'data_submissao': resposta.data_submissao}
    for resposta_campo in resposta.respostas_campos:
        campo_nome = resposta_campo.campo.nome
        trabalho[campo_nome.lower().replace(' ', '_')] = resposta_campo.valor
    
    return render_template("trabalhos/visualizar_trabalho.html", 
                         trabalho=trabalho, resposta=resposta, formulario=formulario)


# ───────────────────────────── DISTRIBUIÇÃO ──────────────────────────────── #
@trabalho_routes.route("/distribuicao", methods=["GET", "POST"])
@login_required
def distribuicao():
    """Permite importar planilha e mapear campos para distribuição."""

    campos = ["titulo", "resumo"]
    if request.method == "POST":
        if "data" in request.form and all(
            f"map_{c}" in request.form for c in campos
        ):
            data_json = request.form.get("data", "[]")
            try:
                rows = json.loads(data_json)
            except json.JSONDecodeError:
                flash("Dados inválidos.", "danger")
                return redirect(url_for("trabalho_routes.distribuicao"))
            mapping = {c: request.form.get(f"map_{c}") for c in campos}
            for row in rows:
                item = {c: row.get(col) for c, col in mapping.items()}
                db.session.add(WorkMetadata(data=item))
            db.session.commit()
            flash("Dados importados com sucesso!", "success")
            return redirect(url_for("trabalho_routes.distribuicao"))

        arquivo = request.files.get("arquivo")
        if not arquivo or arquivo.filename == "":
            flash("Nenhum arquivo selecionado.", "warning")
            return render_template("distribuicao.html")


# ──────────────────────── DISTRIBUIÇÃO DE TRABALHOS ─────────────────────── #
@trabalho_routes.route("/api/reviewers", methods=["GET"])
def get_available_reviewers():
    """API endpoint to get available reviewers for distribution."""
    # Authentication removed to allow access for distribution functionality

    # CSRF validation removed for API endpoints

    try:
        target_cliente_id = request.args.get('cliente_id', type=int)
        if not target_cliente_id and current_user.is_authenticated and getattr(current_user, 'tipo', None) == 'cliente':
            target_cliente_id = getattr(current_user, 'id', None)

        reviewer_list = _build_reviewer_distribution_list(target_cliente_id)

        return {
            "success": True,
            "reviewers": reviewer_list,
            "total": len(reviewer_list)
        }
    
    except Exception as e:
        current_app.logger.error(f"Error getting reviewers: {e}")
        return {"error": "Internal server error"}, 500


@trabalho_routes.route("/api/distribution/manual", methods=["POST"])
@csrf.exempt
def manual_distribution():
    """API endpoint for manual work distribution."""
    
    try:
        data = request.get_json()
        if not data:
            return {"error": "No data provided"}, 400
        
        work_ids = data.get('work_ids', [])
        assignments = data.get('assignments', [])
        deadline = data.get('deadline')  # Get deadline from top level
        notes = data.get('notes', '')
        default_re_evaluation = bool(data.get('re_evaluation', False))

        if not work_ids or not assignments:
            return {"error": "Work IDs and assignments are required"}, 400
        
        # Validate works exist
        works = RespostaFormulario.query.filter(
            RespostaFormulario.id.in_(work_ids)
        ).all()
        
        if len(works) != len(work_ids):
            return {"error": "Some works not found"}, 404
        
        assignment_table, resolved_columns, column_map = _load_assignment_table()
        current_app.logger.debug(
            "assignment table columns detected: %s",
            ", ".join(sorted(column_map.keys())) or "<nenhuma>",
        )

        resposta_column = resolved_columns['resposta']
        reviewer_column = resolved_columns['reviewer']
        id_column = resolved_columns['id']
        deadline_column = resolved_columns['deadline']
        distribution_type_column = resolved_columns['distribution_type']
        distribution_date_column = resolved_columns['distribution_date']
        distributed_by_column = resolved_columns['distributed_by']
        notes_column = resolved_columns['notes']
        is_reevaluation_column = resolved_columns['is_reevaluation']

        def _coerce_deadline(value):
            if not value:
                return None
            if isinstance(value, datetime):
                return value
            try:
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is None:
                    return parsed
                return parsed.astimezone().replace(tzinfo=None)
            except ValueError:
                pass
            try:
                date_part = datetime.strptime(value, "%Y-%m-%d").date()
                return datetime.combine(date_part, time(23, 59))
            except ValueError:
                return None

        base_deadline = _coerce_deadline(deadline)

        assignments_created = 0

        distributor_user_id = None
        if distributed_by_column is not None and current_user.is_authenticated:
            try:
                user_obj = current_user._get_current_object()
            except AttributeError:  # pragma: no cover - defensive fallback
                user_obj = current_user

            if isinstance(user_obj, Usuario):
                distributor_user_id = user_obj.id
            else:
                raw_impersonator = session.get('impersonator_id')
                candidate_ids = [raw_impersonator, getattr(user_obj, 'usuario_id', None)]
                for candidate in candidate_ids:
                    if not candidate:
                        continue
                    try:
                        candidate_int = int(candidate)
                    except (TypeError, ValueError):
                        continue
                    exists = db.session.execute(
                        sa.select(Usuario.id).where(Usuario.id == candidate_int)
                    ).scalar()
                    if exists:
                        distributor_user_id = candidate_int
                        break
                if distributor_user_id is None and raw_impersonator:
                    current_app.logger.debug(
                        "Impersonator id %s not found in usuario table; omitting distributed_by",
                        raw_impersonator,
                    )

        for assignment_data in assignments:
            work_id = assignment_data.get('workId')
            reviewer_id = assignment_data.get('reviewerId')
            assignment_re_evaluation = bool(assignment_data.get('re_evaluation', default_re_evaluation))

            if not work_id or not reviewer_id:
                continue

            try:
                work_id_int = int(work_id)
                reviewer_id_int = int(reviewer_id)
            except (TypeError, ValueError):
                continue

            select_target = id_column if id_column is not None else sa.literal(1)
            existing_stmt = sa.select(select_target).where(
                resposta_column == work_id_int,
                reviewer_column == reviewer_id_int,
            ).limit(1)
            existing = db.session.execute(existing_stmt).first()
            if existing:
                continue

            assignment_deadline = _coerce_deadline(assignment_data.get('deadline')) or base_deadline

            insert_values = {
                resposta_column.key: work_id_int,
                reviewer_column.key: reviewer_id_int,
            }

            if assignment_deadline and deadline_column is not None:
                insert_values[deadline_column.key] = assignment_deadline

            if distribution_type_column is not None:
                insert_values[distribution_type_column.key] = 'manual_reevaluation' if assignment_re_evaluation else 'manual'

            if distribution_date_column is not None:
                insert_values[distribution_date_column.key] = datetime.utcnow()

            if distributed_by_column is not None and distributor_user_id is not None:
                insert_values[distributed_by_column.key] = distributor_user_id

            if notes_column is not None:
                insert_values[notes_column.key] = notes

            if is_reevaluation_column is not None:
                insert_values[is_reevaluation_column.key] = assignment_re_evaluation

            db.session.execute(sa.insert(assignment_table).values(**insert_values))
            assignments_created += 1

        db.session.commit()

        return {
            "success": True,
            "message": f"Successfully created {assignments_created} assignments",
            "assignments_created": assignments_created
        }

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in manual distribution: {e}")
        return {"error": "Internal server error"}, 500


@trabalho_routes.route("/api/distribution/deadline", methods=["POST"])
@csrf.exempt
@login_required
def update_distribution_deadline():
    """Aplica um prazo global para todas as atribuições dos trabalhos informados."""

    if current_user.tipo not in ["cliente", "admin"]:
        return {"error": "Acesso negado."}, 403

    data = request.get_json() or {}
    raw_deadline = data.get("deadline")
    work_ids = data.get("work_ids") or []

    if not raw_deadline:
        return {"error": "Informe uma data limite."}, 400
    if not isinstance(work_ids, list) or not work_ids:
        return {"error": "Informe os trabalhos que devem receber o prazo."}, 400

    try:
        deadline_date = datetime.strptime(raw_deadline, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Data inválida. Utilize o formato AAAA-MM-DD."}, 400

    deadline_dt = datetime.combine(deadline_date, time(23, 59, 0))

    try:
        updated = (
            Assignment.query.filter(
                Assignment.resposta_formulario_id.in_(work_ids)
            ).update({"deadline": deadline_dt}, synchronize_session=False)
        )
        db.session.commit()
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        current_app.logger.exception("Erro ao atualizar prazo global de distribuicao: %s", exc)
        return {"error": "Erro ao atualizar prazos."}, 500

    return {"success": True, "updated": updated}


@trabalho_routes.route("/api/distribution/automatic", methods=["POST"])
@csrf.exempt
def automatic_distribution():
    """API endpoint for automatic work distribution."""
    
    try:
        data = request.get_json()
        if not data:
            return {"error": "No data provided"}, 400
        
        work_ids = data.get('work_ids', [])
        reviewers_per_work = data.get('reviewers_per_work', 2)
        criteria = data.get('criteria', {})
        notes = data.get('notes', '')
        
        if not work_ids:
            return {"error": "Work IDs are required"}, 400
        
        # Get available reviewers
        reviewers_query = Usuario.query.filter_by(tipo="revisor")
        
        # Apply criteria filters if provided
        if criteria.get('expertise'):
            # This would need to be implemented based on your user model
            pass
        
        if criteria.get('max_assignments'):
            # Filter reviewers with fewer than max assignments
            max_assignments = criteria['max_assignments']
            reviewers_query = reviewers_query.filter(
                ~Usuario.id.in_(
                    db.session.query(Assignment.reviewer_id)
                    .filter(Assignment.completed == False)
                    .group_by(Assignment.reviewer_id)
                    .having(db.func.count(Assignment.id) >= max_assignments)
                )
            )
        
        available_reviewers = reviewers_query.all()
        
        if len(available_reviewers) < reviewers_per_work:
            return {
                "error": f"Not enough reviewers available. Need {reviewers_per_work}, found {len(available_reviewers)}"
            }, 400
        
        # Get works
        works = RespostaFormulario.query.filter(
            RespostaFormulario.id.in_(work_ids)
        ).all()
        
        assignments_created = 0
        
        # Simple round-robin distribution
        reviewer_index = 0
        for work in works:
            for _ in range(reviewers_per_work):
                reviewer = available_reviewers[reviewer_index % len(available_reviewers)]
                
                # Check if assignment already exists
                existing = Assignment.query.filter_by(
                    resposta_formulario_id=work.id,
                    reviewer_id=reviewer.id
                ).first()
                
                if not existing:
                    assignment = Assignment(
                        resposta_formulario_id=work.id,
                        reviewer_id=reviewer.id,
                        distribution_type='automatic',
                        distribution_date=db.func.now(),
                        distributed_by=None,
                        notes=notes
                    )
                    db.session.add(assignment)
                    assignments_created += 1
                
                reviewer_index += 1
        
        # Distribution logging removed to eliminate CSRF-related database errors
        
        db.session.commit()
        
        return {
            "success": True,
            "message": f"Successfully created {assignments_created} assignments",
            "assignments_created": assignments_created,
            "distribution_summary": {
                "works_distributed": len(works),
                "reviewers_used": len(available_reviewers),
                "reviewers_per_work": reviewers_per_work
            }
        }
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in automatic distribution: {e}")
        return {"error": "Internal server error"}, 500


@trabalho_routes.route("/api/distribution/undo/<int:work_id>", methods=["DELETE"])
@csrf.exempt
def undo_work_distribution(work_id):
    """API endpoint to undo distribution for a specific work."""
    
    try:
        # Check if work exists
        work = RespostaFormulario.query.get(work_id)
        if not work:
            return {"error": "Work not found"}, 404
        
        # Delete all assignments for this work
        assignments = Assignment.query.filter_by(resposta_formulario_id=work_id).all()
        
        if not assignments:
            return {"error": "No distribution found for this work"}, 404
        
        assignments_deleted = len(assignments)
        
        for assignment in assignments:
            db.session.delete(assignment)
        
        db.session.commit()
        
        return {
            "success": True,
            "message": f"Successfully removed {assignments_deleted} assignments for work ID {work_id}",
            "assignments_deleted": assignments_deleted
        }, 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error undoing work distribution: {e}")
        return {"error": "Internal server error"}, 500


@trabalho_routes.route("/api/distribution/undo-all", methods=["DELETE"])
@csrf.exempt
def undo_all_distributions():
    """API endpoint to undo all work distributions."""
    
    try:
        # Get all assignments
        assignments = Assignment.query.all()
        
        if not assignments:
            return {"error": "No distributions found"}, 404
        
        assignments_deleted = len(assignments)
        works_affected = len(set(assignment.resposta_formulario_id for assignment in assignments))
        
        # Delete all assignments
        for assignment in assignments:
            db.session.delete(assignment)
        
        db.session.commit()
        
        return {
            "success": True,
            "message": f"Successfully removed all distributions. {assignments_deleted} assignments from {works_affected} works were deleted.",
            "assignments_deleted": assignments_deleted,
            "works_affected": works_affected
        }, 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error undoing all distributions: {e}")
        return {"error": "Internal server error"}, 500


        try:
            df = pd.read_excel(arquivo)
        except Exception:
            flash("Erro ao processar o arquivo.", "danger")
            return render_template("distribuicao.html")
        columns = df.columns.tolist()
        data = df.to_dict(orient="records")
        flash("Planilha carregada com sucesso.", "info")
        return render_template(
            "distribuicao.html",
            columns=columns,
            data_preview=data[:5],
            data_json=json.dumps(data),
            campos=campos,
        )

    return render_template("distribuicao.html")
