// Script para a página offline
// Verifica periodicamente se a conexão foi restaurada
setInterval(() => {
    if (navigator.onLine) {
        window.location.reload();
    }
}, 5000); // Verificar a cada 5 segundos

// Adiciona evento para detectar quando a conexão é restaurada
window.addEventListener('online', () => {
    window.location.reload();
});

// Adiciona evento para detectar quando a conexão é perdida
window.addEventListener('offline', () => {
    console.log('Conexão perdida');
});