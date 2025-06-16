document.addEventListener('DOMContentLoaded', function() {
    // Variáveis globais
    let map;
    let marker;
    let currentLocation = {
      lat: -15.77972, // Coordenadas iniciais (Brasil)
      lng: -47.92972
    };
    let suggestionTimeout;

    // ——— pagamento habilitado?  (1 = sim / 0 = não)
    const pagamentoHabilitado = document.getElementById('pagamento_habilitado').value === '1';

    // Se o cliente NÃO pode cobrar:
    //   – força o checkbox "inscrição gratuita"
    //   – desabilita seu uso
    //   – oculta qualquer coluna de preços
    if (!pagamentoHabilitado) {
      inscricaoGratuita.checked = true;
      inscricaoGratuita.disabled = true;
      updatePriceFields();          // já esconde colunas de preço
    }

    // Configuração de sugestões para o campo de localização
    const localizacaoInput = document.getElementById('localizacao-input');
    const suggestionsContainer = document.getElementById('suggestions');
    
    // Configurar o mapa quando o modal for aberto
    document.getElementById('mapaModal').addEventListener('shown.bs.modal', function () {
      if (!map) {
        initMap();
      }
     
      // Centralize no local salvo, se existir
      if (document.getElementById('latitude').value && document.getElementById('longitude').value) {
        const lat = parseFloat(document.getElementById('latitude').value);
        const lng = parseFloat(document.getElementById('longitude').value);
        map.setView([lat, lng], 15);
       
        if (marker) {
          marker.setLatLng([lat, lng]);
        } else {
          marker = L.marker([lat, lng]).addTo(map);
        }
       
        // Mostrar detalhes do local
        showLocationDetails(lat, lng);
      }
    });
   
    // Inicializar o mapa
    function initMap() {
      map = L.map('mapa-container').setView([currentLocation.lat, currentLocation.lng], 13);
     
        L.tileLayer('https://tiles.stadiamaps.com/tiles/stay22/{z}/{x}/{y}{r}.png?api_key=5b05060b-8e26-4d1c-bcaa-306d76157824', {
          maxZoom: 20,
          attribution: '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a> &copy; OpenStreetMap contributors'
        }).addTo(map);
     
      // Adicionar marker no mapa se já existir localização
      if (document.getElementById('latitude').value && document.getElementById('longitude').value) {
        const lat = parseFloat(document.getElementById('latitude').value);
        const lng = parseFloat(document.getElementById('longitude').value);
        marker = L.marker([lat, lng]).addTo(map);
      }
     
      // Permitir clicar no mapa para selecionar local
      map.on('click', function(e) {
        const lat = e.latlng.lat;
        const lng = e.latlng.lng;
       
        // Atualizar ou criar marcador
        if (marker) {
          marker.setLatLng([lat, lng]);
        } else {
          marker = L.marker([lat, lng]).addTo(map);
        }
       
        showLocationDetails(lat, lng);
      });
    }
   
    // Mostrar detalhes do local selecionado
    function showLocationDetails(lat, lng) {
      document.getElementById('endereco-detalhes').classList.remove('d-none');
      document.getElementById('info-latitude').textContent = lat.toFixed(6);
      document.getElementById('info-longitude').textContent = lng.toFixed(6);
     
      // Fazer geocoding reverso para obter o endereço
        fetch(`https://api.stadiamaps.com/geocoding/v1/reverse?point.lat=${lat}&point.lon=${lng}&apikey=5b05060b-8e26-4d1c-bcaa-306d76157824`)
          .then(response => response.json())
          .then(data => {
            if (data && data.features && data.features.length > 0) {
              const label = data.features[0].properties.label;
              document.getElementById('endereco-completo').textContent = label;
              currentLocation = {
                lat: lat,
                lng: lng,
                address: label
              };
            }
          })
        .catch(error => {
          console.error('Erro ao obter endereço:', error);
          document.getElementById('endereco-completo').textContent = 'Endereço não disponível';
        });
    }
   
    // Buscar locais com base no texto digitado
    function searchPlaces(query, modalSearch = false) {
      const searchInput = modalSearch ? document.getElementById('modal-search-input') : localizacaoInput;
     
      if (query.length < 3) return;
     
        fetch(`https://api.stadiamaps.com/geocoding/v1/search?text=${encodeURIComponent(query)}&apikey=5b05060b-8e26-4d1c-bcaa-306d76157824`)
          .then(response => response.json())
          .then(data => {
          if (modalSearch) {
            // Se for busca no modal, centraliza o primeiro resultado no mapa
            if (data.features && data.features.length > 0) {
              const feature = data.features[0];
              const coords = feature.geometry.coordinates;
              const lat = coords[1];
              const lng = coords[0];
             
              map.setView([lat, lng], 15);
             
              if (marker) {
                marker.setLatLng([lat, lng]);
              } else {
                marker = L.marker([lat, lng]).addTo(map);
              }
             
              showLocationDetails(lat, lng);
            }
          } else {
            // Se for busca no campo, mostra sugestões
            suggestionsContainer.innerHTML = '';
           
            if (data.features && data.features.length > 0) {
              data.features.forEach(feature => {
                const coords = feature.geometry.coordinates;
                const label = feature.properties.label;

                const item = document.createElement('div');
                item.className = 'suggestion-item';
                item.textContent = label;
                item.addEventListener('click', function() {
                  localizacaoInput.value = label;
                  document.getElementById('latitude').value = coords[1];
                  document.getElementById('longitude').value = coords[0];
                  document.getElementById('link_mapa').value = `https://www.google.com/maps?q=${coords[1]},${coords[0]}`;
                  suggestionsContainer.style.display = 'none';
                });

                suggestionsContainer.appendChild(item);
              });
             
              suggestionsContainer.style.display = 'block';
            } else {
              suggestionsContainer.style.display = 'none';
            }
          }
        })
        .catch(error => {
          console.error('Erro na busca:', error);
        });
    }
   
    // Event listener para o campo de localização
    localizacaoInput.addEventListener('input', function() {
      const query = this.value.trim();
     
      // Limpar timeout anterior
      if (suggestionTimeout) {
        clearTimeout(suggestionTimeout);
      }
     
      // Esperar um pouco antes de buscar para evitar muitas requisições
      suggestionTimeout = setTimeout(() => {
        if (query.length >= 3) {
          searchPlaces(query);
        } else {
          suggestionsContainer.style.display = 'none';
        }
      }, 300);
    });
   
    // Esconder sugestões ao clicar fora
    document.addEventListener('click', function(e) {
      if (e.target !== localizacaoInput && !suggestionsContainer.contains(e.target)) {
        suggestionsContainer.style.display = 'none';
      }
    });
   
    // Buscar no modal
    document.getElementById('modal-search-btn').addEventListener('click', function() {
      const query = document.getElementById('modal-search-input').value.trim();
      if (query.length >= 3) {
        searchPlaces(query, true);
      }
    });
   
    // Tecla Enter no campo de busca do modal
    document.getElementById('modal-search-input').addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        document.getElementById('modal-search-btn').click();
      }
    });
   
    // Selecionar local do mapa
    document.getElementById('btn-selecionar-local').addEventListener('click', function() {
      if (currentLocation) {
        // Preencher campos com informações do local selecionado
        document.getElementById('latitude').value = currentLocation.lat;
        document.getElementById('longitude').value = currentLocation.lng;
        document.getElementById('localizacao-input').value = currentLocation.address || '';
       
        // Gerar link do Google Maps
        document.getElementById('link_mapa').value = `https://www.google.com/maps?q=${currentLocation.lat},${currentLocation.lng}`;
      }
    });
  });

  // Price masking functionality
