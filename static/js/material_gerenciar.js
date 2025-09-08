// Gerenciamento de Materiais - JavaScript

// Variáveis globais
let materiaisData = [];
let polosData = [];
let filtroAtual = {
    polo: '',
    status: '',
    busca: ''
};

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    carregarDados();
    configurarEventos();
});

// Configurar eventos
function configurarEventos() {
    // Filtros
    document.getElementById('filtro-polo').addEventListener('change', function() {
        filtroAtual.polo = this.value;
        filtrarMateriais();
    });
    
    document.getElementById('filtro-status').addEventListener('change', function() {
        filtroAtual.status = this.value;
        filtrarMateriais();
    });
    
    document.getElementById('busca-material').addEventListener('input', function() {
        filtroAtual.busca = this.value;
        filtrarMateriais();
    });
    
    // Forms
    // Event listeners
    document.getElementById('form-material')?.addEventListener('submit', salvarMaterial);
    document.getElementById('form-movimentacao')?.addEventListener('submit', salvarMovimentacao);

}

// Carregar dados iniciais
async function carregarDados() {
    try {
        showLoading();
        
        // Carregar polos
        const responsePolos = await fetch('/api/polos');
        const polosJson = await responsePolos.json();
        polosData = polosJson.polos || [];

        // Carregar materiais
        const responseMateriais = await fetch('/api/materiais');
        const materiaisJson = await responseMateriais.json();
        materiaisData = (materiaisJson.materiais || []).map(material => ({
            ...material,
            polo: polosData.find(p => p.id === material.polo_id)
        }));
        
        // Atualizar interface
        atualizarTabelaMateriais();
        carregarEstatisticasPolos();
        
    } catch (error) {
        console.error('Erro ao carregar dados:', error);
        showAlert('Erro ao carregar dados', 'danger');
    } finally {
        hideLoading();
    }
}

