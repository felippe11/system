#!/usr/bin/env python3
"""
Cria o evento "Workshop de Educacao Integral - SENADOR RUI PALMEIRA".

O script e idempotente:
- cria o cliente caso nao exista;
- cria ou atualiza o evento;
- cria ou atualiza os tipos de inscricao do evento;
- cria ou atualiza as 5 salas como oficinas;
- cria os dois dias de cada sala;
- cria ou atualiza as regras por tipo de inscricao.

Observacao importante:
- o sistema ja bloqueia automaticamente novas inscricoes quando `oficina.vagas`
  chega a zero;
- a distribuicao "equilibrada" entre as Salas 1 a 4 nao existe nativamente.
  O script prepara as salas e as regras, mas a escolha da sala continua sendo
  feita pelo fluxo atual da aplicacao.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, time

from flask import Flask
from sqlalchemy import func
from werkzeug.security import generate_password_hash


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import Config  # noqa: E402
from extensions import db  # noqa: E402
from models import (  # noqa: E402
    Cliente,
    Evento,
    EventoInscricaoTipo,
    Inscricao,
    Oficina,
    OficinaDia,
    RegraInscricaoEvento,
)


EVENT_NAME = "Workshop de Educação Integral - SENADOR RUI PALMEIRA"
EVENT_DESCRIPTION = (
    "Workshop com eixos simultaneos em 5 salas. "
    "Salas 1 a 4 para Profissionais e Sala 5 exclusiva para Tecnicos da SEMED."
)
EVENT_PROGRAM = (
    "Eixos simultaneos com limite de 35 participantes por sala, em dois dias."
)
EVENT_LOCATION = "Senador Rui Palmeira/AL"
EVENT_CITY = "Senador Rui Palmeira"
EVENT_STATE = "AL"
EVENT_WORKLOAD = "16"
ROOM_CAPACITY = 35


@dataclass(frozen=True)
class RoomSpec:
    title: str
    description: str
    enrollment_type: str


ROOM_SPECS = [
    RoomSpec(
        title="Sala 1 - Profissionais",
        description="Eixo simultaneo - Sala 1 para Profissionais",
        enrollment_type="Profissionais",
    ),
    RoomSpec(
        title="Sala 2 - Profissionais",
        description="Eixo simultaneo - Sala 2 para Profissionais",
        enrollment_type="Profissionais",
    ),
    RoomSpec(
        title="Sala 3 - Profissionais",
        description="Eixo simultaneo - Sala 3 para Profissionais",
        enrollment_type="Profissionais",
    ),
    RoomSpec(
        title="Sala 4 - Profissionais",
        description="Eixo simultaneo - Sala 4 para Profissionais",
        enrollment_type="Profissionais",
    ),
    RoomSpec(
        title="Sala 5 - Técnicos da SEMED",
        description="Eixo simultaneo - Sala exclusiva para Técnicos da SEMED",
        enrollment_type="Técnicos da SEMED",
    ),
]


DAY_SPECS = [
    (date(2026, 4, 9), "08:00", "17:00", 1),
    (date(2026, 4, 10), "08:00", "17:00", 2),
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
        description="Cria o evento de workshop e suas salas."
    )
    parser.add_argument(
        "--client-email",
        default="iafap@appfiber.com",
        help="E-mail do cliente dono do evento.",
    )
    parser.add_argument(
        "--client-password",
        default="123455678",
        help="Senha do cliente. Usada na criacao e opcionalmente na atualizacao.",
    )
    parser.add_argument(
        "--client-name",
        default="IAFAP AppFiber",
        help="Nome do cliente caso ele precise ser criado.",
    )
    parser.add_argument(
        "--force-update-client-password",
        action="store_true",
        help="Atualiza a senha do cliente existente para o valor informado.",
    )
    return parser.parse_args()


def ensure_client(
    *,
    email: str,
    password: str,
    name: str,
    force_update_password: bool,
) -> tuple[Cliente, bool]:
    client = Cliente.query.filter(func.lower(Cliente.email) == email.lower()).first()
    created = False

    if client is None:
        client = Cliente(
            nome=name,
            email=email,
            senha=generate_password_hash(password, method="pbkdf2:sha256"),
            ativo=True,
            tipo="cliente",
        )
        db.session.add(client)
        db.session.flush()
        created = True
    else:
        client.ativo = True
        client.tipo = "cliente"
        if force_update_password:
            client.senha = generate_password_hash(password, method="pbkdf2:sha256")

    return client, created


def ensure_event(client: Cliente) -> tuple[Evento, bool]:
    event = Evento.query.filter_by(cliente_id=client.id, nome=EVENT_NAME).first()
    created = False

    if event is None:
        event = Evento(cliente_id=client.id, nome=EVENT_NAME)
        db.session.add(event)
        db.session.flush()
        created = True

    event.descricao = EVENT_DESCRIPTION
    event.programacao = EVENT_PROGRAM
    event.localizacao = EVENT_LOCATION
    event.link_mapa = None
    event.banner_url = None
    event.inscricao_gratuita = True
    event.data_inicio = datetime(2026, 4, 9, 8, 0, 0)
    event.data_fim = datetime(2026, 4, 10, 17, 0, 0)
    event.hora_inicio = time(8, 0)
    event.hora_fim = time(17, 0)
    event.status = "ativo"
    event.capacidade_padrao = ROOM_CAPACITY
    event.requer_aprovacao = False
    event.publico = True
    event.habilitar_lotes = False
    event.submissao_aberta = False

    return event, created


def ensure_event_type(event: Evento, name: str) -> EventoInscricaoTipo:
    enrollment_type = EventoInscricaoTipo.query.filter_by(
        evento_id=event.id,
        nome=name,
    ).first()

    if enrollment_type is None:
        enrollment_type = EventoInscricaoTipo(
            evento_id=event.id,
            nome=name,
            preco=0.0,
            submission_only=False,
        )
        db.session.add(enrollment_type)
        db.session.flush()
    else:
        enrollment_type.preco = 0.0
        enrollment_type.submission_only = False

    return enrollment_type


def ensure_room(
    *,
    client: Cliente,
    event: Evento,
    enrollment_type: EventoInscricaoTipo,
    spec: RoomSpec,
) -> tuple[Oficina, bool]:
    room = Oficina.query.filter_by(evento_id=event.id, titulo=spec.title).first()
    created = False

    if room is None:
        room = Oficina(
            titulo=spec.title,
            descricao=spec.description,
            ministrante_id=None,
            vagas=ROOM_CAPACITY,
            carga_horaria=EVENT_WORKLOAD,
            estado=EVENT_STATE,
            cidade=EVENT_CITY,
            cliente_id=client.id,
            evento_id=event.id,
            tipo_inscricao="com_inscricao_com_limite",
            tipo_oficina="Workshop",
            inscricao_gratuita=True,
        )
        db.session.add(room)
        db.session.flush()
        created = True
    else:
        room.descricao = spec.description
        room.carga_horaria = EVENT_WORKLOAD
        room.estado = EVENT_STATE
        room.cidade = EVENT_CITY
        room.cliente_id = client.id
        room.evento_id = event.id
        room.tipo_inscricao = "com_inscricao_com_limite"
        room.tipo_oficina = "Workshop"
        room.tipo_oficina_outro = None
        room.inscricao_gratuita = True

        enrollments_count = Inscricao.query.filter_by(oficina_id=room.id).count()
        if enrollments_count == 0:
            room.vagas = ROOM_CAPACITY

    room.tipos_inscricao_permitidos = str(enrollment_type.id)

    return room, created


def ensure_room_days(room: Oficina) -> int:
    created_count = 0

    for day_date, start_at, end_at, order in DAY_SPECS:
        room_day = OficinaDia.query.filter_by(
            oficina_id=room.id,
            data=day_date,
        ).first()

        if room_day is None:
            room_day = OficinaDia(
                oficina_id=room.id,
                data=day_date,
                horario_inicio=start_at,
                horario_fim=end_at,
                ordem_exibicao=order,
            )
            db.session.add(room_day)
            created_count += 1
        else:
            room_day.horario_inicio = start_at
            room_day.horario_fim = end_at
            room_day.ordem_exibicao = order

    return created_count


def ensure_rule(
    *,
    event: Evento,
    enrollment_type: EventoInscricaoTipo,
    room_ids: list[int],
) -> tuple[RegraInscricaoEvento, bool]:
    rule = RegraInscricaoEvento.query.filter_by(
        evento_id=event.id,
        tipo_inscricao_id=enrollment_type.id,
    ).first()
    created = False

    if rule is None:
        rule = RegraInscricaoEvento(
            evento_id=event.id,
            tipo_inscricao_id=enrollment_type.id,
            limite_oficinas=1,
        )
        db.session.add(rule)
        created = True

    rule.limite_oficinas = 1
    rule.set_oficinas_permitidas_list(room_ids)

    return rule, created


def main() -> int:
    args = parse_args()
    app = build_app()

    with app.app_context():
        client, client_created = ensure_client(
            email=args.client_email,
            password=args.client_password,
            name=args.client_name,
            force_update_password=args.force_update_client_password,
        )
        event, event_created = ensure_event(client)

        professionals_type = ensure_event_type(event, "Profissionais")
        technicians_type = ensure_event_type(event, "Técnicos da SEMED")

        professional_room_ids: list[int] = []
        technician_room_ids: list[int] = []

        rooms_created = 0
        days_created = 0

        for spec in ROOM_SPECS:
            enrollment_type = (
                professionals_type
                if spec.enrollment_type == "Profissionais"
                else technicians_type
            )
            room, room_created = ensure_room(
                client=client,
                event=event,
                enrollment_type=enrollment_type,
                spec=spec,
            )
            rooms_created += int(room_created)
            days_created += ensure_room_days(room)

            if spec.enrollment_type == "Profissionais":
                professional_room_ids.append(room.id)
            else:
                technician_room_ids.append(room.id)

        _, professionals_rule_created = ensure_rule(
            event=event,
            enrollment_type=professionals_type,
            room_ids=professional_room_ids,
        )
        _, technicians_rule_created = ensure_rule(
            event=event,
            enrollment_type=technicians_type,
            room_ids=technician_room_ids,
        )

        db.session.commit()

        print("Cliente:", client.email, f"(id={client.id})")
        print("Cliente criado:", "sim" if client_created else "nao")
        print("Evento:", event.nome, f"(id={event.id})")
        print("Evento criado:", "sim" if event_created else "nao")
        print("Salas criadas nesta execucao:", rooms_created)
        print("Dias criados nesta execucao:", days_created)
        print(
            "Regras criadas nesta execucao:",
            int(professionals_rule_created) + int(technicians_rule_created),
        )
        print("Tipos de inscricao garantidos: Profissionais, Técnicos da SEMED")
        print("Observacao: o balanceamento automatico entre as Salas 1 a 4")
        print("nao existe hoje no codigo. O script cria a estrutura e os limites.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
