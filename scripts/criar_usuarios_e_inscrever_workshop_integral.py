#!/usr/bin/env python3
"""
Cria usuarios participantes e realiza inscricao no workshop.

Regras aplicadas:
- Tecnicos da SEMED: apenas na sala da SEMED.
- Demais participantes: distribuicao balanceada nas salas de profissionais.
- Cria CPF valido e unico para novos usuarios.
- Senha unica para todos: 12345678.

Uso:
python scripts/criar_usuarios_e_inscrever_workshop_integral.py --client-email iafap@appfiber.com
"""

from __future__ import annotations

import argparse
import os
import random
import re
import sys
import unicodedata
from dataclasses import dataclass

from flask import Flask
from sqlalchemy import func
from werkzeug.security import generate_password_hash


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import Config  # noqa: E402
from extensions import db  # noqa: E402
from models import Cliente, Evento, EventoInscricaoTipo, Inscricao, Oficina, Usuario  # noqa: E402


WORKSHOP_NAME_HINT = "SENADOR RUI PALMEIRA"
DEFAULT_PASSWORD = "12345678"
DEFAULT_FORMACAO = "Educacao Basica"


@dataclass(frozen=True)
class ParticipantInput:
    name: str
    email: str
    is_semed: bool


RAW_PARTICIPANTS = [
    ParticipantInput("Ryta de Kassia dos Santos", "souzaluzicleide839@gmail.com", False),
    ParticipantInput("Valeria Ferreira de Barbosa Vanderlei", "valeriafsv123@gmail.com", False),
    ParticipantInput("Rosiane Vieira Lima Araujo", "rosiane1859@gmail.com", False),
    ParticipantInput("Suzana da Silva", "83982116632@gmail.com", False),
    ParticipantInput("Maria Aparecida Silva Rocha", "cida.diretora@gmail.com", False),
    ParticipantInput("Maria Lucia da Silva", "lucassilvacampos@gmail.com", False),
    ParticipantInput("Maria Celia Melo Silva", "mariaceliamelosilva@gmail.com", False),
    ParticipantInput("Elissandra Moreira dos Santos", "santoselissandra244@gmail.com", False),
    ParticipantInput("Maria de Fatima Gonzaga de Lima", "fatimagonzaga@hotmail.com", False),
    ParticipantInput("Lindinalva Mercia Vieira de Melo", "linhavieira1986@gmail.com", False),
    ParticipantInput("Jose Edinaldo A. Santos", "souzaluzicleide839@gmail.com", False),
    ParticipantInput("Gleidiane Lopes da Silva", "gleidianelsilva18@gmail.com", False),
    ParticipantInput("Aguinadab Novais Queiroz", "aquinadab@gmail.com", False),
    ParticipantInput("Egnon Felix da Silva", "egnonfelix@gmail.com", False),
    ParticipantInput("Hozana Alves de Lima", "hozana.alves2000@gmail.com", False),
    ParticipantInput("Daniel Melo Silva", "danielmelo2504@gmail.com", False),
    ParticipantInput("Anderson Luiz Silva Lisboa", "anderson21@hotmail.com", False),
    ParticipantInput("Erika Maria Santos Rodrigues", "erika.leanton17@gmail.com", False),
    ParticipantInput("Josivania da Silva", "josivaniasilva5@outlook.com", False),
    ParticipantInput("Ivanildo Soares Vieira", "ivanildosoaresvieira532@gmail.com", False),
    ParticipantInput("Erivaldo Santos Souza", "souzaeriba@hotmail.com", True),
    ParticipantInput("Cloves Soares Vieira", "clovessoaresvieira@gmail.com", True),
    ParticipantInput("Maria Aldenora Tertuliano Oliveira", "aldenora.oliveira@gmail.com", False),
    ParticipantInput("Joenneures Raio de S. Amancio", "rd-raio@hotmail.com", False),
    ParticipantInput("Bruna Carla Gomes Silva", "brunacarlacarlla2019@gmail.com", False),
    ParticipantInput("Adrielly Marinho Silva", "adriellymarinho2016@gmail.com", False),
    ParticipantInput("Debora Ferreira Teixeira", "deboraavj89@gmail.com", False),
    ParticipantInput("Renata Ferreira Lima", "prof.renata2529@gmail.com", False),
    ParticipantInput("Lizandra Soares Santana", "lizandrasantos@gmail.com", False),
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
        description="Cria usuarios e inscreve no workshop com distribuicao por sala."
    )
    parser.add_argument(
        "--client-email",
        default="iafap@appfiber.com",
        help="Email do cliente dono do evento.",
    )
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help="Senha para novos usuarios.",
    )
    parser.add_argument(
        "--event-hint",
        default=WORKSHOP_NAME_HINT,
        help="Trecho do nome do evento para localizacao.",
    )
    return parser.parse_args()


