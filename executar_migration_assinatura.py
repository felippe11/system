#!/usr/bin/env python3
"""
Script simples para executar a migration de assinatura.
"""

import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def executar_migration():
    """Executa a migration para adicionar campo de assinatura."""
    try:
        from app import create_app
        from extensions import db
        
        app = create_app()
        
        with app.app_context():
            print("🔧 EXECUTANDO MIGRATION - CAMPO DE ASSINATURA")
            print("=" * 50)
            
            # Verificar se a coluna já existe
            try:
                result = db.engine.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'certificado_revisor_config' 
                    AND column_name = 'incluir_assinatura_cliente'
                """)
                
                if result.fetchone():
                    print("✅ Campo 'incluir_assinatura_cliente' já existe!")
                    return True
            except Exception as e:
                print(f"⚠️ Erro ao verificar coluna: {e}")
            
            # Adicionar a coluna
            print("📝 Adicionando campo 'incluir_assinatura_cliente'...")
            
            try:
                db.engine.execute("""
                    ALTER TABLE certificado_revisor_config 
                    ADD COLUMN incluir_assinatura_cliente BOOLEAN DEFAULT TRUE
                """)
                print("✅ Campo adicionado com sucesso!")
                
                # Atualizar registros existentes
                print("🔄 Atualizando registros existentes...")
                db.engine.execute("""
                    UPDATE certificado_revisor_config 
                    SET incluir_assinatura_cliente = TRUE 
                    WHERE incluir_assinatura_cliente IS NULL
                """)
                print("✅ Registros existentes atualizados!")
                
                print("\n🎯 MIGRATION CONCLUÍDA COM SUCESSO!")
                print("📋 O campo de assinatura opcional está disponível!")
                return True
                
            except Exception as e:
                print(f"❌ Erro ao adicionar campo: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 INICIANDO MIGRATION DE ASSINATURA")
    print("=" * 40)
    
    sucesso = executar_migration()
    
    if sucesso:
        print("\n✅ MIGRATION EXECUTADA COM SUCESSO!")
        print("📋 Próximos passos:")
        print("   1. Testar a funcionalidade no sistema")
        print("   2. Configurar certificados com/sem assinatura")
        print("   3. Gerar PDFs para verificar funcionamento")
    else:
        print("\n❌ MIGRATION FALHOU!")
        print("📋 Verifique os logs acima para identificar o problema")

