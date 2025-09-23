// Gerenciamento de atribuição de monitores aos polos

async function carregarAtribuicoes() {
    try {
        const resp = await fetch('/api/monitores/polos');
        const data = await resp.json();
        if (!data.success) {
            console.error('Erro ao carregar atribuições');
            return;
        }
        const mapa = {};
        (data.atribuicoes || []).forEach(atr => {
            if (!mapa[atr.monitor_id]) {
                mapa[atr.monitor_id] = [];
            }
            mapa[atr.monitor_id].push(atr);
        });
        document.querySelectorAll('#tabela-monitores tbody tr').forEach(tr => {
            const monitorId = tr.dataset.monitorId;
            const lista = tr.querySelector('.polos-atribuidos');
            lista.innerHTML = '';
            (mapa[monitorId] || []).forEach(atr => {
                const li = document.createElement('li');
                li.dataset.poloId = atr.polo_id;
                li.textContent = atr.polo_nome;
                const btn = document.createElement('button');
                btn.className = 'btn btn-sm btn-danger ms-2 remover-polo';
                btn.dataset.poloId = atr.polo_id;
                btn.innerHTML = '<i class="fas fa-times"></i>';
                li.appendChild(btn);
                lista.appendChild(li);
            });
        });
    } catch (err) {
        console.error('Falha ao carregar atribuições', err);
    }
}

async function atribuirPolo(monitorId, poloId) {
    const resp = await fetch('/api/monitores/atribuir-polo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ monitor_id: monitorId, polo_id: poloId })
    });
    const data = await resp.json();
    if (data.success) {
        await carregarAtribuicoes();
    } else {
        alert(data.message || 'Erro ao atribuir polo');
    }
}

async function removerPolo(monitorId, poloId) {
    const resp = await fetch('/api/monitores/remover-polo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ monitor_id: monitorId, polo_id: poloId })
    });
    const data = await resp.json();
    if (data.success) {
        await carregarAtribuicoes();
    } else {
        alert(data.message || 'Erro ao remover polo');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    carregarAtribuicoes();

    document.querySelectorAll('.atribuir-polo').forEach(btn => {
        btn.addEventListener('click', () => {
            const row = btn.closest('tr');
            const monitorId = row.dataset.monitorId;
            const select = row.querySelector('.select-polo');
            const poloId = select.value;
            if (!poloId) return;
            atribuirPolo(monitorId, poloId);
        });
    });

    document.querySelectorAll('.polos-atribuidos').forEach(lista => {
        lista.addEventListener('click', e => {
            const btn = e.target.closest('.remover-polo');
            if (!btn) return;
            const monitorId = btn.closest('tr').dataset.monitorId;
            const poloId = btn.dataset.poloId;
            removerPolo(monitorId, poloId);
        });
    });
});
