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
    
    // Form de movimentação
    document.getElementById('formMovimentacao').addEventListener('submit', registrarMovimentacao);
    
    // Mudança de polo no modal de movimentação
    document.getElementById('movimentacao-polo').addEventListener('change', carregarMateriaisPolo);
    
    // Mudança de tipo no modal WhatsApp
    document.getElementById('whatsapp-tipo').addEventListener('change', gerarTextoWhatsApp);
    document.getElementById('whatsapp-polo').addEventListener('change', gerarTextoWhatsApp);
}

async function carregarDadosIniciais() {
    try {
        mostrarCarregando(true);
        
        // Carregar polos e materiais
        const [polosResponse, materiaisResponse] = await Promise.all([
            fetch('/api/polos'),
            fetch('/api/materiais')
        ]);
        
        if (polosResponse.ok && materiaisResponse.ok) {
            const polosJson = await polosResponse.json();
            const materiaisJson = await materiaisResponse.json();
            polosData = polosJson.polos || [];
            materiaisData = materiaisJson.materiais || [];
            
            atualizarCardsPolos();
            atualizarTabelaMateriais();
        } else {
            throw new Error('Erro ao carregar dados');
        }
    } catch (error) {
        console.error('Erro:', error);
        mostrarAlerta('Erro ao carregar dados', 'error');
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
                        <button class="btn btn-outline-success" onclick="novaMovimentacao(${material.id}, ${material.polo_id})" title="Nova Movimentação">
                            <i class="fas fa-plus"></i>
                        </button>
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

async function carregarMateriaisPolo() {
    const poloId = document.getElementById('movimentacao-polo').value;
    const selectMaterial = document.getElementById('movimentacao-material');
    
    selectMaterial.innerHTML = '<option value="">Selecione um material</option>';
    
    if (poloId) {
        const materiaisPolo = materiaisData.filter(m => m.polo_id == poloId);
        materiaisPolo.forEach(material => {
            selectMaterial.innerHTML += `<option value="${material.id}">${material.nome}</option>`;
        });
    }
}

async function registrarMovimentacao(event) {
    event.preventDefault();
    
    const formData = {
        material_id: document.getElementById('movimentacao-material').value,
        tipo: document.getElementById('movimentacao-tipo').value,
        quantidade: parseInt(document.getElementById('movimentacao-quantidade').value),
        observacoes: document.getElementById('movimentacao-observacoes').value
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
        
        const result = await response.json();
        
        if (response.ok) {
            mostrarAlerta('Movimentação registrada com sucesso!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('modalMovimentacao')).hide();
            document.getElementById('formMovimentacao').reset();
            carregarDadosIniciais(); // Recarregar dados
        } else {
            throw new Error(result.message || 'Erro ao registrar movimentação');
        }
    } catch (error) {
        console.error('Erro:', error);
        mostrarAlerta(error.message, 'error');
    }
}

function novaMovimentacao(materialId = null, poloId = null) {
    if (poloId) {
        document.getElementById('movimentacao-polo').value = poloId;
        carregarMateriaisPolo();
    }
    
    if (materialId) {
        setTimeout(() => {
            document.getElementById('movimentacao-material').value = materialId;
        }, 100);
    }
    
    const modal = new bootstrap.Modal(document.getElementById('modalMovimentacao'));
    modal.show();
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

function exportarWhatsApp() {
    const modal = new bootstrap.Modal(document.getElementById('modalWhatsApp'));
    modal.show();
    gerarTextoWhatsApp();
}

function gerarTextoWhatsApp() {
    const tipo = document.getElementById('whatsapp-tipo').value;
    const poloId = document.getElementById('whatsapp-polo').value;
    const textarea = document.getElementById('whatsapp-texto');
    
    let materiais = materiaisData;
    
    // Filtrar por polo se selecionado
    if (poloId) {
        materiais = materiais.filter(m => m.polo_id == poloId);
    }
    
    let texto = '';
    const data = new Date().toLocaleDateString('pt-BR');
    
    switch (tipo) {
        case 'estoque_baixo':
            const estoqueBaixo = materiais.filter(m => m.quantidade_atual <= m.quantidade_minima && m.quantidade_atual > 0);
            texto = `🟡 *MATERIAIS COM ESTOQUE BAIXO* - ${data}\n\n`;
            estoqueBaixo.forEach(m => {
                const polo = polosData.find(p => p.id === m.polo_id);
                texto += `📦 ${m.nome}\n`;
                texto += `🏢 Polo: ${polo ? polo.nome : 'N/A'}\n`;
                texto += `📊 Atual: ${m.quantidade_atual} ${m.unidade}\n`;
                texto += `⚠️ Mínimo: ${m.quantidade_minima} ${m.unidade}\n\n`;
            });
            break;
            
        case 'sem_estoque':
            const semEstoque = materiais.filter(m => m.quantidade_atual === 0);
            texto = `🔴 *MATERIAIS SEM ESTOQUE* - ${data}\n\n`;
            semEstoque.forEach(m => {
                const polo = polosData.find(p => p.id === m.polo_id);
                texto += `📦 ${m.nome}\n`;
                texto += `🏢 Polo: ${polo ? polo.nome : 'N/A'}\n`;
                texto += `❌ Estoque: 0 ${m.unidade}\n\n`;
            });
            break;
            
        case 'lista_compras':
            const paraComprar = materiais.filter(m => m.quantidade_atual <= m.quantidade_minima);
            texto = `🛒 *LISTA DE COMPRAS* - ${data}\n\n`;
            paraComprar.forEach(m => {
                const polo = polosData.find(p => p.id === m.polo_id);
                const necessario = m.quantidade_minima - m.quantidade_atual + (m.quantidade_minima * 0.5); // 50% a mais do mínimo
                texto += `📦 ${m.nome}\n`;
                texto += `🏢 Polo: ${polo ? polo.nome : 'N/A'}\n`;
                texto += `🛒 Comprar: ${Math.ceil(necessario)} ${m.unidade}\n\n`;
            });
            break;
            
        case 'geral':
            texto = `📊 *RELATÓRIO GERAL DE MATERIAIS* - ${data}\n\n`;
            const totalMateriais = materiais.length;
            const emEstoque = materiais.filter(m => m.quantidade_atual > m.quantidade_minima).length;
            const estoqueBaixoGeral = materiais.filter(m => m.quantidade_atual <= m.quantidade_minima && m.quantidade_atual > 0).length;
            const semEstoqueGeral = materiais.filter(m => m.quantidade_atual === 0).length;
            
            texto += `📈 *RESUMO GERAL*\n`;
            texto += `📦 Total de materiais: ${totalMateriais}\n`;
            texto += `✅ Em estoque: ${emEstoque}\n`;
            texto += `🟡 Estoque baixo: ${estoqueBaixoGeral}\n`;
            texto += `🔴 Sem estoque: ${semEstoqueGeral}\n\n`;
            
            if (estoqueBaixoGeral > 0 || semEstoqueGeral > 0) {
                texto += `⚠️ *ATENÇÃO NECESSÁRIA*\n`;
                materiais.filter(m => m.quantidade_atual <= m.quantidade_minima).forEach(m => {
                    const polo = polosData.find(p => p.id === m.polo_id);
                    const status = m.quantidade_atual === 0 ? '🔴' : '🟡';
                    texto += `${status} ${m.nome} (${polo ? polo.nome : 'N/A'}): ${m.quantidade_atual}/${m.quantidade_minima} ${m.unidade}\n`;
                });
            }
            break;
    }
    
    if (!texto.trim()) {
        texto = 'Nenhum material encontrado para os critérios selecionados.';
    }
    
    textarea.value = texto;
}

function copiarTextoWhatsApp() {
    const textarea = document.getElementById('whatsapp-texto');
    textarea.select();
    document.execCommand('copy');
    mostrarAlerta('Texto copiado para a área de transferência!', 'success');
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
