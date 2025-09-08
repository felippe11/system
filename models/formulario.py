"""Utilities for default submission form.

This module ensures that the required "Formulário de Trabalhos"
exists in the database. It exposes helpers used during application
startup and deployment scripts.
"""

from __future__ import annotations

from extensions import db
from models.event import CampoFormulario, Formulario

FORM_NAME = "Formulário de Trabalhos"


def formulario_trabalhos_exists() -> bool:
    """Return True if the default form is present."""
    return Formulario.query.filter_by(nome=FORM_NAME).first() is not None


def ensure_formulario_trabalhos() -> Formulario:
    """Ensure the default form exists and return it.

    Creates the form with predefined fields when it is missing.
    """
    formulario = Formulario.query.filter_by(nome=FORM_NAME).first()
    if formulario:
        return formulario

    formulario = Formulario(
        nome=FORM_NAME,
        descricao=
        "Formulário para cadastro de trabalhos acadêmicos pelos clientes",
        permitir_multiplas_respostas=True,
        is_submission_form=False,
    )
    db.session.add(formulario)
    db.session.flush()

    campos = [
        {
            "nome": "Título",
            "tipo": "text",
            "obrigatorio": True,
            "descricao": "Título do trabalho acadêmico",
        },
        {
            "nome": "Categoria",
            "tipo": "select",
            "opcoes": "Prática Educacional,Pesquisa Inovadora,Produto Inovador",
            "obrigatorio": True,
            "descricao": "Categoria do trabalho acadêmico",
        },
        {
            "nome": "Rede de Ensino",
            "tipo": "text",
            "obrigatorio": True,
            "descricao": "Rede de ensino onde o trabalho foi desenvolvido",
        },
        {
            "nome": "Etapa de Ensino",
            "tipo": "text",
            "obrigatorio": True,
            "descricao": "Etapa de ensino relacionada ao trabalho",
        },
        {
            "nome": "URL do PDF",
            "tipo": "url",
            "obrigatorio": True,
            "descricao": "URL do arquivo PDF do trabalho",
        },
    ]
    for campo in campos:
        db.session.add(
            CampoFormulario(
                formulario_id=formulario.id,
                nome=campo["nome"],
                tipo=campo["tipo"],
                obrigatorio=campo["obrigatorio"],
                descricao=campo["descricao"],
                opcoes=campo.get("opcoes"),
            )
        )

    db.session.commit()
    return formulario
