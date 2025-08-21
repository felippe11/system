/* global window */
(function () {
  const form = document.getElementById('formImportarTrabalhos');
  if (!form) return;

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

  form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const data = new FormData(form);
    try {
      const resp = await fetch(form.action, {
        method: 'POST',
        body: data,
        headers: { 'X-CSRFToken': csrfToken },
      });
      const resData = await resp.json().catch(() => null);
      if (resp.ok) {
        if (resData?.status === 'ok') {
          alert(resData.message || 'Importação concluída');
          window.location.reload();
        } else {
          alert(resData?.message || 'Erro ao importar');
        }
      } else {
        alert(resData?.message || 'Erro ao importar');
      }
    } catch (error) {
      console.error('Erro de rede', error);
      alert('Erro de rede');
    }
  });
})();
