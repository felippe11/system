/**
 * pwa-unified.js
 * Script unificado para gerenciar o PWA, incluindo registro de Service Worker
 * e funcionalidades de instalação.
 */

// Registrar o Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/js/sw.js')
      .then(registration => {
        console.log('Service Worker registrado com sucesso:', registration.scope);
      })
      .catch(error => {
        console.log('Falha ao registrar o Service Worker:', error);
      });
  });
}

// Lógica para o botão de instalação da PWA
// Usamos window.deferredPrompt para evitar redeclaração da variável
window.deferredPrompt = null;
var installButton = document.getElementById('pwa-install-btn');

// Oculta o botão de instalação inicialmente
if (installButton) {
  installButton.classList.add('d-none');
}

// Captura o evento beforeinstallprompt
window.addEventListener('beforeinstallprompt', (e) => {
  // Previne o comportamento padrão do navegador
  e.preventDefault();
  // Armazena o evento para uso posterior
  window.deferredPrompt = e;
  // Mostra o botão de instalação
  if (installButton) {
    installButton.classList.remove('d-none');
  }
});

// Adiciona evento de clique ao botão de instalação
if (installButton) {
  installButton.addEventListener('click', async (e) => {
    e.preventDefault();
    if (!window.deferredPrompt) {
      return;
    }
    // Mostra o prompt de instalação
    window.deferredPrompt.prompt();
    // Aguarda a escolha do usuário
    const { outcome } = await window.deferredPrompt.userChoice;
    console.log(`Usuário ${outcome === 'accepted' ? 'aceitou' : 'recusou'} a instalação`);
    // Limpa a referência
    window.deferredPrompt = null;
    // Oculta o botão após a interação
    installButton.classList.add('d-none');
  });
}

// Detecta quando o app foi instalado
window.addEventListener('appinstalled', (e) => {
  console.log('Aplicativo instalado com sucesso!');
});
