#!/usr/bin/env python3
"""
Script para criar o formulário de trabalhos no banco de dados.
Este script deve ser executado no contexto da aplicação Flask.
"""

import sys
import os

# Adicionar o diretório raiz do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.event import Formulario, CampoFormulario
from sqlalchemy import text

def criar_formulario_trabalhos():
    """Cria o formulário de trabalhos e seus campos no banco de dados."""
    app = create_app()
    
    with app.app_context():
        try:
            # Verificar se o formulário já existe
            formulario_existente = Formulario.query.filter_by(nome='Formulário de Trabalhos').first()
            if formulario_existente:
                print(f"Formulário já existe com ID: {formulario_existente.id}")
                return formulario_existente.id
            
            # Criar o formulário
            formulario = Formulario(
                nome='Formulário de Trabalhos',
                descricao='Formulário para cadastro de trabalhos acadêmicos pelos clientes',
                permitir_multiplas_respostas=True,
                is_submission_form=False
            )
            
            db.session.add(formulario)
            db.session.flush()  # Para obter o ID
            
            print(f"Formulário criado com ID: {formulario.id}")
            
            # Criar os campos do formulário
            campos = [
                {
                    'nome': 'Título',
                    'tipo': 'text',
                    'obrigatorio': True,
                    'descricao': 'Título do trabalho acadêmico'
                },
                {
                    'nome': 'Categoria',
                    'tipo': 'select',
                    'opcoes': 'Prática Educacional,Pesquisa Inovadora,Produto Inovador',
                    'obrigatorio': True,
                    'descricao': 'Categoria do trabalho acadêmico'
                },
                {
                    'nome': 'Rede de Ensino',
                    'tipo': 'text',
                    'obrigatorio': True,
                    'descricao': 'Rede de ensino onde o trabalho foi desenvolvido'
                },
                {
                    'nome': 'Etapa de Ensino',
                    'tipo': 'text',
                    'obrigatorio': True,
                    'descricao': 'Etapa de ensino relacionada ao trabalho'
                },
                {
                    'nome': 'URL do PDF',
                    'tipo': 'url',
                    'obrigatorio': True,
                    'descricao': 'URL do arquivo PDF do trabalho'
                }
            ]
            
            for campo_data in campos:
                campo = CampoFormulario(
                    formulario_id=formulario.id,
                    nome=campo_data['nome'],
                    tipo=campo_data['tipo'],
                    obrigatorio=campo_data['obrigatorio'],
                    descricao=campo_data['descricao'],
                    opcoes=campo_data.get('opcoes')
                )
                db.session.add(campo)
                print(f"Campo criado: {campo_data['nome']}")
            
            # Commit das alterações
            db.session.commit()
            print("Formulário de trabalhos criado com sucesso!")
            
            # Verificar os campos criados
            campos_criados = CampoFormulario.query.filter_by(formulario_id=formulario.id).all()
            print(f"\nCampos criados ({len(campos_criados)}):")
            for campo in campos_criados:
                print(f"- {campo.nome} ({campo.tipo}) - Obrigatório: {campo.obrigatorio}")
                if campo.opcoes:
                    print(f"  Opções: {campo.opcoes}")
            
            return formulario.id
            
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao criar formulário: {e}")
            raise

if __name__ == '__main__':
    formulario_id = criar_formulario_trabalhos()
    print(f"\nFormulário criado com ID: {formulario_id}")