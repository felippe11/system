"""
Exemplo de uso do sistema de histórico de alterações orçamentárias
"""

from datetime import datetime
from models.orcamento import Orcamento, HistoricoOrcamento
from models.user import Usuario
from models.material import Polo
from services.historico_orcamento_service import HistoricoOrcamentoService
from extensions import db

def exemplo_completo():
    """Exemplo completo de uso do sistema de histórico orçamentário"""
    
    # Inicializar o serviço
    service = HistoricoOrcamentoService()
    
    print("=== EXEMPLO: Sistema de Histórico de Alterações Orçamentárias ===\n")
    
    # 1. Criar um orçamento de exemplo
    print("1. Criando orçamento de exemplo...")
    
    # Buscar ou criar um polo
    polo = Polo.query.first()
    if not polo:
        polo = Polo(nome="Polo Exemplo", ativo=True)
        db.session.add(polo)
        db.session.commit()
    
    # Buscar um usuário
    usuario = Usuario.query.first()
    
    # Criar orçamento
    orcamento = Orcamento(
        nome="Orçamento Exemplo 2024",
        descricao="Orçamento para demonstração do sistema de histórico",
        valor_total=100000.00,
        valor_custeio=60000.00,
        valor_capital=40000.00,
        periodo_inicio=datetime(2024, 1, 1),
        periodo_fim=datetime(2024, 12, 31),
        polo_id=polo.id,
        ativo=True
    )
    
    db.session.add(orcamento)
    db.session.commit()
    
    print(f"   ✅ Orçamento criado: ID {orcamento.id}")
    
    # 2. Registrar criação do orçamento
    print("\n2. Registrando criação do orçamento...")
    
    service.registrar_criacao(
        orcamento=orcamento,
        usuario_id=usuario.id if usuario else None,
        motivo="Criação inicial do orçamento para o ano de 2024"
    )
    
    print("   ✅ Histórico de criação registrado")
    
    # 3. Simular edição do orçamento
    print("\n3. Simulando edição do orçamento...")
    
    # Valores anteriores
    valores_anteriores = {
        'valor_total': orcamento.valor_total,
        'valor_custeio': orcamento.valor_custeio,
        'valor_capital': orcamento.valor_capital
    }
    
    # Novos valores
    orcamento.valor_total = 120000.00
    orcamento.valor_custeio = 70000.00
    orcamento.valor_capital = 50000.00
    
    db.session.commit()
    
    # Registrar edição
    service.registrar_edicao(
        orcamento=orcamento,
        valores_anteriores=valores_anteriores,
        usuario_id=usuario.id if usuario else None,
        motivo="Aumento do orçamento devido a novas demandas",
        observacoes="Aprovado pela coordenação em reunião de 15/01/2024"
    )
    
    print("   ✅ Histórico de edição registrado")
    print(f"   📊 Variação: +R$ {orcamento.valor_total - valores_anteriores['valor_total']:,.2f}")
    
    # 4. Simular desativação e reativação
    print("\n4. Simulando desativação e reativação...")
    
    # Desativar
    service.registrar_desativacao(
        orcamento=orcamento,
        usuario_id=usuario.id if usuario else None,
        motivo="Suspensão temporária para revisão"
    )
    
    print("   ✅ Histórico de desativação registrado")
    
    # Reativar
    service.registrar_ativacao(
        orcamento=orcamento,
        usuario_id=usuario.id if usuario else None,
        motivo="Reativação após revisão aprovada"
    )
    
    print("   ✅ Histórico de ativação registrado")
    
    # 5. Obter histórico completo
    print("\n5. Obtendo histórico completo...")
    
    historico = service.obter_historico(orcamento_id=orcamento.id)
    
    print(f"   📋 Total de registros: {len(historico)}")
    
    for item in historico:
        print(f"   • {item.data_alteracao.strftime('%d/%m/%Y %H:%M')} - "
              f"{item.tipo_alteracao.upper()} - {item.motivo}")
    
    # 6. Obter estatísticas
    print("\n6. Obtendo estatísticas...")
    
    stats = service.obter_estatisticas()
    
    print(f"   📊 Total de alterações: {stats['total_alteracoes']}")
    print(f"   💰 Variação total positiva: R$ {stats['variacao_total_positiva']:,.2f}")
    print(f"   💸 Variação total negativa: R$ {stats['variacao_total_negativa']:,.2f}")
    print(f"   📈 Tipos de alteração: {', '.join(stats['tipos_alteracao'])}")
    
    # 7. Demonstrar filtros
    print("\n7. Demonstrando filtros...")
    
    # Filtrar apenas edições
    edicoes = service.obter_historico(
        tipo_alteracao='edicao',
        limite=10
    )
    
    print(f"   ✏️  Edições encontradas: {len(edicoes)}")
    
    # Filtrar por período
    historico_periodo = service.obter_historico(
        data_inicio=datetime(2024, 1, 1),
        data_fim=datetime(2024, 12, 31)
    )
    
    print(f"   📅 Registros em 2024: {len(historico_periodo)}")
    
    print("\n=== EXEMPLO CONCLUÍDO ===")
    
    return orcamento

