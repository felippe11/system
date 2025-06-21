import logging
from models import ConfiguracaoCliente
from decimal import Decimal

# Configuração básica de logging
logger = logging.getLogger("taxa_service")

def calcular_taxa_cliente(cliente, taxa_geral):
    """
    Calcula a taxa a ser aplicada para um cliente específico,
    considerando se ele tem uma taxa diferenciada.
    
    Args:
        cliente: O objeto Cliente
        taxa_geral: A taxa geral do sistema (float)
        
    Returns:
        dict: Contendo os dados da taxa aplicada
    """
    resultado = {
        "taxa_aplicada": taxa_geral,
        "usando_taxa_diferenciada": False
    }
    
    logger.info(f"Calculando taxa para cliente ID={getattr(cliente, 'id', 'N/A')}, taxa geral={taxa_geral}")
    
    try:
        # Verifica se o cliente tem um objeto configuracao válido
        if not cliente:
            logger.warning("Cliente é None, usando taxa geral")
            return resultado
            
        # Verifica se o cliente tem uma configuração
        if not hasattr(cliente, 'configuracao') or cliente.configuracao is None:
            logger.info(f"Cliente ID={cliente.id} não tem configuração, usando taxa geral")
            return resultado
            
        # Verifica se a taxa diferenciada está definida
        if cliente.configuracao.taxa_diferenciada is None:
            logger.info(f"Cliente ID={cliente.id} não tem taxa diferenciada definida, usando taxa geral")
            return resultado
            
        # Converte a taxa diferenciada para float com tratamento de erro
        try:
            taxa_diferenciada = float(cliente.configuracao.taxa_diferenciada)
            logger.info(f"Taxa diferenciada para cliente ID={cliente.id}: {taxa_diferenciada}")
            
            # Se a taxa diferenciada for menor que a taxa geral, usa ela
            if taxa_diferenciada < taxa_geral:
                logger.info(f"Usando taxa diferenciada: {taxa_diferenciada} (menor que taxa geral: {taxa_geral})")
                resultado["taxa_aplicada"] = taxa_diferenciada
                resultado["usando_taxa_diferenciada"] = True
            else:
                logger.info(f"Taxa diferenciada ({taxa_diferenciada}) não é menor que taxa geral ({taxa_geral}), usando taxa geral")
        except (ValueError, TypeError) as e:
            logger.warning(f"Erro ao converter taxa diferenciada: {str(e)}, usando taxa geral")
    except Exception as e:
        logger.exception(f"Erro ao calcular taxa diferenciada: {str(e)}")
    
    logger.info(f"Taxa final aplicada: {resultado['taxa_aplicada']}")
    return resultado

def calcular_taxas_clientes(clientes, financeiro_clientes, taxa_geral):
    """
    Calcula as taxas para cada cliente com base em sua receita,
    considerando taxas diferenciadas.
    
    Args:
        clientes: Lista de objetos Cliente
        financeiro_clientes: Dicionário com dados financeiros por cliente
        taxa_geral: Taxa percentual geral do sistema
        
    Returns:
        None (modifica financeiro_clientes in-place)
    """
    for cliente_id, cinfo in financeiro_clientes.items():
        # Encontra o objeto cliente correspondente
        cliente_obj = next((c for c in clientes if c.id == cliente_id), None)
        if not cliente_obj:
            # Cliente não encontrado, usa a taxa padrão
            cinfo["taxas"] = cinfo["receita_total"] * taxa_geral / 100
            cinfo["usando_taxa_diferenciada"] = False
            cinfo["taxa_aplicada"] = taxa_geral
            continue
        
        # Calcula a taxa para este cliente
        resultado_taxa = calcular_taxa_cliente(cliente_obj, taxa_geral)
        taxa_aplicada = resultado_taxa["taxa_aplicada"]
        
        # Aplica a taxa à receita
        cinfo["taxas"] = cinfo["receita_total"] * taxa_aplicada / 100
        cinfo["usando_taxa_diferenciada"] = resultado_taxa["usando_taxa_diferenciada"]
        cinfo["taxa_aplicada"] = taxa_aplicada
