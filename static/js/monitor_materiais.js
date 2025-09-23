// Variáveis globais
let materiaisData = [];
let polosData = [];

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    carregarDadosIniciais();
    configurarEventListeners();
});

function configurarEventListeners() {
    // Filtros
    document.getElementById('filtro-polo').addEventListener('change', filtrarMateriais);
    document.getElementById('filtro-status').addEventListener('change', filtrarMateriais);
    document.getElementById('buscar-material').addEventListener('input', filtrarMateriais);
    
}

async function carregarDadosIniciais() {
    try {
        mostrarCarregando(true);

        const polosResponse = await fetch('/api/polos');
        if (polosResponse.status === 403) {
            mostrarAlerta('Sessão expirada, faça login novamente', 'error');
            return;
        }

        const polosJson = await polosResponse.json();
        if (!polosJson.success) {
            mostrarAlerta(
                polosJson.message || 'Erro ao carregar polos',
                'error'
            );
            return;
        }

        polosData = polosJson.polos || [];

        if (polosData.length === 0) {
            mostrarAlerta('Nenhum polo cadastrado', 'info');
        }

        const materiaisResponse = await fetch('/api/materiais');
        if (materiaisResponse.status === 403) {
            mostrarAlerta('Sessão expirada, faça login novamente', 'error');
            return;
        }

        const materiaisJson = await materiaisResponse.json();
        if (!materiaisJson.success) {
            mostrarAlerta(
                materiaisJson.message || 'Erro ao carregar materiais',
                'error'
            );
            materiaisData = [];
        } else {
            materiaisData = materiaisJson.materiais || [];
            if (materiaisData.length === 0) {
                mostrarAlerta('Nenhum material disponível', 'info');
            }
        }

        atualizarCardsPolos();
        atualizarTabelaMateriais();
    } catch (error) {
        console.error('Erro:', error);
        if (error.message === 'Sessão expirada') {
            mostrarAlerta('Sessão expirada, faça login novamente', 'error');
        } else {
            mostrarAlerta(error.message || 'Erro ao carregar dados', 'error');
        }
    } finally {
        mostrarCarregando(false);
    }
}

