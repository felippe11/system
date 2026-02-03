"""Servico para o sistema de feedback aberto diario (isolado)."""

from __future__ import annotations

from datetime import date
from uuid import uuid4
import json

from sqlalchemy import func

from extensions import db
from models import (
    FeedbackAbertoPergunta,
    FeedbackAbertoDia,
    FeedbackAbertoDiaPergunta,
    FeedbackAbertoEnvio,
    FeedbackAbertoResposta,
    TipoPerguntaFeedbackAberto,
)


class OpenFeedbackService:
    """Operacoes do feedback aberto diario."""

    @staticmethod
    def listar_perguntas(cliente_id: int):
        return (
            FeedbackAbertoPergunta.query
            .filter_by(cliente_id=cliente_id, ativa=True)
            .order_by(FeedbackAbertoPergunta.ordem.asc(), FeedbackAbertoPergunta.id.asc())
            .all()
        )

    @staticmethod
    def criar_pergunta(
        *,
        cliente_id: int,
        titulo: str,
        descricao: str | None,
        tipo: str,
        opcoes: list[str] | None,
        obrigatoria: bool,
        ordem: int,
    ) -> FeedbackAbertoPergunta:
        pergunta = FeedbackAbertoPergunta(
            cliente_id=cliente_id,
            titulo=titulo.strip(),
            descricao=(descricao or "").strip() or None,
            tipo=TipoPerguntaFeedbackAberto(tipo),
            opcoes=json.dumps(opcoes or [], ensure_ascii=True),
            obrigatoria=bool(obrigatoria),
            ordem=ordem,
        )
        db.session.add(pergunta)
        db.session.commit()
        return pergunta

    @staticmethod
    def atualizar_pergunta(pergunta_id: int, **dados) -> FeedbackAbertoPergunta:
        pergunta = FeedbackAbertoPergunta.query.get_or_404(pergunta_id)
        if "titulo" in dados and dados["titulo"]:
            pergunta.titulo = dados["titulo"].strip()
        if "descricao" in dados:
            pergunta.descricao = (dados["descricao"] or "").strip() or None
        if "tipo" in dados and dados["tipo"]:
            pergunta.tipo = TipoPerguntaFeedbackAberto(dados["tipo"])
        if "opcoes" in dados:
            pergunta.opcoes = json.dumps(dados["opcoes"] or [], ensure_ascii=True)
        if "obrigatoria" in dados:
            pergunta.obrigatoria = bool(dados["obrigatoria"])
        if "ordem" in dados and dados["ordem"] is not None:
            pergunta.ordem = int(dados["ordem"])
        db.session.commit()
        return pergunta

    @staticmethod
    def desativar_pergunta(pergunta_id: int) -> None:
        pergunta = FeedbackAbertoPergunta.query.get_or_404(pergunta_id)
        pergunta.ativa = False
        db.session.commit()

    @staticmethod
    def criar_dia(
        *,
        cliente_id: int,
        data: date,
        titulo: str | None,
        pergunta_ids: list[int] | None,
        exigir_nome: bool = False,
        exigir_email: bool = False,
        exigir_telefone: bool = False,
        exigir_identificador: bool = False,
    ) -> FeedbackAbertoDia:
        existente = FeedbackAbertoDia.query.filter_by(
            cliente_id=cliente_id, data=data
        ).first()
        if existente:
            raise ValueError("Ja existe um feedback aberto para esta data.")

        dia = FeedbackAbertoDia(
            cliente_id=cliente_id,
            data=data,
            titulo=(titulo or "").strip() or None,
            token=uuid4().hex,
            ativa=True,
            exigir_nome=exigir_nome,
            exigir_email=exigir_email,
            exigir_telefone=exigir_telefone,
            exigir_identificador=exigir_identificador,
        )
        db.session.add(dia)
        db.session.flush()

        perguntas = FeedbackAbertoPergunta.query.filter(
            FeedbackAbertoPergunta.cliente_id == cliente_id,
            FeedbackAbertoPergunta.ativa.is_(True),
        )
        if pergunta_ids:
            perguntas = perguntas.filter(FeedbackAbertoPergunta.id.in_(pergunta_ids))
        perguntas = perguntas.order_by(
            FeedbackAbertoPergunta.ordem.asc(), FeedbackAbertoPergunta.id.asc()
        ).all()

        for idx, pergunta in enumerate(perguntas):
            db.session.add(
                FeedbackAbertoDiaPergunta(
                    dia_id=dia.id,
                    pergunta_id=pergunta.id,
                    ordem=idx,
                )
            )

        db.session.commit()
        return dia

    @staticmethod
    def carregar_perguntas_do_dia(dia: FeedbackAbertoDia):
        if dia.perguntas:
            return [
                vinculo.pergunta
                for vinculo in sorted(dia.perguntas, key=lambda item: item.ordem)
                if vinculo.pergunta and vinculo.pergunta.ativa
            ]
        return OpenFeedbackService.listar_perguntas(dia.cliente_id)

    @staticmethod
    def registrar_envio(
        dia: FeedbackAbertoDia,
        respostas: dict[int, str | int | None],
        ip: str | None,
        user_agent: str | None,
    ):
        envio = FeedbackAbertoEnvio(dia_id=dia.id, ip_origem=ip, user_agent=user_agent)
        db.session.add(envio)
        db.session.flush()

        for pergunta_id, valor in respostas.items():
            resposta = FeedbackAbertoResposta(envio_id=envio.id, pergunta_id=pergunta_id)
            if isinstance(valor, int):
                resposta.resposta_numerica = valor
            elif valor is not None:
                resposta.resposta_texto = str(valor)
            db.session.add(resposta)

        db.session.commit()
        return envio

    @staticmethod
    def atualizar_dia(
        dia_id: int,
        *,
        data: date | None,
        titulo: str | None,
        pergunta_ids: list[int] | None,
        exigir_nome: bool,
        exigir_email: bool,
        exigir_telefone: bool,
        exigir_identificador: bool,
    ) -> FeedbackAbertoDia:
        dia = FeedbackAbertoDia.query.get_or_404(dia_id)
        if data and data != dia.data:
            existente = FeedbackAbertoDia.query.filter_by(
                cliente_id=dia.cliente_id, data=data
            ).first()
            if existente and existente.id != dia.id:
                raise ValueError("Ja existe um feedback aberto para esta data.")
            dia.data = data

        dia.titulo = (titulo or "").strip() or None
        dia.exigir_nome = bool(exigir_nome)
        dia.exigir_email = bool(exigir_email)
        dia.exigir_telefone = bool(exigir_telefone)
        dia.exigir_identificador = bool(exigir_identificador)

        perguntas = FeedbackAbertoPergunta.query.filter(
            FeedbackAbertoPergunta.cliente_id == dia.cliente_id,
            FeedbackAbertoPergunta.ativa.is_(True),
        )
        if pergunta_ids:
            perguntas = perguntas.filter(FeedbackAbertoPergunta.id.in_(pergunta_ids))
        perguntas = perguntas.order_by(
            FeedbackAbertoPergunta.ordem.asc(), FeedbackAbertoPergunta.id.asc()
        ).all()

        dia.perguntas.clear()
        db.session.flush()

        for idx, pergunta in enumerate(perguntas):
            db.session.add(
                FeedbackAbertoDiaPergunta(
                    dia_id=dia.id,
                    pergunta_id=pergunta.id,
                    ordem=idx,
                )
            )

        db.session.commit()
        return dia

    @staticmethod
    def obter_resumo_dia(dia_id: int):
        total_envios = (
            db.session.query(func.count(FeedbackAbertoEnvio.id))
            .filter(FeedbackAbertoEnvio.dia_id == dia_id)
            .scalar()
        )
        return total_envios or 0
