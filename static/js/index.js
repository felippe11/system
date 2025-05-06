// Atualizar ano atual no footer
document.getElementById('currentYear').textContent = new Date().getFullYear();

// Navbar fixa com mudança ao scroll
window.addEventListener('scroll', function() {
    const navbar = document.querySelector('.navbar');
    if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
});

// Scroll suave para âncoras
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        
        const targetId = this.getAttribute('href');
        if (targetId === '#') return;
        
        const targetElement = document.querySelector(targetId);
        if (targetElement) {
            window.scrollTo({
                top: targetElement.offsetTop - 80,
                behavior: 'smooth'
            });
            
            // Atualizar link ativo
            document.querySelectorAll('.nav-link').forEach(navLink => {
                navLink.classList.remove('active');
            });
            this.classList.add('active');
        }
    });
});

// Ativar link do menu correspondente à seção visível
window.addEventListener('scroll', function() {
    const sections = document.querySelectorAll('section[id]');
    let scrollPosition = window.scrollY + 100;
    
    sections.forEach(section => {
        const sectionTop = section.offsetTop - 100;
        const sectionHeight = section.offsetHeight;
        const sectionId = section.getAttribute('id');
        
        if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
            document.querySelectorAll('.nav-link').forEach(navLink => {
                navLink.classList.remove('active');
                if (navLink.getAttribute('href') === '#' + sectionId) {
                    navLink.classList.add('active');
                }
            });
        }
    });
});

// Cores default para uso como placeholder (sem depender da rota de placeholder)
const placeholderColors = [
    '#1e88e5', '#2196f3', '#03a9f4', '#00bcd4', '#009688', 
    '#4caf50', '#8bc34a', '#cddc39', '#ffeb3b', '#ffc107'
];

// Função para gerar uma cor aleatória do array acima
function getRandomColor() {
    return placeholderColors[Math.floor(Math.random() * placeholderColors.length)];
}

let eventosFiltrados = [];
let todosEventos = []; // Armazenar todos os eventos originais

// Carregar eventos em destaque via AJAX
$(document).ready(function() {
    // Mostrar loader enquanto carrega
    $('#eventos-container').html(`
        <div class="col-12 text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Carregando...</span>
            </div>
            <p class="mt-2">Carregando eventos...</p>
        </div>
    `);
    
    // Fazer requisição à API
    $.ajax({
        url: '/api/eventos/destaque',
        type: 'GET',
        dataType: 'json',
        timeout: 10000, // 10 segundos de timeout
        success: function(dados) {
            console.log("Dados recebidos da API:", dados);
            
            // Verifica se a resposta é um array ou se está dentro de alguma propriedade
            let eventos = dados;
            
            // Verifica se a resposta é um objeto com os eventos em alguma propriedade
            if (!Array.isArray(dados) && typeof dados === 'object') {
                // Tenta encontrar a propriedade que contém o array de eventos
                const possibleArrayProps = Object.keys(dados).filter(key => Array.isArray(dados[key]));
                if (possibleArrayProps.length > 0) {
                    eventos = dados[possibleArrayProps[0]];
                    console.log("Eventos encontrados na propriedade:", possibleArrayProps[0]);
                }
            }
            
            // Verifica novamente se temos um array após o processamento
            if (!Array.isArray(eventos)) {
                console.error("A resposta da API não contém um array de eventos:", dados);
                $('#eventos-container').html(`
                    <div class="col-12 text-center py-5">
                        <h4>Erro ao processar eventos</h4>
                        <p>O formato de resposta da API não é compatível.</p>
                    </div>
                `);
                return;
            }
            
            console.log(`Total de eventos encontrados: ${eventos.length}`);
            renderizarEventos(eventos);
        },
        error: function(xhr, status, error) {
            console.error("Erro ao carregar eventos:", error);
            let mensagem = "Não foi possível carregar os eventos no momento. Tente novamente mais tarde.";
            
            if (xhr.status === 404) {
                mensagem = "API de eventos não encontrada. Verifique se o endpoint está correto.";
            } else if (xhr.status === 500) {
                mensagem = "Erro interno do servidor ao buscar eventos.";
            } else if (status === 'timeout') {
                mensagem = "Tempo limite excedido ao buscar eventos.";
            }
            
            $('#eventos-container').html(`
                <div class="col-12 text-center py-5">
                    <h4>Erro ao carregar eventos</h4>
                    <p>${mensagem}</p>
                </div>
            `);
        }
    });

    // Atualizar handler do input de pesquisa para usar debounce
    let timeoutId;
    $('.search-input').on('input', function() {
        clearTimeout(timeoutId);
        const termo = $(this).val();
        
        timeoutId = setTimeout(() => {
            aplicarFiltroAoDigitar(termo);
        }, 300); // Espera 300ms após o último caractere digitado
    });
});

