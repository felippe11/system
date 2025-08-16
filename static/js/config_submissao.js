
/* global atualizarBotao, csrfToken */
(function () {
  const REVISAO_CONFIGS = window.REVISAO_CONFIGS || {};

  const formRevisao = document.getElementById('formRevisaoConfig');
  const selectEventoRevisao = document.getElementById('selectEventoRevisao');
  const inputNumeroRevisores = document.getElementById('inputNumeroRevisores');
  const inputPrazoRevisao = document.getElementById('inputPrazoRevisao');
  const selectModeloBlind = document.getElementById('selectModeloBlind');

  function carregarConfig(id) {
    const cfg = REVISAO_CONFIGS[id] || {};
    inputNumeroRevisores.value = cfg.numero_revisores || 2;
    inputPrazoRevisao.value = cfg.prazo_revisao ? cfg.prazo_revisao.split('T')[0] : '';
    selectModeloBlind.value = cfg.modelo_blind || 'single';
  }

  if (selectEventoRevisao) {
    carregarConfig(selectEventoRevisao.value);
    selectEventoRevisao.addEventListener('change', () => carregarConfig(selectEventoRevisao.value));
  }

  formRevisao?.addEventListener('submit', async (e) => {
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

  document.querySelectorAll('.btn-toggle').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const url = btn.dataset.toggleUrl;
      if (!url) return;
      try {
        const resp = await fetch(url, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken,
          },
        });
        if (resp.ok) {
          const data = await resp.json();
          if (data.success) {
            atualizarBotao(btn, data.value);
          } else {
            alert(data.message || 'Erro ao atualizar');
          }
        } else {
          alert('Erro ao processar solicitação');
        }
      } catch (err) {
        console.error('Erro de rede', err);
      }
    });
  });
})();
