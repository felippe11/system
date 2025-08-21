/* global window */
(function () {
  const form = document.getElementById('formImportarTrabalhos');
  if (!form) return;

  const csrfToken = document
    .querySelector('meta[name="csrf-token"]')
    ?.getAttribute('content') || '';
  const eventoInput = document.getElementById('eventoId');

  form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const data = new FormData(form);
    if (eventoInput && eventoInput.value) {
      data.append('evento_id', eventoInput.value);
    }
    try {
      const resp = await fetch(form.action, {
        method: 'POST',
        body: data,
        headers: { 'X-CSRFToken': csrfToken },
      });
      if (resp.ok) {
        window.location.reload();
      } else {
        const err = await resp.json().catch(() => null);
        alert(err?.message || 'Erro ao importar');
      }
    } catch (error) {
      console.error('Erro de rede', error);
    }
  });
})();