def normalize_email(value: str) -> str:
    return value.strip().lower()


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def slugify_name(value: str) -> str:
    value = strip_accents(value).lower()
    value = re.sub(r"[^a-z0-9]+", ".", value).strip(".")
    return value or "usuario"


def dedupe_participants(rows: list[ParticipantInput]) -> tuple[list[ParticipantInput], list[str]]:
    used: dict[str, int] = {}
    out: list[ParticipantInput] = []
    warnings: list[str] = []

    for item in rows:
        email = normalize_email(item.email)
        if email not in used:
            used[email] = 1
            out.append(ParticipantInput(item.name, email, item.is_semed))
            continue

        used[email] += 1
        alias_local = slugify_name(item.name)
        alias = f"{alias_local}+dup{used[email]}@appfiber.local"
        warnings.append(
            f"Email duplicado na entrada: '{email}' para '{item.name}'. "
            f"Gerado alias: '{alias}'."
        )
        out.append(ParticipantInput(item.name, alias, item.is_semed))

    return out, warnings


def cpf_digits_only(cpf: str | None) -> str:
    if not cpf:
        return ""
    return re.sub(r"\D", "", cpf)


def format_cpf(digits11: str) -> str:
    return f"{digits11[0:3]}.{digits11[3:6]}.{digits11[6:9]}-{digits11[9:11]}"


def generate_valid_cpf(existing_digits: set[str], rng: random.Random) -> str:
    while True:
        base = [rng.randint(0, 9) for _ in range(9)]
        if len(set(base)) == 1:
            continue

        sum1 = sum((10 - idx) * val for idx, val in enumerate(base))
        d1 = (sum1 * 10) % 11
        if d1 == 10:
            d1 = 0

        sum2 = sum((11 - idx) * val for idx, val in enumerate(base + [d1]))
        d2 = (sum2 * 10) % 11
        if d2 == 10:
            d2 = 0

        digits = "".join(str(x) for x in base + [d1, d2])
        if digits in existing_digits:
            continue

        existing_digits.add(digits)
        return format_cpf(digits)


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


def find_types(event_id: int) -> tuple[EventoInscricaoTipo, EventoInscricaoTipo]:
    prof = (
        EventoInscricaoTipo.query.filter(
            EventoInscricaoTipo.evento_id == event_id,
            EventoInscricaoTipo.nome.ilike("%profission%"),
        )
        .order_by(EventoInscricaoTipo.id.asc())
        .first()
    )
    semed = (
        EventoInscricaoTipo.query.filter(
            EventoInscricaoTipo.evento_id == event_id,
            EventoInscricaoTipo.nome.ilike("%semed%"),
        )
        .order_by(EventoInscricaoTipo.id.asc())
        .first()
    )
    if not prof or not semed:
        raise RuntimeError("Tipos de inscricao do evento (Profissionais/SEMED) nao encontrados.")
    return prof, semed


def find_rooms(event_id: int) -> tuple[Oficina, list[Oficina]]:
    semed_room = (
        Oficina.query.filter(
            Oficina.evento_id == event_id,
            Oficina.titulo.ilike("%semed%"),
        )
        .order_by(Oficina.id.asc())
        .first()
    )
    prof_rooms = (
        Oficina.query.filter(
            Oficina.evento_id == event_id,
            ~Oficina.titulo.ilike("%semed%"),
        )
        .order_by(Oficina.id.asc())
        .all()
    )
    if not semed_room:
        raise RuntimeError("Sala da SEMED nao encontrada no evento.")
    if not prof_rooms:
        raise RuntimeError("Salas de profissionais nao encontradas no evento.")
    return semed_room, prof_rooms


def load_room_counts(room_ids: list[int]) -> dict[int, int]:
    rows = (
        db.session.query(Inscricao.oficina_id, func.count(Inscricao.id))
        .filter(Inscricao.oficina_id.in_(room_ids))
        .group_by(Inscricao.oficina_id)
        .all()
    )
    counts = {room_id: 0 for room_id in room_ids}
    for room_id, total in rows:
        counts[room_id] = int(total)
    return counts


def select_balanced_room(rooms: list[Oficina], room_counts: dict[int, int]) -> Oficina:
    candidates = [r for r in rooms if (r.vagas or 0) > 0]
    if not candidates:
        raise RuntimeError("Sem vagas disponiveis nas salas de profissionais.")

    candidates.sort(key=lambda r: (room_counts.get(r.id, 0), r.id))
    return candidates[0]


