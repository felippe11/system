
/* global atualizarBotao, csrfToken */
(function () {

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
})();
