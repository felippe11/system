// Dashboard Analítico - JavaScript Interativo

// Configuração global dos gráficos
Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
Chart.defaults.color = '#495057';
Chart.defaults.plugins.legend.position = 'bottom';

// Variáveis globais
let chartsInstances = {};
let currentFilters = {};
let dashboardData = {};

// Inicialização do dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setupEventListeners();
    loadDashboardData();
});

// Inicialização principal
function initializeDashboard() {
    console.log('Inicializando Dashboard Analítico...');
    
    // Configurar tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Configurar popovers para explicações de KPIs
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// Configurar event listeners
function setupEventListeners() {
    // Filtros globais
    const filterInputs = document.querySelectorAll('.filtro-global');
    filterInputs.forEach(input => {
        input.addEventListener('change', handleFilterChange);
    });
    
    // Botões de ação
    document.getElementById('aplicarFiltros')?.addEventListener('click', applyFilters);
    document.getElementById('limparFiltros')?.addEventListener('click', clearFilters);
    document.getElementById('exportarCSV')?.addEventListener('click', () => exportData('csv'));
    document.getElementById('exportarExcel')?.addEventListener('click', () => exportData('excel'));
    document.getElementById('exportarPDF')?.addEventListener('click', () => exportData('pdf'));
    
    // Drill-down links
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('drill-down-link')) {
            e.preventDefault();
            handleDrillDown(e.target.dataset.type, e.target.dataset.id);
        }
    });
    
    // Comparação temporal
    document.getElementById('compararPeriodo')?.addEventListener('click', toggleTemporalComparison);
}

// Carregar dados do dashboard
function loadDashboardData() {
    showLoading();
    
    const filters = getCurrentFilters();
    
    fetch('/gerar_relatorio_evento', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(filters)
    })
    .then(response => response.json())
    .then(data => {
        dashboardData = data;
        updateDashboard(data);
        hideLoading();
    })
    .catch(error => {
        console.error('Erro ao carregar dados:', error);
        showError('Erro ao carregar dados do dashboard');
        hideLoading();
    });
}

// Atualizar dashboard com novos dados
function updateDashboard(data) {
    updateKPIs(data.kpis);
    updateCharts(data);
    updateTables(data);
    updateAlerts(data.alertas);
}

// Atualizar KPIs
function updateKPIs(kpis) {
    Object.keys(kpis).forEach(key => {
        const element = document.getElementById(`kpi-${key}`);
        if (element) {
            const valueEl = element.querySelector('.kpi-value');
            const changeEl = element.querySelector('.kpi-change');
            
            if (valueEl) {
                valueEl.textContent = formatKPIValue(key, kpis[key].valor);
            }
            
            if (changeEl && kpis[key].variacao !== undefined) {
                const variacao = kpis[key].variacao;
                changeEl.textContent = `${variacao > 0 ? '+' : ''}${variacao.toFixed(1)}%`;
                changeEl.className = `kpi-change ${variacao >= 0 ? 'positive' : 'negative'}`;
            }
        }
    });
}

// Formatar valores dos KPIs
function formatKPIValue(type, value) {
    switch(type) {
        case 'receita_bruta':
        case 'receita_liquida':
        case 'ticket_medio':
            return new Intl.NumberFormat('pt-BR', {
                style: 'currency',
                currency: 'BRL'
            }).format(value);
        case 'taxa_presenca':
        case 'capacidade_usada':
        case 'taxa_conversao':
        case 'percentual_quitados':
            return `${value.toFixed(1)}%`;
        case 'tempo_medio_checkin':
            return `${Math.round(value)} min`;
        default:
            return new Intl.NumberFormat('pt-BR').format(value);
    }
}

// Atualizar gráficos
function updateCharts(data) {
    // Gráfico de Funil de Conversão
    updateFunnelChart(data.visao_funil);
    
    // Gráfico de Ocupação por Horário
    updateOccupancyChart(data.visao_ocupacao);
    
    // Gráfico de Presença por Oficina
    updatePresenceChart(data.visao_presenca);
    
    // Gráfico de Satisfação
    updateSatisfactionChart(data.visao_qualidade);
    
    // Gráfico Financeiro
    updateFinancialChart(data.visao_financeiro);
    
    // Mapa Geográfico
    updateGeographicChart(data.visao_geografia);
}

