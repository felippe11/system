#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para consultar e exibir dados das tabelas de avaliação de baremas

Este script conecta ao banco de dados e exibe informações das tabelas:
- avaliacao_barema: Informações gerais da avaliação
- avaliacao_criterio: Respostas individuais de cada critério
"""

import sys
import os
from datetime import datetime

# Adicionar o diretório raiz ao path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extensions import db
from models.avaliacao import AvaliacaoBarema, AvaliacaoCriterio
from models.user import Usuario
from models.review import Submission
from app import create_app

def formatar_data(data):
    """Formatar data para exibição"""
    if data:
        return data.strftime('%d/%m/%Y %H:%M:%S')
    return 'N/A'

def exibir_estatisticas_gerais():
    """Exibir estatísticas gerais das tabelas"""
    print("\n" + "="*80)
    print("📊 ESTATÍSTICAS GERAIS")
    print("="*80)
    
    # Contar registros
    total_avaliacoes = AvaliacaoBarema.query.count()
    total_criterios = AvaliacaoCriterio.query.count()
    
    print(f"Total de Avaliações de Barema: {total_avaliacoes}")
    print(f"Total de Critérios Avaliados: {total_criterios}")
    
    # Estatísticas por categoria
    categorias = db.session.query(AvaliacaoBarema.categoria, 
                                 db.func.count(AvaliacaoBarema.id).label('total'),
                                 db.func.avg(AvaliacaoBarema.nota_final).label('media_nota'),
                                 db.func.min(AvaliacaoBarema.nota_final).label('nota_min'),
                                 db.func.max(AvaliacaoBarema.nota_final).label('nota_max')
                                ).group_by(AvaliacaoBarema.categoria).all()
    
    if categorias:
        print("\n📈 Estatísticas por Categoria:")
        print("-" * 80)
        for cat in categorias:
            print(f"Categoria: {cat.categoria}")
            print(f"  - Total de avaliações: {cat.total}")
            print(f"  - Nota média: {cat.media_nota:.2f}" if cat.media_nota else "  - Nota média: N/A")
            print(f"  - Nota mínima: {cat.nota_min}" if cat.nota_min else "  - Nota mínima: N/A")
            print(f"  - Nota máxima: {cat.nota_max}" if cat.nota_max else "  - Nota máxima: N/A")
            print()

def exibir_avaliacoes_barema():
    """Exibir dados da tabela avaliacao_barema"""
    print("\n" + "="*80)
    print("📋 DADOS DA TABELA AVALIACAO_BAREMA")
    print("="*80)
    
    # Query com joins para obter informações relacionadas
    avaliacoes = db.session.query(
        AvaliacaoBarema,
        Usuario.nome.label('revisor_nome'),
        Submission.title.label('trabalho_titulo')
    ).outerjoin(
        Usuario, AvaliacaoBarema.revisor_id == Usuario.id
    ).outerjoin(
        Submission, AvaliacaoBarema.trabalho_id == Submission.id
    ).order_by(AvaliacaoBarema.data_avaliacao.desc()).all()
    
    if not avaliacoes:
        print("❌ Nenhuma avaliação encontrada na tabela avaliacao_barema.")
        return
    
    print(f"Total de registros: {len(avaliacoes)}\n")
    
    for i, (avaliacao, revisor_nome, trabalho_titulo) in enumerate(avaliacoes, 1):
        print(f"📝 Avaliação #{i} (ID: {avaliacao.id})")
        print(f"   Trabalho ID: {avaliacao.trabalho_id}")
        print(f"   Título do Trabalho: {trabalho_titulo or 'N/A'}")
        print(f"   Revisor ID: {avaliacao.revisor_id}")
        print(f"   Nome do Revisor: {revisor_nome or 'N/A'}")
        print(f"   Barema ID: {avaliacao.barema_id}")
        print(f"   Categoria: {avaliacao.categoria}")
        print(f"   Nota Final: {avaliacao.nota_final}")
        print(f"   Data da Avaliação: {formatar_data(avaliacao.data_avaliacao)}")
        print("-" * 60)

def exibir_criterios_avaliacao():
    """Exibir dados da tabela avaliacao_criterio"""
    print("\n" + "="*80)
    print("🎯 DADOS DA TABELA AVALIACAO_CRITERIO")
    print("="*80)
    
    # Query com join para obter informações da avaliação principal
    criterios = db.session.query(
        AvaliacaoCriterio,
        AvaliacaoBarema.categoria,
        AvaliacaoBarema.trabalho_id
    ).join(
        AvaliacaoBarema, AvaliacaoCriterio.avaliacao_id == AvaliacaoBarema.id
    ).order_by(AvaliacaoBarema.id, AvaliacaoCriterio.criterio_id).all()
    
    if not criterios:
        print("❌ Nenhum critério encontrado na tabela avaliacao_criterio.")
        return
    
    print(f"Total de registros: {len(criterios)}\n")
    
    # Agrupar por avaliação
    avaliacoes_agrupadas = {}
    for criterio, categoria, trabalho_id in criterios:
        avaliacao_id = criterio.avaliacao_id
        if avaliacao_id not in avaliacoes_agrupadas:
            avaliacoes_agrupadas[avaliacao_id] = {
                'categoria': categoria,
                'trabalho_id': trabalho_id,
                'criterios': []
            }
        avaliacoes_agrupadas[avaliacao_id]['criterios'].append(criterio)
    
    for avaliacao_id, dados in avaliacoes_agrupadas.items():
        print(f"🎯 Avaliação ID: {avaliacao_id}")
        print(f"   Trabalho ID: {dados['trabalho_id']}")
        print(f"   Categoria: {dados['categoria']}")
        print(f"   Critérios avaliados: {len(dados['criterios'])}")
        print()
        
        for criterio in dados['criterios']:
            print(f"     ✓ Critério ID: {criterio.criterio_id}")
            print(f"       Nota: {criterio.nota}")
            if criterio.observacao:
                print(f"       Observação: {criterio.observacao}")
            else:
                print(f"       Observação: (sem observação)")
            print()
        print("-" * 60)

def exibir_relatorio_detalhado():
    """Exibir relatório detalhado com join das duas tabelas"""
    print("\n" + "="*80)
    print("📊 RELATÓRIO DETALHADO - AVALIAÇÕES COMPLETAS")
    print("="*80)
    
    # Query complexa com joins
    relatorio = db.session.query(
        AvaliacaoBarema,
        Usuario.nome.label('revisor_nome'),
        Submission.title.label('trabalho_titulo'),
        db.func.count(AvaliacaoCriterio.id).label('total_criterios'),
        db.func.avg(AvaliacaoCriterio.nota).label('media_criterios')
    ).outerjoin(
        Usuario, AvaliacaoBarema.revisor_id == Usuario.id
    ).outerjoin(
        Submission, AvaliacaoBarema.trabalho_id == Submission.id
    ).outerjoin(
        AvaliacaoCriterio, AvaliacaoBarema.id == AvaliacaoCriterio.avaliacao_id
    ).group_by(
        AvaliacaoBarema.id, Usuario.nome, Submission.title
    ).order_by(AvaliacaoBarema.data_avaliacao.desc()).all()
    
    if not relatorio:
        print("❌ Nenhum dado encontrado para o relatório detalhado.")
        return
    
    for i, (avaliacao, revisor_nome, trabalho_titulo, total_criterios, media_criterios) in enumerate(relatorio, 1):
        print(f"📋 Relatório #{i}")
        print(f"   ID da Avaliação: {avaliacao.id}")
        print(f"   Trabalho: {trabalho_titulo or 'N/A'} (ID: {avaliacao.trabalho_id})")
        print(f"   Revisor: {revisor_nome or 'N/A'}")
        print(f"   Categoria: {avaliacao.categoria}")
        print(f"   Nota Final: {avaliacao.nota_final}")
        print(f"   Total de Critérios: {total_criterios or 0}")
        print(f"   Média dos Critérios: {media_criterios:.2f}" if media_criterios else "   Média dos Critérios: N/A")
        print(f"   Data: {formatar_data(avaliacao.data_avaliacao)}")
        print("-" * 60)

def main():
    """Função principal"""
    print("🔍 CONSULTA DE DADOS - SISTEMA DE AVALIAÇÃO DE BAREMAS")
    print("=" * 80)
    print(f"Data/Hora da consulta: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Criar contexto da aplicação
    app = create_app()
    
    with app.app_context():
        try:
            # Exibir estatísticas gerais
            exibir_estatisticas_gerais()
            
            # Exibir dados das tabelas
            exibir_avaliacoes_barema()
            exibir_criterios_avaliacao()
            
            # Exibir relatório detalhado
            exibir_relatorio_detalhado()
            
            print("\n✅ Consulta concluída com sucesso!")
            
        except Exception as e:
            print(f"\n❌ Erro durante a consulta: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()