document.addEventListener('DOMContentLoaded', function() {
  // Format number as Brazilian currency
  function formatAsCurrency(value) {
    const number = parseFloat(value);
    if (isNaN(number)) return '';
    
    return number.toLocaleString('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      minimumFractionDigits: 2
    });
  }
  
  // Apply mask to price inputs
  function applyPriceMask() {
    // Select all price inputs that haven't been masked yet
    document.querySelectorAll('input[name="preco_tipo[]"]:not([data-masked]), input[name^="lote_tipo_preco_"]:not([data-masked])').forEach(input => {
      // Mark as masked
      input.setAttribute('data-masked', 'true');
      
      // Create display element for formatted value
      const display = document.createElement('div');
      display.className = 'price-mask-display';
      display.style.position = 'absolute';
      display.style.top = '0';
      display.style.left = '0';
      display.style.width = '100%';
      display.style.height = '100%';
      display.style.backgroundColor = 'white';
      display.style.display = 'flex';
      display.style.alignItems = 'center';
      display.style.paddingLeft = '12px';
      display.style.paddingRight = '12px';
      display.style.pointerEvents = 'none';
      display.style.borderRadius = 'inherit';
      display.style.fontSize = 'inherit';
      display.style.color = 'inherit';
      display.style.fontFamily = 'inherit';
      display.style.zIndex = '1';
      
      // Make input container position relative
      const container = input.parentElement;
      if (window.getComputedStyle(container).position === 'static') {
        container.style.position = 'relative';
      }
      
      // Add display element to DOM
      container.appendChild(display);
      
      // Initially update display
      if (input.value) {
        display.textContent = formatAsCurrency(input.value);
        display.style.display = 'flex';
      } else {
        display.style.display = 'none';
      }
      
      // Show/hide display on focus/blur
      input.addEventListener('focus', function() {
        display.style.display = 'none';
      });
      
      input.addEventListener('blur', function() {
        if (this.value) {
          display.textContent = formatAsCurrency(this.value);
          display.style.display = 'flex';
        } else {
          display.style.display = 'none';
        }
      });
      
      // Update display when value changes
      input.addEventListener('input', function() {
        display.style.display = 'none';
      });
    });
  }
  
  // Apply price masks initially
  applyPriceMask();
  
  // Apply masks when new price fields are added
  const observer = new MutationObserver(function(mutations) {
    let shouldUpdate = false;
    
    mutations.forEach(function(mutation) {
      if (mutation.type === 'childList' && mutation.addedNodes.length) {
        shouldUpdate = true;
      }
    });
    
    if (shouldUpdate) {
      applyPriceMask();
    }
  });
  
  observer.observe(document.body, { childList: true, subtree: true });
  
  // Also apply masks when buttons are clicked that add new price fields
  ['#adicionar-tipo-inscricao', '#adicionar-lote'].forEach(function(selector) {
    const button = document.querySelector(selector);
    if (button) {
      button.addEventListener('click', function() {
        setTimeout(applyPriceMask, 100);
      });
    }
  });
  
  // Re-apply masks when the gratuity checkbox changes
  const gratuitoCheckbox = document.getElementById('inscricao_gratuita');
  if (gratuitoCheckbox) {
    gratuitoCheckbox.addEventListener('change', function() {
      setTimeout(applyPriceMask, 100);
    });
  }
});


  document.addEventListener('DOMContentLoaded', function() {
    // Controle de etapas
    const progressBar = document.getElementById('progress-bar');
    const steps = document.querySelectorAll('.step');
    let currentStep = 1;

// Atualizar barra de progresso e indicadores
function updateProgressBar(step) {
  const totalSteps = steps.length;
  const percent = (step / totalSteps) * 100;
  
  // Atualizar a barra de progresso
  progressBar.style.width = percent + '%';
  progressBar.setAttribute('aria-valuenow', percent);
  
  // Atualizar os indicadores de etapa
  document.querySelectorAll('.step-indicator').forEach((indicator, index) => {
    if (index + 1 < step) {
      indicator.classList.add('completed');
      indicator.classList.remove('active');
    } else if (index + 1 === step) {
      indicator.classList.add('active');
      indicator.classList.remove('completed');
    } else {
      indicator.classList.remove('active', 'completed');
    }
  });
}

    // Navegar para próxima etapa
    document.querySelectorAll('.next-step').forEach(button => {
      button.addEventListener('click', function() {
        const nextStep = parseInt(this.getAttribute('data-next'));
        
        // Esconder etapa atual
        document.getElementById(`step-${currentStep}`).style.display = 'none';
        
        // Mostrar próxima etapa
        document.getElementById(`step-${nextStep}`).style.display = 'block';
        
        // Atualizar etapa atual
        currentStep = nextStep;
        
        // Atualizar barra de progresso
        updateProgressBar(currentStep);
        
        // Rolar para o topo do formulário
        window.scrollTo({top: 0, behavior: 'smooth'});
      });
    });

    // Navegar para etapa anterior
    document.querySelectorAll('.prev-step').forEach(button => {
      button.addEventListener('click', function() {
        const prevStep = parseInt(this.getAttribute('data-prev'));
        
        // Esconder etapa atual
        document.getElementById(`step-${currentStep}`).style.display = 'none';
        
        // Mostrar etapa anterior
        document.getElementById(`step-${prevStep}`).style.display = 'block';
        
        // Atualizar etapa atual
        currentStep = prevStep;
        
        // Atualizar barra de progresso
        updateProgressBar(currentStep);
        
        // Rolar para o topo do formulário
        window.scrollTo({top: 0, behavior: 'smooth'});
      });
    });

    // Toggle price fields visibility
    const inscricaoGratuita = document.getElementById('inscricao_gratuita');
    const tiposContainer = document.getElementById('tipos-inscricao-container');
    const tiposList = document.getElementById('tipos-inscricao-list');
    
    // Toggle lotes visibility
    const habilitarLotes = document.getElementById('habilitar_lotes');
    const lotesSection = document.getElementById('lotes-section');
    
    function toggleLotesVisibility() {
      lotesSection.style.display = habilitarLotes.checked ? 'block' : 'none';
    }
    
    habilitarLotes.addEventListener('change', toggleLotesVisibility);
    
    // Verificar estado inicial da opção lotes
    toggleLotesVisibility();
    
    // Function to update price fields visibility and values
    function updatePriceFields() {
      const isGratuito = inscricaoGratuita.checked;
      
      // Manter o container visível sempre
      tiposContainer.style.display = 'block';
      
      // Selecionar todos os campos de preço e seus labels
      const precoFields = document.querySelectorAll('input[name="preco_tipo[]"]');
      const precoLabels = document.querySelectorAll('.tipo-inscricao-item .col-md-3');
      
      // Atualizar todos os campos de preço
      precoFields.forEach(field => {
        field.parentElement.style.display = isGratuito ? 'none' : 'block';
        if (isGratuito) {
          field.value = '0.00';
        }
      });
      
      // Atualizar todos os labels de preço
      precoLabels.forEach(label => {
        label.style.display = isGratuito ? 'none' : 'block';
      });

      // Atualizar os preços dos lotes também
      updateLotePriceFields();
    }
    
    // Verificar estado inicial
    updatePriceFields();
    
    // Adicionar event listener
    inscricaoGratuita.addEventListener('change', updatePriceFields);
  
    // Adicionar novo tipo de inscrição
    const addButton = document.getElementById('adicionar-tipo-inscricao');
    
    addButton.addEventListener('click', function() {
      const newItem = document.createElement('div');
      newItem.className = 'row mb-3 align-items-end tipo-inscricao-item';
      newItem.innerHTML = `
        <div class="col-md-5">
          <label class="form-label">Tipo de Inscrição</label>
          <input type="text" class="form-control border border-secondary bg-white" name="nome_tipo[]" 
                placeholder="Ex: Estudante, Profissional...">
          <input type="hidden" name="id_tipo[]" value="">
        </div>
        <div class="col-md-3" ${(!pagamentoHabilitado || inscricaoGratuita.checked) ? 'style="display:none;"' : ''}>
          <label class="form-label">Preço (R$)</label>
          <input type="number" step="0.01" class="form-control border border-secondary bg-white"
                name="preco_tipo[]" placeholder="0.00"
                ${!pagamentoHabilitado ? 'disabled' : ''}>
        </div>
        <div class="col-md-4">
          <button type="button" class="btn btn-outline-danger remover-tipo-inscricao" data-inscricoes="0">
            <i class="bi bi-trash"></i> Remover
          </button>
        </div>
      `;
      tiposList.appendChild(newItem);
      
      // Atualizar campos após adicionar um novo item
      updatePriceFields();
      // Atualizar os campos de preço dos lotes
      updateLotePriceFields();
    });
  
    // Remover tipo de inscrição
    tiposList.addEventListener('click', function(e) {
      if (e.target.classList.contains('remover-tipo-inscricao') || 
          e.target.closest('.remover-tipo-inscricao')) {
        const button = e.target.classList.contains('remover-tipo-inscricao') ? 
                      e.target : e.target.closest('.remover-tipo-inscricao');
        const row = button.closest('.tipo-inscricao-item');
        row.remove();
        
        // Atualizar campos de preço dos lotes
        updateLotePriceFields();
      }
    });

    // Gerenciamento de lotes
    const lotesContainer = document.getElementById('lotes-container');
    const btnAdicionarLote = document.getElementById('adicionar-lote');
    
    // Adicionar evento para alternar entre data e quantidade
    lotesContainer.addEventListener('change', function(e) {
      if (e.target.name && e.target.name.includes('lote_usar_data')) {
        const loteItem = e.target.closest('.lote-item');
        const datasDiv = loteItem.querySelector('.lote-datas');
        const qtdCheckbox = loteItem.querySelector('input[name^="lote_usar_qtd"]');
        
        if (e.target.checked) {
          datasDiv.style.display = 'flex';
          qtdCheckbox.checked = false;
          loteItem.querySelector('.lote-quantidade').style.display = 'none';
        } else {
          datasDiv.style.display = 'none';
        }
      }
      
      if (e.target.name && e.target.name.includes('lote_usar_qtd')) {
        const loteItem = e.target.closest('.lote-item');
        const qtdDiv = loteItem.querySelector('.lote-quantidade');
        const dataCheckbox = loteItem.querySelector('input[name^="lote_usar_data"]');
        
        if (e.target.checked) {
          qtdDiv.style.display = 'block';
          dataCheckbox.checked = false;
          loteItem.querySelector('.lote-datas').style.display = 'none';
        } else {
          qtdDiv.style.display = 'none';
        }
      }
    });
    
    // Adicionar novo lote
    btnAdicionarLote.addEventListener('click', function() {
      const lotesCount = document.querySelectorAll('.lote-item').length;
      const newLoteItem = document.createElement('div');
      newLoteItem.className = 'lote-item card mb-3';
      
      newLoteItem.innerHTML = `
        <div class="card-header bg-light d-flex justify-content-between align-items-center">
          <h6 class="mb-0">Lote ${lotesCount + 1}</h6>
          <button type="button" class="btn btn-sm btn-outline-danger remover-lote">
            <i class="bi bi-trash"></i> Remover
          </button>
        </div>
        <div class="card-body">
          <div class="row mb-3">
            <div class="col-md-6">
              <label class="form-label">Nome do Lote</label>
              <input type="text" class="form-control border border-secondary bg-white" name="lote_nome[]" placeholder="Ex: Lote ${lotesCount + 1}">
            </div>
            <div class="col-md-3">
              <label class="form-label">Ordem</label>
              <input type="number" class="form-control border border-secondary bg-white" name="lote_ordem[]" value="${lotesCount + 1}" min="1">
            </div>
          </div>
          
          <div class="row mb-3">
            <div class="col-md-6">
              <div class="form-check mb-2">
                <input type="checkbox" class="form-check-input border border-secondary" name="lote_usar_data[]" checked>
                <label class="form-check-label">Definir por período</label>
              </div>
              <div class="row lote-datas">
                <div class="col-md-6">
                  <label class="form-label">Data Início</label>
                  <input type="date" class="form-control border border-secondary bg-white" name="lote_data_inicio[]">
                </div>
                <div class="col-md-6">
                  <label class="form-label">Data Fim</label>
                  <input type="date" class="form-control border border-secondary bg-white" name="lote_data_fim[]">
                </div>
              </div>
            </div>
            <div class="col-md-6">
              <div class="form-check mb-2">
                <input type="checkbox" class="form-check-input border border-secondary" name="lote_usar_qtd[]">
                <label class="form-check-label">Definir por quantidade</label>
              </div>
              <div class="lote-quantidade" style="display: none;">
                <label class="form-label">Quantidade máxima</label>
                <input type="number" class="form-control border border-secondary bg-white" name="lote_qtd_maxima[]" min="1" placeholder="Limite de inscritos">
              </div>
            </div>
          </div>
          
          <hr>
          <h6 class="mb-3">Preços por tipo de inscrição:</h6>
          <div class="lote-precos">
            <!-- Os campos de preço serão preenchidos pela função updateLotePriceFields -->
          </div>
        </div>
      `;
      
      lotesContainer.appendChild(newLoteItem);
      updateLoteHeaders();
      updateLotePriceFields();
    });
    
    // Remover lote
    lotesContainer.addEventListener('click', function(e) {
      if (e.target.classList.contains('remover-lote') || e.target.closest('.remover-lote')) {
        const button = e.target.classList.contains('remover-lote') ? 
                      e.target : e.target.closest('.remover-lote');
        const loteItem = button.closest('.lote-item');
        
        if (document.querySelectorAll('.lote-item').length > 1) {
          loteItem.remove();
          updateLoteHeaders();
        } else {
          alert('É necessário manter pelo menos um lote.');
        }
      }
    });
    
    // Atualizar cabeçalhos dos lotes
    function updateLoteHeaders() {
      const lotes = document.querySelectorAll('.lote-item');
      lotes.forEach((lote, index) => {
        lote.querySelector('h6').textContent = `Lote ${index + 1}`;
      });
    }
    
    // Gerar campos de preço para tipos de inscrição em cada lote
    function updateLotePriceFields() {
      const lotePrecosDivs = document.querySelectorAll('.lote-precos');
      const isGratuito = inscricaoGratuita.checked;
      const colDisplay = (!pagamentoHabilitado || isGratuito) ? 'none' : '';
      
      // Para cada div de preços de lote
      lotePrecosDivs.forEach((lotePrecos, loteIndex) => {
        let html = '';
        const tiposInscricao = document.querySelectorAll('input[name="nome_tipo[]"]');
        
        if (tiposInscricao.length === 0) {
          html = '<p class="text-warning">Defina os tipos de inscrição primeiro.</p>';
        } else {
          tiposInscricao.forEach((tipo, index) => {
            const tipoNome = tipo.value || `Tipo ${index + 1}`;
            const precoDefault = isGratuito ? '0.00' : '';
            
            html += `
              <div class="row mb-2 align-items-center">
                <div class="col-md-6">
                  <label class="form-label">${tipoNome}</label>
                  <input type="hidden" name="lote_tipo_index_${loteIndex}[]" value="${index}">
                </div>
                <div class="col-md-4" style="display:${colDisplay};">
                  <label class="form-label">Preço (R$)</label>
                  <input type="number" step="0.01" class="form-control border border-secondary bg-white" 
                         name="lote_tipo_preco_${loteIndex}_${index}" 
                         placeholder="0.00" value="${precoDefault}"
                         ${!pagamentoHabilitado ? 'disabled' : ''}>
                </div>
              </div>
            `;
          });
        }
        
        lotePrecos.innerHTML = html;
      });
    }

    // Inicializar os campos de preço para o primeiro lote
    updateLotePriceFields();
    
    // Validação do formulário antes de enviar
    document.querySelector('form').addEventListener('submit', function(e) {
      const tiposItems = tiposList.querySelectorAll('.tipo-inscricao-item');
      
      // Validar tipos de inscrição
      if (tiposItems.length === 0) {
        e.preventDefault();
        alert('Você precisa definir pelo menos um tipo de inscrição.');
        return;
      }
      
      // Verificar se todos os campos de tipos estão preenchidos
      let tipoVazio = false;
      tiposItems.forEach(item => {
        const nomeTipo = item.querySelector('input[name="nome_tipo[]"]');
        if (!nomeTipo.value.trim()) {
          tipoVazio = true;
        }
      });
      
      if (tipoVazio) {
        e.preventDefault();
        alert('Todos os tipos de inscrição precisam ter um nome.');
        return;
      }
      
      // Validar lotes apenas se eles estiverem habilitados
      if (habilitarLotes.checked) {
        const loteItems = lotesContainer.querySelectorAll('.lote-item');
        
        // Validar lotes
        if (loteItems.length === 0) {
          e.preventDefault();
          alert('Você precisa definir pelo menos um lote.');
          return;
        }
        
        // Verificar se todos os lotes possuem nome e critério de definição
        let loteInvalido = false;
        loteItems.forEach(item => {
          const nomeLote = item.querySelector('input[name="lote_nome[]"]');
          const usaData = item.querySelector('input[name^="lote_usar_data"]').checked;
          const usaQtd = item.querySelector('input[name^="lote_usar_qtd"]').checked;
          
          if (!nomeLote.value.trim()) {
            loteInvalido = true;
          }
          
          if (usaData) {
            const dataInicio = item.querySelector('input[name="lote_data_inicio[]"]');
            const dataFim = item.querySelector('input[name="lote_data_fim[]"]');
            
            if (!dataInicio.value || !dataFim.value) {
              loteInvalido = true;
            }
          }
          
          if (usaQtd) {
            const qtdMaxima = item.querySelector('input[name="lote_qtd_maxima[]"]');
            
            if (!qtdMaxima.value || parseInt(qtdMaxima.value) <= 0) {
              loteInvalido = true;
            }
          }
          
          if (!usaData && !usaQtd) {
            loteInvalido = true;
          }
        });
        
        if (loteInvalido) {
          e.preventDefault();
          alert('Todos os lotes precisam ter um nome e um critério de definição (período ou quantidade) completo.');
          return;
        }
      }
    });
  });


