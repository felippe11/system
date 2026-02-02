"""Rotas do sistema de feedback aberto diario (isolado)."""

from datetime import datetime
import json

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user

from extensions import db
from utils.auth import cliente_required
from models import (
    FeedbackAbertoPergunta,
    FeedbackAbertoDia,
    FeedbackAbertoEnvio,
    FeedbackAbertoResposta,
    TipoPerguntaFeedbackAberto,
)
from services.open_feedback_service import OpenFeedbackService


open_feedback_routes = Blueprint("open_feedback_routes", __name__)


def _parse_opcoes(pergunta: FeedbackAbertoPergunta):
    if not pergunta.opcoes:
        return []
    try:
        return json.loads(pergunta.opcoes)
    except (TypeError, json.JSONDecodeError):
        return []


def _normalizar_selecao_multipla(valores: list[str]):
    return [valor.strip() for valor in valores if valor.strip()]


@open_feedback_routes.route("/feedback-aberto")
@cliente_required
def feedback_aberto_home():
    dias = (
        FeedbackAbertoDia.query
        .filter_by(cliente_id=current_user.id)
        .order_by(FeedbackAbertoDia.data.desc())
        .all()
    )
    perguntas = OpenFeedbackService.listar_perguntas(current_user.id)
    return render_template(
        "feedback_aberto/gerenciar.html",
        dias=dias,
        perguntas=perguntas,
    )


@open_feedback_routes.route("/feedback-aberto/dias/criar", methods=["POST"])
@cliente_required
def criar_feedback_aberto_dia():
    data_str = request.form.get("data")
    titulo = request.form.get("titulo")
    pergunta_ids = [
        int(pid)
        for pid in request.form.getlist("perguntas")
        if pid.isdigit()
    ]
    exigir_nome = bool(request.form.get("exigir_nome"))
    exigir_email = bool(request.form.get("exigir_email"))
    exigir_telefone = bool(request.form.get("exigir_telefone"))
    exigir_identificador = bool(request.form.get("exigir_identificador"))

    if not data_str:
        flash("Informe a data do feedback aberto.", "danger")
        return redirect(url_for("open_feedback_routes.feedback_aberto_home"))

    if not pergunta_ids:
        total_perguntas = (
            FeedbackAbertoPergunta.query
            .filter_by(cliente_id=current_user.id, ativa=True)
            .count()
        )
        if total_perguntas == 0:
            flash("Cadastre ao menos uma pergunta antes de criar o dia.", "warning")
            return redirect(url_for("open_feedback_routes.feedback_aberto_home"))

    try:
        data = datetime.strptime(data_str, "%Y-%m-%d").date()
        OpenFeedbackService.criar_dia(
            cliente_id=current_user.id,
            data=data,
            titulo=titulo,
            pergunta_ids=pergunta_ids or None,
            exigir_nome=exigir_nome,
            exigir_email=exigir_email,
            exigir_telefone=exigir_telefone,
            exigir_identificador=exigir_identificador,
        )
        flash("Feedback aberto criado com sucesso.", "success")
    except ValueError as exc:
        flash(str(exc), "warning")
    except Exception:
        flash("Nao foi possivel criar o feedback aberto.", "danger")
    return redirect(url_for("open_feedback_routes.feedback_aberto_home"))


@open_feedback_routes.route("/feedback-aberto/dias/<int:dia_id>/status", methods=["POST"])
@cliente_required
def atualizar_status_feedback_aberto(dia_id: int):
    dia = FeedbackAbertoDia.query.get_or_404(dia_id)
    if dia.cliente_id != current_user.id:
        flash("Acesso negado.", "danger")
        return redirect(url_for("open_feedback_routes.feedback_aberto_home"))

    dia.ativa = not dia.ativa
    db.session.commit()
    flash("Status atualizado.", "success")
    return redirect(url_for("open_feedback_routes.feedback_aberto_home"))


@open_feedback_routes.route("/feedback-aberto/perguntas")
@cliente_required
def feedback_aberto_perguntas():
    perguntas = (
        FeedbackAbertoPergunta.query
        .filter_by(cliente_id=current_user.id, ativa=True)
        .order_by(FeedbackAbertoPergunta.ordem.asc(), FeedbackAbertoPergunta.id.asc())
        .all()
    )
    perguntas_contexto = []
    for pergunta in perguntas:
        opcoes = _parse_opcoes(pergunta)
        perguntas_contexto.append(
            {
                "obj": pergunta,
                "opcoes_texto": "; ".join(opcoes),
            }
        )
    return render_template(
        "feedback_aberto/perguntas.html",
        perguntas=perguntas_contexto,
        tipos=list(TipoPerguntaFeedbackAberto),
    )


