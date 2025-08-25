document.addEventListener('DOMContentLoaded', function() {
    console.log('🔍 DEBUG: DOM carregado, iniciando submission_import.js');
    
    // Verificar se Bootstrap está disponível
    if (typeof bootstrap !== 'undefined') {
        console.log('✅ DEBUG: Bootstrap está disponível');
    } else {
        console.error('❌ DEBUG: Bootstrap não está disponível!');
    }
    
    const formImportarTrabalhos = document.getElementById('formImportarTrabalhos');
    console.log('🔍 DEBUG: Formulário encontrado:', formImportarTrabalhos);
    
    if (formImportarTrabalhos) {
        console.log('🔍 DEBUG: Dataset do formulário:', formImportarTrabalhos.dataset);
        console.log('🔍 DEBUG: Context do formulário:', formImportarTrabalhos.dataset.context);
    }
    
    if (formImportarTrabalhos && formImportarTrabalhos.dataset.context === 'submission-control') {
        console.log('✅ DEBUG: Formulário correto encontrado, adicionando event listener');
        
        formImportarTrabalhos.addEventListener('submit', function(e) {
            console.log('🔍 DEBUG: Submit do formulário interceptado');
            e.preventDefault();
            
            try {
                const fileInput = document.getElementById('arquivo');
                const file = fileInput ? fileInput.files[0] : null;
                
                if (!file) {
                    showErrorMessage('Por favor, selecione um arquivo.');
                    return;
                }
                
                // Validar tamanho do arquivo (10MB)
                if (file.size > 10 * 1024 * 1024) {
                    showErrorMessage('Arquivo muito grande. Tamanho máximo: 10MB');
                    return;
                }
                
                // Validar extensão
                const allowedExtensions = ['.xlsx', '.xls'];
                const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
                if (!allowedExtensions.includes(fileExtension)) {
                    showErrorMessage('Formato de arquivo inválido. Use .xlsx ou .xls');
                    return;
                }
                
                const formData = new FormData(this);
                const eventoIdInput = document.getElementById('evento_id');
                console.log('🔍 DEBUG: eventoIdInput encontrado:', eventoIdInput);
                
                if (!eventoIdInput) {
                    console.error('❌ DEBUG: Elemento evento_id não encontrado!');
                    alert('Erro: ID do evento não encontrado na página.');
                    return;
                }
                
                const eventoId = eventoIdInput.value;
                console.log('🔍 DEBUG: eventoId:', eventoId);
                formData.append('evento_id', eventoId);
                
                const csrfToken = document.querySelector('[name=csrf_token]');
                console.log('🔍 DEBUG: CSRF token input encontrado:', csrfToken);
                
                console.log('🔍 DEBUG: Enviando requisição para:', this.action);
                
                // Mostrar loading
                const submitBtn = this.querySelector('button[type="submit"]');
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processando...';
                submitBtn.disabled = true;
                
                // Mostrar progresso de upload
                const progressInterval = showUploadProgress();
                
                // Primeira etapa: upload do arquivo
                fetch(this.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': csrfToken ? csrfToken.value : ''
                    }
                })
                .then(response => {
                    console.log('🔍 DEBUG: Resposta recebida:', response.status, response.statusText);
                    return response.json();
                })
                .then(data => {
                    console.log('🔍 DEBUG: Dados da resposta:', data);
                    
                    if (data.success) {
                    showSuccessMessage('Arquivo processado com sucesso!');
                    
                    if (data.temp_id && data.columns) {
                        console.log('✅ DEBUG: Dados para modal encontrados, chamando mostrarModalMapeamento');
                        console.log('🔍 DEBUG: temp_id:', data.temp_id);
                        console.log('🔍 DEBUG: columns:', data.columns);
                        // Mostrar modal de mapeamento de colunas
                        updateStepProgress(1);
                        mostrarModalMapeamento(data.temp_id, data.columns, data.preview, eventoIdInput.value);
                        showStep(2);
                    } else {
                        console.log('✅ DEBUG: Importação direta bem-sucedida');
                        // Importação direta (sem mapeamento)
                        updateStepProgress(3);
                        showSuccessMessage('Trabalhos importados com sucesso!');
                        setTimeout(() => location.reload(), 1500);
                    }
                } else {
                        console.error('❌ DEBUG: Erro na resposta:', data);
                        let errorMessage = 'Erro ao importar trabalhos: ';
                        if (data.errors && Array.isArray(data.errors)) {
                            errorMessage += data.errors.join(', ');
                        } else {
                            errorMessage += (data.error || 'Erro desconhecido');
                        }
                        showErrorMessage(errorMessage);
                    }
                })
                .catch(error => {
                    console.error('❌ DEBUG: Erro na requisição:', error);
                    showErrorMessage('Erro ao processar arquivo. Tente novamente.');
                })
                .finally(() => {
                    // Esconder progresso e restaurar botão
                    clearInterval(progressInterval);
                    hideUploadProgress();
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                });
            } catch (error) {
                console.error('❌ DEBUG: Erro no try-catch principal:', error);
                alert('Erro interno ao processar formulário.');
            }
        });
    } else {
        console.log('❌ DEBUG: Formulário não encontrado ou context incorreto');
    }
    
    // Controle de etapas
    function updateStepProgress(currentStep) {
        // Atualizar indicadores de progresso
        const steps = document.querySelectorAll('.step');
        steps.forEach((step, index) => {
            const stepNumber = index + 1;
            step.classList.remove('active', 'completed');
            
            if (stepNumber < currentStep) {
                step.classList.add('completed');
            } else if (stepNumber === currentStep) {
                step.classList.add('active');
            }
        });
        
        // Mostrar/ocultar seções
        const sections = {
            1: 'step-import',
            2: 'step-mapping', 
            3: 'step-view',
            4: 'step-assign'
        };
        
        Object.keys(sections).forEach(step => {
            const element = document.getElementById(sections[step]);
            if (element) {
                element.style.display = parseInt(step) <= currentStep ? 'block' : 'none';
            }
        });
    }
    
    // Funções de mensagem
    function showSuccessMessage(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-success alert-dismissible fade show';
        alert.innerHTML = `
            <i class="fas fa-check-circle me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Tentar encontrar um container adequado
        let container = document.querySelector('.container-fluid');
        if (!container) {
            container = document.querySelector('.container');
        }
        if (!container) {
            container = document.querySelector('main');
        }
        if (!container) {
            container = document.body;
        }
        
        if (container && container.firstChild) {
            container.insertBefore(alert, container.firstChild);
        } else if (container) {
            container.appendChild(alert);
        } else {
            console.error('❌ Erro: Não foi possível encontrar um container para exibir a mensagem de sucesso');
        }
    }
    
    function showErrorMessage(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show';
        alert.innerHTML = `
            <i class="fas fa-exclamation-circle me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Tentar encontrar um container adequado
        let container = document.querySelector('.container-fluid');
        if (!container) {
            container = document.querySelector('.container');
        }
        if (!container) {
            container = document.querySelector('main');
        }
        if (!container) {
            container = document.body;
        }
        
        if (container && container.firstChild) {
            container.insertBefore(alert, container.firstChild);
        } else if (container) {
            container.appendChild(alert);
        } else {
            console.error('❌ Erro: Não foi possível encontrar um container para exibir a mensagem de erro');
        }
    }
    
    function mostrarModalMapeamento(tempId, columns, preview, eventoId) {
        console.log('🔍 DEBUG: Iniciando mostrarModalMapeamento');
        console.log('🔍 DEBUG: tempId:', tempId);
        console.log('🔍 DEBUG: columns:', columns);
        console.log('🔍 DEBUG: eventoId:', eventoId);
        
        // Buscar evento_id
        const eventoIdInput = document.getElementById('evento_id');
        console.log('🔍 DEBUG: eventoIdInput encontrado:', eventoIdInput);
        
        if (!eventoIdInput) {
            console.error('❌ DEBUG: Elemento evento_id não encontrado na função mostrarModalMapeamento!');
            alert('Erro: ID do evento não encontrado na página.');
            return;
        }
        
        const eventoIdValue = eventoIdInput.value;
        console.log('🔍 DEBUG: eventoIdValue:', eventoIdValue);
        
        // Atualizar a seção de mapeamento na página
        const mappingSection = document.getElementById('step-mapping');
        const detectedColumns = document.getElementById('detected-columns');
        
        if (detectedColumns) {
            // Limpar e popular colunas detectadas
            detectedColumns.innerHTML = columns.map(col => 
                `<div class="list-group-item d-flex justify-content-between align-items-center">
                    <span>${col}</span>
                    <span class="badge bg-secondary">Detectada</span>
                </div>`
            ).join('');
        }
        
        try {
            // Criar o modal dinamicamente
            const modalHtml = `
                <div class="modal fade" id="mapearColunasModal" tabindex="-1">
                    <div class="modal-dialog modal-xl">
                        <div class="modal-content">
                            <div class="modal-header bg-info text-white">
                                <h5 class="modal-title">
                                    <i class="fas fa-columns me-2"></i>Mapear Colunas do Arquivo
                                </h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="alert alert-info">
                                    <i class="fas fa-info-circle me-2"></i>
                                    <strong>Instruções:</strong> Associe cada coluna do seu arquivo aos campos correspondentes do sistema. Apenas o campo "Título" é obrigatório.
                                </div>
                                
                                <div class="row">
                                    <div class="col-md-6">
                                        <h6><i class="fas fa-file-excel me-2"></i>Colunas detectadas no arquivo:</h6>
                                        <div class="list-group">
                                            ${columns.map(col => `
                                                <div class="list-group-item d-flex justify-content-between align-items-center">
                                                    <span>${col}</span>
                                                    <span class="badge bg-primary">Disponível</span>
                                                </div>
                                            `).join('')}
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <h6><i class="fas fa-cogs me-2"></i>Mapear para campos do sistema:</h6>
                                        <form id="formMapearColunas">
                                            <input type="hidden" name="temp_id" value="${tempId}">
                                            <div class="mb-3">
                                                <label class="form-label">
                                                    <i class="fas fa-asterisk text-danger" style="font-size: 8px;"></i>
                                                    <strong>Título:</strong>
                                                </label>
                                                <select class="form-select" name="titulo" required>
                                                    <option value="">Selecione uma coluna</option>
                                                    ${columns.map(col => `<option value="${col}">${col}</option>`).join('')}
                                                </select>
                                                <small class="form-text text-muted">Campo obrigatório</small>
                                            </div>
                                            <div class="mb-3">
                                                <label class="form-label"><strong>Categoria:</strong></label>
                                                <select class="form-select" name="categoria">
                                                    <option value="">Selecione uma coluna (opcional)</option>
                                                    ${columns.map(col => `<option value="${col}">${col}</option>`).join('')}
                                                </select>
                                            </div>
                                            <div class="mb-3">
                                                <label class="form-label"><strong>Rede de Ensino:</strong></label>
                                                <select class="form-select" name="rede_ensino">
                                                    <option value="">Selecione uma coluna (opcional)</option>
                                                    ${columns.map(col => `<option value="${col}">${col}</option>`).join('')}
                                                </select>
                                            </div>
                                            <div class="mb-3">
                                                <label class="form-label"><strong>Etapa de Ensino:</strong></label>
                                                <select class="form-select" name="etapa_ensino">
                                                    <option value="">Selecione uma coluna (opcional)</option>
                                                    ${columns.map(col => `<option value="${col}">${col}</option>`).join('')}
                                                </select>
                                            </div>
                                            <div class="mb-3">
                                                <label class="form-label"><strong>PDF URL:</strong></label>
                                                <select class="form-select" name="pdf_url">
                                                    <option value="">Selecione uma coluna (opcional)</option>
                                                    ${columns.map(col => `<option value="${col}">${col}</option>`).join('')}
                                                </select>
                                            </div>
                                        </form>
                                    </div>
                                </div>
                                ${preview ? `
                                    <div class="mt-4">
                                        <h6><i class="fas fa-eye me-2"></i>Prévia dos dados (primeiras 3 linhas):</h6>
                                        <div class="table-responsive">
                                            <table class="table table-sm table-bordered table-hover">
                                                <thead class="table-light">
                                                    <tr>
                                                        ${columns.map(col => `<th>${col}</th>`).join('')}
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    ${preview.slice(0, 3).map(row => 
                                                        `<tr>${columns.map(col => `<td>${row[col] || '<em class="text-muted">vazio</em>'}</td>`).join('')}</tr>`
                                                    ).join('')}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                ` : ''}
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                    <i class="fas fa-times me-2"></i>Cancelar
                                </button>
                                <button type="button" class="btn btn-success" onclick="confirmarMapeamento()">
                    <i class="fas fa-check me-2"></i>Confirmar Mapeamento
                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Remover modal existente se houver
            const existingModal = document.getElementById('mapearColunasModal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // Adicionar o modal ao DOM
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            // Mostrar o modal
            const modal = new bootstrap.Modal(document.getElementById('mapearColunasModal'));
            modal.show();
            
            // Armazenar dados para uso posterior
            window.mappingData = { tempId, columns, preview };
            
        } catch (error) {
            console.error('❌ DEBUG: Erro em mostrarModalMapeamento:', error);
            console.error('❌ DEBUG: Stack trace:', error.stack);
        }
    }
    
    // Função para baixar template
    function downloadTemplate() {
        const link = document.createElement('a');
        link.href = '/static/templates/template_trabalhos.xlsx';
        link.download = 'template_trabalhos.xlsx';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    // Função para mostrar progresso de upload
    function showUploadProgress() {
        const progressDiv = document.getElementById('uploadProgress');
        const progressBar = progressDiv.querySelector('.progress-bar');
        
        progressDiv.style.display = 'block';
        
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 30;
            if (progress > 90) progress = 90;
            
            progressBar.style.width = progress + '%';
            
            if (progress >= 90) {
                clearInterval(interval);
            }
        }, 200);
        
        return interval;
    }
    
    // Função para esconder progresso de upload
    function hideUploadProgress() {
        const progressDiv = document.getElementById('uploadProgress');
        const progressBar = progressDiv.querySelector('.progress-bar');
        
        progressBar.style.width = '100%';
        setTimeout(() => {
            progressDiv.style.display = 'none';
            progressBar.style.width = '0%';
        }, 500);
    }
    
    function confirmarMapeamento() {
        console.log('🔍 DEBUG: Iniciando confirmação de mapeamento');
        
        try {
            const form = document.getElementById('formMapearColunas');
            console.log('🔍 DEBUG: Formulário de mapeamento encontrado:', form);
            
            if (!form) {
                console.error('❌ DEBUG: Formulário de mapeamento não encontrado');
                return;
            }
            
            // Obter dados armazenados
            const mappingData = window.mappingData;
            if (!mappingData || !mappingData.tempId) {
                console.error('❌ DEBUG: Dados de mapeamento não encontrados');
                showAlert('Erro: dados de mapeamento não encontrados.', 'error');
                return;
            }
            
            const formData = new FormData(form);
            
            // Validar campo obrigatório
            const titulo = formData.get('titulo');
            if (!titulo) {
                showAlert('O campo "Título" é obrigatório.', 'warning');
                return;
            }
            
            formData.append('temp_id', mappingData.tempId);
            
            // Obter evento_id do contexto da página
            const eventoIdInput = document.getElementById('evento_id');
        const eventoId = eventoIdInput ? eventoIdInput.value : '1';
        formData.append('evento_id', eventoId);
            
            // Log dos dados do formulário
            console.log('🔍 DEBUG: Dados do formulário de mapeamento:');
            for (let [key, value] of formData.entries()) {
                console.log(`  ${key}: ${value}`);
            }
            
            const csrfToken = document.querySelector('[name=csrf_token]');
            console.log('🔍 DEBUG: CSRF token para confirmação:', csrfToken);
            
            // Mostrar loading no botão
            const confirmBtn = document.querySelector('#mapearColunasModal .btn-success');
            const originalText = confirmBtn.innerHTML;
            confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processando...';
            confirmBtn.disabled = true;
            
            console.log('🔍 DEBUG: Enviando dados para confirmação...');
            showAlert('Processando mapeamento...', 'info');
            
            // Segunda etapa: confirmar mapeamento e importar
            fetch('/importar_trabalhos', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken ? csrfToken.value : ''
                }
            })
            .then(response => {
                console.log('🔍 DEBUG: Resposta da confirmação:', response.status, response.statusText);
                
                // Verificar se a resposta é JSON válida
                const contentType = response.headers.get('content-type');
                console.log('🔍 DEBUG: Content-Type da resposta:', contentType);
                
                if (!response.ok) {
                    console.error('❌ DEBUG: Resposta não OK:', response.status, response.statusText);
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                if (!contentType || !contentType.includes('application/json')) {
                    // Se não for JSON, capturar o texto da resposta para debug
                    return response.text().then(text => {
                        console.error('❌ DEBUG: Resposta não é JSON. Conteúdo:', text.substring(0, 500));
                        throw new Error('Servidor retornou HTML em vez de JSON. Verifique se há erro no servidor.');
                    });
                }
                
                return response.json();
            })
            .then(data => {
                console.log('🔍 DEBUG: Dados da confirmação:', data);
                
                if (data.success) {
                    console.log('✅ DEBUG: Confirmação bem-sucedida');
                    showAlert('Trabalhos importados com sucesso!', 'success');
                    updateStepProgress(2); // Avançar para etapa de visualização
                    
                    // Fechar modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('mapearColunasModal'));
                    if (modal) {
                        modal.hide();
                    }
                    
                    // Limpar dados temporários
                    window.mappingData = null;
                    
                    // Mostrar seção de visualização
                    showStep(3);
                    
                    // Recarregar página após um delay
                    setTimeout(() => location.reload(), 1500);
                } else {
                    console.error('❌ DEBUG: Erro na confirmação:', data);
                    const errorMessage = data.message || 'Erro ao confirmar mapeamento.';
                    showAlert(errorMessage, 'error');
                }
            })
            .catch(error => {
                console.error('❌ DEBUG: Erro na requisição de confirmação:', error);
                showAlert('Erro ao processar solicitação. Tente novamente.', 'error');
            })
            .finally(() => {
                // Restaurar botão
                confirmBtn.innerHTML = originalText;
                confirmBtn.disabled = false;
            });
            
        } catch (error) {
            console.error('❌ DEBUG: Erro em confirmarMapeamento:', error);
            console.error('❌ DEBUG: Stack trace:', error.stack);
        }
    }
    
    // Funções para controle de mapeamento
    function cancelMapping() {
        updateStepProgress(1);
        const modal = bootstrap.Modal.getInstance(document.getElementById('mapearColunasModal'));
        if (modal) {
            modal.hide();
        }
        
        // Limpar dados temporários
        if (window.mappingData) {
            window.mappingData = null;
        }
    }
    
    // Função para mostrar alertas
    function showAlert(message, type = 'info') {
        const alertContainer = document.getElementById('alert-container');
        if (!alertContainer) return;
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        alertContainer.appendChild(alertDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
    
    // Função para atualizar o progresso das etapas
    function updateStepProgress(currentStep) {
        for (let i = 1; i <= 4; i++) {
            const stepElement = document.getElementById(`step-${i}`);
            if (!stepElement) {
                console.warn(`Elemento step-${i} não encontrado`);
                continue;
            }
            
            const stepNumber = stepElement.querySelector('.step-number');
            if (!stepNumber) {
                console.warn(`Elemento .step-number não encontrado em step-${i}`);
                continue;
            }
            
            if (i <= currentStep) {
                stepElement.classList.add('completed');
                stepElement.classList.remove('active');
                stepNumber.innerHTML = '<i class="fas fa-check"></i>';
            } else if (i === currentStep + 1) {
                stepElement.classList.add('active');
                stepElement.classList.remove('completed');
                stepNumber.textContent = i;
            } else {
                stepElement.classList.remove('active', 'completed');
                stepNumber.textContent = i;
            }
        }
    }
    
    // Função para download do template
    function downloadTemplate() {
        const link = document.createElement('a');
        link.href = '/static/templates/template_trabalhos.xlsx';
        link.download = 'template_trabalhos.xlsx';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    // Função para mostrar step específico
    function showStep(stepNumber) {
        // Esconder todas as seções de conteúdo
        const sections = ['step-import', 'step-mapping', 'step-view', 'step-assign'];
        sections.forEach(sectionId => {
            const section = document.getElementById(sectionId);
            if (section) {
                section.style.display = 'none';
            }
        });
        
        // Mostrar seção específica
        const stepMap = {
            1: 'step-import',
            2: 'step-mapping', 
            3: 'step-view',
            4: 'step-assign'
        };
        
        const targetStep = document.getElementById(stepMap[stepNumber]);
        if (targetStep) {
            targetStep.style.display = 'block';
        }
    }
    
    function confirmMapping() {
        confirmarMapeamento();
    }
    
    // Inicializar página
    const hasWorks = document.querySelectorAll('#step-view tbody tr').length > 0;
    if (hasWorks) {
        updateStepProgress(2); // Marcar etapas 1 e 2 como completas
        showStep(3); // Mostrar etapa 3 (visualização)
    } else {
        updateStepProgress(0); // Marcar apenas etapa 1 como ativa
        showStep(1); // Mostrar etapa 1 (importação)
    }
    
    // Função para mostrar a seção de mapeamento
    function showMappingSection(columns, preview) {
        console.log('🔍 DEBUG: Mostrando seção de mapeamento');
        console.log('Colunas:', columns);
        console.log('Preview:', preview);
        
        // Esconder seção de importação
        document.getElementById('step-import').style.display = 'none';
        
        // Mostrar seção de mapeamento
        const mappingSection = document.getElementById('step-mapping');
        mappingSection.style.display = 'block';
        
        // Gerar formulário de mapeamento
        const mappingContainer = document.getElementById('mappingFormContainer');
        if (!mappingContainer) {
            console.error('❌ Elemento mappingFormContainer não encontrado');
            return;
        }
        
        const systemFields = [
            { key: 'titulo', label: 'Título', required: true, icon: 'fas fa-heading' },
            { key: 'categoria', label: 'Categoria', required: false, icon: 'fas fa-tag' },
            { key: 'rede_ensino', label: 'Rede de Ensino', required: false, icon: 'fas fa-school' },
            { key: 'etapa_ensino', label: 'Etapa de Ensino', required: false, icon: 'fas fa-graduation-cap' },
            { key: 'pdf_url', label: 'URL do PDF', required: false, icon: 'fas fa-file-pdf' }
        ];
        
        let formHtml = `
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="fas fa-columns me-2"></i>Mapeamento de Colunas
                    </h5>
                    <small class="text-muted">Configure como as colunas do Excel correspondem aos campos do sistema</small>
                </div>
                <div class="card-body">
                    <div class="row">
        `;
        
        systemFields.forEach(field => {
            formHtml += `
                <div class="col-md-6 mb-3">
                    <label class="form-label fw-bold">
                        <i class="${field.icon} me-2"></i>${field.label}
                        ${field.required ? '<span class="text-danger">*</span>' : ''}
                    </label>
                    <select class="form-select" name="${field.key}" ${field.required ? 'required' : ''}>
                        <option value="">Selecione uma coluna...</option>
            `;
            
            columns.forEach(column => {
                const selected = column.toLowerCase().includes(field.key.toLowerCase()) || 
                               (field.key === 'titulo' && column.toLowerCase().includes('title')) ||
                               (field.key === 'categoria' && column.toLowerCase().includes('category')) ? 'selected' : '';
                formHtml += `<option value="${column}" ${selected}>${column}</option>`;
            });
            
            formHtml += `
                    </select>
                </div>
            `;
        });
        
        formHtml += '</div>';
        
        // Adicionar preview dos dados
        if (preview && preview.length > 0) {
            formHtml += `
                <div class="mt-4">
                    <h6><i class="fas fa-eye me-2"></i>Preview dos Dados (primeiras 3 linhas):</h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-bordered table-hover">
                            <thead class="table-dark">
                                <tr>
            `;
            
            columns.forEach(column => {
                formHtml += `<th class="text-nowrap">${column}</th>`;
            });
            
            formHtml += `
                                </tr>
                            </thead>
                            <tbody>
            `;
            
            preview.slice(0, 3).forEach((row, index) => {
                formHtml += `<tr class="${index % 2 === 0 ? 'table-light' : ''}">`;
                columns.forEach(column => {
                    const value = row[column] || '';
                    const displayValue = value.toString().length > 50 ? 
                        value.toString().substring(0, 50) + '...' : value;
                    formHtml += `<td class="text-nowrap" title="${value}">${displayValue}</td>`;
                });
                formHtml += '</tr>';
            });
            
            formHtml += `
                            </tbody>
                        </table>
                    </div>
                    <small class="text-muted">
                        <i class="fas fa-info-circle me-1"></i>
                        Total de ${preview.length} registros encontrados no arquivo
                    </small>
                </div>
            `;
        }
        
        formHtml += `
                </div>
            </div>
        `;
        
        mappingContainer.innerHTML = formHtml;
    }
    
    // Função para descartar todos os trabalhos
    function descartarTodosTrabalhos() {
        console.log('=== INÍCIO descartarTodosTrabalhos ===');
        
        const confirmCheckbox = document.getElementById('confirmarExclusao');
        const btnConfirmar = document.getElementById('btnConfirmarDescarte');
        
        console.log('Elementos encontrados:');
        console.log('- confirmCheckbox:', confirmCheckbox);
        console.log('- btnConfirmar:', btnConfirmar);
        console.log('- checkbox checked:', confirmCheckbox ? confirmCheckbox.checked : 'N/A');
        
        if (!confirmCheckbox.checked) {
            console.log('ERRO: Checkbox não marcado');
            showErrorMessage('Por favor, confirme que deseja descartar todos os trabalhos.');
            return;
        }
        
        console.log('Checkbox confirmado, iniciando requisição...');
        
        // Desabilitar botão e mostrar loading
        btnConfirmar.disabled = true;
        btnConfirmar.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Descartando...';
        
        const csrfToken = getCsrfToken();
        console.log('CSRF Token:', csrfToken);
        
        console.log('Enviando requisição para descartar todos os trabalhos...');
        
        const requestOptions = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `csrf_token=${encodeURIComponent(csrfToken)}`
        };
        console.log('DEBUG: Opções da requisição:', requestOptions);
        console.log('Fazendo fetch para: /submissoes/descartar_todos');
        
        fetch('/submissoes/descartar_todos', requestOptions)
        .then(response => {
            console.log('Resposta recebida:');
            console.log('- Status:', response.status);
            console.log('- StatusText:', response.statusText);
            console.log('- Headers:', response.headers);
            console.log('- OK:', response.ok);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return response.json();
        })
        .then(data => {
            console.log('Dados JSON recebidos:', data);
            
            if (data.success) {
                console.log('Sucesso! Fechando modal e recarregando página...');
                
                // Fechar modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('modalConfirmarDescarte'));
                if (modal) {
                    modal.hide();
                } else {
                    console.warn('Modal instance não encontrada');
                }
                
                // Mostrar mensagem de sucesso
                showSuccessMessage(data.message || 'Todos os trabalhos foram descartados com sucesso!');
                
                // Atualizar interface
                setTimeout(() => {
                    console.log('Recarregando página...');
                    location.reload();
                }, 1500);
            } else {
                console.log('ERRO na resposta:', data.message);
                showErrorMessage(data.message || 'Erro ao descartar trabalhos.');
            }
        })
        .catch(error => {
            console.error('ERRO na requisição:', error);
            console.error('Stack trace:', error.stack);
            showErrorMessage('Erro interno do servidor. Tente novamente.');
        })
        .finally(() => {
            console.log('Finalizando - restaurando botão...');
            // Restaurar botão
            btnConfirmar.disabled = false;
            btnConfirmar.innerHTML = '<i class="fas fa-trash me-2"></i>Sim, Descartar Todos';
            console.log('=== FIM descartarTodosTrabalhos ===');
        });
    }
    
    // Função para controlar o checkbox de confirmação
    function toggleConfirmButton() {
        const confirmCheckbox = document.getElementById('confirmarExclusao');
        const btnConfirmar = document.getElementById('btnConfirmarDescarte');
        
        console.log('toggleConfirmButton chamada');
        console.log('Checkbox:', confirmCheckbox, 'Checked:', confirmCheckbox ? confirmCheckbox.checked : 'N/A');
        console.log('Botão:', btnConfirmar);
        
        if (confirmCheckbox && btnConfirmar) {
            btnConfirmar.disabled = !confirmCheckbox.checked;
            console.log('Botão disabled:', btnConfirmar.disabled);
            
            // Adicionar/remover classes visuais para feedback
            if (confirmCheckbox.checked) {
                btnConfirmar.classList.remove('disabled');
                btnConfirmar.classList.add('btn-danger');
            } else {
                btnConfirmar.classList.add('disabled');
            }
        } else {
            console.error('Elementos não encontrados em toggleConfirmButton');
        }
    }
    
    // Função para obter CSRF token
    function getCsrfToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        const tokenValue = token ? token.getAttribute('content') : '';
        console.log('CSRF Token obtido:', tokenValue ? 'Token encontrado' : 'Token NÃO encontrado');
        console.log('Meta tag csrf-token:', token);
        return tokenValue;
    }
    
    // Função para inicializar event listeners do modal
    function initModalEventListeners() {
        const confirmCheckbox = document.getElementById('confirmarExclusao');
        const btnConfirmar = document.getElementById('btnConfirmarDescarte');
        
        console.log('Inicializando listeners do modal...');
        console.log('Checkbox encontrado:', confirmCheckbox);
        console.log('Botão encontrado:', btnConfirmar);
        
        if (confirmCheckbox && btnConfirmar) {
            // Verificar se os listeners já foram anexados
            if (confirmCheckbox.hasAttribute('data-listeners-attached')) {
                console.log('Listeners já anexados, pulando inicialização');
                toggleConfirmButton(); // Apenas atualizar o estado
                return;
            }
            
            // Limpar listeners existentes usando cloneNode para garantir remoção completa
            const newCheckbox = confirmCheckbox.cloneNode(true);
            const newButton = btnConfirmar.cloneNode(true);
            
            confirmCheckbox.parentNode.replaceChild(newCheckbox, confirmCheckbox);
            btnConfirmar.parentNode.replaceChild(newButton, btnConfirmar);
            
            // Referenciar os novos elementos
            const freshCheckbox = document.getElementById('confirmarExclusao');
            const freshButton = document.getElementById('btnConfirmarDescarte');
            
            // Adicionar listeners aos elementos limpos
            freshCheckbox.addEventListener('change', function() {
                console.log('Checkbox change event triggered');
                toggleConfirmButton();
            });
            
            freshCheckbox.addEventListener('click', function() {
                console.log('Checkbox click event triggered');
                // Pequeno delay para garantir que o estado seja atualizado
                setTimeout(toggleConfirmButton, 10);
            });
            
            freshButton.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Button click event triggered');
                descartarTodosTrabalhos();
            });
            
            // Marcar que os listeners foram anexados
            freshCheckbox.setAttribute('data-listeners-attached', 'true');
            freshButton.setAttribute('data-listeners-attached', 'true');
            
            console.log('Listeners adicionados com sucesso aos elementos limpos');
            
            // Inicializar estado do botão
            toggleConfirmButton();
        } else {
            console.error('Elementos não encontrados no DOM');
        }
    }
    
    // Função para garantir inicialização segura
    function safeInitialization() {
        // Aguardar um pouco para garantir que o DOM esteja completamente carregado
        setTimeout(function() {
            console.log('Inicialização segura executada');
            initModalEventListeners();
        }, 100);
    }
    
    // Event listeners para o modal de descarte
    document.addEventListener('DOMContentLoaded', function() {
        console.log('DOM carregado, inicializando listeners...');
        safeInitialization();
        
        // Inicializar listeners quando o modal for mostrado
        const modal = document.getElementById('modalConfirmarDescarte');
        if (modal) {
            modal.addEventListener('shown.bs.modal', function() {
                console.log('Modal mostrado, reinicializando listeners...');
                safeInitialization();
            });
            
            // Adicionar listener para quando o modal for aberto
            modal.addEventListener('show.bs.modal', function() {
                console.log('Modal sendo aberto, preparando listeners...');
                // Reset do checkbox quando o modal abre
                const checkbox = document.getElementById('confirmarExclusao');
                if (checkbox) {
                    checkbox.checked = false;
                }
                safeInitialization();
            });
            
            modal.addEventListener('hidden.bs.modal', function() {
                const confirmCheckbox = document.getElementById('confirmarExclusao');
                const btnConfirmar = document.getElementById('btnConfirmarDescarte');
                
                if (confirmCheckbox) confirmCheckbox.checked = false;
                if (btnConfirmar) {
                    btnConfirmar.disabled = true;
                    btnConfirmar.innerHTML = '<i class="fas fa-trash me-2"></i>Sim, Descartar Todos';
                }
            });
        }
        
        // Adicionar listener direto no botão de descarte
        const btnDescartarTodos = document.getElementById('btnDescartarTodos');
        if (btnDescartarTodos) {
            btnDescartarTodos.addEventListener('click', function() {
                // Aguardar um pouco para o modal carregar completamente
                setTimeout(function() {
                    safeInitialization();
                }, 100);
            });
        }
    });
    
    // Fallback: tentar inicializar após um delay se ainda não foi feito
    setTimeout(function() {
        const checkbox = document.getElementById('confirmarExclusao');
        const button = document.getElementById('btnConfirmarDescarte');
        
        if (checkbox && button && !checkbox.hasAttribute('data-listeners-attached')) {
            console.log('Fallback: inicializando listeners após delay');
            safeInitialization();
        }
    }, 1000);
    
    // Função para avançar da etapa 3 para etapa 4
    function avancarParaEtapa4() {
        console.log('🚀 FUNÇÃO avancarParaEtapa4() CHAMADA!');
        console.log('📍 Timestamp:', new Date().toISOString());
        console.log('🔍 Verificando elementos do DOM...');
        
        // Verificar se há trabalhos importados
        const tabelaTrabalhos = document.querySelector('#step-view tbody');
        console.log('📊 Tabela de trabalhos encontrada:', tabelaTrabalhos);
        console.log('📊 Número de trabalhos:', tabelaTrabalhos ? tabelaTrabalhos.children.length : 0);
        
        if (!tabelaTrabalhos || tabelaTrabalhos.children.length === 0) {
            console.log('❌ Nenhum trabalho importado encontrado');
            showErrorMessage('Não há trabalhos importados para atribuir revisores. Importe trabalhos primeiro.');
            return;
        }
        
        console.log('✅ Trabalhos encontrados, prosseguindo...');
        
        // Atualizar progresso para etapa 4
        console.log('🔄 Chamando updateStepProgress(4)...');
        updateStepProgress(4);
        console.log('✅ updateStepProgress(4) executado');
        
        // Mostrar a etapa 4
        console.log('🔄 Chamando showStep(4)...');
        showStep(4);
        console.log('✅ showStep(4) executado');
        
        // Scroll suave para a seção de atribuição
        const stepAssign = document.getElementById('step-assign');
        console.log('🎯 Elemento step-assign encontrado:', stepAssign);
        
        if (stepAssign) {
            console.log('📜 Executando scroll para step-assign...');
            stepAssign.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'start' 
            });
            console.log('✅ Scroll executado');
        } else {
            console.log('❌ Elemento step-assign não encontrado!');
        }
        
        // Mostrar mensagem de sucesso
        console.log('💬 Mostrando mensagem de sucesso...');
        showSuccessMessage('Avançado para Etapa 4: Atribuição de Revisores');
        
        console.log('🎉 Navegação para Etapa 4 concluída com sucesso!');
    }
    
    // Tornar funções globais
    window.updateStepProgress = updateStepProgress;
    window.showSuccessMessage = showSuccessMessage;
    window.showErrorMessage = showErrorMessage;
    window.confirmarMapeamento = confirmarMapeamento;
    window.cancelMapping = cancelMapping;
    window.confirmMapping = confirmMapping;
    window.showMappingSection = showMappingSection;
    window.descartarTodosTrabalhos = descartarTodosTrabalhos;
    window.toggleConfirmButton = toggleConfirmButton;
    window.initModalEventListeners = initModalEventListeners;
    window.downloadTemplate = downloadTemplate;
    window.showStep = showStep;
    window.avancarParaEtapa4 = avancarParaEtapa4;
    
    // Log para verificar se a função foi registrada globalmente
    console.log('🌍 Função avancarParaEtapa4 registrada globalmente:', typeof window.avancarParaEtapa4);
    console.log('🌍 Todas as funções globais registradas:', Object.keys(window).filter(key => key.includes('avancar')));
    
    // Adicionar event listener adicional ao botão como backup
    const btnAvancarEtapa4 = document.getElementById('btnAvancarEtapa4');
    if (btnAvancarEtapa4) {
        console.log('🎯 Botão btnAvancarEtapa4 encontrado, adicionando event listener...');
        btnAvancarEtapa4.addEventListener('click', function(e) {
            console.log('🖱️ Event listener do botão acionado!');
            e.preventDefault();
            avancarParaEtapa4();
        });
        console.log('✅ Event listener adicionado ao botão');
    } else {
        console.log('❌ Botão btnAvancarEtapa4 não encontrado no DOM');
    }
});