function atualizarCardsPolos() {
    const container = document.getElementById('cardsPolos');
    container.innerHTML = '';
    
    polosData.forEach(polo => {
        const materiaisPolo = materiaisData.filter(m => m.polo_id === polo.id);
        const totalMateriais = materiaisPolo.length;
        const estoqueBaixo = materiaisPolo.filter(m => m.quantidade_atual <= m.quantidade_minima && m.quantidade_atual > 0).length;
        const semEstoque = materiaisPolo.filter(m => m.quantidade_atual === 0).length;
        
        const card = `
            <div class="col-md-6 col-lg-4 mb-3">
                <div class="card border-0 shadow-sm h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-3">
                            <h6 class="card-title mb-0">${polo.nome}</h6>
                            <span class="badge bg-primary">${totalMateriais} materiais</span>
                        </div>
                        <div class="row text-center">
                            <div class="col-4">
                                <div class="text-success">
                                    <i class="fas fa-check-circle"></i>
                                    <div class="fw-bold">${totalMateriais - estoqueBaixo - semEstoque}</div>
                                    <small class="text-muted">OK</small>
                                </div>
                            </div>
                            <div class="col-4">
                                <div class="text-warning">
                                    <i class="fas fa-exclamation-triangle"></i>
                                    <div class="fw-bold">${estoqueBaixo}</div>
                                    <small class="text-muted">Baixo</small>
                                </div>
                            </div>
                            <div class="col-4">
                                <div class="text-danger">
                                    <i class="fas fa-times-circle"></i>
                                    <div class="fw-bold">${semEstoque}</div>
                                    <small class="text-muted">Sem</small>
                                </div>
                            </div>
                        </div>
                        <div class="mt-3">
                            <button class="btn btn-outline-primary btn-sm w-100" onclick="filtrarPorPolo(${polo.id})">
                                <i class="fas fa-eye me-2"></i>Ver Materiais
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        container.innerHTML += card;
    });
}

function atualizarTabelaMateriais(materiaisFiltrados = null) {
    const materiais = materiaisFiltrados || materiaisData;
    const tbody = document.getElementById('corpoTabelaMateriais');
    tbody.innerHTML = '';
    
    if (materiais.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4">
                    <i class="fas fa-box-open fa-3x text-muted mb-3"></i>
                    <p class="text-muted">Nenhum material encontrado</p>
                </td>
            </tr>
        `;
        return;
    }
    
    materiais.forEach(material => {
        const polo = polosData.find(p => p.id === material.polo_id);
        const status = getStatusMaterial(material);
        const ultimaMovimentacao = material.ultima_movimentacao ?
            new Date(material.ultima_movimentacao).toLocaleDateString('pt-BR') : 'Nunca';
        const urlMov = `/monitor/materiais/nova-movimentacao?material_id=${material.id}&polo_id=${material.polo_id}`;
        
        const row = `
            <tr>
                <td>
                    <strong>${material.nome}</strong>
                    <small class="text-muted d-block">${material.descricao || ''}</small>
                </td>
                <td>${polo ? polo.nome : 'N/A'}</td>
                <td>
                    <span class="badge ${status.badgeClass}">${material.quantidade_atual} ${material.unidade}</span>
                </td>
                <td>${material.quantidade_minima} ${material.unidade}</td>
                <td>
                    <span class="badge ${status.badgeClass}">
                        <i class="${status.icon} me-1"></i>${status.text}
                    </span>
                </td>
                <td>${ultimaMovimentacao}</td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="verHistorico(${material.id})" title="Histórico">
                            <i class="fas fa-history"></i>
                        </button>
                        <a class="btn btn-outline-success" href="${urlMov}"
                            title="Nova Movimentação">
                            <i class="fas fa-plus"></i>
                        </a>
                    </div>
                </td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
}

function getStatusMaterial(material) {
    if (material.quantidade_atual === 0) {
        return {
            text: 'Sem Estoque',
            badgeClass: 'bg-danger',
            icon: 'fas fa-times-circle'
        };
    } else if (material.quantidade_atual <= material.quantidade_minima) {
        return {
            text: 'Estoque Baixo',
            badgeClass: 'bg-warning',
            icon: 'fas fa-exclamation-triangle'
        };
    } else {
        return {
            text: 'Em Estoque',
            badgeClass: 'bg-success',
            icon: 'fas fa-check-circle'
        };
    }
}

function filtrarMateriais() {
    const poloId = document.getElementById('filtro-polo').value;
    const status = document.getElementById('filtro-status').value;
    const busca = document.getElementById('buscar-material').value.toLowerCase();
    
    let materiaisFiltrados = materiaisData;
    
    // Filtrar por polo
    if (poloId) {
        materiaisFiltrados = materiaisFiltrados.filter(m => m.polo_id == poloId);
    }
    
    // Filtrar por status
    if (status) {
        materiaisFiltrados = materiaisFiltrados.filter(m => {
            const materialStatus = getStatusMaterial(m);
            switch (status) {
                case 'em_estoque':
                    return m.quantidade_atual > m.quantidade_minima;
                case 'estoque_baixo':
                    return m.quantidade_atual <= m.quantidade_minima && m.quantidade_atual > 0;
                case 'sem_estoque':
                    return m.quantidade_atual === 0;
                default:
                    return true;
            }
        });
    }
    
    // Filtrar por busca
    if (busca) {
        materiaisFiltrados = materiaisFiltrados.filter(m => 
            m.nome.toLowerCase().includes(busca) || 
            (m.descricao && m.descricao.toLowerCase().includes(busca))
        );
    }
    
    atualizarTabelaMateriais(materiaisFiltrados);
}

function filtrarPorPolo(poloId) {
    document.getElementById('filtro-polo').value = poloId;
    filtrarMateriais();
}

async function verHistorico(materialId) {
    try {
        const response = await fetch(`/api/materiais/${materialId}/movimentacoes`);
        const data = await response.json();
        const historico = data.movimentacoes || [];
        
        const tbody = document.getElementById('corpoTabelaHistorico');
        tbody.innerHTML = '';
        
        if (historico.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center py-3">
                        <i class="fas fa-history fa-2x text-muted mb-2"></i>
                        <p class="text-muted mb-0">Nenhuma movimentação encontrada</p>
                    </td>
                </tr>
            `;
        } else {
            historico.forEach(mov => {
                const data = new Date(mov.data_movimentacao).toLocaleDateString('pt-BR');
                const tipoIcon = mov.tipo === 'entrada' ? 'fas fa-arrow-up text-success' : 
                               mov.tipo === 'saida' ? 'fas fa-arrow-down text-danger' : 
                               'fas fa-edit text-warning';
                
                tbody.innerHTML += `
                    <tr>
                        <td>${data}</td>
                        <td>
                            <i class="${tipoIcon} me-2"></i>
                            ${mov.tipo.charAt(0).toUpperCase() + mov.tipo.slice(1)}
                        </td>
                        <td>${mov.quantidade} ${mov.material.unidade}</td>
                        <td>${mov.usuario ? mov.usuario.nome : 'Sistema'}</td>
                        <td>${mov.observacoes || '-'}</td>
                    </tr>
                `;
            });
        }
        
        const modal = new bootstrap.Modal(document.getElementById('modalHistorico'));
        modal.show();
    } catch (error) {
        console.error('Erro:', error);
        mostrarAlerta('Erro ao carregar histórico', 'error');
    }
}


async function gerarRelatorio() {
    try {
        const poloId = document.getElementById('filtro-polo').value;
        const url = poloId ? `/relatorios/materiais/excel?polo_id=${poloId}` : '/relatorios/materiais/excel';
        
        const response = await fetch(url);
        
        if (response.ok) {
            const blob = await response.blob();
            const url2 = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url2;
            a.download = `relatorio_materiais_${new Date().toISOString().split('T')[0]}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url2);
            document.body.removeChild(a);
            
            mostrarAlerta('Relatório gerado com sucesso!', 'success');
        } else {
            throw new Error('Erro ao gerar relatório');
        }
    } catch (error) {
        console.error('Erro:', error);
        mostrarAlerta('Erro ao gerar relatório', 'error');
    }
}

// Funções utilitárias
function getCSRFToken() {
    return document.querySelector('meta[name=csrf-token]').getAttribute('content');
}

function mostrarAlerta(mensagem, tipo) {
    const alertClass = tipo === 'success' ? 'alert-success' : 
                      tipo === 'error' ? 'alert-danger' : 'alert-info';
    
    const alert = document.createElement('div');
    alert.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
    alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alert.innerHTML = `
        ${mensagem}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alert);
    
    setTimeout(() => {
        if (alert.parentNode) {
            alert.parentNode.removeChild(alert);
        }
    }, 5000);
}

function mostrarCarregando(mostrar) {
    const overlay = document.getElementById('loadingOverlay');
    if (mostrar) {
        if (!overlay) {
            const div = document.createElement('div');
            div.id = 'loadingOverlay';
            div.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
            div.style.cssText = 'background: rgba(0,0,0,0.5); z-index: 9999;';
            div.innerHTML = `
                <div class="spinner-border text-light" role="status">
                    <span class="visually-hidden">Carregando...</span>
                </div>
            `;
            document.body.appendChild(div);
        }
    } else {
        if (overlay) {
            overlay.remove();
        }
    }
}
