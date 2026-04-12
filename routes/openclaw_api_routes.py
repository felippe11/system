from __future__ import annotations

import hmac
import logging
from functools import wraps

from flask import Blueprint, current_app, jsonify, request, send_file

from services.openclaw_api_service import (
    AuthenticationError,
    OpenClawAPIError,
    OpenClawEnrollmentService,
)
from utils.openclaw_validators import OpenClawValidationError, parse_bool


logger = logging.getLogger("openclaw.routes")
openclaw_api_routes = Blueprint(
    "openclaw_api_routes",
    __name__,
    url_prefix="/api",
)
service = OpenClawEnrollmentService()


def require_openclaw_auth(view_func):
    """Validate bearer token for trusted OpenClaw calls."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_app.config.get("OPENCLAW_API_ENABLED", True):
            raise AuthenticationError("API OpenClaw desabilitada.")

        expected_token = (current_app.config.get("OPENCLAW_API_TOKEN") or "").strip()
        if not expected_token:
            raise AuthenticationError("OPENCLAW_API_TOKEN nao configurado.")

        header = request.headers.get("Authorization", "").strip()
        candidate = ""
        if header.lower().startswith("bearer "):
            candidate = header[7:].strip()
        elif request.headers.get("X-API-Key"):
            candidate = request.headers["X-API-Key"].strip()

        if not candidate or not hmac.compare_digest(candidate, expected_token):
            raise AuthenticationError()
        return view_func(*args, **kwargs)

    return wrapped


@openclaw_api_routes.errorhandler(OpenClawValidationError)
def handle_validation_error(exc: OpenClawValidationError):
    return jsonify(
        {
            "success": False,
            "error": {
                "code": "validation_error",
                "message": str(exc),
                "details": {},
            },
        }
    ), 400


@openclaw_api_routes.errorhandler(OpenClawAPIError)
def handle_openclaw_error(exc: OpenClawAPIError):
    return jsonify({"success": False, "error": exc.to_dict()}), exc.status_code


@openclaw_api_routes.errorhandler(Exception)
def handle_unexpected_error(exc: Exception):  # pragma: no cover - defensive
    logger.exception("Unexpected OpenClaw API error")
    return jsonify(
        {
            "success": False,
            "error": {
                "code": "internal_error",
                "message": "Falha interna ao processar a solicitacao.",
                "details": {},
            },
        }
    ), 500


def _success(data, *, status_code: int = 200):
    return jsonify({"success": True, "data": data}), status_code


@openclaw_api_routes.route("/eventos", methods=["GET"])
@require_openclaw_auth
def listar_eventos():
    cliente_id = request.args.get("cliente_id", type=int)
    include_inactive = parse_bool(request.args.get("incluir_inativos"))
    public_only = parse_bool(request.args.get("somente_publicos"), default=True)
    data = service.list_events(
        cliente_id=cliente_id,
        include_inactive=include_inactive,
        public_only=public_only,
    )
    return _success(data)


@openclaw_api_routes.route("/eventos/<int:evento_id>", methods=["GET"])
@require_openclaw_auth
def detalhar_evento(evento_id: int):
    return _success(service.get_event(evento_id))


@openclaw_api_routes.route("/participantes/cpf/<cpf>", methods=["GET"])
@require_openclaw_auth
def buscar_participante_por_cpf(cpf: str):
    return _success(service.get_participant_by_cpf(cpf))


@openclaw_api_routes.route("/inscricoes", methods=["POST"])
@require_openclaw_auth
def criar_inscricao():
    payload = request.get_json(silent=True) or {}
    data = service.create_registration(
        payload,
        idempotency_key=request.headers.get("X-Idempotency-Key"),
    )
    return _success(data, status_code=201)


@openclaw_api_routes.route("/inscricoes", methods=["GET"])
@require_openclaw_auth
def consultar_inscricao_por_cpf():
    cpf = request.args.get("cpf")
    if not cpf:
        raise OpenClawValidationError("cpf e obrigatorio para consultar inscricoes.")
    evento_id = request.args.get("evento_id", type=int)
    return _success(service.list_registrations_by_cpf(cpf, evento_id=evento_id))


@openclaw_api_routes.route("/inscricoes/protocolo/<protocolo>", methods=["GET"])
@require_openclaw_auth
def consultar_inscricao_por_protocolo(protocolo: str):
    return _success(service.get_registration_by_protocol(protocolo))


@openclaw_api_routes.route("/comprovantes/<int:inscricao_id>", methods=["GET"])
@require_openclaw_auth
def receipt_metadata(inscricao_id: int):
    data = service.get_receipt_metadata(inscricao_id)
    public_data = dict(data)
    public_data.pop("arquivo_path", None)
    return _success(public_data)


@openclaw_api_routes.route("/comprovantes/<int:inscricao_id>/arquivo", methods=["GET"])
def download_receipt_file(inscricao_id: int):
    token = (request.args.get("token") or "").strip()
    if not token:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "missing_token",
                    "message": "Token de comprovante nao informado.",
                    "details": {},
                },
            }
        ), 400

    metadata = service.get_receipt_metadata(inscricao_id)
    if not hmac.compare_digest(token, metadata["protocolo"]):
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "invalid_token",
                    "message": "Token de comprovante invalido.",
                    "details": {},
                },
            }
        ), 403

    return send_file(
        metadata["arquivo_path"],
        as_attachment=True,
        download_name=metadata["arquivo_nome"],
        mimetype="application/pdf",
    )


@openclaw_api_routes.route("/inscricoes/status/<int:inscricao_id>", methods=["GET"])
@require_openclaw_auth
def consultar_status_inscricao(inscricao_id: int):
    return _success(service.get_registration_status(inscricao_id))


@openclaw_api_routes.route("/pagamentos/gerar-link", methods=["POST"])
@require_openclaw_auth
def gerar_link_pagamento():
    payload = request.get_json(silent=True) or {}
    inscricao_id = payload.get("inscricao_id")
    if inscricao_id is None:
        raise OpenClawValidationError("inscricao_id e obrigatorio.")
    return _success(service.generate_payment_link(int(inscricao_id)))
