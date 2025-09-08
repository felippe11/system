// Funções para geração e cópia de links de inscrição de monitores
let linkModal;

document.addEventListener('DOMContentLoaded', () => {
    const modalEl = document.getElementById('gerarLinkModal');
    if (modalEl) {
        linkModal = new bootstrap.Modal(modalEl);
    }

    const abrirModal = document.getElementById('gerar-link-btn');
    if (abrirModal && linkModal) {
        abrirModal.addEventListener('click', () => {
            linkModal.show();
        });
    }
});

async function gerarLinkMonitor() {
    const expiresInput = document.getElementById('expires-at');
    const linkInput = document.getElementById('monitor-link');
    const expiresAt = expiresInput?.value;
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    try {
        const response = await fetch('/monitor/gerar_link', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ expires_at: expiresAt })
        });

        if (!response.ok) {
            throw new Error('Erro ao gerar link');
        }

        const data = await response.json();
        linkInput.value = data.url || '';
    } catch (err) {
        alert(err.message);
    }
}

function copiarLinkMonitor() {
    const linkInput = document.getElementById('monitor-link');
    const link = linkInput?.value;
    if (!link) {
        return;
    }
    navigator.clipboard.writeText(link).then(() => {
        alert('Link copiado para a área de transferência');
    });
}
