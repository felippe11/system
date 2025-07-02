// Service Worker para AppFiber PWA
const CACHE_NAME = 'appfiber-v2';
const urlsToCache = [
  '/',
  '/static/css/estilos.css',
  '/static/favicon/favicon.svg',
  '/static/favicon/favicon.ico',
  '/static/favicon/apple-touch-icon.png',
  '/static/favicon/favicon-96x96.png',
  '/static/favicon/web-app-manifest-192x192.png',
  '/static/favicon/web-app-manifest-512x512.png',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons/font/bootstrap-icons.css',
  'https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap',
  '/static/offline.html'
];

// Página offline para fallback
const OFFLINE_PAGE = '/static/offline.html';


// Instalação do Service Worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Cache aberto');
        return cache.addAll(urlsToCache);
      })
  );
});

// Ativação do Service Worker
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Estratégia de cache: Cache First, then Network com fallback para offline
self.addEventListener('fetch', event => {
  // Verifica se a requisição é para uma página HTML
  const isNavigationRequest = event.request.mode === 'navigate';

  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - retorna a resposta do cache
        if (response) {
          return response;
        }

        // Clone da requisição
        const fetchRequest = event.request.clone();

        return fetch(fetchRequest)
          .then(response => {
            // Verifica se a resposta é válida
            if(!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            // Clone da resposta
            const responseToCache = response.clone();

            caches.open(CACHE_NAME)
              .then(cache => {
                // Adiciona a resposta ao cache
                cache.put(event.request, responseToCache);
              });

            return response;
          })
          .catch(error => {
            // Falha na rede - retorna a página offline para requisições de navegação
            if (isNavigationRequest) {
              return caches.match(OFFLINE_PAGE);
            }
            // Para outros tipos de requisições, apenas propaga o erro
            throw error;
          });
      })
  );
});

// Evento para lidar com mensagens do cliente
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