// Função para renderizar os eventos no carrossel
function renderizarEventos(eventos) {
    if (!todosEventos.length) {
        todosEventos = eventos; // Salva os eventos originais na primeira carga
    }
    eventosFiltrados = eventos;
    const container = $('#eventos-container');
    container.empty();
    
    if (!eventos || eventos.length === 0) {
        container.append('<div class="col-12 text-center py-5"><h4>Nenhum evento em destaque no momento</h4></div>');
        return;
    }
    
    // Cria um novo elemento div para o carrossel se não existir
    if (!container.hasClass('events-carousel')) {
        container.addClass('events-carousel');
    }
    
    console.log(`Renderizando ${eventos.length} eventos no carrossel`);
    
    eventos.forEach((evento, index) => {
        console.log(`Processando evento ${index + 1}:`, evento);
        
        const formatDate = (dateStr) => {
            if (!dateStr) return '';
            // A data pode vir em formatos diferentes dependendo da API
            // Tenta formatar se não estiver no formato desejado
            return dateStr;
        };
        
        // Determina a exibição da data do evento
        const dateRange = evento.data_fim && evento.data_fim !== evento.data_inicio 
            ? `${formatDate(evento.data_inicio)} - ${formatDate(evento.data_fim)}`
            : formatDate(evento.data_inicio) || 'Data a definir';
        
        // Formata o preço do evento
        const price = evento.preco_base > 0 
            ? `R$ ${parseFloat(evento.preco_base).toFixed(2).replace('.', ',')}`
            : 'Gratuito';
        
        // Gera um elemento div colorido como fallback de imagem
        const randomColor = getRandomColor();
        const uniqueId = `event-img-${index}-${Date.now()}`;
        
        // Cria o card do evento
        const eventCard = `
            <div class="event-card">
                <div class="event-img-container">
                    <div id="${uniqueId}" style="background-color: ${randomColor}; height: 200px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                        ${evento.nome}
                    </div>
                </div>
                <div class="event-content">
                    <div class="event-date">
                        <i class="far fa-calendar-alt"></i> ${dateRange}
                    </div>
                    <h3 class="event-title">${evento.nome}</h3>
                    <div class="event-location">
                        <i class="fas fa-map-marker-alt"></i> ${evento.localizacao || 'Local a definir'}
                    </div>
                    <p class="event-description">${evento.descricao ? evento.descricao.substring(0, 150) + (evento.descricao.length > 150 ? '...' : '') : ''}</p>
                    <div class="event-footer">
                        <div class="event-price">${price}</div>
                        ${evento.link_inscricao ? `
                            <a href="${evento.link_inscricao}" class="btn-event">Inscrever-se</a>
                        ` : `
                            <span class="text-muted fw-bold">Inscrições em breve</span>
                        `}
                    </div>
                </div>
            </div>
        `;
        
        container.append(eventCard);
        
        // Se o evento tiver uma URL de banner, tenta carregar a imagem
        if (evento.banner_url) {
            const img = new Image();
            img.onload = function() {
                // Se a imagem carregar com sucesso, substitui o placeholder
                $(`#${uniqueId}`).replaceWith(`<img src="${evento.banner_url}" alt="${evento.nome}" class="event-img">`);
            };
            img.onerror = function() {
                // Se falhar, mantém o placeholder colorido (já está renderizado)
                console.log(`Falha ao carregar imagem para o evento: ${evento.nome}`);
            };
            img.src = evento.banner_url;
        }
    });

    
    
    // Inicializa o carrossel após os eventos serem carregados
    initCarousel();
}

