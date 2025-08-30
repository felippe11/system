#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import app
from models.event import NecessidadeEspecial, AlunoVisitante
from extensions import db

with app.app_context():
    print('=== Verificação da tabela NecessidadeEspecial ===')
    
    # Contar total de registros
    total_necessidades = NecessidadeEspecial.query.count()
    print(f'Total de registros NecessidadeEspecial: {total_necessidades}')
    
    # Contar total de alunos
    total_alunos = AlunoVisitante.query.count()
    print(f'Total de alunos visitantes: {total_alunos}')
    
    if total_necessidades > 0:
        print('\n=== Primeiros 5 registros ===')
        for n in NecessidadeEspecial.query.limit(5).all():
            print(f'ID: {n.id}, Aluno ID: {n.aluno_id}, Tipo: {n.tipo}, Descrição: {n.descricao[:50]}...')
        
        print('\n=== Tipos de necessidades especiais ===')
        tipos = db.session.query(NecessidadeEspecial.tipo, db.func.count(NecessidadeEspecial.id)).group_by(NecessidadeEspecial.tipo).all()
        for tipo, count in tipos:
            print(f'{tipo}: {count} registros')
    else:
        print('\n⚠️  Nenhum registro encontrado na tabela NecessidadeEspecial!')
        print('\n=== Verificando se existem alunos com necessidades especiais ===')
        
        # Verificar se existem alunos que deveriam ter necessidades especiais
        alunos_sample = AlunoVisitante.query.limit(10).all()
        print(f'\nPrimeiros {len(alunos_sample)} alunos:')
        for aluno in alunos_sample:
            print(f'ID: {aluno.id}, Nome: {aluno.nome}, Necessidade: {getattr(aluno, "necessidade_especial", "Não definida")}')