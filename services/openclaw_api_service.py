from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from werkzeug.security import generate_password_hash

from extensions import db
from models import (
    Evento,
    EventoInscricaoTipo,
    Inscricao,
    LoteInscricao,
    LoteTipoInscricao,
    ParticipanteEvento,
    Usuario,
)
from services.mp_service import get_sdk
from services.openclaw_receipt_service import generate_receipt_pdf
from utils import external_url, preco_com_taxa
from utils.openclaw_validators import (
    OpenClawValidationError,
    format_cpf,
    normalize_cpf,
    normalize_email,
    optional_int,
    require_text,
)


logger = logging.getLogger("openclaw.api")


class OpenClawAPIError(RuntimeError):
    """Base exception for OpenClaw API flows."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class AuthenticationError(OpenClawAPIError):
    def __init__(self, message: str = "Token de autenticacao invalido.") -> None:
        super().__init__(
            message,
            code="authentication_failed",
            status_code=401,
        )


class ResourceNotFoundError(OpenClawAPIError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "resource_not_found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=404, details=details)


class ConflictError(OpenClawAPIError):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=409, details=details)


class ExternalServiceError(OpenClawAPIError):
    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            code="external_service_failure",
            status_code=503,
        )


@dataclass(frozen=True)
class PricingContext:
    event: Evento
    enrollment_type: EventoInscricaoTipo | None
    lot: LoteInscricao | None
    price: Decimal


class OpenClawEnrollmentService:
    """Application service for the OpenClaw REST API."""

    def list_events(
        self,
        *,
        cliente_id: int | None = None,
        include_inactive: bool = False,
        public_only: bool = True,
    ) -> list[dict[str, Any]]:
        query = Evento.query
        if cliente_id is not None:
            query = query.filter_by(cliente_id=cliente_id)
        if public_only:
            query = query.filter_by(publico=True)
        if not include_inactive:
            query = query.filter_by(status="ativo")

        events = query.all()
        events.sort(key=lambda item: (item.data_inicio or datetime.max, item.nome.lower()))
        return [self.serialize_event(evento, detailed=False) for evento in events]

    def get_event(self, evento_id: int) -> dict[str, Any]:
        evento = db.session.get(Evento, evento_id)
        if not evento:
            raise ResourceNotFoundError("Evento nao encontrado.", code="event_not_found")
        return self.serialize_event(evento, detailed=True)

    def get_participant_by_cpf(self, cpf: str) -> dict[str, Any]:
        usuario = Usuario.query.filter_by(cpf=normalize_cpf(cpf)).first()
        if not usuario:
            raise ResourceNotFoundError(
                "Participante nao encontrado para o CPF informado.",
                code="participant_not_found",
            )
        return self.serialize_participant(usuario)

    def create_registration(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        del idempotency_key

        evento_id = optional_int(payload, "evento_id")
        if evento_id is None:
            raise OpenClawValidationError("evento_id e obrigatorio.")

        evento = db.session.get(Evento, evento_id)
        if not evento:
            raise ResourceNotFoundError("Evento nao encontrado.", code="event_not_found")
        if evento.status != "ativo":
            raise ConflictError(
                "Evento indisponivel para inscricao.",
                code="event_not_available",
            )

        cpf = normalize_cpf(require_text(payload, "cpf", label="cpf"))
        email = normalize_email(require_text(payload, "email", label="email"))
        nome = require_text(payload, "nome", label="nome")
        formacao = require_text(payload, "formacao", label="formacao")
        senha = str(payload.get("senha") or "").strip() or self._generate_password()
        lote_id = optional_int(payload, "lote_id")
        tipo_inscricao_id = optional_int(payload, "tipo_inscricao_id")

        usuario = self._resolve_or_create_participant(
            evento=evento,
            cpf=cpf,
            email=email,
            nome=nome,
            formacao=formacao,
            senha=senha,
        )

        existing = self._get_event_registration(usuario.id, evento.id)
        if existing:
            raise ConflictError(
                "Participante ja possui inscricao nesse evento.",
                code="duplicate_registration",
                details={
                    "registration": self.serialize_registration(existing),
                    "cpf": format_cpf(cpf) or cpf,
                },
            )

        pricing = self._resolve_pricing(
            event=evento,
            enrollment_type_id=tipo_inscricao_id,
            lot_id=lote_id,
        )
        status_pagamento = "approved" if pricing.price <= 0 else "pending"

        inscricao = Inscricao(
            usuario_id=usuario.id,
            cliente_id=evento.cliente_id,
            evento_id=evento.id,
            status_pagamento=status_pagamento,
            lote_id=pricing.lot.id if pricing.lot else None,
            tipo_inscricao_id=pricing.enrollment_type.id if pricing.enrollment_type else None,
        )

        db.session.add(inscricao)
        self._ensure_event_participation(usuario.id, evento.id)
        db.session.commit()

        logger.info(
            "OpenClaw created registration %s for user %s in event %s",
            inscricao.id,
            usuario.id,
            evento.id,
        )
        return {
            "created": True,
            "payment_required": pricing.price > 0,
            "temporary_password_generated": not bool(str(payload.get("senha") or "").strip()),
            "registration": self.serialize_registration(inscricao),
        }

    def list_registrations_by_cpf(
        self,
        cpf: str,
        *,
        evento_id: int | None = None,
    ) -> dict[str, Any]:
        usuario = Usuario.query.filter_by(cpf=normalize_cpf(cpf)).first()
        if not usuario:
            raise ResourceNotFoundError(
                "Participante nao encontrado para o CPF informado.",
                code="participant_not_found",
            )

        query = (
            Inscricao.query.filter_by(usuario_id=usuario.id)
            .filter(Inscricao.oficina_id.is_(None))
        )
        if evento_id is not None:
            query = query.filter_by(evento_id=evento_id)

        registrations = query.order_by(Inscricao.created_at.desc()).all()
        return {
            "participant": {
                "id": usuario.id,
                "nome": usuario.nome,
                "cpf": format_cpf(usuario.cpf) or usuario.cpf,
                "email": usuario.email,
            },
            "registrations": [
                self.serialize_registration(inscricao) for inscricao in registrations
            ],
        }

    def get_registration_by_protocol(self, protocolo: str) -> dict[str, Any]:
        inscricao = Inscricao.query.filter_by(qr_code_token=protocolo).first()
        if not inscricao:
            raise ResourceNotFoundError(
                "Inscricao nao encontrada para o protocolo informado.",
                code="registration_not_found",
            )
        return self.serialize_registration(inscricao)

    def get_registration_status(self, inscricao_id: int) -> dict[str, Any]:
        inscricao = self._get_registration_or_raise(inscricao_id)
        serialized = self.serialize_registration(inscricao)
        return {
            "inscricao_id": inscricao.id,
            "protocolo": inscricao.qr_code_token,
            "status_pagamento": inscricao.status_pagamento,
            "status_inscricao": serialized["status_inscricao"],
            "payment_required": serialized["payment_required"],
            "comprovante_disponivel": serialized["comprovante_disponivel"],
            "registration": serialized,
        }

    def get_receipt_metadata(self, inscricao_id: int) -> dict[str, Any]:
        inscricao = self._get_registration_or_raise(inscricao_id)
        pdf_path = generate_receipt_pdf(inscricao)
        token = inscricao.qr_code_token
        download_url = external_url(
            "openclaw_api_routes.download_receipt_file",
            inscricao_id=inscricao.id,
        )
        return {
            "inscricao_id": inscricao.id,
            "protocolo": token,
            "status_pagamento": inscricao.status_pagamento,
            "download_url": f"{download_url}?token={token}",
            "arquivo_nome": os.path.basename(pdf_path),
            "arquivo_path": pdf_path,
            "registration": self.serialize_registration(inscricao),
        }

    def generate_payment_link(self, inscricao_id: int) -> dict[str, Any]:
        inscricao = self._get_registration_or_raise(inscricao_id)
        if not inscricao.evento:
            raise ConflictError(
                "A inscricao nao esta vinculada a um evento.",
                code="registration_without_event",
            )
        if inscricao.status_pagamento == "approved":
            return {
                "payment_required": False,
                "status_pagamento": "approved",
                "message": "Pagamento ja confirmado.",
                "registration": self.serialize_registration(inscricao),
            }

        pricing = self._resolve_pricing(
            event=inscricao.evento,
            enrollment_type_id=inscricao.tipo_inscricao_id,
            lot_id=inscricao.lote_id,
        )
        if pricing.price <= 0:
            inscricao.status_pagamento = "approved"
            db.session.commit()
            return {
                "payment_required": False,
                "status_pagamento": "approved",
                "message": "A inscricao nao exige pagamento.",
                "registration": self.serialize_registration(inscricao),
            }

        sdk = get_sdk()
        if not sdk:
            raise ExternalServiceError(
                "Mercado Pago indisponivel. Configure MERCADOPAGO_ACCESS_TOKEN."
            )

        titulo_tipo = (
            pricing.enrollment_type.nome if pricing.enrollment_type else "Inscricao"
        )
        preference_data = {
            "items": [
                {
                    "id": str(inscricao.id),
                    "title": f"Inscricao - {inscricao.evento.nome} - {titulo_tipo}",
                    "description": f"Inscricao para {inscricao.evento.nome}",
                    "quantity": 1,
                    "currency_id": "BRL",
                    "unit_price": float(
                        preco_com_taxa(pricing.price, cliente_id=inscricao.cliente_id)
                    ),
                    "category_id": "evento",
                }
            ],
            "payer": {
                "name": inscricao.usuario.nome,
                "email": inscricao.usuario.email,
                "last_name": inscricao.usuario.nome,
            },
            "external_reference": str(inscricao.id),
            "back_urls": {
                "success": external_url("mercadopago_routes.pagamento_sucesso"),
                "failure": external_url("mercadopago_routes.pagamento_falha"),
                "pending": external_url("mercadopago_routes.pagamento_pendente"),
            },
            "notification_url": external_url("mercadopago_routes.webhook_mp"),
        }
        auto_return = os.getenv("MP_AUTO_RETURN")
        if auto_return:
            preference_data["auto_return"] = auto_return

        try:
            response = sdk.preference().create(preference_data)
            link = response["response"].get("init_point")
        except Exception as exc:  # pragma: no cover - external SDK
            logger.exception("OpenClaw payment link creation failed")
            raise ExternalServiceError(
                "Falha ao gerar link de pagamento no provedor externo."
            ) from exc

        if not link:
            raise ExternalServiceError("O provedor nao retornou um link de pagamento.")

        inscricao.boleto_url = link
        db.session.commit()
        return {
            "payment_required": True,
            "status_pagamento": inscricao.status_pagamento,
            "payment_url": link,
            "registration": self.serialize_registration(inscricao),
        }

    def serialize_event(
        self,
        evento: Evento,
        *,
        detailed: bool,
    ) -> dict[str, Any]:
        active_lots = [
            self.serialize_lot(lote)
            for lote in sorted(evento.lotes, key=lambda item: (item.ordem, item.id))
            if lote.ativo
        ]
        types = [
            self.serialize_enrollment_type(tipo, lots=evento.lotes if detailed else [])
            for tipo in evento.tipos_inscricao
        ]
        return {
            "id": evento.id,
            "cliente_id": evento.cliente_id,
            "nome": evento.nome,
            "descricao": evento.descricao,
            "localizacao": evento.localizacao,
            "link_mapa": evento.link_mapa,
            "status": evento.status,
            "publico": evento.publico,
            "inscricao_gratuita": evento.inscricao_gratuita,
            "data_inicio": evento.data_inicio.isoformat() if evento.data_inicio else None,
            "data_fim": evento.data_fim.isoformat() if evento.data_fim else None,
            "tipos_inscricao": types,
            "lotes": active_lots,
            "oficinas_quantidade": len(getattr(evento, "oficinas", []) or []),
            "inscricao_disponivel": evento.status == "ativo" and evento.publico,
            "resumo": {
                "data_formatada": evento.get_data_formatada(),
                "requer_pagamento": not evento.inscricao_gratuita,
            },
        }

    def serialize_participant(self, usuario: Usuario) -> dict[str, Any]:
        event_registrations = (
            Inscricao.query.filter_by(usuario_id=usuario.id)
            .filter(Inscricao.oficina_id.is_(None))
            .order_by(Inscricao.created_at.desc())
            .all()
        )
        return {
            "id": usuario.id,
            "nome": usuario.nome,
            "cpf": format_cpf(usuario.cpf) or usuario.cpf,
            "email": usuario.email,
            "formacao": usuario.formacao,
            "ativo": usuario.ativo,
            "registrations": [
                self.serialize_registration(item) for item in event_registrations
            ],
        }

    def serialize_registration(self, inscricao: Inscricao) -> dict[str, Any]:
        event = inscricao.evento
        enrollment_type = None
        if inscricao.tipo_inscricao_id:
            enrollment_type = db.session.get(
                EventoInscricaoTipo, inscricao.tipo_inscricao_id
            )
        lot = db.session.get(LoteInscricao, inscricao.lote_id) if inscricao.lote_id else None
        payment_required = not (event.inscricao_gratuita if event else False)
        return {
            "id": inscricao.id,
            "protocolo": inscricao.qr_code_token,
            "usuario": {
                "id": inscricao.usuario.id,
                "nome": inscricao.usuario.nome,
                "cpf": format_cpf(inscricao.usuario.cpf) or inscricao.usuario.cpf,
                "email": inscricao.usuario.email,
            },
            "evento": {
                "id": event.id if event else None,
                "nome": event.nome if event else None,
                "localizacao": event.localizacao if event else None,
                "data_inicio": event.data_inicio.isoformat() if event and event.data_inicio else None,
                "data_fim": event.data_fim.isoformat() if event and event.data_fim else None,
            },
            "tipo_inscricao": {
                "id": enrollment_type.id,
                "nome": enrollment_type.nome,
                "preco": float(enrollment_type.preco),
            } if enrollment_type else None,
            "lote": self.serialize_lot(lot) if lot else None,
            "status_pagamento": inscricao.status_pagamento,
            "status_inscricao": (
                "confirmada" if inscricao.status_pagamento == "approved" else "aguardando_pagamento"
            ),
            "payment_required": payment_required,
            "boleto_url": inscricao.boleto_url,
            "comprovante_disponivel": True,
            "comprovante_endpoint": f"/api/comprovantes/{inscricao.id}",
            "created_at": inscricao.created_at.isoformat() if inscricao.created_at else None,
        }

    def serialize_enrollment_type(
        self,
        enrollment_type: EventoInscricaoTipo,
        *,
        lots: list[LoteInscricao],
    ) -> dict[str, Any]:
        lot_prices = []
        for lot in lots:
            price_entry = LoteTipoInscricao.query.filter_by(
                lote_id=lot.id,
                tipo_inscricao_id=enrollment_type.id,
            ).first()
            if price_entry:
                lot_prices.append(
                    {
                        "lote_id": lot.id,
                        "lote_nome": lot.nome,
                        "preco": float(price_entry.preco),
                        "ativo": lot.is_valid(),
                    }
                )
        return {
            "id": enrollment_type.id,
            "nome": enrollment_type.nome,
            "preco": float(enrollment_type.preco),
            "submission_only": enrollment_type.submission_only,
            "lotes": lot_prices,
        }

    def serialize_lot(self, lot: LoteInscricao | None) -> dict[str, Any] | None:
        if not lot:
            return None
        return {
            "id": lot.id,
            "nome": lot.nome,
            "ativo": bool(lot.ativo and lot.is_valid()),
            "qtd_maxima": lot.qtd_maxima,
            "data_inicio": lot.data_inicio.isoformat() if lot.data_inicio else None,
            "data_fim": lot.data_fim.isoformat() if lot.data_fim else None,
        }

    def _resolve_or_create_participant(
        self,
        *,
        evento: Evento,
        cpf: str,
        email: str,
        nome: str,
        formacao: str,
        senha: str,
    ) -> Usuario:
        existing_by_cpf = Usuario.query.filter_by(cpf=cpf).first()
        existing_by_email = Usuario.query.filter(
            func.lower(Usuario.email) == email.lower()
        ).first()

        if existing_by_email and existing_by_cpf and existing_by_email.id != existing_by_cpf.id:
            raise ConflictError(
                "Email e CPF pertencem a cadastros diferentes.",
                code="participant_conflict",
            )
        if existing_by_email and not existing_by_cpf:
            raise ConflictError(
                "O email informado ja esta vinculado a outro participante.",
                code="participant_conflict",
            )

        if existing_by_cpf:
            if existing_by_cpf.email.lower() != email.lower():
                raise ConflictError(
                    "O CPF informado ja esta vinculado a outro email.",
                    code="participant_conflict",
                )
            if not existing_by_cpf.formacao:
                existing_by_cpf.formacao = formacao
            if not existing_by_cpf.nome:
                existing_by_cpf.nome = nome
            if existing_by_cpf.evento_id != evento.id:
                existing_by_cpf.evento_id = evento.id
            return existing_by_cpf

        user = Usuario(
            nome=nome,
            cpf=cpf,
            email=email,
            senha=generate_password_hash(senha, method="pbkdf2:sha256"),
            formacao=formacao,
            tipo="participante",
            cliente_id=evento.cliente_id,
            evento_id=evento.id,
        )
        db.session.add(user)
        db.session.flush()

        cliente_obj = evento.cliente
        if cliente_obj and cliente_obj not in user.clientes:
            user.clientes.append(cliente_obj)
        return user

    def _resolve_pricing(
        self,
        *,
        event: Evento,
        enrollment_type_id: int | None,
        lot_id: int | None,
    ) -> PricingContext:
        if event.inscricao_gratuita:
            return PricingContext(
                event=event,
                enrollment_type=None,
                lot=None,
                price=Decimal("0.00"),
            )

        enrollment_type = None
        if enrollment_type_id is not None:
            enrollment_type = EventoInscricaoTipo.query.filter_by(
                id=enrollment_type_id,
                evento_id=event.id,
            ).first()
            if not enrollment_type:
                raise OpenClawValidationError("tipo_inscricao_id invalido.")
            if enrollment_type.submission_only:
                raise OpenClawValidationError(
                    "Esse tipo de inscricao exige submissao e nao pode ser usado no WhatsApp."
                )
        elif len(event.tipos_inscricao) == 1:
            enrollment_type = event.tipos_inscricao[0]

        lot = None
        if lot_id is not None:
            lot = LoteInscricao.query.filter_by(id=lot_id, evento_id=event.id).first()
            if not lot:
                raise OpenClawValidationError("lote_id invalido.")
            if not lot.ativo or not lot.is_valid():
                raise ConflictError(
                    "O lote informado nao esta disponivel.",
                    code="lot_not_available",
                )
        elif event.habilitar_lotes:
            active_lots = [item for item in event.lotes if item.ativo and item.is_valid()]
            if len(active_lots) == 1:
                lot = active_lots[0]

        if not enrollment_type:
            raise OpenClawValidationError(
                "Informe um tipo de inscricao valido para concluir a inscricao."
            )

        if lot:
            lot_price = LoteTipoInscricao.query.filter_by(
                lote_id=lot.id,
                tipo_inscricao_id=enrollment_type.id,
            ).first()
            if not lot_price:
                raise OpenClawValidationError(
                    "O tipo de inscricao nao esta disponivel para o lote informado."
                )
            return PricingContext(
                event=event,
                enrollment_type=enrollment_type,
                lot=lot,
                price=Decimal(str(lot_price.preco)),
            )

        return PricingContext(
            event=event,
            enrollment_type=enrollment_type,
            lot=None,
            price=Decimal(str(enrollment_type.preco)),
        )

    def _get_event_registration(self, usuario_id: int, evento_id: int) -> Inscricao | None:
        return (
            Inscricao.query.filter_by(usuario_id=usuario_id, evento_id=evento_id)
            .filter(Inscricao.oficina_id.is_(None))
            .first()
        )

    def _ensure_event_participation(self, usuario_id: int, evento_id: int) -> None:
        existing = ParticipanteEvento.query.filter_by(
            usuario_id=usuario_id,
            evento_id=evento_id,
        ).first()
        if not existing:
            db.session.add(
                ParticipanteEvento(usuario_id=usuario_id, evento_id=evento_id)
            )

    def _get_registration_or_raise(self, inscricao_id: int) -> Inscricao:
        inscricao = db.session.get(Inscricao, inscricao_id)
        if not inscricao:
            raise ResourceNotFoundError(
                "Inscricao nao encontrada.",
                code="registration_not_found",
            )
        return inscricao

    def _generate_password(self) -> str:
        length = int(os.getenv("OPENCLAW_DEFAULT_PASSWORD_LENGTH", "16"))
        return secrets.token_urlsafe(max(8, length))[: max(8, length)]
