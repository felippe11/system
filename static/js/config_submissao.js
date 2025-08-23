
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
            atualizarBotao(btn, data.value);
          } else {
            alert(data.message || 'Erro ao atualizar');
          }
        } else {
          const data = await resp.json().catch(() => null);
          alert(data?.message || 'Erro ao processar solicitação');
        }
      } catch (err) {
        console.error('Erro de rede', err);
      }
    });
  });

    const formImportarTrabalhos = document.getElementById('formImportarTrabalhos');
    const modalContainer = document.getElementById('mapearColunasModal');
    const template = document.getElementById('mapearColunasTemplate');

    console.log('Elementos encontrados:');
    console.log('Formulário de importação encontrado:', formImportarTrabalhos);
    console.log('modalContainer:', modalContainer ? 'encontrado' : 'não encontrado');
    console.log('template:', template ? 'encontrado' : 'não encontrado');
    console.log('form.dataset.context:', formImportarTrabalhos ? formImportarTrabalhos.dataset.context : 'form não existe');

    // Só anexa o handler se o formulário existe, tem o modal de mapeamento e está no contexto correto
    // Isso evita conflito com submission_import.js
    if (formImportarTrabalhos && modalContainer && template && formImportarTrabalhos.dataset.context === 'config-submissao') {
        console.log('Anexando handler de submit ao formulário');
        formImportarTrabalhos.addEventListener('submit', async function(e) {
            console.log('Evento de submit capturado');
            e.preventDefault();
            
            const fileInput = this.querySelector('input[type="file"]');
            console.log('Input de arquivo:', fileInput);
            const file = fileInput.files[0];
            console.log('Arquivo selecionado:', file);
            
            if (!file) {
                console.log('Nenhum arquivo selecionado');
                alert('Por favor, selecione um arquivo.');
                return;
            }
            
            const formData = new FormData();
            formData.append('arquivo', file);
            console.log('FormData criado:', formData);
            console.log('URL de ação:', this.action);
            try {
                console.log('Enviando requisição para:', this.action);
                console.log('FormData contém:', Array.from(formData.entries()));
                console.log('CSRF Token:', csrfToken);
                
                const resp = await fetch(this.action, {
                    method: 'POST',
                    body: formData,
                    headers: { 'X-CSRFToken': csrfToken },
                });
                
                console.log('=== RESPOSTA DETALHADA ===');
                console.log('Status:', resp.status);
                console.log('Status Text:', resp.statusText);
                console.log('Headers:', Object.fromEntries(resp.headers.entries()));
                console.log('URL:', resp.url);
                console.log('OK:', resp.ok);
                
                if (!resp.ok) {
                    console.error('Erro na resposta HTTP:', resp.status, resp.statusText);
                    const responseText = await resp.text();
                    console.error('Corpo da resposta de erro:', responseText);
                    try {
                        const errData = JSON.parse(responseText);
                        alert(errData?.message || 'Erro ao importar');
                    } catch {
                        alert('Erro ao importar: ' + resp.statusText);
                    }
                    return;
                }
                
                const responseText = await resp.text();
                console.log('Texto da resposta:', responseText);
                
                let data;
                try {
                    data = JSON.parse(responseText);
                } catch (parseError) {
                    console.error('Erro ao fazer parse do JSON:', parseError);
                    console.error('Resposta não é JSON válido:', responseText);
                    alert('Erro: Resposta inválida do servidor');
                    return;
                }
                
                console.log('=== DADOS PARSEADOS ===');
                console.log('Dados completos:', data);
                console.log('data.success:', data.success);
                console.log('data.message:', data.message);
                console.log('data.columns:', data.columns);
                console.log('data.data:', data.data);
                if (data.success) {
                    console.log('Sucesso - criando modal de mapeamento');
                    const columns = data.columns || [];
                    const rows = data.data || [];
                    if (!columns.length) {
                        alert('Nenhuma coluna encontrada');
                        return;
                    }

      if (template && modalContainer) {
        modalContainer.innerHTML = template.innerHTML;
        const modalEl = modalContainer.querySelector('.modal');
        const selectsWrap = modalEl.querySelector('#mapearCampos');
        const fields = ['titulo', 'categoria', 'rede_ensino', 'etapa_ensino', 'pdf_url'];
        fields.forEach((field) => {
          const div = document.createElement('div');
          div.className = 'mb-3';
          const label = document.createElement('label');
          label.className = 'form-label';
          label.htmlFor = field;
          label.textContent = field.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
          const select = document.createElement('select');
          select.className = 'form-select';
          select.id = field;
          select.dataset.field = field;
          select.required = true;
          const optEmpty = document.createElement('option');
          optEmpty.value = '';
          optEmpty.textContent = 'Selecione';
          select.appendChild(optEmpty);
          columns.forEach((col) => {
            const opt = document.createElement('option');
            opt.value = col;
            opt.textContent = col;
            select.appendChild(opt);
          });
          div.appendChild(label);
          div.appendChild(select);
          selectsWrap.appendChild(div);
        });

        const modal = new bootstrap.Modal(modalEl);
        const confirmBtn = modalEl.querySelector('#confirmarMapeamento');
        attachOnce(confirmBtn, 'click', async () => {
          const selects = selectsWrap.querySelectorAll('select');
          const chosen = [];
          for (const sel of selects) {
            if (!sel.value) {
              alert('Preencha todas as colunas');
              return;
            }
            chosen.push(sel.value);
          }
          const payload = new FormData();
          chosen.forEach((c) => payload.append('columns', c));
          payload.append('temp_id', data.temp_id);
          payload.append('data', JSON.stringify(rows));
          try {
            console.log('=== SEGUNDA REQUISIÇÃO (CONFIRMAÇÃO) ===');
            console.log('URL:', formImportarTrabalhos.action);
            console.log('Payload:', Array.from(payload.entries()));
            console.log('CSRF Token:', csrfToken);
            
            const resp2 = await fetch(formImportarTrabalhos.action, {
              method: 'POST',
              body: payload,
              headers: { 'X-CSRFToken': csrfToken },
            });
            
            console.log('=== RESPOSTA DA CONFIRMAÇÃO ===');
            console.log('Status:', resp2.status);
            console.log('Status Text:', resp2.statusText);
            console.log('Headers:', Object.fromEntries(resp2.headers.entries()));
            console.log('OK:', resp2.ok);
            
            const responseText2 = await resp2.text();
            console.log('Texto da resposta:', responseText2);
            
            let resData;
            try {
              resData = JSON.parse(responseText2);
            } catch (parseError) {
              console.error('Erro ao fazer parse do JSON na confirmação:', parseError);
              console.error('Resposta não é JSON válido:', responseText2);
              alert('Erro: Resposta inválida do servidor na confirmação');
              return;
            }
            
            console.log('=== DADOS DA CONFIRMAÇÃO ===');
            console.log('Dados completos:', resData);
            console.log('resData.success:', resData.success);
            console.log('resData.message:', resData.message);
            
            if (resp2.ok) {
              alert(resData?.message || 'Importação concluída');
              window.location.reload();
            } else {
              alert(resData?.message || 'Erro ao importar');
            }
          } catch (err2) {
            console.error('Erro de rede na confirmação:', err2);
            alert('Erro de rede: ' + err2.message);
          }
        });
        modal.show();
      }
                } else {
                    console.log('Dados recebidos no else:', data);
                    console.log('Tipo de data:', typeof data);
                    const errorMessage = data?.message || 'Erro desconhecido - dados inválidos';
                    console.error('Erro nos dados:', errorMessage);
                    alert('Erro: ' + errorMessage);
                }
            } catch (err) {
                console.error('Erro capturado:', err);
                alert('Erro ao processar arquivo: ' + err.message);
            }
        });
    }
});