// Gráfico de Funil de Conversão
function updateFunnelChart(data) {
    const ctx = document.getElementById('funnelChart');
    if (!ctx || !data) return;
    
    if (chartsInstances.funnel) {
        chartsInstances.funnel.destroy();
    }
    
    chartsInstances.funnel = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.etapas,
            datasets: [{
                label: 'Quantidade',
                data: data.valores,
                backgroundColor: [
                    '#667eea', '#764ba2', '#f093fb', '#f5576c',
                    '#4facfe', '#00f2fe', '#43e97b', '#38f9d7'
                ],
                borderRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Funil de Conversão'
                },
                tooltip: {
                    callbacks: {
                        afterLabel: function(context) {
                            const index = context.dataIndex;
                            if (index > 0) {
                                const current = context.raw;
                                const previous = data.valores[index - 1];
                                const conversion = ((current / previous) * 100).toFixed(1);
                                return `Conversão: ${conversion}%`;
                            }
                            return '';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return new Intl.NumberFormat('pt-BR').format(value);
                        }
                    }
                }
            }
        }
    });
}

// Gráfico de Ocupação (Mapa de Calor)
function updateOccupancyChart(data) {
    const ctx = document.getElementById('occupancyChart');
    if (!ctx || !data) return;
    
    if (chartsInstances.occupancy) {
        chartsInstances.occupancy.destroy();
    }
    
    chartsInstances.occupancy = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Ocupação (%)',
                data: data.pontos,
                backgroundColor: function(context) {
                    const value = context.parsed.y;
                    if (value >= 90) return '#e74c3c';
                    if (value >= 75) return '#f39c12';
                    if (value >= 50) return '#f1c40f';
                    return '#2ecc71';
                },
                pointRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Mapa de Calor - Ocupação por Horário'
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            const point = context[0];
                            return `${point.label || 'Horário'}: ${point.parsed.x}h`;
                        },
                        label: function(context) {
                            return `Ocupação: ${context.parsed.y.toFixed(1)}%`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Horário'
                    },
                    min: 8,
                    max: 18
                },
                y: {
                    title: {
                        display: true,
                        text: 'Ocupação (%)'
                    },
                    min: 0,
                    max: 100
                }
            }
        }
    });
}

// Gráfico de Presença por Oficina
function updatePresenceChart(data) {
    const ctx = document.getElementById('presenceChart');
    if (!ctx || !data) return;
    
    if (chartsInstances.presence) {
        chartsInstances.presence.destroy();
    }
    
    chartsInstances.presence = new Chart(ctx, {
        type: 'horizontalBar',
        data: {
            labels: data.oficinas,
            datasets: [{
                label: 'Taxa de Presença (%)',
                data: data.taxas_presenca,
                backgroundColor: '#667eea',
                borderColor: '#764ba2',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Taxa de Presença por Oficina'
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });
}

// Gráfico de Satisfação
function updateSatisfactionChart(data) {
    const ctx = document.getElementById('satisfactionChart');
    if (!ctx || !data) return;
    
    if (chartsInstances.satisfaction) {
        chartsInstances.satisfaction.destroy();
    }
    
    chartsInstances.satisfaction = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Promotores', 'Neutros', 'Detratores'],
            datasets: [{
                data: [data.promotores, data.neutros, data.detratores],
                backgroundColor: ['#2ecc71', '#f1c40f', '#e74c3c'],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `NPS: ${data.nps || 0}`
                },
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Gráfico Financeiro
function updateFinancialChart(data) {
    const ctx = document.getElementById('financialChart');
    if (!ctx || !data) return;
    
    if (chartsInstances.financial) {
        chartsInstances.financial.destroy();
    }
    
    chartsInstances.financial = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.periodos,
            datasets: [{
                label: 'Receita Bruta',
                data: data.receita_bruta,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4
            }, {
                label: 'Receita Líquida',
                data: data.receita_liquida,
                borderColor: '#2ecc71',
                backgroundColor: 'rgba(46, 204, 113, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Evolução Financeira'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return new Intl.NumberFormat('pt-BR', {
                                style: 'currency',
                                currency: 'BRL',
                                minimumFractionDigits: 0
                            }).format(value);
                        }
                    }
                }
            }
        }
    });
}

// Mapa Geográfico (usando Chart.js como fallback)
function updateGeographicChart(data) {
    const ctx = document.getElementById('geographicChart');
    if (!ctx || !data) return;
    
    if (chartsInstances.geographic) {
        chartsInstances.geographic.destroy();
    }
    
    chartsInstances.geographic = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.cidades,
            datasets: [{
                label: 'Inscritos',
                data: data.inscritos,
                backgroundColor: '#667eea',
                yAxisID: 'y'
            }, {
                label: 'Presentes',
                data: data.presentes,
                backgroundColor: '#2ecc71',
                yAxisID: 'y'
            }, {
                label: 'Satisfação Média',
                data: data.satisfacao,
                type: 'line',
                borderColor: '#f39c12',
                backgroundColor: 'rgba(243, 156, 18, 0.1)',
                yAxisID: 'y1'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Distribuição Geográfica'
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    beginAtZero: true
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    min: 0,
                    max: 5,
                    grid: {
                        drawOnChartArea: false
                    }
                }
            }
        }
    });
}

