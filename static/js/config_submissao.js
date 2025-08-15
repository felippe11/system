const form_revisao = document.getElementById('formRevisaoConfig');
const select_evento_revisao = document.getElementById('selectEventoRevisao');
const input_numero_revisores = document.getElementById('inputNumeroRevisores');
const input_prazo_revisao = document.getElementById('inputPrazoRevisao');
const select_modelo_blind = document.getElementById('selectModeloBlind');

/**
 * Carrega a configuração de revisão para o evento atual.
 * @param {string} id - Identificador do evento.
 */
function carregar_config(id) {
    const cfg = REVISAO_CONFIGS[id] || {};
    input_numero_revisores.value = cfg.numero_revisores || 2;
    input_prazo_revisao.value = cfg.prazo_revisao ? cfg.prazo_revisao.split('T')[0] : '';
    select_modelo_blind.value = cfg.modelo_blind || 'single';
}

if (select_evento_revisao) {
    carregar_config(select_evento_revisao.value);
    select_evento_revisao.addEventListener('change', () => carregar_config(select_evento_revisao.value));
}

/**
 * Envia a configuração de revisão para o servidor.
 * @param {Event} event - Evento de submissão do formulário.
 */
async function enviar_config_revisao(event) {
    event.preventDefault();
    const evento_id = select_evento_revisao.value;
    const payload = {
        numero_revisores: parseInt(input_numero_revisores.value, 10),
        modelo_blind: select_modelo_blind.value,
    };
    if (input_prazo_revisao.value) {
        payload.prazo_revisao = input_prazo_revisao.value;
    }
    const resp = await fetch(`/revisao_config/${evento_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    if (resp.ok) {
        REVISAO_CONFIGS[evento_id] = payload;
        alert('Configuração de revisão atualizada');
    } else {
        alert('Erro ao salvar configuração');
    }
}

form_revisao?.addEventListener('submit', enviar_config_revisao);