@open_feedback_routes.route("/feedback-aberto/perguntas/criar", methods=["POST"])
@cliente_required
def criar_feedback_aberto_pergunta():
    titulo = request.form.get("titulo", "").strip()
    tipo = request.form.get("tipo")
    opcoes_raw = request.form.get("opcoes", "")

    if not titulo or not tipo:
        flash("Titulo e tipo sao obrigatorios.", "danger")
        return redirect(url_for("open_feedback_routes.feedback_aberto_perguntas"))

    if opcoes_raw:
        opcoes = [item.strip() for item in opcoes_raw.split(";") if item.strip()]
    else:
        opcoes = []

    try:
        OpenFeedbackService.criar_pergunta(
            cliente_id=current_user.id,
            titulo=titulo,
            descricao=request.form.get("descricao"),
            tipo=tipo,
            opcoes=opcoes,
            obrigatoria=bool(request.form.get("obrigatoria")),
            ordem=int(request.form.get("ordem") or 0),
        )
        flash("Pergunta criada.", "success")
    except Exception:
        flash("Nao foi possivel criar a pergunta.", "danger")
    return redirect(url_for("open_feedback_routes.feedback_aberto_perguntas"))


@open_feedback_routes.route("/feedback-aberto/perguntas/<int:pergunta_id>/editar", methods=["POST"])
@cliente_required
def editar_feedback_aberto_pergunta(pergunta_id: int):
    pergunta = FeedbackAbertoPergunta.query.get_or_404(pergunta_id)
    if pergunta.cliente_id != current_user.id:
        flash("Acesso negado.", "danger")
        return redirect(url_for("open_feedback_routes.feedback_aberto_perguntas"))

    opcoes_raw = request.form.get("opcoes", "")
    if opcoes_raw:
        opcoes = [item.strip() for item in opcoes_raw.split(";") if item.strip()]
    else:
        opcoes = []

    try:
        OpenFeedbackService.atualizar_pergunta(
            pergunta_id,
            titulo=request.form.get("titulo"),
            descricao=request.form.get("descricao"),
            tipo=request.form.get("tipo"),
            opcoes=opcoes,
            obrigatoria=bool(request.form.get("obrigatoria")),
            ordem=int(request.form.get("ordem") or 0),
        )
        flash("Pergunta atualizada.", "success")
    except Exception:
        flash("Nao foi possivel atualizar a pergunta.", "danger")
    return redirect(url_for("open_feedback_routes.feedback_aberto_perguntas"))


@open_feedback_routes.route("/feedback-aberto/perguntas/<int:pergunta_id>/excluir", methods=["POST"])
@cliente_required
def excluir_feedback_aberto_pergunta(pergunta_id: int):
    pergunta = FeedbackAbertoPergunta.query.get_or_404(pergunta_id)
    if pergunta.cliente_id != current_user.id:
        flash("Acesso negado.", "danger")
        return redirect(url_for("open_feedback_routes.feedback_aberto_perguntas"))

    OpenFeedbackService.desativar_pergunta(pergunta_id)
    flash("Pergunta removida.", "success")
    return redirect(url_for("open_feedback_routes.feedback_aberto_perguntas"))


