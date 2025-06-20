from models import ConfiguracaoCliente
from decimal import Decimal

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
    
    # Verifica se o cliente tem uma configuração e uma taxa diferenciada
    if (hasattr(cliente, 'configuracao') and 
        cliente.configuracao and 
        cliente.configuracao.taxa_diferenciada is not None):
        
        taxa_diferenciada = float(cliente.configuracao.taxa_diferenciada)
        
        # Se a taxa diferenciada for menor que a taxa geral, usa ela
        if taxa_diferenciada < taxa_geral:
            resultado["taxa_aplicada"] = taxa_diferenciada
            resultado["usando_taxa_diferenciada"] = True
    
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
