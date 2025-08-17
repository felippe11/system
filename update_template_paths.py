#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Atualiza chamadas render_template("arquivo.html", ...)
inserindo o sub-diretório adequado segundo o dicionário `mapping`.
"""

import logging
import os
import re
import argparse
from pathlib import Path

logger = logging.getLogger(__name__)

# ────────────────────────────────
# 1) Mapeamento: arquivo → sub-pasta
#    (adicione ou ajuste conforme precisar)
# ────────────────────────────────
mapping: dict[str, str] = {
    # ── auth ───────────────────
    "login.html": "auth",
    "cadastro.html": "auth",
    "cadastro_participante.html": "auth",
    "cadastro_ministrante.html": "auth",
    "cadastro_professor.html": "auth",
    "cadastro_usuario.html": "auth",
    "cadastrar_cliente.html": "auth",
    "esqueci_senha_cpf.html": "auth",
    "reset_senha_cpf.html": "auth",

    # ── dashboard ──────────────
    "dashboard_admin.html": "dashboard",
    "dashboard_participante.html": "dashboard",
    "dashboard_ministrante.html": "dashboard",
    "dashboard_professor.html": "dashboard",
    "dashboard_cliente.html": "dashboard",
    "dashboard_superadmin.html": "dashboard",

    # ── evento ─────────────────
    "criar_evento.html": "evento",
    "configurar_evento.html": "evento",
    "listar_inscritos_evento.html": "evento",
    "eventos_disponiveis.html": "evento",

    # ── inscricao ──────────────
    "gerenciar_inscricoes.html": "inscricao",
    "preencher_formulario.html": "inscricao",

    # ── oficina ────────────────
    "criar_oficina.html": "oficina",
    "editar_oficina.html": "oficina",
    "feedback_oficina.html": "oficina",

    # ── sorteio ────────────────
    "criar_sorteio.html": "sorteio",
    "gerenciar_sorteios.html": "sorteio",

    # ── trabalho ───────────────
    "meus_trabalhos.html": "trabalho",
    "avaliar_trabalho.html": "trabalho",
    "avaliar_trabalhos.html": "trabalho",
    "submeter_trabalho.html": "trabalho",
    "definir_status_resposta.html": "trabalho",
    "listar_respostas.html": "trabalho",
    "dar_feedback_resposta.html": "trabalho",
    "visualizar_resposta.html": "trabalho",

    # ── agendamento ────────────
    "criar_agendamento.html": "agendamento",
    "editar_agendamento.html": "agendamento",
    "configurar_agendamentos.html": "agendamento",
    "configurar_horarios_agendamento.html": "agendamento",
    "gerar_horarios_agendamento.html": "agendamento",
    "eventos_agendamento.html": "agendamento",
    "relatorio_geral_agendamentos.html": "agendamento",
    "listar_agendamentos.html": "agendamento",

    # ── certificado ────────────
    "templates_certificado.html": "certificado",
    "upload_personalizacao_cert.html": "certificado",
    "usar_template.html": "certificado",

    # ── formulario ─────────────
    "criar_formulario.html": "formulario",
    "templates_formulario.html": "formulario",
    "editar_formulario.html": "formulario",
    "formularios.html": "formulario",
    "formularios_participante.html": "formulario",
    "gerenciar_campos.html": "formulario",
    "gerenciar_campos_template.html": "formulario",
    "editar_campo.html": "formulario",

    # ── patrocinador ───────────
    "upload_material.html": "patrocinador",
    "listar_patrocinadores.html": "patrocinador",
    "gerenciar_patrocinadores.html": "patrocinador",

    # ── checkin ────────────────
    "checkin.html": "checkin",
    "checkin_qr_agendamento.html": "checkin",
    "lista_checkins.html": "checkin",
    "confirmar_checkin.html": "checkin",
    "scan_qr.html": "checkin",

    # ── config ─────────────────
    "config_system.html": "config",

    # ── relatorio ──────────────
    "enviar_relatorio.html": "relatorio",
}

# ────────────────────────────────
# 2) Regex para capturar render_template(...)
#    aceita aspas simples ou duplas
# ────────────────────────────────
pattern = re.compile(r'render_template\(\s*([\'"])([^/\'"]+\.html)\1')

# ────────────────────────────────
# 3) Pasta base do projeto
#    (pode ser passado via --base-path, padrão é o diretório atual)
# ────────────────────────────────
parser = argparse.ArgumentParser(description="Atualiza caminhos de templates")
parser.add_argument(
    "--base-path",
    type=Path,
    default=Path.cwd(),
    help="Diretório base para percorrer"
)
args = parser.parse_args()
base_path: Path = args.base_path

# ────────────────────────────────
# 4) Função de atualização
# ────────────────────────────────
def update_file(filepath: str) -> None:
    """Lê o arquivo, substitui paths e grava de volta se precisar."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    modified = False

    def repl(match: re.Match) -> str:
        quote = match.group(1)
        filename = match.group(2)

        # já contém barra? então já está OK
        if "/" in filename:
            return match.group(0)

        prefix = mapping.get(filename)
        if prefix:
            nonlocal modified
            new_filename = f"{prefix}/{filename}"
            modified = True
            return f'render_template({quote}{new_filename}{quote}'
        return match.group(0)

    new_content = pattern.sub(repl, content)

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        logger.info('Atualizado: %s', filepath)

# ────────────────────────────────
# 5) Percorre todos os .py do projeto
# ────────────────────────────────
for root, _, files in os.walk(base_path):
    for file in files:
        if file.endswith('.py'):
            update_file(os.path.join(root, file))
