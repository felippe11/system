// Gerenciamento de atribuição de formadores aos polos

async function carregarAtribuicoes() {
    try {
        const resp = await fetch('/api/formadores/polos');
        const data = await resp.json();
        if (!data.success) {
            console.error('Erro ao carregar atribuições');
            return;
        }
        const mapa = {};
        (data.atribuicoes || []).forEach(atr => {
            if (!mapa[atr.formador_id]) {
                mapa[atr.formador_id] = [];
            }
            mapa[atr.formador_id].push(atr);
        });
        document.querySelectorAll('#tabela-formadores tbody tr').forEach(tr => {
            const formadorId = tr.dataset.formadorId;
            const lista = tr.querySelector('.polos-atribuidos');
            lista.innerHTML = '';
            (mapa[formadorId] || []).forEach(atr => {
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

async function atribuirPolo(formadorId, poloId) {
    const resp = await fetch('/api/formadores/atribuir-polo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ formador_id: formadorId, polo_id: poloId })
    });
    const data = await resp.json();
    if (data.success) {
        await carregarAtribuicoes();
    } else {
        alert(data.message || 'Erro ao atribuir polo');
    }
}

async function removerPolo(formadorId, poloId) {
    const resp = await fetch('/api/formadores/remover-polo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ formador_id: formadorId, polo_id: poloId })
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
            const formadorId = row.dataset.formadorId;
            const select = row.querySelector('.select-polo');
            const poloId = select.value;
            if (!poloId) return;
            atribuirPolo(formadorId, poloId);
        });
    });

    document.querySelectorAll('.polos-atribuidos').forEach(lista => {
        lista.addEventListener('click', e => {
            const btn = e.target.closest('.remover-polo');
            if (!btn) return;
            const formadorId = btn.closest('tr').dataset.formadorId;
            const poloId = btn.dataset.poloId;
            removerPolo(formadorId, poloId);
        });
    });
});