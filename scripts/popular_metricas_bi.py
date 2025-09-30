#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para popular métricas padrão do Business Intelligence
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.relatorio_bi import MetricaBI

def popular_metricas_padrao():
    """Popula as métricas padrão do sistema de BI"""
    
    metricas_padrao = [
        {
            'nome': 'inscricoes_totais',
            'descricao': 'Total de inscrições realizadas',
            'formula_sql': 'SELECT COUNT(*) FROM inscricao WHERE status_pagamento = \'approved\'',
            'tipo_dado': 'numero'
        },
        {
            'nome': 'usuarios_unicos',
            'descricao': 'Número de usuários únicos inscritos',
            'formula_sql': 'SELECT COUNT(DISTINCT usuario_id) FROM inscricao WHERE status_pagamento = \'approved\'',
            'tipo_dado': 'numero'
        },
        {
            'nome': 'checkins_total',
            'descricao': 'Total de check-ins realizados',
            'formula_sql': 'SELECT COUNT(*) FROM checkin',
            'tipo_dado': 'numero'
        },
        {
            'nome': 'taxa_presenca',
            'descricao': 'Taxa de presença (check-ins / inscrições confirmadas)',
            'formula_sql': '''
                SELECT 
                    CASE 
                        WHEN COUNT(i.id) > 0 THEN 
                            (COUNT(c.id)::float / COUNT(i.id)) * 100 
                        ELSE 0 
                    END as taxa
                FROM inscricao i
                LEFT JOIN checkin c ON c.inscricao_id = i.id
                WHERE i.status_pagamento = 'approved'
            ''',
            'tipo_dado': 'percentual'
        },
        {
            'nome': 'receita_total',
            'descricao': 'Receita total gerada',
            'formula_sql': 'SELECT COALESCE(SUM(valor), 0) FROM pagamento WHERE status = \'approved\'',
            'tipo_dado': 'moeda'
        },
        {
            'nome': 'ticket_medio',
            'descricao': 'Valor médio por inscrição',
            'formula_sql': '''
                SELECT 
                    CASE 
                        WHEN COUNT(*) > 0 THEN 
                            COALESCE(SUM(valor), 0) / COUNT(*) 
                        ELSE 0 
                    END as ticket_medio
                FROM pagamento 
                WHERE status = 'approved'
            ''',
            'tipo_dado': 'moeda'
        },
        {
            'nome': 'satisfacao_media',
            'descricao': 'Nota média de satisfação',
            'formula_sql': '''
                SELECT 
                    CASE 
                        WHEN COUNT(*) > 0 THEN 
                            AVG(CAST(resposta AS FLOAT)) 
                        ELSE 0 
                    END as satisfacao_media
                FROM feedback_resposta fr
                JOIN feedback_pergunta fp ON fp.id = fr.pergunta_id
                WHERE fp.tipo = 'nota' AND fr.resposta ~ '^[0-9]+$'
            ''',
            'tipo_dado': 'numero'
        },
        {
            'nome': 'nps_score',
            'descricao': 'Net Promoter Score',
            'formula_sql': '''
                SELECT 
                    CASE 
                        WHEN COUNT(*) > 0 THEN 
                            ((COUNT(CASE WHEN CAST(resposta AS INTEGER) >= 9 THEN 1 END) - 
                              COUNT(CASE WHEN CAST(resposta AS INTEGER) <= 6 THEN 1 END))::float / COUNT(*)) * 100
                        ELSE 0 
                    END as nps
                FROM feedback_resposta fr
                JOIN feedback_pergunta fp ON fp.id = fr.pergunta_id
                WHERE fp.tipo = 'nps' AND fr.resposta ~ '^[0-9]+$'
            ''',
            'tipo_dado': 'numero'
        },
        {
            'nome': 'certificados_gerados',
            'descricao': 'Total de certificados gerados',
            'formula_sql': 'SELECT COUNT(*) FROM certificado WHERE status = \'gerado\'',
            'tipo_dado': 'numero'
        },
        {
            'nome': 'taxa_conversao',
            'descricao': 'Taxa de conversão de visitantes em inscritos',
            'formula_sql': '''
                SELECT 
                    CASE 
                        WHEN 10000 > 0 THEN 
                            (COUNT(*)::float / 10000) * 100 
                        ELSE 0 
                    END as taxa_conversao
                FROM inscricao 
                WHERE status_pagamento = 'approved'
            ''',
            'tipo_dado': 'percentual'
        },
        {
            'nome': 'ocupacao_media',
            'descricao': 'Taxa média de ocupação das atividades',
            'formula_sql': '''
                SELECT 
                    CASE 
                        WHEN COUNT(o.id) > 0 THEN 
                            AVG(
                                CASE 
                                    WHEN o.vagas > 0 THEN 
                                        (COUNT(i.id)::float / o.vagas) * 100 
                                    ELSE 0 
                                END
                            )
                        ELSE 0 
                    END as ocupacao_media
                FROM oficina o
                LEFT JOIN inscricao i ON i.oficina_id = o.id AND i.status_pagamento = 'approved'
                WHERE o.tipo_inscricao = 'com_inscricao_com_limite'
                GROUP BY o.id
            ''',
            'tipo_dado': 'percentual'
        },
        {
            'nome': 'tempo_medio_checkin',
            'descricao': 'Tempo médio entre inscrição e check-in',
            'formula_sql': '''
                SELECT 
                    CASE 
                        WHEN COUNT(*) > 0 THEN 
                            AVG(EXTRACT(EPOCH FROM (c.data_hora - i.data_inscricao))/3600)
                        ELSE 0 
                    END as tempo_medio_horas
                FROM inscricao i
                JOIN checkin c ON c.inscricao_id = i.id
                WHERE i.status_pagamento = 'approved'
            ''',
            'tipo_dado': 'tempo'
        }
    ]
    
    print("Iniciando população das métricas padrão...")
    
    for metrica_data in metricas_padrao:
        # Verificar se a métrica já existe
        metrica_existente = MetricaBI.query.filter_by(nome=metrica_data['nome']).first()
        
        if metrica_existente:
            print(f"Métrica '{metrica_data['nome']}' já existe. Atualizando...")
            metrica_existente.descricao = metrica_data['descricao']
            metrica_existente.formula_sql = metrica_data['formula_sql']
            metrica_existente.tipo_dado = metrica_data['tipo_dado']
        else:
            print(f"Criando métrica '{metrica_data['nome']}'...")
            nova_metrica = MetricaBI(
                nome=metrica_data['nome'],
                descricao=metrica_data['descricao'],
                formula_sql=metrica_data['formula_sql'],
                tipo_dado=metrica_data['tipo_dado']
            )
            db.session.add(nova_metrica)
    
    try:
        db.session.commit()
        print("✅ Métricas padrão populadas com sucesso!")
        print(f"Total de métricas: {len(metricas_padrao)}")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao popular métricas: {e}")
        raise

def main():
    """Função principal"""
    app = create_app()
    
    with app.app_context():
        popular_metricas_padrao()

if __name__ == '__main__':
    main()