@open_feedback_routes.route("/feedback-aberto/preencher/<token>", methods=["GET", "POST"])
def preencher_feedback_aberto(token: str):
    dia = FeedbackAbertoDia.query.filter_by(token=token).first()
    if not dia:
        return render_template("feedback_aberto/link_invalido.html")

    if not dia.ativa:
        return render_template("feedback_aberto/link_inativo.html", dia=dia)

    perguntas = OpenFeedbackService.carregar_perguntas_do_dia(dia)
    perguntas_contexto = [
        {"obj": pergunta, "opcoes": _parse_opcoes(pergunta)} for pergunta in perguntas
    ]

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip() or None
        email = (request.form.get("email") or "").strip() or None
        telefone = (request.form.get("telefone") or "").strip() or None
        identificador = (request.form.get("identificador") or "").strip() or None

        if dia.exigir_nome and not nome:
            flash("Informe o nome.", "warning")
            return render_template(
                "feedback_aberto/preencher.html",
                dia=dia,
                perguntas=perguntas_contexto,
            )
        if dia.exigir_email and not email:
            flash("Informe o email.", "warning")
            return render_template(
                "feedback_aberto/preencher.html",
                dia=dia,
                perguntas=perguntas_contexto,
            )
        if dia.exigir_telefone and not telefone:
            flash("Informe o telefone.", "warning")
            return render_template(
                "feedback_aberto/preencher.html",
                dia=dia,
                perguntas=perguntas_contexto,
            )
        if dia.exigir_identificador and not identificador:
            flash("Informe a matricula/ID.", "warning")
            return render_template(
                "feedback_aberto/preencher.html",
                dia=dia,
                perguntas=perguntas_contexto,
            )

        respostas = []
        erros = []
        for pergunta in perguntas:
            campo = f"q_{pergunta.id}"
            if pergunta.tipo == TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA_MULTIPLA:
                valores = request.form.getlist(campo)
                valor = _normalizar_selecao_multipla(valores)
            else:
                valor = request.form.get(campo)
            if pergunta.obrigatoria and not valor:
                erros.append(pergunta.titulo)
                continue

            if not valor:
                continue

            if pergunta.tipo == TipoPerguntaFeedbackAberto.ESCALA_NUMERICA:
                try:
                    valor_tratado = int(valor)
                except ValueError:
                    erros.append(pergunta.titulo)
                    continue
            elif pergunta.tipo == TipoPerguntaFeedbackAberto.NUMERO:
                try:
                    valor_tratado = int(valor)
                except ValueError:
                    erros.append(pergunta.titulo)
                    continue
            elif pergunta.tipo == TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA_MULTIPLA:
                valor_tratado = valor
            else:
                valor_tratado = valor.strip()

            respostas.append((pergunta, valor_tratado))

        if erros:
            flash("Responda os campos obrigatorios antes de enviar.", "warning")
            return render_template(
                "feedback_aberto/preencher.html",
                dia=dia,
                perguntas=perguntas_contexto,
            )

        envio = FeedbackAbertoEnvio(
            dia_id=dia.id,
            nome=nome,
            email=email,
            telefone=telefone,
            identificador=identificador,
            ip_origem=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(envio)
        db.session.flush()

        for pergunta, valor_tratado in respostas:
            resposta = FeedbackAbertoResposta(
                envio_id=envio.id,
                pergunta_id=pergunta.id,
            )
            if pergunta.tipo == TipoPerguntaFeedbackAberto.ESCALA_NUMERICA:
                resposta.resposta_numerica = valor_tratado
            elif pergunta.tipo in (
                TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
                TipoPerguntaFeedbackAberto.SIM_NAO,
            ):
                resposta.resposta_escolha = valor_tratado
            elif pergunta.tipo == TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA_MULTIPLA:
                resposta.resposta_texto = json.dumps(valor_tratado, ensure_ascii=True)
            elif pergunta.tipo == TipoPerguntaFeedbackAberto.NUMERO:
                resposta.resposta_numerica = valor_tratado
            else:
                resposta.resposta_texto = valor_tratado
            db.session.add(resposta)

        db.session.commit()
        return render_template("feedback_aberto/obrigado.html", dia=dia)

    return render_template(
        "feedback_aberto/preencher.html",
        dia=dia,
        perguntas=perguntas_contexto,
    )


@open_feedback_routes.route("/feedback-aberto/resultados")
@cliente_required
def feedback_aberto_resultados():
    data_inicio = request.args.get("inicio")
    data_fim = request.args.get("fim")
    dias = (
        FeedbackAbertoDia.query
        .filter_by(cliente_id=current_user.id)
    )
    if data_inicio:
        try:
            inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
            dias = dias.filter(FeedbackAbertoDia.data >= inicio)
        except ValueError:
            flash("Data inicial invalida.", "warning")
    if data_fim:
        try:
            fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
            dias = dias.filter(FeedbackAbertoDia.data <= fim)
        except ValueError:
            flash("Data final invalida.", "warning")
    dias = dias.order_by(FeedbackAbertoDia.data.desc()).all()
    return render_template("feedback_aberto/resultados.html", dias=dias)


@open_feedback_routes.route("/feedback-aberto/resultados/<int:dia_id>")
@cliente_required
def feedback_aberto_resultados_dia(dia_id: int):
    dia = FeedbackAbertoDia.query.get_or_404(dia_id)
    if dia.cliente_id != current_user.id:
        flash("Acesso negado.", "danger")
        return redirect(url_for("open_feedback_routes.feedback_aberto_resultados"))

    perguntas = OpenFeedbackService.carregar_perguntas_do_dia(dia)
    respostas = (
        FeedbackAbertoResposta.query
        .join(
            FeedbackAbertoEnvio,
            FeedbackAbertoResposta.envio_id == FeedbackAbertoEnvio.id,
        )
        .filter(FeedbackAbertoEnvio.dia_id == dia.id)
        .all()
    )

    mapa_respostas = {pergunta.id: [] for pergunta in perguntas}
    for resposta in respostas:
        if resposta.pergunta_id in mapa_respostas:
            mapa_respostas[resposta.pergunta_id].append(resposta)

    estatisticas = []
    for pergunta in perguntas:
        respostas_pergunta = mapa_respostas.get(pergunta.id, [])
        valores = []
        for resposta in respostas_pergunta:
            if resposta.resposta_numerica is not None:
                valores.append(resposta.resposta_numerica)
            elif resposta.resposta_escolha:
                valores.append(resposta.resposta_escolha)
            elif resposta.resposta_texto:
                if pergunta.tipo == TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA_MULTIPLA:
                    try:
                        valores.extend(json.loads(resposta.resposta_texto))
                    except (TypeError, json.JSONDecodeError):
                        valores.append(resposta.resposta_texto)
                else:
                    valores.append(resposta.resposta_texto)

        info = {
            "pergunta": pergunta,
            "tipo": pergunta.tipo,
            "total": len(respostas_pergunta),
            "valores": valores,
            "opcoes": _parse_opcoes(pergunta),
        }

        if pergunta.tipo == TipoPerguntaFeedbackAberto.ESCALA_NUMERICA and valores:
            info["media"] = sum(valores) / len(valores)
            info["min"] = min(valores)
            info["max"] = max(valores)

        if pergunta.tipo in (
            TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            TipoPerguntaFeedbackAberto.SIM_NAO,
            TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA_MULTIPLA,
        ):
            contagem = {}
            for valor in valores:
                contagem[valor] = contagem.get(valor, 0) + 1
            info["contagem"] = contagem

        estatisticas.append(info)

    total_envios = OpenFeedbackService.obter_resumo_dia(dia.id)
    return render_template(
        "feedback_aberto/resultados_dia.html",
        dia=dia,
        estatisticas=estatisticas,
        total_envios=total_envios,
    )


@open_feedback_routes.route(
    "/feedback-aberto/resultados/<int:dia_id>/exportar.csv"
)
@cliente_required
def exportar_feedback_aberto_csv(dia_id: int):
    dia = FeedbackAbertoDia.query.get_or_404(dia_id)
    if dia.cliente_id != current_user.id:
        flash("Acesso negado.", "danger")
        return redirect(url_for("open_feedback_routes.feedback_aberto_resultados"))

    perguntas = OpenFeedbackService.carregar_perguntas_do_dia(dia)
    pergunta_ids = [pergunta.id for pergunta in perguntas]
    respostas = (
        FeedbackAbertoResposta.query
        .join(
            FeedbackAbertoEnvio,
            FeedbackAbertoResposta.envio_id == FeedbackAbertoEnvio.id,
        )
        .filter(FeedbackAbertoEnvio.dia_id == dia.id)
        .filter(FeedbackAbertoResposta.pergunta_id.in_(pergunta_ids))
        .all()
    )

    mapa_perguntas = {pergunta.id: pergunta for pergunta in perguntas}
    mapa_envios = {}
    for resposta in respostas:
        envio = resposta.envio
        if envio.id not in mapa_envios:
            mapa_envios[envio.id] = {
                "envio": envio,
                "respostas": {},
            }
        mapa_envios[envio.id]["respostas"][resposta.pergunta_id] = resposta

    linhas = []
    cabecalho = [
        "data",
        "titulo",
        "envio_id",
        "criado_em",
        "nome",
        "email",
        "telefone",
        "identificador",
        "ip_origem",
    ]
    cabecalho.extend([pergunta.titulo for pergunta in perguntas])
    linhas.append(";".join(cabecalho))

    for envio_id, info in mapa_envios.items():
        envio = info["envio"]
        row = [
            dia.data.isoformat(),
            dia.titulo or "Feedback aberto",
            str(envio_id),
            envio.created_at.isoformat() if envio.created_at else "",
            envio.nome or "",
            envio.email or "",
            envio.telefone or "",
            envio.identificador or "",
            envio.ip_origem or "",
        ]
        for pergunta in perguntas:
            resposta = info["respostas"].get(pergunta.id)
            if not resposta:
                row.append("")
                continue
            if resposta.resposta_numerica is not None:
                row.append(str(resposta.resposta_numerica))
            elif resposta.resposta_escolha:
                row.append(resposta.resposta_escolha)
            elif resposta.resposta_texto:
                if pergunta.tipo == TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA_MULTIPLA:
                    try:
                        escolhas = json.loads(resposta.resposta_texto)
                        row.append(", ".join(escolhas))
                    except (TypeError, json.JSONDecodeError):
                        row.append(resposta.resposta_texto)
                else:
                    row.append(resposta.resposta_texto)
            else:
                row.append("")
        linhas.append(";".join(row))

    conteudo = "\n".join(linhas)
    nome_arquivo = f"feedback_aberto_{dia.data.isoformat()}.csv"
    return (
        conteudo,
        200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f"attachment; filename={nome_arquivo}",
        },
    )
