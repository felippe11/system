function toggleEvento(checkbox, container, select) {
    if (checkbox.checked) {
        container.classList.remove('d-none');
    } else {
        container.classList.add('d-none');
        if (select) {
            select.value = '';
        }
    }
}

function initVincularProcesso() {
    const checkbox = document.getElementById('vincular_processo');
    const container = document.getElementById('evento_relacionado_container');
    const select = document.getElementById('evento_relacionado');

    if (!checkbox || !container) {
        return;
    }

    const handler = () => toggleEvento(checkbox, container, select);
    checkbox.addEventListener('change', handler);
    handler();
}

document.addEventListener('DOMContentLoaded', initVincularProcesso);

// Placeholder: future helpers for processo seletivo, como distribuição de trabalhos