def exemplo_exportacao():
    """Exemplo de exportação de dados"""
    
    print("\n=== EXEMPLO: Exportação de Dados ===\n")
    
    service = HistoricoOrcamentoService()
    
    # Obter dados para exportação
    dados = service.obter_historico_para_exportacao()
    
    print(f"📊 Total de registros para exportação: {len(dados)}")
    
    if dados:
        print("\n📋 Exemplo de registro:")
        primeiro = dados[0]
        print(f"   ID: {primeiro['id']}")
        print(f"   Data: {primeiro['data_alteracao']}")
        print(f"   Tipo: {primeiro['tipo_alteracao']}")
        print(f"   Orçamento: {primeiro['orcamento_nome']}")
        print(f"   Usuário: {primeiro['usuario_nome']}")
        print(f"   Valor Total: R$ {primeiro['valor_total_novo']:,.2f}")
    
    print("\n=== EXPORTAÇÃO CONCLUÍDA ===")

def exemplo_integracao():
    """Exemplo de integração com outros sistemas"""
    
    print("\n=== EXEMPLO: Integração com Outros Sistemas ===\n")
    
    service = HistoricoOrcamentoService()
    
    # Simular webhook ou notificação
    def callback_alteracao(historico_item):
        print(f"🔔 Notificação: {historico_item.tipo_alteracao} no orçamento {historico_item.orcamento_id}")
        print(f"   Valor: R$ {historico_item.valor_total_novo:,.2f}")
        print(f"   Variação: R$ {historico_item.variacao_total:,.2f}")
    
    # Buscar orçamento existente
    orcamento = Orcamento.query.first()
    
    if orcamento:
        # Registrar alteração com callback
        valores_anteriores = {
            'valor_total': orcamento.valor_total,
            'valor_custeio': orcamento.valor_custeio,
            'valor_capital': orcamento.valor_capital
        }
        
        # Simular alteração
        orcamento.valor_total += 5000.00
        orcamento.valor_custeio += 3000.00
        orcamento.valor_capital += 2000.00
        
        db.session.commit()
        
        # Registrar com callback
        historico_item = service.registrar_edicao(
            orcamento=orcamento,
            valores_anteriores=valores_anteriores,
            motivo="Ajuste automático via integração"
        )
        
        # Simular callback
        callback_alteracao(historico_item)
    
    print("\n=== INTEGRAÇÃO CONCLUÍDA ===")

if __name__ == "__main__":
    from app import create_app
    
    app = create_app()
    
    with app.app_context():
        try:
            # Executar exemplos
            orcamento = exemplo_completo()
            exemplo_exportacao()
            exemplo_integracao()
            
        except Exception as e:
            print(f"\n❌ Erro durante execução: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Limpeza (opcional)
            print("\n🧹 Limpeza concluída")