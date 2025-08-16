from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from flask import Request

from extensions import db
from models import RevisorEtapa, RevisorProcess


def parse_revisor_form(req: Request) -> Dict[str, Any]:
    """Extracts and normalizes form data for reviewer process configuration."""
    formulario_id = req.form.get("formulario_id", type=int)
    num_etapas = req.form.get("num_etapas", type=int, default=1)
    stage_names: List[str] = req.form.getlist("stage_name")
    start_raw = req.form.get("availability_start")
    end_raw = req.form.get("availability_end")
    exibir_val = req.form.get("exibir_participantes")
    exibir_para_participantes = exibir_val in {"on", "1", "true"}

    def _parse_dt(raw: str | None) -> datetime | None:
        try:
            return datetime.strptime(raw, "%Y-%m-%d") if raw else None
        except ValueError:
            return None

    return {
        "formulario_id": formulario_id,
        "num_etapas": num_etapas,
        "stage_names": stage_names,
        "availability_start": _parse_dt(start_raw),
        "availability_end": _parse_dt(end_raw),
        "exibir_para_participantes": exibir_para_participantes,
    }


def update_revisor_process(processo: RevisorProcess, dados: Dict[str, Any]) -> None:
    """Updates a reviewer process with parsed data."""
    processo.formulario_id = dados.get("formulario_id")
    processo.num_etapas = dados.get("num_etapas")
    processo.availability_start = dados.get("availability_start")
    processo.availability_end = dados.get("availability_end")
    processo.exibir_para_participantes = dados.get("exibir_para_participantes")
    db.session.commit()


def recreate_stages(processo: RevisorProcess, stage_names: List[str]) -> None:
    """Recreates stages for the given reviewer process."""
    RevisorEtapa.query.filter_by(process_id=processo.id).delete()
    for idx, nome in enumerate(stage_names, start=1):
        if nome:
            db.session.add(RevisorEtapa(process_id=processo.id, numero=idx, nome=nome))
    db.session.commit()