// Função para carregar estatísticas por polo
function carregarEstatisticasPolos() {
    showLoading();
    
    fetch('/api/estatisticas/polos', {
        method: 'GET',
        headers: {
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            atualizarEstatisticasPolos(data.estatisticas_por_polo, data.estatisticas_gerais);
        } else {
            showAlert('Erro ao carregar estatísticas: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        showAlert('Erro ao carregar estatísticas', 'danger');
    })
    .finally(() => {
        hideLoading();
    });
}

// Função para atualizar estatísticas por polo na interface
function atualizarEstatisticasPolos(estatisticasPolos, estatisticasGerais) {
    const container = document.getElementById('estatisticasPolos');
    if (!container) return;
    
    container.innerHTML = '';
    
    // Adicionar estatísticas gerais
    const cardGeral = document.createElement('div');
    cardGeral.className = 'col-md-6 col-lg-4 mb-3';
    cardGeral.innerHTML = `
        <div class="card border-primary">
            <div class="card-header bg-primary text-white">
                <h6 class="mb-0"><i class="fas fa-chart-bar"></i> Estatísticas Gerais</h6>
            </div>
            <div class="card-body">
                <div class="row text-center">
                    <div class="col-6">
                        <h5 class="text-primary">${estatisticasGerais.total_materiais}</h5>
                        <small>Total Materiais</small>
                    </div>
                    <div class="col-6">
                        <h5 class="text-info">${estatisticasGerais.total_polos}</h5>
                        <small>Total Polos</small>
                    </div>
                </div>
                <hr>
                <div class="row text-center">
                    <div class="col-4">
                        <h6 class="text-success">${estatisticasGerais.em_estoque}</h6>
                        <small>OK</small>
                    </div>
                    <div class="col-4">
                        <h6 class="text-warning">${estatisticasGerais.estoque_baixo}</h6>
                        <small>Baixo</small>
                    </div>
                    <div class="col-4">
                        <h6 class="text-danger">${estatisticasGerais.sem_estoque}</h6>
                        <small>Sem</small>
                    </div>
                </div>
                <div class="progress mt-2" style="height: 8px;">
                    <div class="progress-bar bg-success" style="width: ${estatisticasGerais.percentual_ok}%"></div>
                </div>
                <small class="text-muted">${estatisticasGerais.percentual_ok}% em situação adequada</small>
            </div>
        </div>
    `;
    container.appendChild(cardGeral);
    
    // Adicionar estatísticas por polo
    estatisticasPolos.forEach(estatistica => {
        const card = document.createElement('div');
        card.className = 'col-md-6 col-lg-4 mb-3';
        
        const corCard = estatistica.percentual_ok >= 80 ? 'success' : 
                       estatistica.percentual_ok >= 60 ? 'warning' : 'danger';
        
        card.innerHTML = `
            <div class="card border-${corCard}">
                <div class="card-header bg-${corCard} text-white">
                    <h6 class="mb-0">
                        <i class="fas fa-map-marker-alt"></i> ${estatistica.polo.nome}
                        <button class="btn btn-sm btn-outline-light float-right" 
                                onclick="verMateriaisPolo(${estatistica.polo.id})" 
                                title="Ver materiais">
                            <i class="fas fa-eye"></i>
                        </button>
                    </h6>
                </div>
                <div class="card-body">
                    <div class="row text-center mb-2">
                        <div class="col-12">
                            <h5 class="text-primary">${estatistica.total_materiais}</h5>
                            <small>Total de Materiais</small>
                        </div>
                    </div>
                    <div class="row text-center">
                        <div class="col-4">
                            <h6 class="text-success">${estatistica.em_estoque}</h6>
                            <small>OK</small>
                        </div>
                        <div class="col-4">
                            <h6 class="text-warning">${estatistica.estoque_baixo}</h6>
                            <small>Baixo</small>
                        </div>
                        <div class="col-4">
                            <h6 class="text-danger">${estatistica.sem_estoque}</h6>
                            <small>Sem</small>
                        </div>
                    </div>
                    <div class="progress mt-2" style="height: 8px;">
                        <div class="progress-bar bg-${corCard}" style="width: ${estatistica.percentual_ok}%"></div>
                    </div>
                    <small class="text-muted">${estatistica.percentual_ok}% adequado</small>
                    ${estatistica.valor_total_estoque > 0 ? `
                        <hr>
                        <small class="text-info">
                            <i class="fas fa-dollar-sign"></i> 
                            R$ ${estatistica.valor_total_estoque.toFixed(2)}
                        </small>
                    ` : ''}
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

// Atualizar tabela de materiais
function atualizarTabelaMateriais() {
    const tbody = document.getElementById('lista-materiais');
    tbody.innerHTML = '';
    
    const materiaisFiltrados = filtrarMateriaisData();
    
    materiaisFiltrados.forEach(material => {
        const row = criarLinhaTabela(material);
        tbody.appendChild(row);
    });
}

// Criar linha da tabela
function criarLinhaTabela(material) {
    const tr = document.createElement('tr');
    
    const status = getStatusMaterial(material);
    const necessario = Math.max(0, material.quantidade_minima - material.quantidade_atual);
    
    tr.innerHTML = `
        <td>
            <strong>${material.nome}</strong>
            ${material.descricao ? `<br><small class="text-muted">${material.descricao}</small>` : ''}
        </td>
        <td>
            <span class="badge bg-secondary">${material.polo ? material.polo.nome : '-'}</span>
        </td>
        <td>${material.categoria || '-'}</td>
        <td>
            <span class="badge ${status.badgeClass}">
                ${material.quantidade_atual} ${material.unidade}
            </span>
        </td>
        <td>${material.quantidade_minima} ${material.unidade}</td>
        <td>
            <span class="badge ${status.badgeClass}">${status.texto}</span>
        </td>
        <td>
            ${necessario > 0 ? `<span class="text-danger">${necessario} ${material.unidade}</span>` : '-'}
        </td>
        <td>
            <div class="btn-group btn-group-sm">
                <button class="btn btn-outline-primary" onclick="abrirMovimentacao(${material.id})" title="Movimentar">
                    <i class="fas fa-exchange-alt"></i>
                </button>
                <button class="btn btn-outline-secondary" onclick="window.location.href='/editar-material/${material.id}'" title="Editar">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-outline-danger" onclick="excluirMaterial(${material.id})" title="Excluir">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </td>
    `;
    
    return tr;
}

// Obter status do material
function getStatusMaterial(material) {
    if (material.quantidade_atual <= 0) {
        return { texto: 'Esgotado', badgeClass: 'bg-danger' };
    } else if (material.quantidade_atual <= material.quantidade_minima) {
        return { texto: 'Baixo Estoque', badgeClass: 'bg-warning' };
    } else {
        return { texto: 'Normal', badgeClass: 'bg-success' };
    }
}

// Filtrar materiais
function filtrarMateriaisData() {
    return materiaisData.filter(material => {
        // Filtro por polo
        if (filtroAtual.polo && material.polo_id != filtroAtual.polo) {
            return false;
        }
        
        // Filtro por status
        if (filtroAtual.status) {
            const status = getStatusMaterial(material);
            if (filtroAtual.status === 'baixo' && status.texto !== 'Baixo Estoque') {
                return false;
            }
            if (filtroAtual.status === 'esgotado' && status.texto !== 'Esgotado') {
                return false;
            }
            if (filtroAtual.status === 'normal' && status.texto !== 'Normal') {
                return false;
            }
        }
        
        // Filtro por busca
        if (filtroAtual.busca) {
            const busca = filtroAtual.busca.toLowerCase();
            return material.nome.toLowerCase().includes(busca) ||
                   (material.descricao && material.descricao.toLowerCase().includes(busca)) ||
                   (material.categoria && material.categoria.toLowerCase().includes(busca));
        }
        
        return true;
    });
}

// Aplicar filtros
function filtrarMateriais() {
    atualizarTabelaMateriais();
}

// Funções de salvar polo e material removidas - agora usando páginas separadas

// Abrir página de movimentação
function abrirMovimentacao(materialId) {
    window.location.href = `/materiais/${materialId}/movimentar`;
}

// Salvar movimentação
async function salvarMovimentacao(event) {
    event.preventDefault();
    
    const formData = {
        material_id: document.getElementById('movimentacao-material-id').value,
        tipo: document.getElementById('movimentacao-tipo').value,
        quantidade: parseInt(document.getElementById('movimentacao-quantidade').value),
        observacao: document.getElementById('movimentacao-observacao').value
    };
    
    try {
        const response = await fetch('/api/movimentacoes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            showAlert('Movimentação registrada com sucesso!', 'success');
            document.getElementById('form-movimentacao').reset();
            bootstrap.Modal.getInstance(document.getElementById('modalMovimentacao')).hide();
            carregarDados();
        } else {
            const error = await response.json();
            showAlert(error.message || 'Erro ao registrar movimentação', 'danger');
        }
    } catch (error) {
        console.error('Erro:', error);
        showAlert('Erro ao registrar movimentação', 'danger');
    }
}

// Salvar material
async function salvarMaterial(event) {
    event.preventDefault();

    const form = document.getElementById('form-material');
    const materialId = form.getAttribute('data-edit-id');

    const formData = {
        polo_id: document.getElementById('material-polo').value,
        nome: document.getElementById('material-nome').value,
        descricao: document.getElementById('material-descricao').value,
        unidade: document.getElementById('material-unidade').value,
        categoria: document.getElementById('material-categoria').value,
        quantidade_minima: parseInt(document.getElementById('material-quantidade-minima').value) || 0,
        preco_unitario: parseFloat(document.getElementById('material-preco').value) || null,
        fornecedor: document.getElementById('material-fornecedor').value || null
    };

    try {
        const response = await fetch(`/api/materiais/${materialId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        if (response.ok) {
            showAlert('Material atualizado com sucesso!', 'success');
            form.reset();
            form.removeAttribute('data-edit-id');
            bootstrap.Modal.getInstance(document.getElementById('modalMaterial')).hide();
            carregarDados();
        } else {
            const error = await response.json();
            showAlert(error.message || 'Erro ao atualizar material', 'danger');
        }
    } catch (error) {
        console.error('Erro:', error);
        showAlert('Erro ao atualizar material', 'danger');
    }
}


// Excluir material
async function excluirMaterial(materialId) {
    if (!confirm('Tem certeza que deseja excluir este material?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/materiais/${materialId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });
        
        if (response.ok) {
            showAlert('Material excluído com sucesso!', 'success');
            carregarDados();
        } else {
            const error = await response.json();
            showAlert(error.message || 'Erro ao excluir material', 'danger');
        }
    } catch (error) {
        console.error('Erro:', error);
        showAlert('Erro ao excluir material', 'danger');
    }
}

// Ver materiais do polo
function verMateriaisPolo(poloId) {
    document.getElementById('filtro-polo').value = poloId;
    filtroAtual.polo = poloId;
    filtrarMateriais();
    
    // Scroll para a tabela
    document.getElementById('tabela-materiais').scrollIntoView({ behavior: 'smooth' });
}


// Atualizar lista
function atualizarLista() {
    carregarDados();
}

// Gerar relatório geral
function gerarRelatorioGeral() {
    const grupos = {
        'OK': {},
        'Estoque Baixo': {},
        'Sem Estoque': {}
    };

    materiaisData.forEach(material => {
        const poloNome = material.polo ? material.polo.nome : 'N/A';
        const status = material.quantidade_atual === 0
            ? 'Sem Estoque'
            : material.quantidade_atual <= material.quantidade_minima
                ? 'Estoque Baixo'
                : 'OK';

        if (!grupos[status][poloNome]) {
            grupos[status][poloNome] = [];
        }
        grupos[status][poloNome].push(material);
    });

    const statusOrder = ['OK', 'Estoque Baixo', 'Sem Estoque'];
    const linhas = ['📋 RELATÓRIO GERAL'];
    const contadores = {
        'OK': 0,
        'Estoque Baixo': 0,
        'Sem Estoque': 0
    };

    statusOrder.forEach(status => {
        const polos = grupos[status];
        const totalStatus = Object.values(polos).reduce((sum, lista) => sum + lista.length, 0);
        contadores[status] = totalStatus;
        linhas.push(`\n${status} (${totalStatus})`);
        Object.keys(polos).sort((a, b) => a.localeCompare(b)).forEach(poloNome => {
            linhas.push(`  ${poloNome}:`);
            polos[poloNome]
                .sort((a, b) => a.nome.localeCompare(b.nome))
                .forEach(material => {
                    linhas.push(
                        `    - ${material.nome} - Atual: ${material.quantidade_atual} ${material.unidade}`
                    );
                });
        });
    });

    linhas.push(
        `\n📊 RESUMO`,
        `• Total: ${materiaisData.length} materiais`,
        `• OK: ${contadores['OK']}`,
        `• Estoque Baixo: ${contadores['Estoque Baixo']}`,
        `• Sem Estoque: ${contadores['Sem Estoque']}`
    );

    const textoCompleto = linhas.join('\n');

    navigator.clipboard.writeText(textoCompleto).then(() => {
        showAlert('Relatório copiado para a área de transferência!', 'success');
    });
}

// Gerar lista de compras
function gerarListaCompras() {
    window.location.href = '/materiais/lista-compras';
}

// Função para baixar relatório em Excel
function baixarRelatorioExcel(tipo = 'geral', poloId = null) {
    let url = `/relatorios/materiais/excel?tipo=${tipo}`;
    if (poloId) {
        url += `&polo_id=${poloId}`;
    }
    
    showLoading();
    
    fetch(url, {
        method: 'GET',
        headers: {
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(async response => {
        if (response.ok) {
            return response.blob();
        }
        const data = await response.json().catch(() => ({}));
        const message =
            data.error?.message || data.message || 'Erro ao gerar relatório';
        throw new Error(message);
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `relatorio_materiais_${tipo}_${new Date().toISOString().slice(0, 10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        showAlert('Relatório baixado com sucesso!', 'success');
    })
    .catch(error => {
        console.error('Erro:', error);
        showAlert(error.message || 'Erro ao baixar relatório', 'danger');
    })
    .finally(() => {
        hideLoading();
    });
}

// Funções utilitárias
function getCSRFToken() {
    return document.querySelector('meta[name=csrf-token]').getAttribute('content');
}

function showAlert(message, type = 'info') {
    // Criar e mostrar alerta Bootstrap
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Remover automaticamente após 5 segundos
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

function showLoading() {
    // Implementar loading spinner se necessário
}

function hideLoading() {
    // Remover loading spinner se necessário
}
