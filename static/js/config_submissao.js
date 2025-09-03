
/* global atualizarBotao */
document.addEventListener('DOMContentLoaded', function() {
    console.log('config_submissao.js carregado');
  
    // Definir csrfToken a partir da meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    console.log('csrfToken:', csrfToken ? 'definido' : 'indefinido');
    console.log('csrfToken value:', csrfToken);
    
    // Verificar se estamos na página correta
    const form = document.querySelector('form[data-context="config-submissao"]');
    console.log('Formulário encontrado:', form);
    
    if (!form) {
        console.log('Formulário não encontrado - saindo');
        return; // Não estamos na página de configuração de submissão
    }
    
    // Verificar se csrfToken está disponível
    console.log('Verificando csrfToken:', typeof csrfToken, csrfToken);
    if (typeof csrfToken === 'undefined') {
        console.error('csrfToken não está definido');
        return;
    }

    function attachOnce(el, event, handler) {
        if (!el) return;
        const key = `listener_${event}`;
        if (el.dataset[key]) return;
        el.dataset[key] = 'true';
        el.addEventListener(event, handler);
    }

    document.querySelectorAll('.btn-toggle').forEach((btn) => {
        attachOnce(btn, 'click', async () => {
            const url = btn.dataset.toggleUrl;
            if (!url) return;
            try {
                const resp = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                    },
                    credentials: 'include',
                });
                if (resp.ok) {
                    const data = await resp.json();
                    if (data.success) {
                        btn.textContent = data.enabled ? 'Ativado' : 'Desativado';
                        btn.className = data.enabled
                            ? 'btn btn-success btn-toggle'
                            : 'btn btn-secondary btn-toggle';
                    }
                }
            } catch (error) {
                console.error('Erro ao alternar configuração:', error);
            }
        });
    });

    // Funcionalidade de Importação de Trabalhos
    const importModal = document.getElementById('importarTrabalhosModal');
    if (importModal) {
        const uploadForm = document.getElementById('uploadForm');
        const mappingForm = document.getElementById('mappingForm');
        const step1 = document.getElementById('importStep1');
        const step2 = document.getElementById('importStep2');
        const step3 = document.getElementById('importStep3');
        const voltarBtn = document.getElementById('voltarStep1');
        
        let uploadedData = null;
        
        // Reset modal ao abrir
        importModal.addEventListener('show.bs.modal', function() {
            showStep(1);
            uploadForm.reset();
            uploadedData = null;
        });
        
        // Upload do arquivo
        uploadForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(uploadForm);
            
            try {
                const response = await fetch('/importar_trabalhos', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': csrfToken
                    }
                });
                
                const result = await response.json();
                
                if (result.success) {
                    uploadedData = result;
                    populateColumnSelects(result.columns, result.suggested_mappings);
                    populatePreview(result.columns, result.data);
                    document.getElementById('totalRows').textContent = result.total_rows;
                    document.getElementById('tempId').value = result.temp_id;
                    document.getElementById('eventoIdHidden').value = document.getElementById('eventoSelect').value;
                    showStep(2);
                } else {
                    alert('Erro ao fazer upload: ' + result.message);
                }
            } catch (error) {
                console.error('Erro:', error);
                alert('Erro ao fazer upload do arquivo.');
            }
        });
        
        // Mapeamento e importação final
        mappingForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            showStep(3);
            
            const formData = new FormData(mappingForm);
            
            try {
                const response = await fetch('/importar_trabalhos', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': csrfToken
                    }
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Adicionar feedback visual durante upload
                    const uploadProgress = document.createElement('div');
                    uploadProgress.className = 'progress mb-3';
                    uploadProgress.innerHTML = `
                      <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%"></div>
                    `;
                    
                    // Atualizar evento de submit do uploadForm
                    uploadForm.addEventListener('submit', async function(e) {
                        e.preventDefault();
                        
                        // Exibir loader e desativar botão
                        this.insertAdjacentElement('beforebegin', uploadProgress);
                        const submitBtn = this.querySelector('button[type="submit"]');
                        submitBtn.disabled = true;
                        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status"></span> Processando...`;
                    
                        const formData = new FormData(uploadForm);
                        
                        try {
                            const response = await fetch('/importar_trabalhos', {
                                method: 'POST',
                                body: formData,
                                headers: {
                                    'X-CSRFToken': csrfToken
                                }
                            });
                            
                            const result = await response.json();
                            
                            if (result.success) {
                                // Atualizar progresso para 100%
                                uploadProgress.querySelector('.progress-bar').style.width = '100%';
                                
                                // Transição automática após 1s
                                setTimeout(() => {
                                    showStep(2);
                                    uploadProgress.remove();
                                    submitBtn.disabled = false;
                                    submitBtn.textContent = 'Próxima Etapa →';
                                }, 1000);
                            } else {
                                // Feedback de erro no modal
                                const errorAlert = `<div class="alert alert-danger mt-3">${result.message}</div>`;
                                this.insertAdjacentHTML('afterend', errorAlert);
                                setTimeout(() => document.querySelector('.alert').remove(), 5000);
                            }
                            
                            // Restaurar botão em caso de erro
                            submitBtn.disabled = false;
                            submitBtn.textContent = 'Enviar Arquivo';
                    });
                    
                    // Adicionar navegação automática na conclusão
                    const successAlert = `<div class="alert alert-success">✅ Arquivo processado com sucesso! Redirecionando...</div>`;
                    
                    // Modificar o handler de sucesso final
                    if (result.success) {
                        document.getElementById('importStep3').insertAdjacentHTML('afterbegin', successAlert);
                        setTimeout(() => {
                            window.location.href = '/distribuicao_trabalhos?temp_id=' + result.temp_id;
                        }, 2000);
                    }
                    
                } else {
                    alert('Erro na importação: ' + result.message);
                    showStep(2);
                }
            } catch (error) {
                console.error('Erro:', error);
                alert('Erro durante a importação.');
                showStep(2);
            }
        });
        
        // Botão voltar
        voltarBtn.addEventListener('click', function() {
            showStep(1);
        });
        
        function showStep(stepNumber) {
            step1.style.display = stepNumber === 1 ? 'block' : 'none';
            step2.style.display = stepNumber === 2 ? 'block' : 'none';
            step3.style.display = stepNumber === 3 ? 'block' : 'none';
        }
        
        function populateColumnSelects(columns, suggestedMappings) {
            const selects = {
                'tituloSelect': 'titulo',
                'categoriaSelect': 'categoria',
                'autorNomeSelect': 'autor_nome',
                'autorEmailSelect': 'autor_email',
                'redeEnsinoSelect': 'rede_ensino',
                'etapaEnsinoSelect': 'etapa_ensino'
            };
            
            Object.keys(selects).forEach(selectId => {
                const select = document.getElementById(selectId);
                const mappingKey = selects[selectId];
                
                // Limpar opções existentes (exceto a primeira)
                while (select.children.length > 1) {
                    select.removeChild(select.lastChild);
                }
                
                // Adicionar colunas
                columns.forEach(column => {
                    const option = document.createElement('option');
                    option.value = column;
                    option.textContent = column;
                    select.appendChild(option);
                });
                
                // Aplicar sugestão automática se disponível
                if (suggestedMappings && suggestedMappings[mappingKey] && suggestedMappings[mappingKey].length > 0) {
                    select.value = suggestedMappings[mappingKey][0];
                }
            });
        }
        
        function populatePreview(columns, data) {
            const header = document.getElementById('previewHeader');
            const body = document.getElementById('previewBody');
            
            // Limpar conteúdo anterior
            header.innerHTML = '';
            body.innerHTML = '';
            
            // Criar cabeçalho
            columns.forEach(column => {
                const th = document.createElement('th');
                th.textContent = column;
                header.appendChild(th);
            });
            
            // Criar linhas de dados (máximo 5 para preview)
            data.slice(0, 5).forEach(row => {
                const tr = document.createElement('tr');
                columns.forEach(column => {
                    const td = document.createElement('td');
                    td.textContent = row[column] || '';
                    tr.appendChild(td);
                });
                body.appendChild(tr);
            });
        }
    }
});
