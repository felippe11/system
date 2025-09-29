#!/usr/bin/env python3
"""
Script simples para popular dados de teste de certificados de revisores.
"""

import os
import sys
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Executa a população de dados."""
    try:
        from app import create_app
        from extensions import db
        from models import (
            Usuario, Cliente, Evento, 
            RevisorProcess, RevisorCandidatura, 
            CertificadoRevisorConfig, CertificadoRevisor,
            revisor_process_evento_association
        )
        
        app = create_app()
        
        with app.app_context():
            print("🚀 Iniciando população de dados...")
            
            # Criar cliente
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
                print(f"✅ Cliente criado: {cliente.nome}")
            else:
                print(f"ℹ️  Cliente já existe: {cliente.nome}")
            
            # Criar evento
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
                print(f"✅ Evento criado: {evento.nome}")
            else:
                print(f"ℹ️  Evento já existe: {evento.nome}")
            
            # Criar processo
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
                print(f"✅ Processo criado: {processo.nome}")
            else:
                print(f"ℹ️  Processo já existe: {processo.nome}")
            
            # Associar processo ao evento
            if evento not in processo.eventos:
                processo.eventos.append(evento)
                db.session.commit()
                print(f"✅ Processo associado ao evento")
            
            # Criar revisores
            revisores_data = [
                {"nome": "Dr. João Silva", "email": "joao.silva@example.com", "cpf": "111.111.111-11"},
                {"nome": "Dra. Maria Santos", "email": "maria.santos@example.com", "cpf": "222.222.222-22"},
                {"nome": "Dr. Pedro Oliveira", "email": "pedro.oliveira@example.com", "cpf": "333.333.333-33"},
                {"nome": "Dra. Ana Costa", "email": "ana.costa@example.com", "cpf": "444.444.444-44"},
                {"nome": "Dr. Carlos Ferreira", "email": "carlos.ferreira@example.com", "cpf": "555.555.555-55"}
            ]
            
            for revisor_data in revisores_data:
                usuario = Usuario.query.filter_by(email=revisor_data["email"]).first()
                if not usuario:
                    usuario = Usuario(
                        nome=revisor_data["nome"],
                        email=revisor_data["email"],
                        senha=generate_password_hash("123456"),
                        cpf=revisor_data["cpf"],
                        formacao="Doutorado",
                        tipo="revisor",
                        ativo=True
                    )
                    db.session.add(usuario)
                    db.session.commit()
                    print(f"✅ Revisor criado: {usuario.nome}")
                
                # Criar candidatura aprovada
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
                        etapa_atual=1
                    )
                    db.session.add(candidatura)
                    db.session.commit()
                    print(f"✅ Candidatura aprovada: {candidatura.nome}")
            
            # Criar configuração
            config = CertificadoRevisorConfig.query.filter_by(
                cliente_id=cliente.id,
                evento_id=evento.id
            ).first()
            
            if not config:
                config = CertificadoRevisorConfig(
                    cliente_id=cliente.id,
                    evento_id=evento.id,
                    titulo_certificado="Certificado de Revisor Científico",
                    texto_certificado="Certificamos que {nome_revisor} atuou como revisor de trabalhos científicos no evento '{evento_nome}', contribuindo para a avaliação e seleção de trabalhos de alta qualidade acadêmica.",
                    liberacao_automatica=False,
                    criterio_trabalhos_minimos=1,
                    ativo=True
                )
                db.session.add(config)
                db.session.commit()
                print(f"✅ Configuração criada")
            
            print(f"\n🎉 POPULAÇÃO CONCLUÍDA!")
            print(f"🔗 Acesse: http://127.0.0.1:5000/certificado_revisor/configurar/{evento.id}")
            print(f"👤 Login cliente: cliente.teste@example.com / 123456")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