def ensure_user(
    participant: ParticipantInput,
    *,
    cliente: Cliente,
    event: Evento,
    tipo_inscricao_id: int,
    password_hash: str,
    existing_cpf_digits: set[str],
    rng: random.Random,
) -> tuple[Usuario, bool]:
    user = Usuario.query.filter(func.lower(Usuario.email) == participant.email).first()
    created = False

    if user is None:
        cpf = generate_valid_cpf(existing_cpf_digits, rng)
        user = Usuario(
            nome=participant.name,
            cpf=cpf,
            email=participant.email,
            senha=password_hash,
            formacao=DEFAULT_FORMACAO,
            tipo="participante",
            cliente_id=cliente.id,
            evento_id=event.id,
            tipo_inscricao_id=tipo_inscricao_id,
            ativo=True,
        )
        db.session.add(user)
        db.session.flush()
        created = True
    else:
        user.ativo = True
        user.tipo = "participante"
        user.cliente_id = cliente.id
        user.evento_id = event.id
        user.tipo_inscricao_id = tipo_inscricao_id
        if not user.formacao:
            user.formacao = DEFAULT_FORMACAO
        if not user.senha:
            user.senha = password_hash
        existing_cpf_digits.add(cpf_digits_only(user.cpf))

    if cliente not in user.clientes:
        user.clientes.append(cliente)

    return user, created


def main() -> int:
    args = parse_args()
    app = build_app()

    participants, warnings = dedupe_participants(RAW_PARTICIPANTS)

    rng = random.Random()
    password_hash = generate_password_hash(args.password, method="pbkdf2:sha256")

    with app.app_context():
        cliente = Cliente.query.filter(Cliente.email.ilike(args.client_email)).first()
        if not cliente:
            raise SystemExit(f"Cliente nao encontrado: {args.client_email}")

        event = find_event(cliente.id, args.event_hint)
        prof_type, semed_type = find_types(event.id)
        semed_room, prof_rooms = find_rooms(event.id)

        room_ids = [semed_room.id] + [r.id for r in prof_rooms]
        room_counts = load_room_counts(room_ids)

        existing_cpf_digits = {
            cpf_digits_only(cpf)
            for (cpf,) in db.session.query(Usuario.cpf).all()
            if cpf_digits_only(cpf)
        }

        users_created = 0
        users_updated = 0
        enrollments_created = 0
        enrollments_updated = 0
        failed: list[str] = []

        for p in participants:
            try:
                target_type = semed_type if p.is_semed else prof_type
                user, created = ensure_user(
                    p,
                    cliente=cliente,
                    event=event,
                    tipo_inscricao_id=target_type.id,
                    password_hash=password_hash,
                    existing_cpf_digits=existing_cpf_digits,
                    rng=rng,
                )
                if created:
                    users_created += 1
                else:
                    users_updated += 1

                existing_ins = Inscricao.query.filter_by(
                    usuario_id=user.id,
                    evento_id=event.id,
                ).first()

                if existing_ins and existing_ins.oficina_id:
                    existing_ins.cliente_id = cliente.id
                    existing_ins.tipo_inscricao_id = target_type.id
                    existing_ins.status_pagamento = "approved"
                    enrollments_updated += 1
                    continue

                if p.is_semed:
                    if (semed_room.vagas or 0) <= 0:
                        raise RuntimeError(
                            f"Sem vagas na sala da SEMED para {p.name} ({p.email})."
                        )
                    selected_room = semed_room
                else:
                    selected_room = select_balanced_room(prof_rooms, room_counts)

                if existing_ins:
                    existing_ins.oficina_id = selected_room.id
                    existing_ins.evento_id = event.id
                    existing_ins.cliente_id = cliente.id
                    existing_ins.tipo_inscricao_id = target_type.id
                    existing_ins.status_pagamento = "approved"
                    enrollments_updated += 1
                else:
                    ins = Inscricao(
                        usuario_id=user.id,
                        oficina_id=selected_room.id,
                        evento_id=event.id,
                        cliente_id=cliente.id,
                        tipo_inscricao_id=target_type.id,
                        status_pagamento="approved",
                    )
                    db.session.add(ins)
                    enrollments_created += 1

                selected_room.vagas = (selected_room.vagas or 0) - 1
                room_counts[selected_room.id] = room_counts.get(selected_room.id, 0) + 1

            except Exception as exc:  # pylint: disable=broad-except
                failed.append(f"{p.name} <{p.email}> -> {exc}")

        if failed:
            db.session.rollback()
            print("Falha. Nenhuma alteracao foi confirmada.")
            for msg in warnings:
                print("WARN:", msg)
            for err in failed:
                print("ERRO:", err)
            return 1

        db.session.commit()

        print(f"Cliente: {cliente.email} (id={cliente.id})")
        print(f"Evento: {event.nome} (id={event.id})")
        print(f"Participantes processados: {len(participants)}")
        print(f"Usuarios criados: {users_created}")
        print(f"Usuarios atualizados/reaproveitados: {users_updated}")
        print(f"Inscricoes criadas: {enrollments_created}")
        print(f"Inscricoes atualizadas: {enrollments_updated}")
        for msg in warnings:
            print("WARN:", msg)

        print("Distribuicao final (inscricoes por sala no evento):")
        final_counts = load_room_counts(room_ids)
        print(f"- {semed_room.titulo}: {final_counts.get(semed_room.id, 0)}")
        for room in prof_rooms:
            print(f"- {room.titulo}: {final_counts.get(room.id, 0)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