// Atualizar tabelas
function updateTables(data) {
    // Atualizar tabela de top oficinas
    updateTopOficinasTable(data.top_oficinas);
    
    // Atualizar tabela de certificados
    updateCertificadosTable(data.visao_certificados);
}

// Atualizar tabela de top oficinas
function updateTopOficinasTable(data) {
    const tbody = document.querySelector('#topOficinasTable tbody');
    if (!tbody || !data) return;
    
    tbody.innerHTML = '';
    
    data.forEach((oficina, index) => {
        const row = tbody.insertRow();
        row.innerHTML = `
            <td>${index + 1}</td>
            <td><a href="#" class="drill-down-link" data-type="oficina" data-id="${oficina.id}">${oficina.nome}</a></td>
            <td>${oficina.inscritos}</td>
            <td>${oficina.presentes}</td>
            <td>${oficina.taxa_presenca.toFixed(1)}%</td>
            <td>${oficina.satisfacao.toFixed(1)}</td>
        `;
    });
}

// Atualizar tabela de certificados
function updateCertificadosTable(data) {
    const tbody = document.querySelector('#certificadosTable tbody');
    if (!tbody || !data) return;
    
    tbody.innerHTML = '';
    
    data.por_tipo.forEach(cert => {
        const row = tbody.insertRow();
        row.innerHTML = `
            <td>${cert.tipo}</td>
            <td>${cert.gerados}</td>
            <td>${cert.baixados}</td>
            <td>${cert.taxa_download.toFixed(1)}%</td>
            <td>${cert.tempo_medio_emissao} min</td>
        `;
    });
}

