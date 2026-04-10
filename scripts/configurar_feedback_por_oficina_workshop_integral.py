#!/usr/bin/env python3
"""
Configura formularios no modulo /feedback-aberto para o Workshop.

O script cria/atualiza 5 formularios (um por sala), cada um com seu proprio link:
- Sala 1 - Profissionais
- Sala 2 - Profissionais
- Sala 3 - Profissionais
- Sala 4 - Profissionais
- Sala 5 - Tecnicos da SEMED

Importante: no feedback-aberto existe restricao unica por (cliente_id, data).
Para viabilizar 5 links no mesmo cliente sem mudar funcionalidade, cada formulario
usa uma data distinta (alocada automaticamente a partir de --start-date).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta

from flask import Flask


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import Config  # noqa: E402
from extensions import db  # noqa: E402
from models import (  # noqa: E402
    Cliente,
    Evento,
    Oficina,
    FeedbackAbertoPergunta,
    FeedbackAbertoDia,
    FeedbackAbertoDiaPergunta,
    TipoPerguntaFeedbackAberto,
)


WORKSHOP_NAME_HINT = "SENADOR RUI PALMEIRA"
SCALE_OPTIONS = ["Excelente", "Bom", "Regular", "Precisa melhorar"]


@dataclass(frozen=True)
class QuestionSpec:
    titulo: str
    tipo: TipoPerguntaFeedbackAberto
    obrigatoria: bool
    opcoes: list[str] | None = None
    descricao: str | None = None


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
        description="Configura formularios por sala no modulo /feedback-aberto."
    )
    parser.add_argument(
        "--client-email",
        default="iafap@appfiber.com",
        help="Email do cliente.",
    )
    parser.add_argument(
        "--event-hint",
        default=WORKSHOP_NAME_HINT,
        help="Trecho para localizar o evento.",
    )
    parser.add_argument(
        "--base-url",
        default="https://sistema-de-oficinas-aay2.onrender.com",
        help="URL base para compor os links no resumo final.",
    )
    parser.add_argument(
        "--start-date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Data inicial (YYYY-MM-DD) para alocacao dos 5 formularios.",
    )
    parser.add_argument(
        "--title-prefix",
        default="FORMULARIO DE AVALIACAO - Feedback | Workshop de Educacao Integral - Senador Rui Palmeira",
        help="Prefixo do titulo de cada formulario.",
    )
    return parser.parse_args()


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    no_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    lowered = no_marks.lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def find_event(cliente_id: int, hint: str) -> Evento:
    event = (
        Evento.query.filter(
            Evento.cliente_id == cliente_id,
            Evento.nome.ilike(f"%{hint}%"),
        )
        .order_by(Evento.data_inicio.desc().nullslast(), Evento.id.desc())
        .first()
    )
    if not event:
        raise RuntimeError(
            f"Nenhum evento encontrado para cliente_id={cliente_id} com hint '{hint}'."
        )
    return event


def map_target_rooms(evento_id: int) -> dict[int, Oficina]:
    rooms = (
        Oficina.query.filter(Oficina.evento_id == evento_id)
        .order_by(Oficina.id.asc())
        .all()
    )
    room_by_number: dict[int, Oficina] = {}

    for room in rooms:
        title_norm = normalize_text(room.titulo)
        sala_match = re.search(r"\bsala\s+([1-5])\b", title_norm)
        if not sala_match:
            continue
        number = int(sala_match.group(1))
        if number in room_by_number:
            continue
        if number == 5 and "semed" in title_norm:
            room_by_number[number] = room
        elif number in (1, 2, 3, 4) and "semed" not in title_norm:
            room_by_number[number] = room

    missing = [n for n in (1, 2, 3, 4, 5) if n not in room_by_number]
    if missing:
        available = ", ".join(f"{r.id}:{r.titulo}" for r in rooms) or "(nenhuma)"
        raise RuntimeError(
            f"Nao foi possivel mapear as salas {missing}. Oficinas encontradas: {available}"
        )
    return room_by_number


def build_common_questions() -> list[QuestionSpec]:
    return [
        QuestionSpec(
            titulo="Segmento de participacao",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=["Profissionais da rede", "Equipe tecnica da SEMED"],
        ),
        QuestionSpec(
            titulo="Funcao",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=[
                "Professor(a)",
                "Coordenador(a)",
                "Gestor(a)",
                "Tecnico da SEMED",
                "Outro",
            ],
        ),
        QuestionSpec(
            titulo="Escola / Setor",
            tipo=TipoPerguntaFeedbackAberto.TEXTO_LIVRE,
            obrigatoria=True,
            descricao="Campo de texto curto.",
        ),
    ]


def build_professional_block() -> list[QuestionSpec]:
    return [
        QuestionSpec(
            titulo="Eixo 1: Cuidado e Saude Mental",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Eixo 2: Protecao Integral e Praticas Protetivas",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Eixo 3: Curriculo, Planejamento e Organizacao da Educacao Integral",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Eixo 4: Sustentabilidade, Territorio e ODS",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
    ]


def build_semed_block() -> list[QuestionSpec]:
    return [
        QuestionSpec(
            titulo="Base legal e diretrizes da Educacao Integral",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Curriculo, planejamento e organizacao da politica",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Cuidado, permanencia e equidade",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Protecao integral e praticas protetivas",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Territorio, intersetorialidade e ODS",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Construcao de metas e plano de implementacao",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Consolidacao e validacao do plano",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
    ]


def build_formadores_block() -> list[QuestionSpec]:
    # Todos NAO obrigatorios conforme solicitado.
    names = [
        "Ana Clara",
        "Marcio Ferraz",
        "Thiago Hilario",
        "Donizete",
        "Paula",
        "Yasmine",
        "Erivaldo",
        "Francisco",
    ]
    return [
        QuestionSpec(
            titulo=f"Formador(a): {name}",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=False,
            opcoes=SCALE_OPTIONS,
            descricao="Opcional. Avalie apenas quem atuou na sua sala.",
        )
        for name in names
    ]


def build_general_block() -> list[QuestionSpec]:
    return [
        QuestionSpec(
            titulo="Organizacao geral do evento",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Distribuicao das salas e turmas",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Tempo das atividades",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Clareza da programacao",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Organizacao do almoco",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Ambiente e acolhimento durante o almoco",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Qualidade da alimentacao",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Tempo destinado ao almoco",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Recepcao dos participantes",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="Clima do evento (acolhimento, respeito e interacao)",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=SCALE_OPTIONS,
        ),
        QuestionSpec(
            titulo="O workshop contribuiu para melhorar sua pratica profissional?",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=["Muito", "Sim", "Pouco", "Nao contribuiu"],
        ),
        QuestionSpec(
            titulo="Voce se sente preparado(a) para aplicar o que aprendeu?",
            tipo=TipoPerguntaFeedbackAberto.MULTIPLA_ESCOLHA,
            obrigatoria=True,
            opcoes=["Sim", "Parcialmente", "Nao"],
        ),
        QuestionSpec(
            titulo="Principal aprendizado do workshop",
            tipo=TipoPerguntaFeedbackAberto.TEXTO_LIVRE,
            obrigatoria=True,
        ),
        QuestionSpec(
            titulo="Principal desafio identificado na sua realidade",
            tipo=TipoPerguntaFeedbackAberto.TEXTO_LIVRE,
            obrigatoria=True,
        ),
        QuestionSpec(
            titulo="Uma acao que voce pretende implementar na sua escola ou setor",
            tipo=TipoPerguntaFeedbackAberto.TEXTO_LIVRE,
            obrigatoria=True,
        ),
    ]


def build_extra_open_semed() -> QuestionSpec:
    return QuestionSpec(
        titulo="Qual encaminhamento considera prioritario para a implementacao da politica na rede?",
        tipo=TipoPerguntaFeedbackAberto.TEXTO_LIVRE,
        obrigatoria=True,
    )


def build_form_questions(is_semed_room: bool) -> list[QuestionSpec]:
    base = build_common_questions()
    bloco_especifico = build_semed_block() if is_semed_room else build_professional_block()
    formadores = build_formadores_block()
    gerais = build_general_block()
    questions = base + bloco_especifico + formadores + gerais
    if is_semed_room:
        questions.append(build_extra_open_semed())
    return questions


def upsert_question(cliente_id: int, spec: QuestionSpec, ordem_global: int) -> FeedbackAbertoPergunta:
    pergunta = FeedbackAbertoPergunta.query.filter_by(
        cliente_id=cliente_id,
        titulo=spec.titulo,
    ).first()

    if not pergunta:
        pergunta = FeedbackAbertoPergunta(
            cliente_id=cliente_id,
            titulo=spec.titulo,
        )
        db.session.add(pergunta)

    pergunta.descricao = spec.descricao
    pergunta.tipo = spec.tipo
    pergunta.opcoes = json.dumps(spec.opcoes or [], ensure_ascii=False)
    pergunta.obrigatoria = spec.obrigatoria
    pergunta.ordem = ordem_global
    pergunta.ativa = True
    return pergunta


def ensure_day(
    *,
    cliente_id: int,
    titulo: str,
    target_date,
    used_dates: set,
) -> FeedbackAbertoDia:
    # Reaproveita dia existente pelo titulo (idempotencia).
    dia = FeedbackAbertoDia.query.filter_by(cliente_id=cliente_id, titulo=titulo).first()
    if dia:
        dia.ativa = True
        dia.exigir_nome = False
        dia.exigir_email = False
        dia.exigir_telefone = False
        dia.exigir_identificador = False
        used_dates.add(dia.data)
        return dia

    # Se nao existe por titulo, precisa achar uma data livre para inserir.
    candidate = target_date
    while candidate in used_dates:
        candidate += timedelta(days=1)

    dia = FeedbackAbertoDia.query.filter_by(cliente_id=cliente_id, data=candidate).first()
    while dia is not None:
        used_dates.add(candidate)
        candidate += timedelta(days=1)
        while candidate in used_dates:
            candidate += timedelta(days=1)
        dia = FeedbackAbertoDia.query.filter_by(cliente_id=cliente_id, data=candidate).first()

    novo_dia = FeedbackAbertoDia(
        cliente_id=cliente_id,
        data=candidate,
        titulo=titulo,
        token=os.urandom(24).hex(),
        ativa=True,
        exigir_nome=False,
        exigir_email=False,
        exigir_telefone=False,
        exigir_identificador=False,
    )
    db.session.add(novo_dia)
    used_dates.add(candidate)
    return novo_dia


def replace_day_questions(dia_id: int, pergunta_ids_in_order: list[int]) -> None:
    FeedbackAbertoDiaPergunta.query.filter_by(dia_id=dia_id).delete()
    for idx, pergunta_id in enumerate(pergunta_ids_in_order, start=1):
        db.session.add(
            FeedbackAbertoDiaPergunta(
                dia_id=dia_id,
                pergunta_id=pergunta_id,
                ordem=idx,
            )
        )


def main() -> int:
    args = parse_args()
    app = build_app()

    with app.app_context():
        cliente = Cliente.query.filter(Cliente.email.ilike(args.client_email)).first()
        if not cliente:
            raise SystemExit(f"Cliente nao encontrado: {args.client_email}")

        evento = find_event(cliente.id, args.event_hint)
        room_map = map_target_rooms(evento.id)

        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()

        # Banco de perguntas (global por cliente).
        all_specs_unique: list[QuestionSpec] = []
        seen_titles: set[str] = set()
        for is_semed in (False, True):
            for spec in build_form_questions(is_semed):
                key = normalize_text(spec.titulo)
                if key in seen_titles:
                    continue
                seen_titles.add(key)
                all_specs_unique.append(spec)

        perguntas_by_title_key: dict[str, FeedbackAbertoPergunta] = {}
        for ordem_global, spec in enumerate(all_specs_unique, start=1):
            pergunta = upsert_question(cliente.id, spec, ordem_global)
            perguntas_by_title_key[normalize_text(spec.titulo)] = pergunta
        db.session.flush()

        existing_days = FeedbackAbertoDia.query.filter_by(cliente_id=cliente.id).all()
        used_dates = {d.data for d in existing_days}

        results: list[dict] = []
        for idx, room_number in enumerate((1, 2, 3, 4, 5)):
            room = room_map[room_number]
            is_semed = room_number == 5
            specs = build_form_questions(is_semed)
            titulo_form = f"{args.title_prefix} | Sala {room_number} - {room.titulo}"
            target_date = start_date + timedelta(days=idx)

            dia = ensure_day(
                cliente_id=cliente.id,
                titulo=titulo_form,
                target_date=target_date,
                used_dates=used_dates,
            )
            db.session.flush()

            pergunta_ids: list[int] = []
            for spec in specs:
                key = normalize_text(spec.titulo)
                pergunta = perguntas_by_title_key[key]
                pergunta_ids.append(pergunta.id)

            replace_day_questions(dia.id, pergunta_ids)

            results.append(
                {
                    "room_number": room_number,
                    "room_title": room.titulo,
                    "dia_id": dia.id,
                    "data": dia.data.isoformat(),
                    "titulo_form": dia.titulo,
                    "token": dia.token,
                    "questions_count": len(pergunta_ids),
                    "is_semed": is_semed,
                }
            )

        db.session.commit()

        base = args.base_url.rstrip("/")
        print(f"Cliente: {cliente.email} (id={cliente.id})")
        print(f"Evento: {evento.nome} (id={evento.id})")
        print(f"Formularios no feedback-aberto: {len(results)}")
        print("")
        print("Formularios gerados/atualizados:")
        for item in results:
            tipo = "SEMED" if item["is_semed"] else "Profissionais"
            print(
                f"- Sala {item['room_number']} ({tipo}) | dia_id={item['dia_id']} | "
                f"data={item['data']} | perguntas={item['questions_count']}"
            )
            print(f"  Titulo: {item['titulo_form']}")
            print(f"  Link: {base}/feedback-aberto/preencher/{item['token']}")

        print("")
        print("Observacao tecnica:")
        print(
            "- O feedback-aberto permite apenas 1 formulario por data por cliente; "
            "por isso o script aloca datas diferentes automaticamente."
        )
        print(
            "- Formadores foram configurados como nao obrigatorios em todas as salas."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

