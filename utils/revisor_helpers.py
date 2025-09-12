from __future__ import annotations

from datetime import datetime, time
from typing import Any, Dict, Iterable, List, Optional

from flask import Request

from extensions import db
from models import (
    Evento,
    Formulario,
    CampoFormulario,
    RevisorCriterio,
    RevisorEtapa,
    RevisorProcess,
    RevisorRequisito,
)


def parse_revisor_form(req: Request) -> Dict[str, Any]:
    """Extracts and normalizes form data for reviewer process configuration."""
    raw_form_id = req.form.get("formulario_id")
    try:
        formulario_id = int(raw_form_id) if raw_form_id else None
    except (TypeError, ValueError):
        formulario_id = None

    nome = req.form.get("nome", "").strip()
    if not nome:
        raise ValueError("Nome do processo é obrigatório")
    descricao = req.form.get("descricao")
    status = req.form.get("status", "aberto").lower()

    num_etapas = req.form.get("num_etapas", type=int, default=1)
    stage_names: List[str] = [s.strip() for s in req.form.getlist("stage_name")]
    if len(stage_names) < num_etapas or any(
        not nome for nome in stage_names[:num_etapas]
    ):
        raise ValueError("Todos os nomes das etapas são obrigatórios")
    eventos_ids: List[int] = req.form.getlist("eventos_ids", type=int)
    criterio_nomes: List[str] = req.form.getlist("criterio_nome")
    start_raw = req.form.get("availability_start")
    end_raw = req.form.get("availability_end")
    exibir_val = req.form.get("exibir_para_participantes")
    exibir_para_participantes = exibir_val in {"on", "1", "true"}

    def _parse_dt(raw: str | None, *, end: bool = False) -> datetime | None:
        try:
            if not raw:
                return None
            dt = datetime.strptime(raw, "%Y-%m-%d")
            return datetime.combine(dt.date(), time.max if end else time.min)
        except ValueError:
            return None

    criterios: List[Dict[str, Any]] = []
    for idx, nome in enumerate(criterio_nomes):
        requisitos = [r for r in req.form.getlist(f"criterio_{idx}_requisito") if r]
        if nome or requisitos:
            criterios.append({"nome": nome, "requisitos": requisitos})

    # Parse field step assignments
    campos_etapas: Dict[int, int] = {}
    for key, value in req.form.items():
        if key.startswith("campo_") and key.endswith("_etapa"):
            try:
                campo_id = int(key.split("_")[1])
                etapa = int(value) if value else 1
                campos_etapas[campo_id] = etapa
            except (ValueError, IndexError):
                continue

    return {
        "formulario_id": formulario_id,
        "nome": nome,
        "descricao": descricao,
        "status": status,
        "num_etapas": num_etapas,
        "stage_names": stage_names,
        "availability_start": _parse_dt(start_raw),
        "availability_end": _parse_dt(end_raw, end=True),
        "exibir_para_participantes": exibir_para_participantes,
        "eventos_ids": eventos_ids,
        "criterios": criterios,
        "campos_etapas": campos_etapas,
    }


def update_revisor_process(processo: RevisorProcess, dados: Dict[str, Any]) -> None:
    """Updates a reviewer process with parsed data."""
    processo.formulario_id = dados.get("formulario_id")

    processo.nome = dados.get("nome", processo.nome)
    processo.descricao = dados.get("descricao")
    processo.status = dados.get("status", processo.status)

    processo.num_etapas = dados.get("num_etapas")
    processo.availability_start = dados.get("availability_start")
    processo.availability_end = dados.get("availability_end")
    processo.exibir_para_participantes = dados.get("exibir_para_participantes")


def update_process_eventos(
    processo: RevisorProcess, eventos_ids: Optional[Iterable[int]]
) -> None:
    """Atualiza a relação de eventos associados ao processo.

    Limpa os vínculos existentes e associa apenas os eventos cujos IDs são
    fornecidos. Quando ``eventos_ids`` está vazio ou ``None``, o processo
    permanece sem eventos vinculados.
    """

    processo.eventos = []
    if eventos_ids:
        processo.eventos = Evento.query.filter(Evento.id.in_(eventos_ids)).all()
    db.session.flush()


def recreate_stages(processo: RevisorProcess, stage_names: List[str]) -> None:
    """Recreates stages for the given reviewer process."""
    # First, delete dependent records from revisor_candidatura_etapa
    # Get all stage IDs for this process
    etapa_ids = [etapa.id for etapa in RevisorEtapa.query.filter_by(process_id=processo.id).all()]
    
    if etapa_ids:
        # Import here to avoid circular imports
        from models.review import RevisorCandidaturaEtapa
        # Delete all candidatura_etapa records that reference these stages
        RevisorCandidaturaEtapa.query.filter(RevisorCandidaturaEtapa.etapa_id.in_(etapa_ids)).delete(synchronize_session=False)
    
    # Now we can safely delete the stages
    RevisorEtapa.query.filter_by(process_id=processo.id).delete()
    
    # Create new stages
    for idx, nome in enumerate(stage_names, start=1):
        if nome:
            db.session.add(RevisorEtapa(process_id=processo.id, numero=idx, nome=nome))


def recreate_criterios(
    processo: RevisorProcess, criterios: List[Dict[str, Any]]
) -> None:
    """Recreates barema criteria and requirements for a process."""
    RevisorCriterio.query.filter_by(process_id=processo.id).delete()
    for dados in criterios:
        nome = dados.get("nome")
        if not nome:
            continue
        criterio = RevisorCriterio(process_id=processo.id, nome=nome)
        db.session.add(criterio)
        db.session.flush()
        for req_desc in dados.get("requisitos", []):
            if req_desc:
                db.session.add(
                    RevisorRequisito(criterio_id=criterio.id, descricao=req_desc)
                )


def ensure_reviewer_required_fields(formulario: Formulario) -> None:
    """Ensure that reviewer application forms have required name and email fields.

    The function checks for fields named ``nome`` and ``email`` in ``formulario``.
    Missing fields are created with ``obrigatorio=True``, ``protegido=True`` and type ``text``; existing
    fields are marked as required and protected if not already.
    """

    existing = {campo.nome: campo for campo in formulario.campos}
    for field in ("nome", "email"):
        campo = existing.get(field)
        if campo is None:
            db.session.add(
                CampoFormulario(
                    formulario_id=formulario.id,
                    nome=field,
                    tipo="text",
                    obrigatorio=True,
                    protegido=True,  # Marca como protegido para impedir edição/exclusão
                )
            )
        else:
            # Marca campos existentes como obrigatórios e protegidos
            if not campo.obrigatorio:
                campo.obrigatorio = True
            if not campo.protegido:
                campo.protegido = True
    db.session.flush()