// Atualizar alertas
function updateAlerts(alertas) {
    const container = document.getElementById('alertasContainer');
    if (!container || !alertas) return;
    
    container.innerHTML = '';
    
    alertas.forEach(alerta => {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${alerta.tipo} alert-custom`;
        alertDiv.innerHTML = `
            <strong>${alerta.titulo}</strong>
            <p class="mb-0">${alerta.mensagem}</p>
        `;
        container.appendChild(alertDiv);
    });
}

// Manipular mudanças nos filtros
function handleFilterChange(event) {
    const filterId = event.target.id;
    const filterValue = event.target.value;
    
    currentFilters[filterId] = filterValue;
    
    // Auto-aplicar filtros após 500ms de inatividade
    clearTimeout(window.filterTimeout);
    window.filterTimeout = setTimeout(() => {
        applyFilters();
    }, 500);
}

// Aplicar filtros
function applyFilters() {
    loadDashboardData();
}

// Limpar filtros
function clearFilters() {
    const filterInputs = document.querySelectorAll('.filtro-global');
    filterInputs.forEach(input => {
        input.value = '';
    });
    
    currentFilters = {};
    loadDashboardData();
}

// Obter filtros atuais
function getCurrentFilters() {
    const filters = {};
    
    const filterInputs = document.querySelectorAll('.filtro-global');
    filterInputs.forEach(input => {
        if (input.value) {
            filters[input.id] = input.value;
        }
    });
    
    return filters;
}

// Drill-down
function handleDrillDown(type, id) {
    console.log(`Drill-down: ${type} - ${id}`);
    
    // Implementar lógica de drill-down específica
    switch(type) {
        case 'oficina':
            showOficinaDetails(id);
            break;
        case 'participante':
            showParticipanteDetails(id);
            break;
        case 'evento':
            showEventoDetails(id);
            break;
        default:
            console.log('Tipo de drill-down não implementado:', type);
    }
}

// Mostrar detalhes da oficina
function showOficinaDetails(oficinaId) {
    showLoading();
    
    fetch(`/api/dashboard/oficina/${oficinaId}`)
        .then(response => {
            if (!response.ok) {
                if (response.status === 403) {
                    throw new Error('Acesso negado. Você não tem permissão para visualizar estes dados.');
                }
                throw new Error(`Erro ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            const modalContent = `
                <div class="modal fade" id="oficinaModal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Detalhes da Oficina: ${data.info.titulo}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="row">
                                    <div class="col-md-6">
                                        <h6>Informações Gerais</h6>
                                        <p><strong>Descrição:</strong> ${data.info.descricao || 'N/A'}</p>
                                        <p><strong>Vagas:</strong> ${data.info.vagas}</p>
                                        <p><strong>Carga Horária:</strong> ${data.info.carga_horaria || 'N/A'}</p>
                                        <p><strong>Local:</strong> ${data.info.cidade}, ${data.info.estado}</p>
                                        <p><strong>Modalidade:</strong> ${data.info.modalidade || 'N/A'}</p>
                                    </div>
                                    <div class="col-md-6">
                                        <h6>Métricas</h6>
                                        <p><strong>Inscritos:</strong> ${data.metricas.total_inscricoes}</p>
                                        <p><strong>Presentes:</strong> ${data.metricas.total_presencas}</p>
                                        <p><strong>Taxa de Presença:</strong> ${(data.metricas.taxa_presenca || 0).toFixed(1)}%</p>
                                        <p><strong>Ocupação:</strong> ${(data.metricas.ocupacao || 0).toFixed(1)}%</p>
                                    </div>
                                </div>
                                <div class="mt-3">
                                    <h6>Lista de Inscrições</h6>
                                    <div class="table-responsive">
                                        <table class="table table-sm">
                                            <thead>
                                                <tr>
                                                    <th>Nome</th>
                                                    <th>Email</th>
                                                    <th>Status</th>
                                                    <th>Data Inscrição</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                ${data.inscricoes && data.inscricoes.length > 0 ? data.inscricoes.map(i => `
                                                    <tr>
                                                        <td>${i.usuario_nome}</td>
                                                        <td>${i.usuario_email}</td>
                                                        <td><span class="badge bg-${i.status === 'presente' ? 'success' : i.status === 'confirmado' ? 'primary' : 'warning'}">${i.status}</span></td>
                                                        <td>${i.data_inscricao ? new Date(i.data_inscricao).toLocaleDateString('pt-BR') : 'N/A'}</td>
                                                    </tr>
                                                `).join('') : '<tr><td colspan="4" class="text-center">Nenhuma inscrição encontrada</td></tr>'}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                                <button type="button" class="btn btn-primary" onclick="exportOficinaData(${oficinaId})">Exportar Dados</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Remove modal anterior se existir
            const existingModal = document.getElementById('oficinaModal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // Adiciona novo modal
            document.body.insertAdjacentHTML('beforeend', modalContent);
            const modal = new bootstrap.Modal(document.getElementById('oficinaModal'));
            modal.show();
            
            hideLoading();
        })
        .catch(error => {
            console.error('Erro ao carregar detalhes da oficina:', error);
            showError(error.message || 'Erro ao carregar detalhes da oficina. Tente novamente.');
            hideLoading();
        });
}

// Mostrar detalhes do participante
function showParticipanteDetails(participanteId) {
    showLoading();
    
    fetch(`/api/dashboard/participante/${participanteId}`)
        .then(response => {
            if (!response.ok) {
                if (response.status === 403) {
                    throw new Error('Acesso negado. Você não tem permissão para visualizar estes dados.');
                }
                throw new Error(`Erro ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            const modalContent = `
                <div class="modal fade" id="participanteModal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Perfil do Participante: ${data.info.nome}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="row">
                                    <div class="col-md-6">
                                        <h6>Informações Pessoais</h6>
                                        <p><strong>Email:</strong> ${data.info.email || 'N/A'}</p>
                                        <p><strong>CPF:</strong> ${data.info.cpf || 'N/A'}</p>
                                        <p><strong>Telefone:</strong> ${data.info.telefone || 'N/A'}</p>
                                        <p><strong>Cidade:</strong> ${data.info.cidade || 'N/A'}</p>
                                        <p><strong>Estado:</strong> ${data.info.estado || 'N/A'}</p>
                                    </div>
                                    <div class="col-md-6">
                                        <h6>Métricas de Participação</h6>
                                        <p><strong>Total de Inscrições:</strong> ${data.metricas.total_inscricoes}</p>
                                        <p><strong>Eventos Concluídos:</strong> ${data.metricas.eventos_concluidos}</p>
                                        <p><strong>Taxa de Presença:</strong> ${data.metricas.taxa_presenca}%</p>
                                        <p><strong>Certificados Emitidos:</strong> ${data.metricas.certificados_emitidos}</p>
                                        <p><strong>Avaliação Média:</strong> ${data.metricas.avaliacao_media || 'N/A'}</p>
                                    </div>
                                </div>
                                <div class="mt-3">
                                    <h6>Histórico de Inscrições</h6>
                                    <div class="table-responsive">
                                        <table class="table table-sm">
                                            <thead>
                                                <tr>
                                                    <th>Evento</th>
                                                    <th>Oficina</th>
                                                    <th>Data</th>
                                                    <th>Status</th>
                                                    <th>Presença</th>
                                                    <th>Avaliação</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                ${data.inscricoes.map(i => `
                                                    <tr>
                                                        <td>${i.evento_nome}</td>
                                                        <td>${i.oficina_nome}</td>
                                                        <td>${i.data_inscricao}</td>
                                                        <td><span class="badge bg-${i.status === 'confirmado' ? 'success' : i.status === 'pendente' ? 'warning' : 'danger'}">${i.status}</span></td>
                                                        <td><span class="badge bg-${i.presente ? 'success' : 'danger'}">${i.presente ? 'Presente' : 'Ausente'}</span></td>
                                                        <td>${i.avaliacao ? '⭐'.repeat(i.avaliacao) : '-'}</td>
                                                    </tr>
                                                `).join('')}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                                <button type="button" class="btn btn-primary" onclick="exportParticipanteData(${participanteId})">Exportar Histórico</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Remove modal anterior se existir
            const existingModal = document.getElementById('participanteModal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // Adiciona novo modal
            document.body.insertAdjacentHTML('beforeend', modalContent);
            const modal = new bootstrap.Modal(document.getElementById('participanteModal'));
            modal.show();
            
            hideLoading();
        })
        .catch(error => {
            console.error('Erro ao carregar detalhes do participante:', error);
            showError(error.message || 'Erro ao carregar detalhes do participante. Tente novamente.');
            hideLoading();
        });
}

// Mostrar detalhes do evento
function showEventoDetails(eventoId) {
    showLoading();
    
    fetch(`/api/dashboard/evento/${eventoId}`)
        .then(response => {
            if (!response.ok) {
                if (response.status === 403) {
                    throw new Error('Acesso negado. Você não tem permissão para visualizar estes dados.');
                }
                throw new Error(`Erro ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            const modalContent = `
                <div class="modal fade" id="eventoModal" tabindex="-1">
                    <div class="modal-dialog modal-xl">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Detalhes do Evento: ${data.info.titulo}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="row">
                                    <div class="col-md-4">
                                        <h6>Informações Gerais</h6>
                                        <p><strong>Cliente:</strong> ${data.info.cliente_nome || 'N/A'}</p>
                                        <p><strong>Período:</strong> ${data.info.data_inicio} - ${data.info.data_fim}</p>
                                        <p><strong>Local:</strong> ${data.info.local || 'N/A'}</p>
                                        <p><strong>Modalidade:</strong> ${data.info.modalidade || 'N/A'}</p>
                                        <p><strong>Status:</strong> ${data.info.status}</p>
                                    </div>
                                    <div class="col-md-4">
                                        <h6>Métricas Gerais</h6>
                                        <p><strong>Total de Oficinas:</strong> ${data.metricas.total_oficinas}</p>
                                        <p><strong>Total de Inscritos:</strong> ${data.metricas.total_inscritos}</p>
                                        <p><strong>Taxa de Presença:</strong> ${data.metricas.taxa_presenca}%</p>
                                        <p><strong>Receita Total:</strong> R$ ${data.metricas.receita_total || '0,00'}</p>
                                    </div>
                                    <div class="col-md-4">
                                        <h6>Indicadores de Qualidade</h6>
                                        <p><strong>Avaliação Média:</strong> ${data.metricas.avaliacao_media || 'N/A'}/5</p>
                                        <p><strong>NPS:</strong> ${data.metricas.nps || 'N/A'}</p>
                                        <p><strong>Certificados Emitidos:</strong> ${data.metricas.certificados_emitidos}</p>
                                        <p><strong>Taxa de Conclusão:</strong> ${data.metricas.taxa_conclusao}%</p>
                                    </div>
                                </div>
                                <div class="mt-3">
                                    <h6>Oficinas do Evento</h6>
                                    <div class="table-responsive">
                                        <table class="table table-sm">
                                            <thead>
                                                <tr>
                                                    <th>Oficina</th>
                                                    <th>Formador</th>
                                                    <th>Data</th>
                                                    <th>Inscritos</th>
                                                    <th>Presentes</th>
                                                    <th>Taxa Presença</th>
                                                    <th>Ações</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                ${data.oficinas.map(o => `
                                                    <tr>
                                                        <td>${o.titulo}</td>
                                                        <td>${o.formador_nome || 'N/A'}</td>
                                                        <td>${o.data_inicio}</td>
                                                        <td>${o.total_inscritos}</td>
                                                        <td>${o.total_presentes}</td>
                                                        <td>${o.taxa_presenca}%</td>
                                                        <td>
                                                            <button class="btn btn-sm btn-outline-primary" onclick="showOficinaDetails(${o.id})">
                                                                <i class="fas fa-eye"></i>
                                                            </button>
                                                        </td>
                                                    </tr>
                                                `).join('')}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                                <button type="button" class="btn btn-primary" onclick="exportEventoData(${eventoId})">Exportar Relatório</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Remove modal anterior se existir
            const existingModal = document.getElementById('eventoModal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // Adiciona novo modal
            document.body.insertAdjacentHTML('beforeend', modalContent);
            const modal = new bootstrap.Modal(document.getElementById('eventoModal'));
            modal.show();
            
            hideLoading();
        })
        .catch(error => {
            console.error('Erro ao carregar detalhes do evento:', error);
            showError(error.message || 'Erro ao carregar detalhes do evento. Tente novamente.');
            hideLoading();
        });
}

// Exportar dados específicos de oficina
function exportOficinaData(oficinaId) {
    const url = `/api/oficina/${oficinaId}/export?format=excel`;
    window.open(url, '_blank');
}

// Exportar dados específicos de participante
function exportParticipanteData(participanteId) {
    const url = `/api/participante/${participanteId}/export?format=excel`;
    window.open(url, '_blank');
}

// Exportar dados específicos de evento
function exportEventoData(eventoId) {
    const url = `/api/evento/${eventoId}/export?format=excel`;
    window.open(url, '_blank');
}

// Comparação temporal
function toggleTemporalComparison() {
    const compareBtn = document.getElementById('compararPeriodo');
    const compareSection = document.getElementById('periodoComparacao');
    
    if (!compareBtn || !compareSection) {
        console.warn('Elementos de comparação temporal não encontrados');
        return;
    }
    
    const isActive = compareBtn.classList.contains('active');
    
    if (isActive) {
        // Desativar comparação
        compareBtn.classList.remove('active');
        compareBtn.innerHTML = '<i class="fas fa-chart-line"></i> Comparar Período';
        compareSection.style.display = 'none';
        
        // Remover dados de comparação dos gráficos
        removeComparisonData();
    } else {
        // Ativar comparação
        compareBtn.classList.add('active');
        compareBtn.innerHTML = '<i class="fas fa-times"></i> Cancelar Comparação';
        compareSection.style.display = 'block';
        
        // Adicionar campos de período de comparação se não existirem
        if (!compareSection.querySelector('.comparison-fields')) {
            const comparisonFields = `
                <div class="comparison-fields">
                    <div class="row">
                        <div class="col-md-6">
                            <label class="form-label">Período de Comparação - Início</label>
                            <input type="date" class="form-control" id="dataInicioComparacao">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Período de Comparação - Fim</label>
                            <input type="date" class="form-control" id="dataFimComparacao">
                        </div>
                    </div>
                    <div class="row mt-3">
                        <div class="col-12">
                            <button type="button" class="btn btn-primary" onclick="applyTemporalComparison()">
                                <i class="fas fa-chart-bar"></i> Aplicar Comparação
                            </button>
                        </div>
                    </div>
                </div>
            `;
            compareSection.innerHTML = comparisonFields;
        }
    }
}

// Aplicar comparação temporal
function applyTemporalComparison() {
    const dataInicio = document.getElementById('dataInicioComparacao')?.value;
    const dataFim = document.getElementById('dataFimComparacao')?.value;
    
    if (!dataInicio || !dataFim) {
        showError('Por favor, selecione ambas as datas para comparação');
        return;
    }
    
    if (new Date(dataInicio) >= new Date(dataFim)) {
        showError('A data de início deve ser anterior à data de fim');
        return;
    }
    
    showLoading();
    
    // Obter filtros atuais
    const currentFilters = getCurrentFilters();
    
    // Criar filtros para período de comparação
    const comparisonFilters = {
        ...currentFilters,
        data_inicio: dataInicio,
        data_fim: dataFim
    };
    
    // Buscar dados do período de comparação
    fetch('/gerar_relatorio_evento', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(comparisonFilters)
    })
    .then(response => response.json())
    .then(comparisonData => {
        // Adicionar dados de comparação aos gráficos
        addComparisonData(dashboardData, comparisonData);
        
        // Atualizar KPIs com comparação
        updateKPIsWithComparison(dashboardData.kpis, comparisonData.kpis);
        
        hideLoading();
        
        showSuccess('Comparação temporal aplicada com sucesso!');
    })
    .catch(error => {
        console.error('Erro ao carregar dados de comparação:', error);
        showError('Erro ao carregar dados de comparação');
        hideLoading();
    });
}

// Adicionar dados de comparação aos gráficos
function addComparisonData(currentData, comparisonData) {
    // Atualizar gráfico de funil com comparação
    if (chartsInstances.funnel && currentData.visao_funil && comparisonData.visao_funil) {
        const chart = chartsInstances.funnel;
        
        // Adicionar dataset de comparação
        chart.data.datasets.push({
            label: 'Período de Comparação',
            data: comparisonData.visao_funil.valores,
            backgroundColor: 'rgba(108, 117, 125, 0.7)',
            borderColor: 'rgba(108, 117, 125, 1)',
            borderWidth: 1,
            borderRadius: 5
        });
        
        chart.update();
    }
    
    // Atualizar outros gráficos com dados de comparação
    updateChartsWithComparison(currentData, comparisonData);
}

// Remover dados de comparação
function removeComparisonData() {
    Object.keys(chartsInstances).forEach(chartKey => {
        const chart = chartsInstances[chartKey];
        if (chart && chart.data.datasets.length > 1) {
            // Manter apenas o primeiro dataset (dados atuais)
            chart.data.datasets = [chart.data.datasets[0]];
            chart.update();
        }
    });
}

// Atualizar KPIs com comparação
function updateKPIsWithComparison(currentKPIs, comparisonKPIs) {
    Object.keys(currentKPIs).forEach(key => {
        const currentValue = currentKPIs[key];
        const comparisonValue = comparisonKPIs[key];
        
        if (currentValue !== undefined && comparisonValue !== undefined) {
            const variation = ((currentValue - comparisonValue) / comparisonValue * 100);
            
            const element = document.querySelector(`[data-kpi="${key}"] .kpi-change`);
            if (element) {
                element.innerHTML = `
                    <i class="fas fa-${variation >= 0 ? 'arrow-up' : 'arrow-down'}"></i>
                    ${variation >= 0 ? '+' : ''}${variation.toFixed(1)}% vs período comparação
                `;
                element.className = `kpi-change ${variation >= 0 ? 'positive' : 'negative'}`;
            }
        }
    });
}

// Atualizar gráficos com dados de comparação
function updateChartsWithComparison(currentData, comparisonData) {
    // Implementar lógica específica para cada tipo de gráfico
    console.log('Atualizando gráficos com dados de comparação:', { currentData, comparisonData });
}

// Funções utilitárias para UI
function showLoading() {
    // Remove loading anterior se existir
    const existingLoading = document.getElementById('loadingOverlay');
    if (existingLoading) {
        existingLoading.remove();
    }
    
    const loadingHTML = `
        <div id="loadingOverlay" class="loading-overlay">
            <div class="text-center text-white">
                <div class="loading-spinner"></div>
                <div class="mt-3">Carregando dados...</div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', loadingHTML);
}

function hideLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.remove();
    }
}

