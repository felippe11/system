let materiais = [];
let polos = [];

document.addEventListener('DOMContentLoaded', () => {
    carregarDados();
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
    const incluirBaixa = document.getElementById('incluir-baixa').dataset.checked === 'true';
    const incluirEsgotados = document.getElementById('incluir-esgotados').dataset.checked === 'true';

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
        const comprar = mat.quantidade_atual <= mat.quantidade_minima ? (mat.quantidade_minima + 1) - mat.quantidade_atual : 0;
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${mat.nome}</td><td>${mat.polo ? mat.polo.nome : ''}</td><td>${mat.quantidade_atual}</td><td>${mat.quantidade_minima}</td><td>${comprar}</td>`;
        tbody.appendChild(tr);
    });
}

function gerarTexto() {
    return filtrarMateriais().map(m => {
        const comprar = m.quantidade_atual <= m.quantidade_minima ? (m.quantidade_minima + 1) - m.quantidade_atual : 0;
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
    const grupos = filtrarMateriais().reduce((acc, m) => {
        const nomePolo = m.polo ? m.polo.nome : 'Sem Polo';
        const comprar = m.quantidade_atual <= m.quantidade_minima ? (m.quantidade_minima + 1) - m.quantidade_atual : 0;
        if (!acc[nomePolo]) {
            acc[nomePolo] = [];
        }
        acc[nomePolo].push([
            m.nome,
            nomePolo,
            m.quantidade_atual,
            m.quantidade_minima,
            comprar,
            m.unidade
        ]);
        return acc;
    }, {});
    let y = 10;
    Object.keys(grupos).forEach(poloNome => {
        doc.text(poloNome, 10, y);
        doc.autoTable({
            startY: y + 5,
            head: [['Material', 'Polo', 'Qtd Atual', 'Qtd Mínima', 'Comprar', 'Unidade']],
            body: grupos[poloNome]
        });
        y = doc.lastAutoTable.finalY + 10;
    });
    doc.save('lista_compras.pdf');
}

function exportarXLSX() {
    const dados = filtrarMateriais().map(m => {
        const comprar = m.quantidade_atual <= m.quantidade_minima ? (m.quantidade_minima + 1) - m.quantidade_atual : 0;
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
