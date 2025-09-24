/**
 * Script de debug para a página de feedback
 * Este arquivo ajuda a identificar problemas com os botões
 */

console.log('🔧 Feedback Debug Script carregado');

// Função para testar todos os elementos da página
function testarElementosFeedback() {
    console.log('=== TESTE DE ELEMENTOS DA PÁGINA DE FEEDBACK ===');
    
    const elementos = {
        'oficinaSelect': document.getElementById('oficinaSelect'),
        'atividadeSelect': document.getElementById('atividadeSelect'),
        'perguntasContainer': document.getElementById('perguntasContainer'),
        'criarPerguntaBtn': document.getElementById('criarPerguntaBtn'),
        'perguntaModal': document.getElementById('perguntaModal'),
        'perguntaForm': document.getElementById('perguntaForm'),
        'tipoSelect': document.getElementById('tipo'),
        'opcoesContainer': document.getElementById('opcoesContainer'),
        'salvarPergunta': document.getElementById('salvarPergunta'),
        'exportarBtn': document.querySelector('a[href*="exportar_feedback"]')
    };
    
    Object.keys(elementos).forEach(nome => {
        const elemento = elementos[nome];
        if (elemento) {
            console.log(`✅ ${nome}: encontrado`, elemento);
        } else {
            console.error(`❌ ${nome}: não encontrado`);
        }
    });
    
    console.log('=== FIM DO TESTE DE ELEMENTOS ===');
}

// Função para testar event listeners
function testarEventListeners() {
    console.log('=== TESTE DE EVENT LISTENERS ===');
    
    const criarPerguntaBtn = document.getElementById('criarPerguntaBtn');
    if (criarPerguntaBtn) {
        // Verificar se já tem event listeners
        const listeners = getEventListeners ? getEventListeners(criarPerguntaBtn) : 'Não disponível';
        console.log('Event listeners no botão Nova Pergunta:', listeners);
        
        // Verificar se o botão está desabilitado
        console.log('Botão desabilitado:', criarPerguntaBtn.disabled);
        console.log('Botão readonly:', criarPerguntaBtn.readOnly);
        
        // Verificar estilos que podem impedir cliques
        const computedStyle = window.getComputedStyle(criarPerguntaBtn);
        console.log('Estilos críticos:', {
            pointerEvents: computedStyle.pointerEvents,
            cursor: computedStyle.cursor,
            opacity: computedStyle.opacity,
            visibility: computedStyle.visibility,
            display: computedStyle.display
        });
        
        // Adicionar listener de teste
        criarPerguntaBtn.addEventListener('click', function(e) {
            console.log('🎯 TESTE: Botão Nova Pergunta clicado via debug script');
            console.log('Event details:', {
                type: e.type,
                target: e.target,
                currentTarget: e.currentTarget,
                bubbles: e.bubbles,
                cancelable: e.cancelable
            });
            e.preventDefault(); // Prevenir ação padrão para teste
        });
        console.log('✅ Event listener de teste adicionado ao botão Nova Pergunta');
        
        // Teste de clique programático
        setTimeout(() => {
            console.log('🧪 Testando clique programático...');
            try {
                const event = new MouseEvent('click', {
                    view: window,
                    bubbles: true,
                    cancelable: true
                });
                criarPerguntaBtn.dispatchEvent(event);
                console.log('✅ Clique programático executado');
            } catch (error) {
                console.error('❌ Erro no clique programático:', error);
            }
        }, 1000);
    }
    
    const exportarBtn = document.querySelector('a[href*="exportar_feedback"]');
    if (exportarBtn) {
        exportarBtn.addEventListener('click', function(e) {
            console.log('🎯 TESTE: Botão Exportar clicado via debug script');
            console.log('URL de destino:', this.href);
        });
        console.log('✅ Event listener de teste adicionado ao botão Exportar');
    }
    
    console.log('=== FIM DO TESTE DE EVENT LISTENERS ===');
}

// Executar testes quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 DOM carregado, executando testes de debug...');
    
    // Aguardar um pouco para garantir que outros scripts tenham carregado
    setTimeout(() => {
        testarElementosFeedback();
        testarEventListeners();
    }, 500);
});

// Exportar funções para uso global
window.testarElementosFeedback = testarElementosFeedback;
window.testarEventListeners = testarEventListeners;