function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'error');
}

function showNotification(message, type) {
    // Remove notificação anterior se existir
    const existingNotification = document.getElementById('notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    const notificationHTML = `
        <div id="notification" class="alert alert-${type}-custom alert-dismissible fade show" 
             style="position: fixed; top: 20px; right: 20px; z-index: 10000; min-width: 300px;">
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'}"></i>
            ${message}
            <button type="button" class="btn-close" onclick="hideNotification()"></button>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', notificationHTML);
    
    // Auto-hide após 5 segundos
    setTimeout(() => {
        hideNotification();
    }, 5000);
}

function hideNotification() {
    const notification = document.getElementById('notification');
    if (notification) {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }
}

// Função para obter filtros atuais
function getCurrentFilters() {
    const form = document.getElementById('filtrosForm');
    if (!form) return {};
    
    const formData = new FormData(form);
    const filters = {};
    
    for (let [key, value] of formData.entries()) {
        if (value && value.trim() !== '') {
            filters[key] = value;
        }
    }
    
    return filters;
}

// Função para limpar filtros
function limparFiltros() {
    const form = document.getElementById('filtrosForm');
    if (form) {
        form.reset();
        
        // Recarregar dados com filtros limpos
        loadDashboardData();
        
        showSuccess('Filtros limpos com sucesso!');
    }
}

// Função para salvar filtros
function salvarFiltros() {
    const filters = getCurrentFilters();
    
    // Salvar no localStorage
    localStorage.setItem('dashboard_filters', JSON.stringify(filters));
    
    showSuccess('Filtros salvos com sucesso!');
}

// Função para carregar filtros salvos
function carregarFiltrosSalvos() {
    const savedFilters = localStorage.getItem('dashboard_filters');
    
    if (savedFilters) {
        try {
            const filters = JSON.parse(savedFilters);
            
            // Aplicar filtros salvos ao formulário
            Object.keys(filters).forEach(key => {
                const input = document.querySelector(`[name="${key}"]`);
                if (input) {
                    input.value = filters[key];
                }
            });
            
            showSuccess('Filtros carregados com sucesso!');
        } catch (error) {
            console.error('Erro ao carregar filtros salvos:', error);
            showError('Erro ao carregar filtros salvos');
        }
    }
}

// Função para exportar dados
function exportData(format) {
    const filters = getCurrentFilters();
    const url = `/gerar_relatorio_evento?export=${format}&${new URLSearchParams(filters).toString()}`;
    
    showLoading();
    
    // Criar link temporário para download
    const link = document.createElement('a');
    link.href = url;
    link.download = `dashboard_${format}_${new Date().toISOString().split('T')[0]}.${format}`;
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    setTimeout(() => {
        hideLoading();
        showSuccess(`Dados exportados em ${format.toUpperCase()} com sucesso!`);
    }, 2000);
}

// Função para aplicar filtros
function applyFilters() {
    const form = document.getElementById('filtrosForm');
    if (form) {
        // Submeter formulário
        form.submit();
    }
}

// Função para drill-down genérica
function drillDown(tipo, valor) {
    console.log(`Drill-down acionado: ${tipo} = ${valor}`);
    
    switch(tipo) {
        case 'inscricoes':
            // Filtrar por inscrições
            showInscricoesDetails();
            break;
        case 'presenca':
            // Filtrar por presença
            showPresencaDetails();
            break;
        case 'capacidade':
            // Filtrar por capacidade
            showCapacidadeDetails();
            break;
        case 'receita':
            // Filtrar por receita
            showReceitaDetails();
            break;
        default:
            console.log('Tipo de drill-down não implementado:', tipo);
    }
}

// Funções específicas de drill-down para KPIs
function showInscricoesDetails() {
    // Implementar modal com detalhes de inscrições
    showSuccess('Detalhes de inscrições - Em desenvolvimento');
}

function showPresencaDetails() {
    // Implementar modal com detalhes de presença
    showSuccess('Detalhes de presença - Em desenvolvimento');
}

function showCapacidadeDetails() {
    // Implementar modal com detalhes de capacidade
    showSuccess('Detalhes de capacidade - Em desenvolvimento');
}

function showReceitaDetails() {
    // Implementar modal com detalhes de receita
    showSuccess('Detalhes de receita - Em desenvolvimento');
}

// Exportar dados
function exportData(format) {
    showLoading();
    
    const filters = getCurrentFilters();
    filters.export_format = format;
    
    fetch('/gerar_relatorio_evento/export', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(filters)
    })
    .then(response => {
        if (response.ok) {
            return response.blob();
        }
        throw new Error('Erro na exportação');
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dashboard_analitico_${new Date().toISOString().split('T')[0]}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        hideLoading();
    })
    .catch(error => {
        console.error('Erro na exportação:', error);
        showError('Erro ao exportar dados');
        hideLoading();
    });
}

