#!/usr/bin/env python3
"""Organiza arquivos de template em suas pastas usando shutil.move."""
import shutil
from pathlib import Path

moves = [
    ("agendar_visita.html", "agendamento"),
    ("dashboard_agendamentos.html", "agendamento"),
    ("detalhes_agendamentos.html", "agendamento"),
    ("configurar_regras_inscricao.html", "agendamento"),
    ("criar_evento_agendamento.html", "agendamento"),
    ("criar_periodo_agendamento.html", "agendamento"),
    ("listar_horarios_agendamento.html", "agendamento"),
    ("criar_template.html", "template"),
    ("editar_ministrante.html", "ministrante"),
    ("gerenciar_ministrantes.html", "ministrante"),
    ("editar_participante.html", "participante"),
    ("editar_sala_visitacao.html", "sala"),
    ("salas_visitacao.html", "sala"),
    ("pagamento_certo.html", "pagamento"),
    ("pagamento_errado.html", "pagamento"),
    ("feedback.html", "feedback"),
    ("importar_agendamentos.html", "importacao"),
]

def main() -> None:
    base = Path("templates")
    for filename, folder in moves:
        src = base / filename
        dest_dir = base / folder
        dest = dest_dir / filename
        if src.exists():
            dest_dir.mkdir(parents=True, exist_ok=True)
            print(f"Movendo {src} -> {dest}")
            shutil.move(str(src), str(dest))
        else:
            print(f"Arquivo {src} não encontrado, ignorando")

if __name__ == "__main__":
    main()
