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
    // Event listeners removidos - agora usando páginas separadas
    document.getElementById('form-movimentacao').addEventListener('submit', salvarMovimentacao);
    
    // Exportação WhatsApp
    document.getElementById('tipo-exportacao').addEventListener('change', gerarTextoWhatsApp);
    document.getElementById('polo-exportacao').addEventListener('change', gerarTextoWhatsApp);
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
        materiaisData = materiaisJson.materiais || [];
        
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
            <span class="badge bg-secondary">${material.polo.nome}</span>
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
                <button class="btn btn-outline-secondary" onclick="editarMaterial(${material.id})" title="Editar">
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

// Abrir modal de movimentação
function abrirMovimentacao(materialId) {
    const material = materiaisData.find(m => m.id === materialId);
    if (!material) return;
    
    document.getElementById('movimentacao-material-id').value = materialId;
    document.getElementById('movimentacao-material-nome').textContent = material.nome;
    document.getElementById('estoque-atual').textContent = `${material.quantidade_atual} ${material.unidade}`;
    
    const modal = new bootstrap.Modal(document.getElementById('modalMovimentacao'));
    modal.show();
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

// Editar material
function editarMaterial(materialId) {
    const material = materiaisData.find(m => m.id === materialId);
    if (!material) return;
    
    // Preencher formulário com dados do material
    document.getElementById('material-polo').value = material.polo_id;
    document.getElementById('material-nome').value = material.nome;
    document.getElementById('material-descricao').value = material.descricao || '';
    document.getElementById('material-unidade').value = material.unidade;
    document.getElementById('material-categoria').value = material.categoria || '';
    document.getElementById('material-quantidade-inicial').value = material.quantidade_atual;
    document.getElementById('material-quantidade-minima').value = material.quantidade_minima;
    
    // Alterar título e ação do modal
    document.querySelector('#modalMaterial .modal-title').textContent = 'Editar Material';
    document.getElementById('form-material').setAttribute('data-edit-id', materialId);
    
    const modal = new bootstrap.Modal(document.getElementById('modalMaterial'));
    modal.show();
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

// Editar polo
function editarPolo(poloId) {
    const polo = polosData.find(p => p.id === poloId);
    if (!polo) return;
    
    // Preencher formulário com dados do polo
    document.getElementById('polo-nome').value = polo.nome;
    document.getElementById('polo-descricao').value = polo.descricao || '';
    document.getElementById('polo-endereco').value = polo.endereco || '';
    document.getElementById('polo-responsavel').value = polo.responsavel || '';
    document.getElementById('polo-telefone').value = polo.telefone || '';
    document.getElementById('polo-email').value = polo.email || '';
    
    // Alterar título e ação do modal
    document.querySelector('#modalPolo .modal-title').textContent = 'Editar Polo';
    document.getElementById('form-polo').setAttribute('data-edit-id', poloId);
    
    const modal = new bootstrap.Modal(document.getElementById('modalPolo'));
    modal.show();
}

// Atualizar lista
function atualizarLista() {
    carregarDados();
}

// Gerar relatório geral
function gerarRelatorioGeral() {
    const relatorio = materiaisData.map(material => {
        const polo = polosData.find(p => p.id === material.polo_id);
        const status = material.quantidade_atual === 0 ? 'SEM ESTOQUE' :
                      material.quantidade_atual <= material.quantidade_minima ? 'ESTOQUE BAIXO' : 'OK';
        
        return `${material.nome} (${polo ? polo.nome : 'N/A'}) - Atual: ${material.quantidade_atual} ${material.unidade} - Status: ${status}`;
    }).join('\n');
    
    const textoCompleto = `📋 RELATÓRIO GERAL DE MATERIAIS\n\n${relatorio}\n\n📊 RESUMO:\n• Total: ${materiaisData.length} materiais\n• OK: ${materiaisData.filter(m => m.quantidade_atual > m.quantidade_minima).length}\n• Estoque Baixo: ${materiaisData.filter(m => m.quantidade_atual > 0 && m.quantidade_atual <= m.quantidade_minima).length}\n• Sem Estoque: ${materiaisData.filter(m => m.quantidade_atual === 0).length}`;
    
    navigator.clipboard.writeText(textoCompleto).then(() => {
        showAlert('Relatório copiado para a área de transferência!', 'success');
    });
}

// Gerar lista de compras
function gerarListaCompras() {
    window.open('/relatorio?tipo=compras', '_blank');
}

// Função para baixar relatório em Excel
function baixarRelatorioExcel(tipo = 'geral', poloId = null) {
    let url = `/relatorio?tipo=${tipo}`;
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
    .then(response => {
        if (response.ok) {
            return response.blob();
        }
        throw new Error('Erro ao gerar relatório');
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
        showAlert('Erro ao baixar relatório', 'danger');
    })
    .finally(() => {
        hideLoading();
    });
}

// Exportar para WhatsApp
function exportarWhatsApp() {
    // Atualizar lista de polos no modal
    const selectPolo = document.getElementById('selectPoloParaWhatsApp');
    if (selectPolo) {
        selectPolo.innerHTML = '<option value="">Selecione um polo...</option>';
        polosData.forEach(polo => {
            const option = document.createElement('option');
            option.value = polo.id;
            option.textContent = polo.nome;
            selectPolo.appendChild(option);
        });
    }
    
    $('#modalWhatsApp').modal('show');
}

// Gerar texto WhatsApp para polo selecionado
function gerarTextoWhatsAppPoloSelecionado(tipo) {
    const selectPolo = document.getElementById('selectPoloParaWhatsApp');
    const poloId = selectPolo ? parseInt(selectPolo.value) : null;
    
    if (!poloId) {
        showAlert('Por favor, selecione um polo primeiro', 'warning');
        return;
    }
    
    gerarTextoWhatsAppPolo(poloId, tipo);
}

// Gerar texto para WhatsApp baseado no tipo
function gerarTextoWhatsApp(tipo) {
    let materiais = [];
    let titulo = '';
    let emoji = '';
    
    switch(tipo) {
        case 'baixo_estoque':
            materiais = materiaisData.filter(m => m.quantidade_atual > 0 && m.quantidade_atual <= m.quantidade_minima);
            titulo = 'MATERIAIS COM ESTOQUE BAIXO';
            emoji = '⚠️';
            break;
        case 'sem_estoque':
            materiais = materiaisData.filter(m => m.quantidade_atual === 0);
            titulo = 'MATERIAIS SEM ESTOQUE';
            emoji = '🚨';
            break;
        case 'compras':
            materiais = materiaisData.filter(m => m.quantidade_atual < m.quantidade_minima);
            titulo = 'LISTA DE COMPRAS';
            emoji = '🛒';
            break;
        case 'geral':
            materiais = materiaisData;
            titulo = 'RELATÓRIO GERAL DE MATERIAIS';
            emoji = '📋';
            break;
    }
    
    if (materiais.length === 0) {
        showAlert(`Não há materiais para exportar no tipo: ${titulo}`, 'info');
        return;
    }
    
    const texto = materiais.map(material => {
        const polo = polosData.find(p => p.id === material.polo_id);
        const status = material.quantidade_atual === 0 ? 'SEM ESTOQUE' :
                      material.quantidade_atual <= material.quantidade_minima ? 'ESTOQUE BAIXO' : 'OK';
        
        if (tipo === 'compras') {
            const qtdNecessaria = Math.max(0, material.quantidade_minima - material.quantidade_atual + Math.ceil(material.quantidade_minima * 0.5));
            return `• ${material.nome} (${polo ? polo.nome : 'N/A'}) - Comprar: ${qtdNecessaria} ${material.unidade}`;
        } else {
            return `• ${material.nome} (${polo ? polo.nome : 'N/A'}) - Atual: ${material.quantidade_atual} ${material.unidade} - ${status}`;
        }
    }).join('\n');
    
    // Estatísticas resumidas
    const totalMateriais = materiaisData.length;
    const estoqueOk = materiaisData.filter(m => m.quantidade_atual > m.quantidade_minima).length;
    const estoqueBaixo = materiaisData.filter(m => m.quantidade_atual > 0 && m.quantidade_atual <= m.quantidade_minima).length;
    const semEstoque = materiaisData.filter(m => m.quantidade_atual === 0).length;
    
    const resumo = tipo === 'geral' ? `\n\n📊 RESUMO:\n• Total: ${totalMateriais} materiais\n• ✅ OK: ${estoqueOk}\n• ⚠️ Estoque Baixo: ${estoqueBaixo}\n• 🚨 Sem Estoque: ${semEstoque}` : '';
    
    const textoCompleto = `${emoji} ${titulo}\n\n${texto}${resumo}\n\n📱 Enviado via Sistema IAFAP - ${new Date().toLocaleDateString('pt-BR')}`;
    
    // Copiar para área de transferência
    navigator.clipboard.writeText(textoCompleto).then(() => {
        showAlert('Texto copiado para área de transferência! Cole no WhatsApp.', 'success');
        $('#modalWhatsApp').modal('hide');
    }).catch(() => {
        // Fallback para navegadores mais antigos
        const textArea = document.createElement('textarea');
        textArea.value = textoCompleto;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showAlert('Texto copiado para área de transferência! Cole no WhatsApp.', 'success');
        $('#modalWhatsApp').modal('hide');
    });
}

// Gerar texto WhatsApp por polo
function gerarTextoWhatsAppPolo(poloId, tipo) {
    const polo = polosData.find(p => p.id === poloId);
    if (!polo) {
        showAlert('Polo não encontrado', 'error');
        return;
    }
    
    let materiais = materiaisData.filter(m => m.polo_id === poloId);
    let titulo = '';
    let emoji = '';
    
    switch(tipo) {
        case 'baixo_estoque':
            materiais = materiais.filter(m => m.quantidade_atual > 0 && m.quantidade_atual <= m.quantidade_minima);
            titulo = `MATERIAIS COM ESTOQUE BAIXO - ${polo.nome}`;
            emoji = '⚠️';
            break;
        case 'sem_estoque':
            materiais = materiais.filter(m => m.quantidade_atual === 0);
            titulo = `MATERIAIS SEM ESTOQUE - ${polo.nome}`;
            emoji = '🚨';
            break;
        case 'compras':
            materiais = materiais.filter(m => m.quantidade_atual < m.quantidade_minima);
            titulo = `LISTA DE COMPRAS - ${polo.nome}`;
            emoji = '🛒';
            break;
        case 'geral':
            titulo = `RELATÓRIO DE MATERIAIS - ${polo.nome}`;
            emoji = '📋';
            break;
    }
    
    if (materiais.length === 0) {
        showAlert(`Não há materiais para exportar no polo ${polo.nome}`, 'info');
        return;
    }
    
    const texto = materiais.map(material => {
        const status = material.quantidade_atual === 0 ? 'SEM ESTOQUE' :
                      material.quantidade_atual <= material.quantidade_minima ? 'ESTOQUE BAIXO' : 'OK';
        
        if (tipo === 'compras') {
            const qtdNecessaria = Math.max(0, material.quantidade_minima - material.quantidade_atual + Math.ceil(material.quantidade_minima * 0.5));
            return `• ${material.nome} - Comprar: ${qtdNecessaria} ${material.unidade}`;
        } else {
            return `• ${material.nome} - Atual: ${material.quantidade_atual} ${material.unidade} - ${status}`;
        }
    }).join('\n');
    
    const textoCompleto = `${emoji} ${titulo}\n\n${texto}\n\n📱 Enviado via Sistema IAFAP - ${new Date().toLocaleDateString('pt-BR')}`;
    
    // Copiar para área de transferência
    navigator.clipboard.writeText(textoCompleto).then(() => {
        showAlert('Texto copiado para área de transferência! Cole no WhatsApp.', 'success');
    }).catch(() => {
        // Fallback para navegadores mais antigos
        const textArea = document.createElement('textarea');
        textArea.value = textoCompleto;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showAlert('Texto copiado para área de transferência! Cole no WhatsApp.', 'success');
    });
}

// Gerar texto para WhatsApp
function gerarTextoWhatsApp() {
    const tipo = document.getElementById('tipo-exportacao').value;
    const poloId = document.getElementById('polo-exportacao').value;
    
    let materiais = materiaisData;
    
    // Filtrar por polo se selecionado
    if (poloId) {
        materiais = materiais.filter(m => m.polo_id == poloId);
    }
    
    let texto = '';
    const dataAtual = new Date().toLocaleDateString('pt-BR');
    
    if (tipo === 'geral') {
        texto = `📦 *RELATÓRIO GERAL DE MATERIAIS*\n`;
        texto += `📅 Data: ${dataAtual}\n\n`;
        
        materiais.forEach(material => {
            const status = getStatusMaterial(material);
            const emoji = status.texto === 'Esgotado' ? '🔴' : status.texto === 'Baixo Estoque' ? '🟡' : '🟢';
            texto += `${emoji} *${material.nome}*\n`;
            texto += `   📍 Polo: ${material.polo.nome}\n`;
            texto += `   📊 Estoque: ${material.quantidade_atual} ${material.unidade}\n`;
            texto += `   ⚠️ Mínimo: ${material.quantidade_minima} ${material.unidade}\n\n`;
        });
        
    } else if (tipo === 'baixo_estoque') {
        const materiaisBaixo = materiais.filter(m => {
            const status = getStatusMaterial(m);
            return status.texto === 'Baixo Estoque' || status.texto === 'Esgotado';
        });
        
        texto = `⚠️ *MATERIAIS COM BAIXO ESTOQUE*\n`;
        texto += `📅 Data: ${dataAtual}\n\n`;
        
        materiaisBaixo.forEach(material => {
            const emoji = material.quantidade_atual <= 0 ? '🔴' : '🟡';
            texto += `${emoji} *${material.nome}*\n`;
            texto += `   📍 Polo: ${material.polo.nome}\n`;
            texto += `   📊 Estoque: ${material.quantidade_atual} ${material.unidade}\n`;
            texto += `   ⚠️ Mínimo: ${material.quantidade_minima} ${material.unidade}\n\n`;
        });
        
    } else if (tipo === 'compras') {
        const materiaisComprar = materiais.filter(m => {
            const necessario = Math.max(0, m.quantidade_minima - m.quantidade_atual);
            return necessario > 0;
        });
        
        texto = `🛒 *LISTA DE COMPRAS*\n`;
        texto += `📅 Data: ${dataAtual}\n\n`;
        
        materiaisComprar.forEach(material => {
            const necessario = Math.max(0, material.quantidade_minima - material.quantidade_atual);
            texto += `🛍️ *${material.nome}*\n`;
            texto += `   📍 Polo: ${material.polo.nome}\n`;
            texto += `   🔢 Quantidade: ${necessario} ${material.unidade}\n\n`;
        });
    }
    
    document.getElementById('texto-whatsapp').value = texto;
}

// Copiar texto para área de transferência
function copiarTexto() {
    const textarea = document.getElementById('texto-whatsapp');
    textarea.select();
    document.execCommand('copy');
    showAlert('Texto copiado para a área de transferência!', 'success');
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
