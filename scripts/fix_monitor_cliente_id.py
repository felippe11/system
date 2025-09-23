#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Atualiza monitores com ``cliente_id`` nulo usando agendamentos existentes."""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models.user import Monitor
from models.event import MonitorAgendamento, AgendamentoVisita


def fix_monitor_cliente_id():
    """Define o cliente para monitores que estão sem ``cliente_id``."""
    app = create_app()
    with app.app_context():
        print("=== Atualizando monitores sem cliente_id ===")
        monitores = Monitor.query.filter_by(cliente_id=None).all()
        print(f"Monitores encontrados: {len(monitores)}")

        atualizados = 0
        for monitor in monitores:
            ma = (
                MonitorAgendamento.query.join(
                    AgendamentoVisita,
                    MonitorAgendamento.agendamento_id == AgendamentoVisita.id,
                )
                .filter(
                    MonitorAgendamento.monitor_id == monitor.id,
                    AgendamentoVisita.cliente_id.isnot(None),
                )
                .first()
            )
            if ma:
                monitor.cliente_id = ma.agendamento.cliente_id
                atualizados += 1
                print(
                    f"Monitor {monitor.id} atualizado para cliente "
                    f"{monitor.cliente_id}"
                )

        if atualizados:
            db.session.commit()
            print(f"{atualizados} monitores atualizados.")
        else:
            print("Nenhum monitor atualizado.")


if __name__ == "__main__":
    fix_monitor_cliente_id()
