#!/usr/bin/env python3
"""
Configura o formulario de feedback aberto do workshop para um cliente.

Cria/atualiza:
- perguntas do formulario;
- dia/token de feedback aberto;
- vinculos das perguntas no dia.

Uso tipico:
python scripts/configurar_feedback_aberto_workshop_integral.py --client-email iafap@appfiber.com --date 2026-04-10
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from flask import Flask


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import Config  # noqa: E402
from extensions import db  # noqa: E402
from models import (  # noqa: E402
    Cliente,
    FeedbackAbertoDia,
    FeedbackAbertoDiaPergunta,
    FeedbackAbertoPergunta,
    TipoPerguntaFeedbackAberto,
)


SCALE_OPTIONS = ["Excelente", "Bom", "Regular", "Precisa melhorar"]


@dataclass(frozen=True)
class QuestionSpec:
    ordem: int
    titulo: str
    tipo: str
    obrigatoria: bool
    opcoes: list[str] | None = None
    descricao: str | None = None


QUESTION_SPECS = [
    QuestionSpec(
        ordem=1,
        titulo="Segmento de participacao",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=["Profissionais da rede", "Equipe tecnica da SEMED"],
    ),
    QuestionSpec(
        ordem=2,
        titulo="Funcao",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=["Professor(a)", "Coordenador(a)", "Gestor(a)", "Tecnico da SEMED", "Outro"],
    ),
    QuestionSpec(
        ordem=3,
        titulo="Escola / Setor",
        tipo="email",
        obrigatoria=True,
    ),
    QuestionSpec(
        ordem=4,
        titulo="Eixo 1: Cuidado e Saude Mental",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Profissionais da rede'.",
    ),
    QuestionSpec(
        ordem=5,
        titulo="Eixo 2: Protecao Integral e Praticas Protetivas",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Profissionais da rede'.",
    ),
    QuestionSpec(
        ordem=6,
        titulo="Eixo 3: Curriculo, Planejamento e Organizacao da Educacao Integral",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Profissionais da rede'.",
    ),
    QuestionSpec(
        ordem=7,
        titulo="Eixo 4: Sustentabilidade, Territorio e ODS",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Profissionais da rede'.",
    ),
    QuestionSpec(
        ordem=8,
        titulo="Base legal e diretrizes da Educacao Integral",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Equipe tecnica da SEMED'.",
    ),
    QuestionSpec(
        ordem=9,
        titulo="Curriculo, planejamento e organizacao da politica",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Equipe tecnica da SEMED'.",
    ),
    QuestionSpec(
        ordem=10,
        titulo="Cuidado, permanencia e equidade",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Equipe tecnica da SEMED'.",
    ),
    QuestionSpec(
        ordem=11,
        titulo="Protecao integral e praticas protetivas (trilha tecnica)",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Equipe tecnica da SEMED'.",
    ),
    QuestionSpec(
        ordem=12,
        titulo="Territorio, intersetorialidade e ODS",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Equipe tecnica da SEMED'.",
    ),
    QuestionSpec(
        ordem=13,
        titulo="Construcao de metas e plano de implementacao",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Equipe tecnica da SEMED'.",
    ),
    QuestionSpec(
        ordem=14,
        titulo="Consolidacao e validacao do plano",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Equipe tecnica da SEMED'.",
    ),
    QuestionSpec(
        ordem=15,
        titulo="Ana Clara (formadora)",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Profissionais da rede'.",
    ),
    QuestionSpec(
        ordem=16,
        titulo="Marcio Ferraz (formador)",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Profissionais da rede'.",
    ),
    QuestionSpec(
        ordem=17,
        titulo="Thiago Hilario (formador)",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Profissionais da rede'.",
    ),
    QuestionSpec(
        ordem=18,
        titulo="Donizete (formador)",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Profissionais da rede'.",
    ),
    QuestionSpec(
        ordem=19,
        titulo="Paula (formadora)",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Profissionais da rede'.",
    ),
    QuestionSpec(
        ordem=20,
        titulo="Yasmine (formadora)",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Profissionais da rede'.",
    ),
    QuestionSpec(
        ordem=21,
        titulo="Erivaldo (formador)",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Equipe tecnica da SEMED'.",
    ),
    QuestionSpec(
        ordem=22,
        titulo="Francisco (formador)",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Responder apenas para 'Equipe tecnica da SEMED'.",
    ),
    QuestionSpec(
        ordem=23,
        titulo="Organizacao geral do evento",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionSpec(
        ordem=24,
        titulo="Distribuicao das salas e turmas",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionSpec(
        ordem=25,
        titulo="Tempo das atividades",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionSpec(
        ordem=26,
        titulo="Clareza da programacao",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionSpec(
        ordem=27,
        titulo="Organizacao do almoco",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionSpec(
        ordem=28,
        titulo="Ambiente e acolhimento durante o almoco",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionSpec(
        ordem=29,
        titulo="Qualidade da alimentacao",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionSpec(
        ordem=30,
        titulo="Tempo destinado ao almoco",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionSpec(
        ordem=31,
        titulo="Recepcao dos participantes",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionSpec(
        ordem=32,
        titulo="Clima do evento (acolhimento, respeito e interacao)",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionSpec(
        ordem=33,
        titulo="O workshop contribuiu para melhorar sua pratica profissional?",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=["Muito", "Sim", "Pouco", "Nao contribuiu"],
    ),
    QuestionSpec(
        ordem=34,
        titulo="Voce se sente preparado(a) para aplicar o que aprendeu?",
        tipo="multipla_escolha",
        obrigatoria=True,
        opcoes=["Sim", "Parcialmente", "Nao"],
    ),
    QuestionSpec(
        ordem=35,
        titulo="Principal aprendizado do workshop",
        tipo="texto_livre",
        obrigatoria=True,
    ),
    QuestionSpec(
        ordem=36,
        titulo="Principal desafio identificado na sua realidade",
        tipo="texto_livre",
        obrigatoria=True,
    ),
    QuestionSpec(
        ordem=37,
        titulo="Uma acao que voce pretende implementar na sua escola ou setor",
        tipo="texto_livre",
        obrigatoria=True,
    ),
    QuestionSpec(
        ordem=38,
        titulo="Qual encaminhamento considera prioritario para a implementacao da politica na rede?",
        tipo="texto_livre",
        obrigatoria=True,
        descricao="Responder apenas para 'Equipe tecnica da SEMED'.",
    ),
]


def build_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["SQLALCHEMY_DATABASE_URI"] = Config.normalize_pg(
        app.config["SQLALCHEMY_DATABASE_URI"]
    )
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = Config.build_engine_options(
        app.config["SQLALCHEMY_DATABASE_URI"]
    )
    db.init_app(app)
    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Configura o feedback aberto do workshop para um cliente."
    )
    parser.add_argument(
        "--client-email",
        default="iafap@appfiber.com",
        help="E-mail do cliente.",
    )
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Data do feedback no formato YYYY-MM-DD.",
    )
    parser.add_argument(
        "--title",
        default="FORMULARIO DE AVALIACAO - Feedback | Workshop de Educacao Integral - Senador Rui Palmeira",
        help="Titulo do formulario do dia.",
    )
    parser.add_argument(
        "--base-url",
        default="https://sistema-de-oficinas-aay2.onrender.com",
        help="URL base para imprimir o link final.",
    )
    return parser.parse_args()


def upsert_question(cliente_id: int, spec: QuestionSpec) -> FeedbackAbertoPergunta:
    pergunta = FeedbackAbertoPergunta.query.filter_by(
        cliente_id=cliente_id,
        titulo=spec.titulo,
    ).first()

    if pergunta is None:
        pergunta = FeedbackAbertoPergunta(cliente_id=cliente_id, titulo=spec.titulo)
        db.session.add(pergunta)

    pergunta.descricao = spec.descricao
    pergunta.tipo = TipoPerguntaFeedbackAberto(spec.tipo)
    pergunta.opcoes = json.dumps(spec.opcoes or [], ensure_ascii=False)
    pergunta.obrigatoria = spec.obrigatoria
    pergunta.ordem = spec.ordem
    pergunta.ativa = True
    return pergunta


def ensure_day(cliente_id: int, date_str: str, title: str) -> FeedbackAbertoDia:
    feedback_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    dia = FeedbackAbertoDia.query.filter_by(
        cliente_id=cliente_id,
        data=feedback_date,
    ).first()

    if dia is None:
        dia = FeedbackAbertoDia(
            cliente_id=cliente_id,
            data=feedback_date,
            token=uuid4().hex,
            ativa=True,
        )
        db.session.add(dia)

    dia.titulo = title
    dia.ativa = True
    dia.exigir_nome = False
    dia.exigir_email = False
    dia.exigir_telefone = False
    dia.exigir_identificador = False
    return dia


def replace_day_questions(dia: FeedbackAbertoDia, perguntas: list[FeedbackAbertoPergunta]) -> None:
    FeedbackAbertoDiaPergunta.query.filter_by(dia_id=dia.id).delete()
    for idx, pergunta in enumerate(sorted(perguntas, key=lambda p: p.ordem)):
        db.session.add(
            FeedbackAbertoDiaPergunta(
                dia_id=dia.id,
                pergunta_id=pergunta.id,
                ordem=idx,
            )
        )


def main() -> int:
    args = parse_args()
    app = build_app()

    with app.app_context():
        cliente = Cliente.query.filter(
            Cliente.email.ilike(args.client_email)
        ).first()
        if cliente is None:
            raise SystemExit(
                f"Cliente nao encontrado para o email: {args.client_email}"
            )

        perguntas = [upsert_question(cliente.id, spec) for spec in QUESTION_SPECS]
        db.session.flush()

        dia = ensure_day(cliente.id, args.date, args.title)
        db.session.flush()
        replace_day_questions(dia, perguntas)
        db.session.commit()

        base = args.base_url.rstrip("/")
        link = f"{base}/feedback-aberto/preencher/{dia.token}"

        print(f"Cliente: {cliente.email} (id={cliente.id})")
        print(f"Perguntas garantidas: {len(perguntas)}")
        print(f"Dia configurado: {dia.data.isoformat()} (id={dia.id})")
        print(f"Link publico: {link}")
        print(
            "Observacao: exibicao condicional por segmento nao e nativa no modulo atual; "
            "as perguntas condicionais foram marcadas na descricao."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