function aplicarFiltroAoDigitar(termo) {
    const termoNormalizado = termo.trim().toLowerCase();

    if (termoNormalizado === '') {
        renderizarEventos(todosEventos); // Retorna à lista original
        return;
    }

    const eventosFiltradosLocal = todosEventos.filter(evento =>
        evento.nome.toLowerCase().includes(termoNormalizado) ||
        (evento.descricao && evento.descricao.toLowerCase().includes(termoNormalizado)) ||
        (evento.localizacao && evento.localizacao.toLowerCase().includes(termoNormalizado))
    );

    renderizarEventos(eventosFiltradosLocal);
}

// Função para inicializar o carrossel
function initCarousel() {
    const carousel = document.querySelector('.events-carousel');
    if (!carousel) {
        console.error("Elemento do carrossel não encontrado");
        return;
    }

    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const carouselWrapper = document.querySelector('.events-carousel-wrapper');

    if (!prevBtn || !nextBtn || !carouselWrapper) {
        console.error("Elementos de navegação do carrossel não encontrados");
        return;
    }

    let position = 0;
    const gap = 20;
    let cardWidth = 0;
    let visibleCards = getVisibleCards();
    let totalCards = carousel.children.length;
    
    console.log(`Carrossel inicializado com ${totalCards} cards`);

    // Calcular a largura do card baseado no container
    function calculateCardWidth() {
        const containerWidth = carouselWrapper.offsetWidth;
        cardWidth = (containerWidth / visibleCards) - (gap * (visibleCards - 1) / visibleCards);
        
        // Aplicar largura aos cards
        document.querySelectorAll('.event-card').forEach(card => {
            card.style.minWidth = `${cardWidth}px`;
            card.style.maxWidth = `${cardWidth}px`;
        });
    }

    function getVisibleCards() {
        if (window.innerWidth >= 992) return 3;
        if (window.innerWidth >= 768) return 2;
        return 1;
    }

    function updateCarousel() {
        calculateCardWidth();
        carousel.style.transform = `translateX(${position}px)`;
        
        // Desabilita botões quando não há mais cards para mostrar
        prevBtn.disabled = position >= 0;
        nextBtn.disabled = position <= -((totalCards - visibleCards) * (cardWidth + gap));
        
        // Estiliza botões desabilitados
        prevBtn.style.opacity = prevBtn.disabled ? '0.5' : '1';
        prevBtn.style.cursor = prevBtn.disabled ? 'not-allowed' : 'pointer';
        nextBtn.style.opacity = nextBtn.disabled ? '0.5' : '1';
        nextBtn.style.cursor = nextBtn.disabled ? 'not-allowed' : 'pointer';
    }

    function handleResize() {
        const prevVisibleCards = visibleCards;
        visibleCards = getVisibleCards();
        
        if (prevVisibleCards !== visibleCards) {
            position = 0;
            calculateCardWidth();
        }
        
        updateCarousel();
    }

    prevBtn.addEventListener('click', function() {
        if (position < 0) {
            position += cardWidth + gap;
            if (position > 0) position = 0;
            updateCarousel();
        }
    });

    nextBtn.addEventListener('click', function() {
        const maxPosition = -((totalCards - visibleCards) * (cardWidth + gap));
        if (position > maxPosition) {
            position -= cardWidth + gap;
            if (position < maxPosition) position = maxPosition;
            updateCarousel();
        }
    });

    // Adiciona debounce ao redimensionamento
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(function() {
            handleResize();
        }, 250);
    });

    // Inicializa o carrossel
    handleResize();
}

