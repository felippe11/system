#!/usr/bin/env python3
"""
Script para verificar se os dados de certificados de revisores foram criados corretamente.
"""

import os
import sys

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

def verify_data():
    """Verifica se os dados de teste foram criados corretamente."""
    
    app = create_app()
    
    with app.app_context():
        print("🔍 Verificando dados de certificados de revisores...")
        
        # 1. Verificar cliente
        cliente = Cliente.query.filter_by(email="cliente.teste@example.com").first()
        if cliente:
            print(f"✅ Cliente encontrado: {cliente.nome} (ID: {cliente.id})")
        else:
            print("❌ Cliente não encontrado!")
            return
        
        # 2. Verificar evento
        evento = Evento.query.filter_by(nome="Evento Teste Certificados").first()
        if evento:
            print(f"✅ Evento encontrado: {evento.nome} (ID: {evento.id})")
        else:
            print("❌ Evento não encontrado!")
            return
        
        # 3. Verificar processo de revisor
        processo = RevisorProcess.query.filter_by(
            cliente_id=cliente.id,
            nome="Processo Teste Certificados"
        ).first()
        
        if processo:
            print(f"✅ Processo encontrado: {processo.nome} (ID: {processo.id})")
            
            # Verificar associação com evento
            if evento in processo.eventos:
                print(f"✅ Processo associado ao evento")
            else:
                print("❌ Processo NÃO associado ao evento!")
        else:
            print("❌ Processo não encontrado!")
            return
        
        # 4. Verificar revisores
        revisores = Usuario.query.filter(
            Usuario.email.in_([
                "joao.silva@example.com",
                "maria.santos@example.com", 
                "pedro.oliveira@example.com",
                "ana.costa@example.com",
                "carlos.ferreira@example.com"
            ])
        ).all()
        
        print(f"✅ Revisores encontrados: {len(revisores)}")
        for revisor in revisores:
            print(f"   • {revisor.nome} ({revisor.email})")
        
        # 5. Verificar candidaturas
        candidaturas = RevisorCandidatura.query.filter_by(
            process_id=processo.id,
            status="aprovado"
        ).all()
        
        print(f"✅ Candidaturas aprovadas: {len(candidaturas)}")
        for candidatura in candidaturas:
            print(f"   • {candidatura.nome} ({candidatura.email})")
        
        # 6. Verificar configuração de certificado
        config = CertificadoRevisorConfig.query.filter_by(
            cliente_id=cliente.id,
            evento_id=evento.id
        ).first()
        
        if config:
            print(f"✅ Configuração de certificado encontrada")
            print(f"   • Título: {config.titulo_certificado}")
            print(f"   • Texto: {config.texto_certificado[:50]}...")
        else:
            print("❌ Configuração de certificado não encontrada!")
        
        # 7. Verificar certificados
        certificados = CertificadoRevisor.query.filter_by(
            cliente_id=cliente.id,
            evento_id=evento.id
        ).all()
        
        print(f"✅ Certificados encontrados: {len(certificados)}")
        
        certificados_liberados = [c for c in certificados if c.liberado]
        certificados_nao_liberados = [c for c in certificados if not c.liberado]
        
        print(f"   • Liberados: {len(certificados_liberados)}")
        for cert in certificados_liberados:
            print(f"     - {cert.revisor.nome} ({cert.trabalhos_revisados} trabalhos)")
        
        print(f"   • Não liberados: {len(certificados_nao_liberados)}")
        for cert in certificados_nao_liberados:
            print(f"     - {cert.revisor.nome} ({cert.trabalhos_revisados} trabalhos)")
        
        # 8. Testar função de busca de revisores aprovados
        print("\n🧪 Testando função de busca de revisores aprovados...")
        
        # Simular a função _get_revisores_aprovados
        from models.review import revisor_process_evento_association
        
        revisores_aprovados = db.session.query(Usuario).join(
            RevisorCandidatura, Usuario.email == RevisorCandidatura.email
        ).join(
            RevisorProcess, RevisorCandidatura.process_id == RevisorProcess.id
        ).join(
            revisor_process_evento_association, 
            RevisorProcess.id == revisor_process_evento_association.c.revisor_process_id
        ).filter(
            revisor_process_evento_association.c.evento_id == evento.id,
            RevisorCandidatura.status == 'aprovado'
        ).all()
        
        print(f"✅ Revisores aprovados encontrados pela query: {len(revisores_aprovados)}")
        for revisor in revisores_aprovados:
            print(f"   • {revisor.nome} ({revisor.email})")
        
        if len(revisores_aprovados) == len(candidaturas):
            print("✅ Função de busca funcionando corretamente!")
        else:
            print("❌ Problema na função de busca!")
            print(f"   Esperado: {len(candidaturas)}, Encontrado: {len(revisores_aprovados)}")
        
        print("\n🎯 RESULTADO FINAL:")
        if (cliente and evento and processo and len(revisores) == 5 and 
            len(candidaturas) == 5 and config and len(certificados) == 5 and
            len(revisores_aprovados) == 5):
            print("✅ TODOS OS DADOS FORAM CRIADOS CORRETAMENTE!")
            print(f"\n🔗 Acesse: http://127.0.0.1:5000/certificado_revisor/configurar/{evento.id}")
        else:
            print("❌ ALGUNS DADOS ESTÃO FALTANDO!")

if __name__ == "__main__":
    verify_data()

