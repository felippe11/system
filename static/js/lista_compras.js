let materiais = [];
let polos = [];

document.addEventListener('DOMContentLoaded', () => {
    carregarDados();
    document.getElementById('incluir-baixa').addEventListener('change', renderTabela);
    document.getElementById('incluir-esgotados').addEventListener('change', renderTabela);
    document.getElementById('btn-whatsapp').addEventListener('click', exportarWhatsApp);
    document.getElementById('btn-pdf').addEventListener('click', exportarPDF);
    document.getElementById('btn-xlsx').addEventListener('click', exportarXLSX);
});

async function carregarDados() {
    try {
        const [resPolos, resMateriais] = await Promise.all([
            fetch('/api/polos'),
            fetch('/api/materiais')
        ]);

        const polosJson = await resPolos.json();
        polos = polosJson.polos || [];

        const matJson = await resMateriais.json();
        materiais = (matJson.materiais || []).map(m => ({
            ...m,
            polo: polos.find(p => p.id === m.polo_id)
        }));
        renderTabela();
    } catch (err) {
        console.error('Erro ao carregar dados:', err);
    }
}

function filtrarMateriais() {
    const incluirBaixa = document.getElementById('incluir-baixa').checked;
    const incluirEsgotados = document.getElementById('incluir-esgotados').checked;

    return materiais.filter(m => {
        if (m.status_estoque === 'esgotado') {
            return incluirEsgotados;
        }
        if (m.status_estoque === 'baixo') {
            return incluirBaixa;
        }
        return false;
    });
}

function renderTabela() {
    const tbody = document.querySelector('#tabela-lista-compras tbody');
    if (!tbody) return;
    const dados = filtrarMateriais();
    tbody.innerHTML = '';
    dados.forEach(mat => {
        const comprar = Math.ceil(mat.quantidade_minima - mat.quantidade_atual + mat.quantidade_minima * 0.5);
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${mat.nome}</td><td>${mat.polo ? mat.polo.nome : ''}</td><td>${mat.quantidade_atual}</td><td>${mat.quantidade_minima}</td><td>${comprar}</td>`;
        tbody.appendChild(tr);
    });
}

function gerarTexto() {
    return filtrarMateriais().map(m => {
        const comprar = Math.ceil(m.quantidade_minima - m.quantidade_atual + m.quantidade_minima * 0.5);
        return `${m.nome} - Comprar ${comprar} ${m.unidade}`;
    }).join('\n');
}

function exportarWhatsApp() {
    const texto = gerarTexto();
    navigator.clipboard.writeText(texto);
}

function exportarPDF() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    let y = 10;
    filtrarMateriais().forEach((m, idx) => {
        const comprar = Math.ceil(m.quantidade_minima - m.quantidade_atual + m.quantidade_minima * 0.5);
        doc.text(`${idx + 1}. ${m.nome} - ${comprar} ${m.unidade}`, 10, y);
        y += 10;
    });
    doc.save('lista_compras.pdf');
}

function exportarXLSX() {
    const dados = filtrarMateriais().map(m => {
        const comprar = Math.ceil(m.quantidade_minima - m.quantidade_atual + m.quantidade_minima * 0.5);
        return {
            Material: m.nome,
            Polo: m.polo ? m.polo.nome : '',
            QuantidadeAtual: m.quantidade_atual,
            QuantidadeMinima: m.quantidade_minima,
            Comprar: comprar,
            Unidade: m.unidade
        };
    });
    const ws = XLSX.utils.json_to_sheet(dados);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Lista');
    XLSX.writeFile(wb, 'lista_compras.xlsx');
}
