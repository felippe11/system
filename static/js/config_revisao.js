
/* global window */
/**
 * Funções para gestão de revisão: geração de códigos e atribuições.
 */
(function () {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

  const reviewerSelect = document.getElementById('reviewerSelect');
  const minRev = parseInt(
    reviewerSelect?.dataset.min || window.MIN_REVIEWERS || 1,
    10,
  );
  const maxRev = parseInt(
    reviewerSelect?.dataset.max || window.MAX_REVIEWERS || 2,
    10,
  );

  /**
   * Atacha listeners para gerar códigos de revisão.
   */
  function setupCodeGeneration() {
    document.querySelectorAll('.gerar-codigos').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const loc = btn.dataset.locator;
        try {
          const resp = await fetch(`/submissions/${loc}/codes`, {
            headers: { 'X-CSRFToken': csrfToken },
          });
          if (!resp.ok) throw new Error('Falha no fetch');
          const data = await resp.json();
          if (data.reviews) {
            alert(data.reviews.map((r) => r.access_code).join('\n'));
          }
        } catch (err) {
          console.error('Erro ao gerar códigos', err);
          alert('Erro ao gerar códigos');
        }
      });
    });
  }

  /**
   * Atribui revisores manualmente após validar limites.
   */
  function setupAssignManual() {
    document.getElementById('assignManual')?.addEventListener('click', async () => {
      const subId = document.getElementById('submissionSelect').value;
      const selected = Array.from(reviewerSelect.selectedOptions).map(
        (o) => o.value,
      );
      if (selected.length < minRev || selected.length > maxRev) {
        alert(`Selecione entre ${minRev} e ${maxRev} revisores.`);
        return;
      }
      const payload = {};
      payload[subId] = selected;
      try {
        const resp = await fetch('/assign_reviews', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify(payload),
        });
        const data = await resp.json();
        if (data.success) {
          alert('Revisores atribuídos com sucesso');
          window.location.reload();
        } else {
          alert(data.message || 'Falha ao atribuir revisores');
        }
      } catch (err) {
        console.error('Erro na atribuição manual', err);
      }
    });
  }

  /**
   * Realiza sorteio automático de revisores.
   */
  function setupAssignAutomatic() {
    document
      .getElementById('assignAutomatic')
      ?.addEventListener('click', async () => {
        try {
          const resp = await fetch('/assign_by_filters', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({ filters: {} }),
          });
          const data = await resp.json();
          if (resp.ok && data.success) {
            alert('Sorteio realizado');
            window.location.reload();
          } else {
            alert(data.message || 'Falha no sorteio');
          }
        } catch (err) {
          console.error('Erro no sorteio automático', err);
        }
      });
  }

  /**
   * Atribui revisores automaticamente por área.
   */
  function setupAutoArea() {
    document.getElementById('autoArea')?.addEventListener('click', async () => {
      const eventoId = document.getElementById('eventoId').value;
      if (!eventoId) {
        alert('Informe o ID do evento');
        return;
      }
      try {
        const resp = await fetch(`/auto_assign/${eventoId}`, {
          method: 'POST',
          headers: { 'X-CSRFToken': csrfToken },
        });
        const data = await resp.json();
        if (resp.ok && data.success) {
          alert('Atribuições criadas');
          window.location.reload();
        } else {
          alert(data.message || 'Erro na atribuição automática');
        }
      } catch (err) {
        console.error('Erro na atribuição por área', err);
      }
    });
  }

  /**
   * Inicializa os listeners do módulo de revisão.
   */
  function init() {
    setupCodeGeneration();
    setupAssignManual();
    setupAssignAutomatic();
    setupAutoArea();
  }

  document.addEventListener('DOMContentLoaded', init);
})();

