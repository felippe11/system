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
let deferredPrompt;
const installButton = document.getElementById('pwa-install-btn');

// Oculta o botão de instalação inicialmente
if (installButton) {
  installButton.classList.add('d-none');
}

// Captura o evento beforeinstallprompt
window.addEventListener('beforeinstallprompt', (e) => {
  // Previne o comportamento padrão do navegador
  e.preventDefault();
  // Armazena o evento para uso posterior
  deferredPrompt = e;
  // Mostra o botão de instalação
  if (installButton) {
    installButton.classList.remove('d-none');
  }
});

// Adiciona evento de clique ao botão de instalação
if (installButton) {
  installButton.addEventListener('click', async () => {
    if (!deferredPrompt) {
      return;
    }
    // Mostra o prompt de instalação
    deferredPrompt.prompt();
    // Aguarda a escolha do usuário
    const { outcome } = await deferredPrompt.userChoice;
    console.log(`Usuário ${outcome === 'accepted' ? 'aceitou' : 'recusou'} a instalação`);
    // Limpa a referência
    deferredPrompt = null;
    // Oculta o botão após a interação
    installButton.classList.add('d-none');
  });
}

// Detecta quando o app foi instalado
window.addEventListener('appinstalled', (e) => {
  console.log('Aplicativo instalado com sucesso!');
});