// Mostrar loading
function showLoading() {
    const loadingEl = document.getElementById('loadingIndicator');
    if (loadingEl) {
        loadingEl.style.display = 'block';
    }
}

// Esconder loading
function hideLoading() {
    const loadingEl = document.getElementById('loadingIndicator');
    if (loadingEl) {
        loadingEl.style.display = 'none';
    }
}

// Mostrar erro
function showError(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.dashboard-container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-remover após 5 segundos
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// Utilitários
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Auto-refresh do dashboard (opcional)
function startAutoRefresh(intervalMinutes = 5) {
    setInterval(() => {
        console.log('Auto-refresh do dashboard...');
        loadDashboardData();
    }, intervalMinutes * 60 * 1000);
}

// Iniciar auto-refresh se configurado
// startAutoRefresh(5); // Refresh a cada 5 minutos

// Interactive Visualizations Functions
function initGeographicMap() {
    const mapElement = document.getElementById('geographic-map');
    if (!mapElement) return;
    
    // Placeholder for Leaflet map initialization
    mapElement.innerHTML = `
        <div style="text-align: center; padding: 20px;">
            <i class="fas fa-map-marked-alt fa-3x mb-3"></i>
            <h5>Mapa Geográfico Interativo</h5>
            <p class="text-muted">Distribuição de eventos por localização</p>
            <small class="text-info">Integração com Leaflet.js em desenvolvimento</small>
        </div>
    `;
}

function initEventCalendar() {
    const calendarElement = document.getElementById('event-calendar');
    if (!calendarElement) return;
    
    // Placeholder for FullCalendar initialization
    calendarElement.innerHTML = `
        <div style="text-align: center; padding: 20px;">
            <i class="fas fa-calendar-alt fa-3x mb-3"></i>
            <h5>Calendário de Eventos</h5>
            <p class="text-muted">Visualização temporal de workshops e eventos</p>
            <small class="text-info">Integração com FullCalendar.js em desenvolvimento</small>
        </div>
    `;
}

function initAttendanceHeatmap() {
    const heatmapElement = document.getElementById('attendance-heatmap');
    if (!heatmapElement) return;
    
    // Placeholder for D3.js heatmap
    heatmapElement.innerHTML = `
        <div style="text-align: center; padding: 20px;">
            <i class="fas fa-th fa-3x mb-3"></i>
            <h5>Mapa de Calor - Presença</h5>
            <p class="text-muted">Padrões de presença por dia e horário</p>
            <small class="text-info">Integração com D3.js em desenvolvimento</small>
        </div>
    `;
}

// Initialize interactive visualizations when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Add a small delay to ensure all elements are rendered
    setTimeout(() => {
        initGeographicMap();
        initEventCalendar();
        initAttendanceHeatmap();
    }, 500);
});