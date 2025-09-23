"""
Serviço para integração entre sistema de compras e gestão de materiais.
Responsável pela sincronização bidirecional entre compras e estoque.
"""

from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_
from models import db, Compra, ItemCompra, Material, MovimentacaoMaterial, Polo

try:  # Nem todos os ambientes precisam do relatório em PDF
    from services.pdf_service import gerar_relatorio_necessidades
except ImportError:  # pragma: no cover - fallback
    gerar_relatorio_necessidades = None


class IntegracaoComprasMateriais:
    """Classe responsável pela integração entre compras e materiais."""
    
    @staticmethod
    def processar_entrega_compra(compra_id: int, usuario_id: int = None) -> Dict:
        """
        Processa a entrega de uma compra, atualizando o estoque dos materiais.
        
        Args:
            compra_id: ID da compra entregue
            usuario_id: ID do usuário responsável pelo processamento
            
        Returns:
            Dict com resultado do processamento
        """
        try:
            compra = Compra.query.get(compra_id)
            if not compra:
                return {'success': False, 'error': 'Compra não encontrada'}
            
            if compra.status != 'entregue':
                return {'success': False, 'error': 'Compra deve estar com status "entregue"'}
            
            materiais_atualizados = []
            movimentacoes_criadas = []
            
            # Processar cada item da compra
            for item in compra.itens:
                if item.material_id:
                    # Atualizar estoque do material
                    material = Material.query.get(item.material_id)
                    if material:
                        # Calcular nova quantidade
                        quantidade_anterior = material.quantidade_atual
                        material.quantidade_atual += int(item.quantidade)
                        material.data_atualizacao = datetime.utcnow()
                        
                        # Criar movimentação de entrada
                        movimentacao = MovimentacaoMaterial(
                            material_id=material.id,
                            tipo='entrada',
                            quantidade=int(item.quantidade),
                            observacao=f'Entrada por compra {compra.numero_compra} - {item.descricao}',
                            usuario_id=usuario_id,
                            data_movimentacao=compra.data_entrega_realizada or datetime.utcnow()
                        )
                        
                        db.session.add(movimentacao)
                        movimentacoes_criadas.append({
                            'material': material.nome,
                            'quantidade_anterior': quantidade_anterior,
                            'quantidade_adicionada': int(item.quantidade),
                            'quantidade_atual': material.quantidade_atual
                        })
                        
                        materiais_atualizados.append(material.id)
                
                else:
                    # Tentar encontrar material por nome/descrição
                    material_encontrado = IntegracaoComprasMateriais._buscar_material_por_descricao(
                        item.descricao, compra.polo_id, compra.cliente_id
                    )
                    
                    if material_encontrado:
                        # Vincular item ao material encontrado
                        item.material_id = material_encontrado.id
                        
                        # Atualizar estoque
                        quantidade_anterior = material_encontrado.quantidade_atual
                        material_encontrado.quantidade_atual += int(item.quantidade)
                        material_encontrado.data_atualizacao = datetime.utcnow()
                        
                        # Criar movimentação
                        movimentacao = MovimentacaoMaterial(
                            material_id=material_encontrado.id,
                            tipo='entrada',
                            quantidade=int(item.quantidade),
                            observacao=f'Entrada por compra {compra.numero_compra} - {item.descricao} (vinculação automática)',
                            usuario_id=usuario_id,
                            data_movimentacao=compra.data_entrega_realizada or datetime.utcnow()
                        )
                        
                        db.session.add(movimentacao)
                        movimentacoes_criadas.append({
                            'material': material_encontrado.nome,
                            'quantidade_anterior': quantidade_anterior,
                            'quantidade_adicionada': int(item.quantidade),
                            'quantidade_atual': material_encontrado.quantidade_atual,
                            'vinculacao_automatica': True
                        })
                        
                        materiais_atualizados.append(material_encontrado.id)
            
            db.session.commit()
            
            return {
                'success': True,
                'materiais_atualizados': len(materiais_atualizados),
                'movimentacoes_criadas': len(movimentacoes_criadas),
                'detalhes': movimentacoes_criadas
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': f'Erro ao processar entrega: {str(e)}'}
    
    @staticmethod
    def _buscar_material_por_descricao(descricao: str, polo_id: int = None, cliente_id: int = None) -> Optional[Material]:
        """
        Busca material por descrição similar.
        
        Args:
            descricao: Descrição do item
            polo_id: ID do polo (opcional)
            cliente_id: ID do cliente
            
        Returns:
            Material encontrado ou None
        """
        # Normalizar descrição para busca
        descricao_normalizada = descricao.lower().strip()
        
        # Buscar por nome exato
        query = Material.query.filter(
            Material.ativo == True,
            Material.cliente_id == cliente_id
        )
        
        if polo_id:
            query = query.filter(Material.polo_id == polo_id)
        
        # Busca por nome exato
        material = query.filter(
            db.func.lower(Material.nome) == descricao_normalizada
        ).first()
        
        if material:
            return material
        
        # Busca por similaridade (contém)
        material = query.filter(
            or_(
                Material.nome.ilike(f'%{descricao_normalizada}%'),
                Material.descricao.ilike(f'%{descricao_normalizada}%')
            )
        ).first()
        
        return material
    
    @staticmethod
    def gerar_compra_por_necessidades(cliente_id: int, polo_id: int = None, 
                                    fornecedor: str = None, tipo_gasto: str = 'custeio') -> Dict:
        """
        Gera uma compra baseada nas necessidades de estoque dos materiais.
        
        Args:
            cliente_id: ID do cliente
            polo_id: ID do polo (opcional)
            fornecedor: Nome do fornecedor
            tipo_gasto: Tipo de gasto (custeio/capital)
            
        Returns:
            Dict com dados da compra sugerida
        """
        try:
            # Buscar materiais com estoque baixo
            query = Material.query.filter(
                Material.cliente_id == cliente_id,
                Material.ativo == True,
                Material.quantidade_atual <= Material.quantidade_minima
            )
            
            if polo_id:
                query = query.filter(Material.polo_id == polo_id)
            
            materiais_necessarios = query.all()
            
            if not materiais_necessarios:
                return {
                    'success': False,
                    'message': 'Nenhum material com necessidade de reposição encontrado'
                }
            
            # Calcular itens necessários
            itens_compra = []
            valor_total_estimado = 0
            
            for material in materiais_necessarios:
                quantidade_necessaria = material.quantidade_necessaria
                if quantidade_necessaria > 0:
                    preco_unitario = material.preco_unitario or 0
                    valor_item = quantidade_necessaria * preco_unitario
                    
                    itens_compra.append({
                        'material_id': material.id,
                        'material_nome': material.nome,
                        'descricao': f'{material.nome} - {material.descricao or ""}',
                        'quantidade': quantidade_necessaria,
                        'unidade': material.unidade,
                        'preco_unitario': preco_unitario,
                        'valor_total': valor_item,
                        'quantidade_atual': material.quantidade_atual,
                        'quantidade_minima': material.quantidade_minima,
                        'status_estoque': material.status_estoque
                    })
                    
                    valor_total_estimado += valor_item
            
            # Gerar número da compra
            numero_compra = IntegracaoComprasMateriais._gerar_numero_compra_automatica()
            
            compra_sugerida = {
                'numero_compra': numero_compra,
                'descricao': f'Compra automática para reposição de estoque - {len(itens_compra)} itens',
                'fornecedor': fornecedor or 'A definir',
                'valor_total': valor_total_estimado,
                'tipo_gasto': tipo_gasto,
                'cliente_id': cliente_id,
                'polo_id': polo_id,
                'itens': itens_compra,
                'observacoes': f'Compra gerada automaticamente baseada em necessidades de estoque em {datetime.now().strftime("%d/%m/%Y %H:%M")}'
            }
            
            return {
                'success': True,
                'compra_sugerida': compra_sugerida,
                'total_itens': len(itens_compra),
                'valor_total_estimado': valor_total_estimado
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Erro ao gerar compra: {str(e)}'}
    
    @staticmethod
    def _gerar_numero_compra_automatica() -> str:
        """Gera número único para compra automática."""
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f'AUTO-{timestamp}'
    
    @staticmethod
    def sincronizar_precos_materiais(compra_id: int) -> Dict:
        """
        Sincroniza preços dos materiais baseado nos preços da compra.
        
        Args:
            compra_id: ID da compra
            
        Returns:
            Dict com resultado da sincronização
        """
        try:
            compra = Compra.query.get(compra_id)
            if not compra:
                return {'success': False, 'error': 'Compra não encontrada'}
            
            materiais_atualizados = []
            
            for item in compra.itens:
                if item.material_id and item.preco_unitario:
                    material = Material.query.get(item.material_id)
                    if material:
                        preco_anterior = material.preco_unitario
                        material.preco_unitario = item.preco_unitario
                        material.data_atualizacao = datetime.utcnow()
                        
                        materiais_atualizados.append({
                            'material': material.nome,
                            'preco_anterior': preco_anterior,
                            'preco_atual': material.preco_unitario
                        })
            
            db.session.commit()
            
            return {
                'success': True,
                'materiais_atualizados': len(materiais_atualizados),
                'detalhes': materiais_atualizados
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': f'Erro ao sincronizar preços: {str(e)}'}
    
    @staticmethod
    def obter_relatorio_necessidades(cliente_id: int, polo_id: int = None) -> Dict:
        """
        Gera relatório de necessidades de materiais.
        
        Args:
            cliente_id: ID do cliente
            polo_id: ID do polo (opcional)
            
        Returns:
            Dict com relatório de necessidades
        """
        try:
            # Buscar materiais com diferentes status de estoque
            query_base = Material.query.filter(
                Material.cliente_id == cliente_id,
                Material.ativo == True
            )
            
            if polo_id:
                query_base = query_base.filter(Material.polo_id == polo_id)
            
            # Materiais esgotados
            esgotados = query_base.filter(Material.quantidade_atual <= 0).all()
            
            # Materiais com estoque baixo
            estoque_baixo = query_base.filter(
                and_(
                    Material.quantidade_atual > 0,
                    Material.quantidade_atual <= Material.quantidade_minima
                )
            ).all()
            
            # Materiais com estoque normal
            estoque_normal = query_base.filter(
                Material.quantidade_atual > Material.quantidade_minima
            ).all()
            
            # Calcular valores
            valor_total_necessario = 0
            itens_necessarios = []
            
            for material in esgotados + estoque_baixo:
                quantidade_necessaria = material.quantidade_necessaria
                if quantidade_necessaria > 0:
                    valor_necessario = quantidade_necessaria * (material.preco_unitario or 0)
                    valor_total_necessario += valor_necessario
                    
                    itens_necessarios.append({
                        'material': material.nome,
                        'polo': material.polo.nome if material.polo else 'N/A',
                        'quantidade_atual': material.quantidade_atual,
                        'quantidade_minima': material.quantidade_minima,
                        'quantidade_necessaria': quantidade_necessaria,
                        'preco_unitario': material.preco_unitario or 0,
                        'valor_necessario': valor_necessario,
                        'status': material.status_estoque,
                        'unidade': material.unidade
                    })
            
            relatorio = {
                'cliente_id': cliente_id,
                'polo_id': polo_id,
                'data_relatorio': datetime.now().isoformat(),
                'resumo': {
                    'total_materiais': len(esgotados) + len(estoque_baixo) + len(estoque_normal),
                    'materiais_esgotados': len(esgotados),
                    'materiais_estoque_baixo': len(estoque_baixo),
                    'materiais_estoque_normal': len(estoque_normal),
                    'total_itens_necessarios': len(itens_necessarios),
                    'valor_total_necessario': valor_total_necessario
                },
                'itens_necessarios': itens_necessarios,
                'materiais_por_status': {
                    'esgotados': [m.to_dict() for m in esgotados],
                    'estoque_baixo': [m.to_dict() for m in estoque_baixo],
                    'estoque_normal': [m.to_dict() for m in estoque_normal]
                }
            }
            
            return {'success': True, 'relatorio': relatorio}
            
        except Exception as e:
            return {'success': False, 'error': f'Erro ao gerar relatório: {str(e)}'}
    
    @staticmethod
    def verificar_disponibilidade_orcamento(cliente_id: int, valor_compra: float, 
                                          tipo_gasto: str = 'custeio') -> Dict:
        """
        Verifica se há orçamento disponível para a compra.
        
        Args:
            cliente_id: ID do cliente
            valor_compra: Valor da compra
            tipo_gasto: Tipo de gasto (custeio/capital)
            
        Returns:
            Dict com informações de disponibilidade orçamentária
        """
        try:
            from models.compra import OrcamentoCliente
            
            # Buscar orçamento ativo do ano atual
            ano_atual = datetime.now().year
            orcamento = OrcamentoCliente.query.filter_by(
                cliente_id=cliente_id,
                ano_orcamento=ano_atual,
                ativo=True
            ).first()
            
            if not orcamento:
                return {
                    'disponivel': False,
                    'motivo': 'Nenhum orçamento ativo encontrado para o ano atual',
                    'valor_disponivel': 0
                }
            
            # Verificar disponibilidade por tipo de gasto
            if tipo_gasto == 'custeio':
                valor_disponivel = orcamento.valor_custeio_disponivel - orcamento.valor_gasto_custeio
                valor_orcamento = orcamento.valor_custeio_disponivel
            else:  # capital
                valor_disponivel = orcamento.valor_capital_disponivel - orcamento.valor_gasto_capital
                valor_orcamento = orcamento.valor_capital_disponivel
            
            disponivel = valor_disponivel >= valor_compra
            
            return {
                'disponivel': disponivel,
                'valor_compra': valor_compra,
                'valor_disponivel': valor_disponivel,
                'valor_orcamento': valor_orcamento,
                'tipo_gasto': tipo_gasto,
                'percentual_uso': ((valor_orcamento - valor_disponivel) / valor_orcamento * 100) if valor_orcamento > 0 else 0,
                'percentual_apos_compra': ((valor_orcamento - valor_disponivel + valor_compra) / valor_orcamento * 100) if valor_orcamento > 0 else 0
            }
            
        except Exception as e:
            return {
                'disponivel': False,
                'error': f'Erro ao verificar orçamento: {str(e)}'
            }
