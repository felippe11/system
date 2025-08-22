
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

  const form = document.getElementById('formImportarTrabalhos');
  const modalContainer = document.getElementById('mapearColunasModal');
  const template = document.getElementById('mapearColunasTemplate');

  attachOnce(form, 'submit', async (ev) => {
    ev.preventDefault();
    const formData = new FormData(form);
    try {
      const resp = await fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': csrfToken },
      });
      if (!resp.ok) {
        const errData = await resp.json().catch(() => null);
        alert(errData?.message || 'Erro ao importar');
        return;
      }
      const data = await resp.json();
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
          payload.append('data', JSON.stringify(rows));
          try {
            const resp2 = await fetch(form.action, {
              method: 'POST',
              body: payload,
              headers: { 'X-CSRFToken': csrfToken },
            });
            const resData = await resp2.json().catch(() => null);
            if (resp2.ok) {
              alert(resData?.message || 'Importação concluída');
              window.location.reload();
            } else {
              alert(resData?.message || 'Erro ao importar');
            }
          } catch (err2) {
            console.error('Erro de rede', err2);
          }
        });
        modal.show();
      }
    } catch (err) {
      console.error('Erro de rede', err);
    }
  });
})();
