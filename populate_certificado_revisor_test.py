#!/usr/bin/env python3
"""
Script de população para testar o sistema de certificados de revisores.
Cria dados completos para testar todas as funcionalidades.
"""

import os
import sys
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import (
    Usuario, Cliente, Evento, 
    RevisorProcess, RevisorCandidatura, 
    CertificadoRevisorConfig, CertificadoRevisor,
    revisor_process_evento_association
)

def create_test_data():
    """Cria dados completos para teste do sistema de certificados de revisores."""
    
    app = create_app()
    
    with app.app_context():
        print("🚀 Iniciando população de dados de teste para certificados de revisores...")
        
        # 1. Criar cliente de teste
        cliente = Cliente.query.filter_by(email="cliente.teste@example.com").first()
        if not cliente:
            cliente = Cliente(
                nome="Cliente Teste Certificados",
                email="cliente.teste@example.com",
                senha=generate_password_hash("123456"),
                ativo=True
            )
            db.session.add(cliente)
            db.session.commit()
            print(f"✅ Cliente criado: {cliente.nome} (ID: {cliente.id})")
        else:
            print(f"ℹ️  Cliente já existe: {cliente.nome} (ID: {cliente.id})")
        
        # 2. Criar evento de teste
        evento = Evento.query.filter_by(nome="Evento Teste Certificados").first()
        if not evento:
            evento = Evento(
                nome="Evento Teste Certificados",
                descricao="Evento para testar certificados de revisores",
                data_inicio=datetime.now() - timedelta(days=30),
                data_fim=datetime.now() + timedelta(days=30),
                localizacao="Local Teste",
                cliente_id=cliente.id,
                status="ativo"
            )
            db.session.add(evento)
            db.session.commit()
            print(f"✅ Evento criado: {evento.nome} (ID: {evento.id})")
        else:
            print(f"ℹ️  Evento já existe: {evento.nome} (ID: {evento.id})")
        
        # 3. Criar processo de revisor
        processo = RevisorProcess.query.filter_by(
            cliente_id=cliente.id,
            nome="Processo Teste Certificados"
        ).first()
        
        if not processo:
            processo = RevisorProcess(
                cliente_id=cliente.id,
                nome="Processo Teste Certificados",
                descricao="Processo seletivo para testar certificados",
                status="aberto",
                num_etapas=1,
                availability_start=datetime.now() - timedelta(days=60),
                availability_end=datetime.now() + timedelta(days=30)
            )
            db.session.add(processo)
            db.session.commit()
            print(f"✅ Processo de revisor criado: {processo.nome} (ID: {processo.id})")
        else:
            print(f"ℹ️  Processo já existe: {processo.nome} (ID: {processo.id})")
        
        # 4. Associar processo ao evento
        if evento not in processo.eventos:
            processo.eventos.append(evento)
            db.session.commit()
            print(f"✅ Processo associado ao evento")
        
        # 5. Criar usuários revisores de teste
        revisores_data = [
            {
                "nome": "Dr. João Silva",
                "email": "joao.silva@example.com",
                "cpf": "111.111.111-11",
                "formacao": "Doutorado em Ciência da Computação"
            },
            {
                "nome": "Dra. Maria Santos",
                "email": "maria.santos@example.com", 
                "cpf": "222.222.222-22",
                "formacao": "Doutorado em Engenharia de Software"
            },
            {
                "nome": "Dr. Pedro Oliveira",
                "email": "pedro.oliveira@example.com",
                "cpf": "333.333.333-33",
                "formacao": "Doutorado em Inteligência Artificial"
            },
            {
                "nome": "Dra. Ana Costa",
                "email": "ana.costa@example.com",
                "cpf": "444.444.444-44",
                "formacao": "Doutorado em Machine Learning"
            },
            {
                "nome": "Dr. Carlos Ferreira",
                "email": "carlos.ferreira@example.com",
                "cpf": "555.555.555-55",
                "formacao": "Doutorado em Data Science"
            }
        ]
        
        revisores_criados = []
        for revisor_data in revisores_data:
            usuario = Usuario.query.filter_by(email=revisor_data["email"]).first()
            if not usuario:
                usuario = Usuario(
                    nome=revisor_data["nome"],
                    email=revisor_data["email"],
                    senha=generate_password_hash("123456"),
                    cpf=revisor_data["cpf"],
                    formacao=revisor_data["formacao"],
                    tipo="revisor",
                    ativo=True
                )
                db.session.add(usuario)
                db.session.commit()
                print(f"✅ Revisor criado: {usuario.nome} (ID: {usuario.id})")
            else:
                print(f"ℹ️  Revisor já existe: {usuario.nome} (ID: {usuario.id})")
            
            revisores_criados.append(usuario)
        
        # 6. Criar candidaturas aprovadas
        for usuario in revisores_criados:
            candidatura = RevisorCandidatura.query.filter_by(
                process_id=processo.id,
                email=usuario.email
            ).first()
            
            if not candidatura:
                candidatura = RevisorCandidatura(
                    process_id=processo.id,
                    nome=usuario.nome,
                    email=usuario.email,
                    status="aprovado",
                    etapa_atual=1,
                    respostas={
                        "experiencia": "Mais de 5 anos",
                        "area_interesse": usuario.formacao,
                        "disponibilidade": "Total",
                        "motivacao": "Contribuir para o desenvolvimento científico"
                    }
                )
                db.session.add(candidatura)
                db.session.commit()
                print(f"✅ Candidatura aprovada: {candidatura.nome}")
            else:
                # Atualizar status se necessário
                if candidatura.status != "aprovado":
                    candidatura.status = "aprovado"
                    db.session.commit()
                    print(f"✅ Candidatura atualizada para aprovada: {candidatura.nome}")
                else:
                    print(f"ℹ️  Candidatura já aprovada: {candidatura.nome}")
        
        # 7. Criar configuração de certificado
        config = CertificadoRevisorConfig.query.filter_by(
            cliente_id=cliente.id,
            evento_id=evento.id
        ).first()
        
        if not config:
            config = CertificadoRevisorConfig(
                cliente_id=cliente.id,
                evento_id=evento.id,
                titulo_certificado="Certificado de Revisor Científico",
                texto_certificado="Certificamos que {nome_revisor} atuou como revisor de trabalhos científicos no evento '{evento_nome}', contribuindo para a avaliação e seleção de trabalhos de alta qualidade acadêmica. Durante o período de revisão, demonstrou competência técnica e comprometimento com os padrões de excelência científica.",
                fundo_certificado="static/certificados/fundo_padrao.jpg",
                liberacao_automatica=False,
                criterio_trabalhos_minimos=1,
                ativo=True
            )
            db.session.add(config)
            db.session.commit()
            print(f"✅ Configuração de certificado criada")
        else:
            print(f"ℹ️  Configuração já existe")
        
        # 8. Criar alguns certificados já liberados para teste
        certificados_liberados = []
        for i, usuario in enumerate(revisores_criados[:3]):  # Apenas os 3 primeiros
            certificado = CertificadoRevisor.query.filter_by(
                revisor_id=usuario.id,
                cliente_id=cliente.id,
                evento_id=evento.id
            ).first()
            
            if not certificado:
                certificado = CertificadoRevisor(
                    revisor_id=usuario.id,
                    cliente_id=cliente.id,
                    evento_id=evento.id,
                    liberado=True,
                    data_liberacao=datetime.now() - timedelta(days=i),
                    liberado_por=None,  # Cliente liberando
                    titulo=config.titulo_certificado,
                    texto_personalizado=config.texto_certificado,
                    fundo_personalizado=config.fundo_certificado,
                    trabalhos_revisados=3 + i,  # Simular diferentes quantidades
                    data_inicio_atividade=datetime.now() - timedelta(days=30),
                    data_fim_atividade=datetime.now() - timedelta(days=1)
                )
                db.session.add(certificado)
                db.session.commit()
                certificados_liberados.append(certificado)
                print(f"✅ Certificado liberado: {usuario.nome}")
            else:
                certificados_liberados.append(certificado)
                print(f"ℹ️  Certificado já existe: {usuario.nome}")
        
        # 9. Criar alguns certificados não liberados
        for usuario in revisores_criados[3:]:  # Os 2 últimos
            certificado = CertificadoRevisor.query.filter_by(
                revisor_id=usuario.id,
                cliente_id=cliente.id,
                evento_id=evento.id
            ).first()
            
            if not certificado:
                certificado = CertificadoRevisor(
                    revisor_id=usuario.id,
                    cliente_id=cliente.id,
                    evento_id=evento.id,
                    liberado=False,
                    titulo=config.titulo_certificado,
                    texto_personalizado=config.texto_certificado,
                    fundo_personalizado=config.fundo_certificado,
                    trabalhos_revisados=1 + len(certificados_liberados),
                    data_inicio_atividade=datetime.now() - timedelta(days=20),
                    data_fim_atividade=datetime.now() - timedelta(days=5)
                )
                db.session.add(certificado)
                db.session.commit()
                print(f"✅ Certificado não liberado criado: {usuario.nome}")
            else:
                print(f"ℹ️  Certificado já existe: {usuario.nome}")
        
        print("\n🎉 POPULAÇÃO CONCLUÍDA COM SUCESSO!")
        print("\n📊 RESUMO DOS DADOS CRIADOS:")
        print(f"   • Cliente: {cliente.nome} (ID: {cliente.id})")
        print(f"   • Evento: {evento.nome} (ID: {evento.id})")
        print(f"   • Processo: {processo.nome} (ID: {processo.id})")
        print(f"   • Revisores: {len(revisores_criados)}")
        print(f"   • Candidaturas aprovadas: {len(revisores_criados)}")
        print(f"   • Certificados liberados: {len(certificados_liberados)}")
        print(f"   • Certificados não liberados: {len(revisores_criados) - len(certificados_liberados)}")
        
        print("\n🔗 LINKS PARA TESTE:")
        print(f"   • Dashboard Cliente: http://127.0.0.1:5000/dashboard_cliente")
        print(f"   • Configurar Certificados: http://127.0.0.1:5000/certificado_revisor/configurar/{evento.id}")
        print(f"   • Login Cliente: cliente.teste@example.com / 123456")
        
        print("\n👥 CREDENCIAIS DOS REVISORES:")
        for usuario in revisores_criados:
            print(f"   • {usuario.nome}: {usuario.email} / 123456")
        
        print("\n✨ PRÓXIMOS PASSOS:")
        print("   1. Faça login como cliente")
        print("   2. Acesse a aba 'Revisores' no dashboard")
        print("   3. Clique em 'Certificados de Revisores'")
        print("   4. Configure e teste as funcionalidades")
        print("   5. Faça login como revisor para testar o download")

if __name__ == "__main__":
    create_test_data()
