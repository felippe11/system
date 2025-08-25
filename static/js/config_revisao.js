
/* global window */
(function () {
  const container = document.getElementById('configSubmissao');
  if (!container) return;

  // Global URL for other scripts
  if (!window.URL_CONFIG_CLIENTE_ATUAL) {
    window.URL_CONFIG_CLIENTE_ATUAL = container.dataset.urlConfigClienteAtual || '';
  }

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

  function attachOnce(el, event, handler) {
    if (!el) return;
    const key = `listener_${event}`;
    if (el.dataset[key]) return;
    el.dataset[key] = 'true';
    el.addEventListener(event, handler);
  }

  const REVISAO_CONFIGS = JSON.parse(container.dataset.revisaoConfigs || '{}');
  const formRevisao = document.getElementById('formRevisaoConfig');
  const selectEventoRevisao = document.getElementById('selectEventoRevisao');
  const inputNumeroRevisores = document.getElementById('inputNumeroRevisores');
  const inputPrazoRevisao = document.getElementById('inputPrazoRevisao');
  const selectModeloBlind = document.getElementById('selectModeloBlind');

  function carregarConfig(id) {
    const cfg = REVISAO_CONFIGS[id] || {};
    if (inputNumeroRevisores) inputNumeroRevisores.value = cfg.numero_revisores || 2;
    if (inputPrazoRevisao) inputPrazoRevisao.value = cfg.prazo_revisao ? cfg.prazo_revisao.split('T')[0] : '';
    if (selectModeloBlind) selectModeloBlind.value = cfg.modelo_blind || 'single';
  }

  if (selectEventoRevisao) {
    carregarConfig(selectEventoRevisao.value);
    attachOnce(selectEventoRevisao, 'change', () => carregarConfig(selectEventoRevisao.value));
  }

  attachOnce(formRevisao, 'submit', async (e) => {
    e.preventDefault();
    const eventoId = selectEventoRevisao.value;
    const payload = {
      numero_revisores: parseInt(inputNumeroRevisores.value, 10),
      modelo_blind: selectModeloBlind.value,
    };
    if (inputPrazoRevisao.value) {
      payload.prazo_revisao = inputPrazoRevisao.value;
    }
    const resp = await fetch(`/revisao_config/${eventoId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify(payload),
    });
    if (resp.ok) {
      REVISAO_CONFIGS[eventoId] = payload;
      alert('Configuração de revisão atualizada');
    } else {
      alert('Erro ao salvar configuração');
    }
  });

  document.querySelectorAll('.gerar-codigos').forEach((btn) => {
    attachOnce(btn, 'click', () => {
      const loc = btn.dataset.locator;
      const code = btn.dataset.code; // Código da submissão se disponível
      
      // Construir URL com código se disponível
      let url = `/submissions/${loc}/codes`;
      if (code) {
        url += `?code=${encodeURIComponent(code)}`;
      }
      
      console.log('Fazendo requisição para:', url);
      
      fetch(url)
        .then((r) => {
          console.log('Status da resposta:', r.status);
          if (!r.ok) {
            throw new Error(`HTTP ${r.status}: ${r.statusText}`);
          }
          return r.json();
        })
        .then((data) => {
          console.log('Dados recebidos:', data);
          if (data.reviews && data.reviews.length > 0) {
            const codes = data.reviews.map((r) => `Revisor: ${r.reviewer_name || 'N/A'} - Código: ${r.access_code}`).join('\n');
            alert(`Códigos de Acesso dos Revisores:\n\n${codes}`);
          } else {
            alert('Nenhum código de revisor encontrado para esta submissão.');
          }
        })
        .catch((error) => {
          console.error('Erro na requisição:', error);
          alert(`Erro ao obter códigos: ${error.message}`);
        });
    });
  });

  const minRev = parseInt(container.dataset.minRev || '1', 10);
  const maxRev = parseInt(container.dataset.maxRev || '2', 10);

  attachOnce(document.getElementById('assignManual'), 'click', () => {
    console.log('Botão Atribuir Manualmente clicado');
    const subId = document.getElementById('submissionSelect').value;
    const selected = Array.from(
      document.getElementById('reviewerSelect').selectedOptions,
    ).map((o) => o.value);
    console.log('Submissão selecionada:', subId);
    console.log('Revisores selecionados:', selected);
    console.log('Limites min/max:', minRev, maxRev);
    
    if (selected.length < minRev || selected.length > maxRev) {
      alert(`Selecione entre ${minRev} e ${maxRev} revisores.`);
      return;
    }
    const payload = {};
    payload[subId] = selected;
    console.log('Payload para envio:', payload);
    console.log('CSRF Token:', csrfToken);
    
    fetch('/assign_reviews', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify(payload),
    })
      .then((r) => {
        console.log('Resposta recebida:', r.status, r.statusText);
        return r.json();
      })
      .then((data) => {
        console.log('Dados da resposta:', data);
        if (data.success) {
          alert('Revisores atribuídos com sucesso');
          location.reload();
        } else {
          alert('Falha ao atribuir revisores: ' + (data.message || 'Erro desconhecido'));
        }
      })
      .catch((error) => {
        console.error('Erro na requisição:', error);
        alert('Erro de rede ao atribuir revisores');
      });
  });

  attachOnce(document.getElementById('assignAutomatic'), 'click', () => {
    console.log('Botão Sorteio Automático clicado');
    const filters = {};
    document.querySelectorAll('[data-filter]').forEach((el) => {
      const valor = el.value.trim();
      if (valor) filters[el.dataset.filter] = valor;
    });
    console.log('Filtros aplicados:', filters);
    console.log('CSRF Token:', csrfToken);
    
    fetch('/assign_by_filters', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({ filters }),
    })
      .then((r) => {
        console.log('Resposta do sorteio:', r.status, r.statusText);
        return r.json();
      })
      .then((data) => {
        console.log('Dados do sorteio:', data);
        if (data.success) {
          alert('Sorteio realizado');
          location.reload();
        } else {
          alert(data.message || 'Falha no sorteio');
        }
      })
      .catch((error) => {
        console.error('Erro no sorteio:', error);
        alert('Erro de rede no sorteio');
      });
  });

  attachOnce(document.getElementById('autoArea'), 'click', () => {
    console.log('Botão Auto por Área clicado');
    const eventoId = document.getElementById('eventoId').value;
    console.log('ID do evento:', eventoId);
    
    if (!eventoId) {
      alert('Informe o ID do evento');
      return;
    }
    console.log('CSRF Token:', csrfToken);
    
    fetch(`/auto_assign/${eventoId}`, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
    })
      .then((r) => {
        console.log('Resposta auto área:', r.status, r.statusText);
        return r.json();
      })
      .then((data) => {
        console.log('Dados auto área:', data);
        if (data.success) {
          alert('Atribuições criadas');
          location.reload();
        } else {
          alert(data.message || 'Erro na atribuição automática');
        }
      })
      .catch((error) => {
        console.error('Erro na atribuição por área:', error);
        alert('Erro de rede na atribuição por área');
      });
  });

  attachOnce(document.getElementById('assignByCategory'), 'click', () => {
    console.log('Botão Distribuir por Categoria clicado');
    
    // Confirmar ação com o usuário
    if (!confirm('Deseja distribuir automaticamente os trabalhos para revisores baseado na categoria? Esta ação irá criar atribuições para todos os trabalhos compatíveis.')) {
      return;
    }
    
    console.log('CSRF Token:', csrfToken);
    
    // Desabilitar botão durante processamento
    const btn = document.getElementById('assignByCategory');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processando...';
    
    fetch('/assign_by_category', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({})
    })
      .then((r) => {
        console.log('Resposta distribuição por categoria:', r.status, r.statusText);
        return r.json();
      })
      .then((data) => {
        console.log('Dados distribuição por categoria:', data);
        if (data.success) {
          alert(`Distribuição concluída com sucesso!\n\nResumo:\n- ${data.assignments_created || 0} atribuições criadas\n- ${data.works_assigned || 0} trabalhos atribuídos\n- ${data.reviewers_used || 0} revisores utilizados`);
          location.reload();
        } else {
          alert(data.message || 'Erro na distribuição por categoria');
        }
      })
      .catch((error) => {
        console.error('Erro na distribuição por categoria:', error);
        alert('Erro de rede na distribuição por categoria');
      })
      .finally(() => {
        // Reabilitar botão
        btn.disabled = false;
        btn.innerHTML = originalText;
      });
  });
})();
