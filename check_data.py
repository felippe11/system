#!/usr/bin/env python3
"""
Script para verificar dados existentes de certificados de revisores.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_data():
    try:
        from app import create_app
        from extensions import db
        from models import (
            Usuario, Cliente, Evento, 
            RevisorProcess, RevisorCandidatura, 
            CertificadoRevisorConfig, CertificadoRevisor
        )
        
        app = create_app()
        
        with app.app_context():
            print("🔍 Verificando dados existentes...")
            
            # Verificar cliente
            cliente = Cliente.query.filter_by(email="cliente.teste@example.com").first()
            if cliente:
                print(f"✅ Cliente: {cliente.nome} (ID: {cliente.id})")
            else:
                print("❌ Cliente não encontrado")
                return
            
            # Verificar evento
            evento = Evento.query.filter_by(nome="Evento Teste Certificados").first()
            if evento:
                print(f"✅ Evento: {evento.nome} (ID: {evento.id})")
            else:
                print("❌ Evento não encontrado")
                return
            
            # Verificar processo
            processo = RevisorProcess.query.filter_by(
                cliente_id=cliente.id,
                nome="Processo Teste Certificados"
            ).first()
            
            if processo:
                print(f"✅ Processo: {processo.nome} (ID: {processo.id})")
                print(f"   Eventos associados: {len(processo.eventos)}")
            else:
                print("❌ Processo não encontrado")
                return
            
            # Verificar revisores
            revisores = Usuario.query.filter(
                Usuario.email.in_([
                    "joao.silva@example.com",
                    "maria.santos@example.com", 
                    "pedro.oliveira@example.com",
                    "ana.costa@example.com",
                    "carlos.ferreira@example.com"
                ])
            ).all()
            
            print(f"✅ Revisores: {len(revisores)}")
            for revisor in revisores:
                print(f"   • {revisor.nome}")
            
            # Verificar candidaturas
            candidaturas = RevisorCandidatura.query.filter_by(
                process_id=processo.id,
                status="aprovado"
            ).all()
            
            print(f"✅ Candidaturas aprovadas: {len(candidaturas)}")
            
            # Verificar configuração
            config = CertificadoRevisorConfig.query.filter_by(
                cliente_id=cliente.id,
                evento_id=evento.id
            ).first()
            
            if config:
                print(f"✅ Configuração de certificado encontrada")
            else:
                print("❌ Configuração não encontrada")
            
            # Verificar certificados
            certificados = CertificadoRevisor.query.filter_by(
                cliente_id=cliente.id,
                evento_id=evento.id
            ).all()
            
            print(f"✅ Certificados: {len(certificados)}")
            
            if len(certificados) > 0:
                liberados = [c for c in certificados if c.liberado]
                print(f"   • Liberados: {len(liberados)}")
                print(f"   • Não liberados: {len(certificados) - len(liberados)}")
            
            print(f"\n🔗 URL para teste: http://127.0.0.1:5000/certificado_revisor/configurar/{evento.id}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    check_data()

