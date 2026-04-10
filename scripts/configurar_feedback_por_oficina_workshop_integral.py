#!/usr/bin/env python3
"""
Configura feedback por oficina para o Workshop de Educacao Integral.

Objetivo:
- um link publico por oficina (rota /feedback/responder/oficina/<id>);
- 4 salas de profissionais com bloco de eixos formativos;
- 1 sala da SEMED com bloco da trilha tecnica;
- perguntas de formadores repetidas em todas as salas e NAO obrigatorias.

Uso:
python scripts/configurar_feedback_por_oficina_workshop_integral.py \
  --client-email iafap@appfiber.com \
  --event-hint "SENADOR RUI PALMEIRA"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass

from flask import Flask


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import Config  # noqa: E402
from extensions import db  # noqa: E402
from models import Cliente, Evento, Oficina, PerguntaFeedback, TipoPergunta  # noqa: E402


WORKSHOP_NAME_HINT = "SENADOR RUI PALMEIRA"
SCALE_OPTIONS = ["Excelente", "Bom", "Regular", "Precisa melhorar"]


@dataclass(frozen=True)
class QuestionTemplate:
    titulo: str
    tipo: TipoPergunta
    obrigatoria: bool
    opcoes: list[str] | None = None
    descricao: str | None = None


@dataclass(frozen=True)
class QuestionSpec:
    ordem: int
    titulo: str
    tipo: TipoPergunta
    obrigatoria: bool
    opcoes: list[str] | None = None
    descricao: str | None = None


IDENTIFICACAO = [
    QuestionTemplate(
        titulo="Segmento de participacao",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=["Profissionais da rede", "Equipe tecnica da SEMED"],
    ),
    QuestionTemplate(
        titulo="Funcao",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=["Professor(a)", "Coordenador(a)", "Gestor(a)", "Tecnico da SEMED", "Outro"],
    ),
    QuestionTemplate(
        titulo="Escola / Setor",
        tipo=TipoPergunta.TEXTO_LIVRE,
        obrigatoria=True,
        descricao="Campo de texto curto.",
    ),
]

EIXOS_PROFISSIONAIS = [
    QuestionTemplate(
        titulo="Eixo 1: Cuidado e Saude Mental",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Bloco para participantes de Profissionais da rede.",
    ),
    QuestionTemplate(
        titulo="Eixo 2: Protecao Integral e Praticas Protetivas",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Bloco para participantes de Profissionais da rede.",
    ),
    QuestionTemplate(
        titulo="Eixo 3: Curriculo, Planejamento e Organizacao da Educacao Integral",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Bloco para participantes de Profissionais da rede.",
    ),
    QuestionTemplate(
        titulo="Eixo 4: Sustentabilidade, Territorio e ODS",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Bloco para participantes de Profissionais da rede.",
    ),
]

TRILHA_SEMED = [
    QuestionTemplate(
        titulo="Base legal e diretrizes da Educacao Integral",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Bloco para participantes da Equipe tecnica da SEMED.",
    ),
    QuestionTemplate(
        titulo="Curriculo, planejamento e organizacao da politica",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Bloco para participantes da Equipe tecnica da SEMED.",
    ),
    QuestionTemplate(
        titulo="Cuidado, permanencia e equidade",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Bloco para participantes da Equipe tecnica da SEMED.",
    ),
    QuestionTemplate(
        titulo="Protecao integral e praticas protetivas",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Bloco para participantes da Equipe tecnica da SEMED.",
    ),
    QuestionTemplate(
        titulo="Territorio, intersetorialidade e ODS",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Bloco para participantes da Equipe tecnica da SEMED.",
    ),
    QuestionTemplate(
        titulo="Construcao de metas e plano de implementacao",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Bloco para participantes da Equipe tecnica da SEMED.",
    ),
    QuestionTemplate(
        titulo="Consolidacao e validacao do plano",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
        descricao="Bloco para participantes da Equipe tecnica da SEMED.",
    ),
]

FORMADORES_TODAS_SALAS = [
    QuestionTemplate(
        titulo="Formador(a): Ana Clara",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=False,
        opcoes=SCALE_OPTIONS,
        descricao="Opcional. Avalie apenas quem atuou na sua sala.",
    ),
    QuestionTemplate(
        titulo="Formador(a): Marcio Ferraz",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=False,
        opcoes=SCALE_OPTIONS,
        descricao="Opcional. Avalie apenas quem atuou na sua sala.",
    ),
    QuestionTemplate(
        titulo="Formador(a): Thiago Hilario",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=False,
        opcoes=SCALE_OPTIONS,
        descricao="Opcional. Avalie apenas quem atuou na sua sala.",
    ),
    QuestionTemplate(
        titulo="Formador(a): Donizete",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=False,
        opcoes=SCALE_OPTIONS,
        descricao="Opcional. Avalie apenas quem atuou na sua sala.",
    ),
    QuestionTemplate(
        titulo="Formador(a): Paula",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=False,
        opcoes=SCALE_OPTIONS,
        descricao="Opcional. Avalie apenas quem atuou na sua sala.",
    ),
    QuestionTemplate(
        titulo="Formador(a): Yasmine",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=False,
        opcoes=SCALE_OPTIONS,
        descricao="Opcional. Avalie apenas quem atuou na sua sala.",
    ),
    QuestionTemplate(
        titulo="Formador(a): Erivaldo",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=False,
        opcoes=SCALE_OPTIONS,
        descricao="Opcional. Avalie apenas quem atuou na sua sala.",
    ),
    QuestionTemplate(
        titulo="Formador(a): Francisco",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=False,
        opcoes=SCALE_OPTIONS,
        descricao="Opcional. Avalie apenas quem atuou na sua sala.",
    ),
]

BLOCOS_GERAIS = [
    QuestionTemplate(
        titulo="Organizacao geral do evento",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionTemplate(
        titulo="Distribuicao das salas e turmas",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionTemplate(
        titulo="Tempo das atividades",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionTemplate(
        titulo="Clareza da programacao",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionTemplate(
        titulo="Organizacao do almoco",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionTemplate(
        titulo="Ambiente e acolhimento durante o almoco",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionTemplate(
        titulo="Qualidade da alimentacao",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionTemplate(
        titulo="Tempo destinado ao almoco",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionTemplate(
        titulo="Recepcao dos participantes",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionTemplate(
        titulo="Clima do evento (acolhimento, respeito e interacao)",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=SCALE_OPTIONS,
    ),
    QuestionTemplate(
        titulo="O workshop contribuiu para melhorar sua pratica profissional?",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=["Muito", "Sim", "Pouco", "Nao contribuiu"],
    ),
    QuestionTemplate(
        titulo="Voce se sente preparado(a) para aplicar o que aprendeu?",
        tipo=TipoPergunta.MULTIPLA_ESCOLHA,
        obrigatoria=True,
        opcoes=["Sim", "Parcialmente", "Nao"],
    ),
    QuestionTemplate(
        titulo="Principal aprendizado do workshop",
        tipo=TipoPergunta.TEXTO_LIVRE,
        obrigatoria=True,
    ),
    QuestionTemplate(
        titulo="Principal desafio identificado na sua realidade",
        tipo=TipoPergunta.TEXTO_LIVRE,
        obrigatoria=True,
    ),
    QuestionTemplate(
        titulo="Uma acao que voce pretende implementar na sua escola ou setor",
        tipo=TipoPergunta.TEXTO_LIVRE,
        obrigatoria=True,
    ),
]

ABERTA_EXTRA_SEMED = QuestionTemplate(
    titulo="Qual encaminhamento considera prioritario para a implementacao da politica na rede?",
    tipo=TipoPergunta.TEXTO_LIVRE,
    obrigatoria=True,
    descricao="Pergunta adicional para Equipe tecnica da SEMED.",
)


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
        description="Configura feedback por oficina do Workshop de Educacao Integral."
    )
    parser.add_argument(
        "--client-email",
        default="iafap@appfiber.com",
        help="Email do cliente dono do evento.",
    )
    parser.add_argument(
        "--event-hint",
        default=WORKSHOP_NAME_HINT,
        help="Trecho do nome do evento para localizacao.",
    )
    parser.add_argument(
        "--base-url",
        default="https://sistema-de-oficinas-aay2.onrender.com",
        help="URL base para imprimir os links por oficina.",
    )
    return parser.parse_args()


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    lowered = without_marks.lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def build_question_specs(templates: list[QuestionTemplate]) -> list[QuestionSpec]:
    return [
        QuestionSpec(
            ordem=index,
            titulo=item.titulo,
            tipo=item.tipo,
            obrigatoria=item.obrigatoria,
            opcoes=item.opcoes,
            descricao=item.descricao,
        )
        for index, item in enumerate(templates, start=1)
    ]


def profissional_specs() -> list[QuestionSpec]:
    templates = (
        IDENTIFICACAO
        + EIXOS_PROFISSIONAIS
        + FORMADORES_TODAS_SALAS
        + BLOCOS_GERAIS
    )
    return build_question_specs(templates)


def semed_specs() -> list[QuestionSpec]:
    templates = (
        IDENTIFICACAO
        + TRILHA_SEMED
        + FORMADORES_TODAS_SALAS
        + BLOCOS_GERAIS
        + [ABERTA_EXTRA_SEMED]
    )
    return build_question_specs(templates)


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

        if number in (1, 2, 3, 4):
            if "profission" in title_norm:
                room_by_number[number] = room
        elif number == 5 and "semed" in title_norm:
            room_by_number[number] = room

    if 5 not in room_by_number:
        fallback_semed = next(
            (room for room in rooms if "semed" in normalize_text(room.titulo)),
            None,
        )
        if fallback_semed:
            room_by_number[5] = fallback_semed

    for number in (1, 2, 3, 4):
        if number in room_by_number:
            continue
        fallback_room = next(
            (
                room
                for room in rooms
                if f"sala {number}" in normalize_text(room.titulo)
                and "semed" not in normalize_text(room.titulo)
            ),
            None,
        )
        if fallback_room:
            room_by_number[number] = fallback_room

    missing = [num for num in (1, 2, 3, 4, 5) if num not in room_by_number]
    if missing:
        available = ", ".join(f"{room.id}:{room.titulo}" for room in rooms) or "(nenhuma)"
        raise RuntimeError(
            "Nao foi possivel mapear todas as salas esperadas "
            f"(faltando: {missing}). Oficinas encontradas: {available}"
        )

    return room_by_number


def upsert_room_questions(
    *,
    cliente_id: int,
    oficina_id: int,
    specs: list[QuestionSpec],
) -> tuple[int, int, int]:
    existentes_ativos = (
        PerguntaFeedback.query.filter_by(
            cliente_id=cliente_id,
            oficina_id=oficina_id,
            ativa=True,
        )
        .order_by(PerguntaFeedback.id.asc())
        .all()
    )

    by_title: dict[str, list[PerguntaFeedback]] = {}
    for pergunta in existentes_ativos:
        key = normalize_text(pergunta.titulo)
        by_title.setdefault(key, []).append(pergunta)

    created = 0
    updated = 0
    kept: list[PerguntaFeedback] = []

    for spec in specs:
        key = normalize_text(spec.titulo)
        candidates = by_title.get(key, [])

        pergunta = None
        if candidates:
            pergunta = candidates.pop(0)
            updated += 1
        else:
            pergunta = PerguntaFeedback(
                cliente_id=cliente_id,
                oficina_id=oficina_id,
                titulo=spec.titulo,
            )
            db.session.add(pergunta)
            created += 1

        pergunta.oficina_id = oficina_id
        pergunta.template_id = None
        pergunta.atividade_id = None
        pergunta.titulo = spec.titulo
        pergunta.descricao = spec.descricao
        pergunta.tipo = spec.tipo
        pergunta.opcoes = (
            json.dumps(spec.opcoes, ensure_ascii=False)
            if spec.opcoes is not None
            else None
        )
        pergunta.obrigatoria = spec.obrigatoria
        pergunta.ordem = spec.ordem
        pergunta.ativa = True
        kept.append(pergunta)

    deactivated = 0
    for pergunta in existentes_ativos:
        if pergunta not in kept:
            pergunta.ativa = False
            deactivated += 1

    return created, updated, deactivated


def main() -> int:
    args = parse_args()
    app = build_app()

    with app.app_context():
        cliente = Cliente.query.filter(Cliente.email.ilike(args.client_email)).first()
        if not cliente:
            raise SystemExit(f"Cliente nao encontrado: {args.client_email}")

        event = find_event(cliente.id, args.event_hint)
        room_map = map_target_rooms(event.id)

        prof_specs = profissional_specs()
        semed_only_specs = semed_specs()

        report_lines: list[str] = []
        total_created = 0
        total_updated = 0
        total_deactivated = 0

        for room_number in (1, 2, 3, 4, 5):
            room = room_map[room_number]
            specs = semed_only_specs if room_number == 5 else prof_specs

            created, updated, deactivated = upsert_room_questions(
                cliente_id=cliente.id,
                oficina_id=room.id,
                specs=specs,
            )
            total_created += created
            total_updated += updated
            total_deactivated += deactivated

            report_lines.append(
                f"Sala {room_number} -> {room.titulo} (id={room.id}) | "
                f"criadas={created} atualizadas={updated} desativadas={deactivated} "
                f"perguntas_ativas={len(specs)}"
            )

        db.session.commit()

        base = args.base_url.rstrip("/")
        print(f"Cliente: {cliente.email} (id={cliente.id})")
        print(f"Evento: {event.nome} (id={event.id})")
        print(
            f"Perguntas -> criadas={total_created}, "
            f"atualizadas={total_updated}, desativadas={total_deactivated}"
        )
        print("")
        print("Resumo por sala:")
        for line in report_lines:
            print(f"- {line}")
        print("")
        print("Links publicos por oficina:")
        for room_number in (1, 2, 3, 4, 5):
            room = room_map[room_number]
            print(f"- Sala {room_number}: {base}/feedback/responder/oficina/{room.id}")

        print("")
        print(
            "Regra aplicada: formadores repetidos em todas as salas e NAO obrigatorios."
        )
        print(
            "Segmentacao aplicada por sala: Salas 1-4 com bloco de Profissionais; "
            "Sala 5 com bloco tecnico da SEMED."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

