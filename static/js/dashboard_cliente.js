/**
 * dashboard_cliente.js
 *
 * Este arquivo contém a lógica JavaScript para o painel de gerenciamento do cliente.
 * Ele lida com:
 * - Botão de toggle para submissão global.
 * - Carregamento dinâmico de estados e cidades (API IBGE).
 * - Aplicação de filtros de estado e cidade.
 * - Busca e atualização do estado das configurações do cliente (check-in, feedback, certificado).
 * - Manipulação de botões de toggle para configurações individuais.
 * - Geração e exibição de relatório de mensagens.
 * - Funcionalidades para copiar mensagem e enviar via WhatsApp.
 * - Gerenciamento do modal de geração de links de cadastro para eventos:
 * - Carregamento de eventos.
 * - Exibição de links existentes para um evento.
 * - Geração de novos links (com slug customizado ou token).
 * - Exclusão de links existentes.
 * - Copiar e compartilhar links gerados.
 * - Efeitos visuais e interatividade para o botão de exportar check-ins.
 * - Geração dinâmica de campos de upload para patrocinadores.
 * - Filtragem de check-ins por oficina.
 * - Toggle para o QR Code de credenciamento do evento.
 *
 * IMPORTANTE: Este script depende de variáveis globais de URL (ex: URL_CONFIG_CLIENTE_ATUAL)
 * que devem ser definidas em um bloco <script> no template HTML antes de carregar este arquivo.
 * Exemplo no HTML:
 * <script>
 * var URL_CONFIG_CLIENTE_ATUAL = "/rota/para/config_cliente_atual";
 * // ... outras URLs
 * var ESTADO_FILTER_INICIAL = "SP"; // Exemplo
 * var CIDADE_FILTER_INICIAL = "São Paulo"; // Exemplo
 * </script>
*/

// Token CSRF lido do meta tag
var csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';


// Carregamento inicial - Estados, cidades e configurações
document.addEventListener('DOMContentLoaded', function () {
  // 1. Buscar estados do IBGE e configurar filtros
  const estadoSelect = document.getElementById('estadoSelect');
  const cidadeSelect = document.getElementById('cidadeSelect');

  // Use as variáveis globais definidas no HTML se existirem, senão use string vazia.
  const estadoFilter = typeof ESTADO_FILTER_INICIAL !== 'undefined' ? ESTADO_FILTER_INICIAL : "";
  const cidadeFilter = typeof CIDADE_FILTER_INICIAL !== 'undefined' ? CIDADE_FILTER_INICIAL : "";

  if (estadoSelect && cidadeSelect) {
    fetch('https://servicodados.ibge.gov.br/api/v1/localidades/estados')
      .then(response => response.json())
      .then(data => {
        data.sort((a, b) => a.nome.localeCompare(b.nome));
        data.forEach(estado => {
          const option = document.createElement('option');
          option.value = estado.sigla;
          option.text = estado.nome;
          if (estado.sigla === estadoFilter) {
            option.selected = true;
          }
          estadoSelect.add(option);
        });
        // Se um estado já estiver selecionado (ex: pelo filtro), dispara o evento change para carregar cidades
        if (estadoSelect.value) {
          estadoSelect.dispatchEvent(new Event('change'));
        }
      })
      .catch(error => console.error('Erro ao buscar estados:', error));

    // Evento de mudança de estado para carregar cidades
    estadoSelect.addEventListener('change', function () {
      const uf = this.value;
      cidadeSelect.innerHTML = '<option value="">Todas as Cidades</option>'; // Reseta cidades
      if (uf) {
        fetch(`https://servicodados.ibge.gov.br/api/v1/localidades/estados/${uf}/municipios`)
          .then(response => response.json())
          .then(data => {
            data.sort((a, b) => a.nome.localeCompare(b.nome));
            data.forEach(cidade => {
              const option = document.createElement('option');
              option.value = cidade.nome;
              option.text = cidade.nome;
              if (cidade.nome === cidadeFilter) {
                option.selected = true;
              }
              cidadeSelect.add(option);
            });
          })
          .catch(error => console.error('Erro ao buscar cidades:', error));
      }
    });
  } else {
    console.warn("Elementos select de estado ou cidade não encontrados.");
  }
  var URL_EVENTO_CONFIG_BASE =
    typeof window.URL_EVENTO_CONFIG_BASE !== "undefined"
      ? window.URL_EVENTO_CONFIG_BASE
      : "/api/configuracao_evento";
  var EVENTO_ATUAL = null;

  var fieldButtonMap = {
    "permitir_checkin_global": document.getElementById("btnToggleCheckin"),
    "habilitar_qrcode_evento_credenciamento": document.getElementById("btnToggleQrCredenciamento"),
    "habilitar_feedback": document.getElementById("btnToggleFeedback"),
    "habilitar_certificado_individual": document.getElementById("btnToggleCertificado"),
    "mostrar_taxa": document.getElementById("btnToggleMostrarTaxa"),
    "obrigatorio_nome": document.getElementById("btnToggleObrigatorioNome"),
    "obrigatorio_cpf": document.getElementById("btnToggleObrigatorioCpf"),
    "obrigatorio_email": document.getElementById("btnToggleObrigatorioEmail"),
    "obrigatorio_senha": document.getElementById("btnToggleObrigatorioSenha"),
    "obrigatorio_formacao": document.getElementById("btnToggleObrigatorioFormacao")
  };

  var configButtons = Object.values(fieldButtonMap).filter(btn => btn);
  var eventoSelect = document.getElementById("selectConfigEvento");
  var previewEventoBtn = document.getElementById("previewEventoBtn");
  function setConfigButtonsState(enabled) {
    configButtons.forEach(btn => {
      btn.disabled = !enabled;
    });
  }
  if (eventoSelect) {
    const updatePreview = () => {
      if (previewEventoBtn) {
        const base = previewEventoBtn.dataset.baseUrl || previewEventoBtn.href;
        previewEventoBtn.href = `${base}${encodeURIComponent(eventoSelect.value)}`;
      }
    };

    // Se não houver valor inicial, pega a primeira opção disponível
    if (!eventoSelect.value) {
      const primeiraOpcao = Array.from(eventoSelect.options).find(opt => opt.value);
      if (primeiraOpcao) {
        eventoSelect.value = primeiraOpcao.value;
      }
    }

    EVENTO_ATUAL = eventoSelect.value;
    setConfigButtonsState(Boolean(EVENTO_ATUAL));

    if (EVENTO_ATUAL) {
      updatePreview();
      carregarConfiguracao(EVENTO_ATUAL);
    }

    eventoSelect.addEventListener("change", function () {
      EVENTO_ATUAL = this.value;
      setConfigButtonsState(Boolean(EVENTO_ATUAL));
      if (!EVENTO_ATUAL) return;
      updatePreview();
      carregarConfiguracao(EVENTO_ATUAL);
    });
  }

  function carregarConfiguracao(eventoId) {
    if (!eventoId) return;
    fetch(`${URL_EVENTO_CONFIG_BASE}/${eventoId}`, { credentials: "include" })
      .then(response => response.json())
      .then(data => {
        if (!data.success) return;
        Object.entries(fieldButtonMap).forEach(([campo, btn]) => {
          if (btn) atualizarBotao(btn, data[campo]);
        });
      });
  }

  var toggleButtons = Object.values(fieldButtonMap);
  toggleButtons.forEach(button => {
    if (!button) return;
    const campo = button.dataset.field;
    if (!campo) return;

    button.addEventListener('click', function () {
      if (!EVENTO_ATUAL) {
        alert('Selecione um evento');
        return;
      }

      fetch(`${URL_EVENTO_CONFIG_BASE}/${EVENTO_ATUAL}/${campo}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': csrfToken
        },
        credentials: 'include'
      })
        .then(res => {
          if (res.status === 403) {
            alert('Você não tem permissão para alterar este evento.');
            return;
          }
          return res.json();
        })
        .then(data => {
          if (!data) return;
          if (data.success) {
            atualizarBotao(button, data.value);
          } else {
            alert('Falha ao atualizar configuração: ' + (data.message || 'Erro desconhecido.'));
          }
        });
    });
  });

});


document.addEventListener('DOMContentLoaded', function () {
  const selectReview = document.getElementById('selectReviewModel');
  if (selectReview) {
    selectReview.addEventListener('change', function () {
      const url = this.dataset.updateUrl;
      if (!url) return;
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        credentials: 'include',
        body: JSON.stringify({ review_model: this.value })
      })
        .then(r => r.json())
        .then(data => {
          if (data.success) alert('Configuração atualizada!');
        });
    });
  }

  const inputMin = document.getElementById('inputRevisoresMin');
  if (inputMin) {
    inputMin.addEventListener('change', function () {
      const url = this.dataset.updateUrl;
      if (!url) return;
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        credentials: 'include',
        body: JSON.stringify({ value: this.value })
      });
    });
  }

  const inputMax = document.getElementById('inputRevisoresMax');
  if (inputMax) {
    inputMax.addEventListener('change', function () {
      const url = this.dataset.updateUrl;
      if (!url) return;
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        credentials: 'include',
        body: JSON.stringify({ value: this.value })
      });
    });
  }

  const inputPrazo = document.getElementById('inputPrazoParecer');
  if (inputPrazo) {
    inputPrazo.addEventListener('change', function () {
      const url = this.dataset.updateUrl;
      if (!url) return;
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        credentials: 'include',
        body: JSON.stringify({ value: this.value })
      });
    });
  }

  const inputMaxTrab = document.getElementById('inputMaxTrabalhosRevisor');
  if (inputMaxTrab) {
    inputMaxTrab.addEventListener('change', function () {
      const url = this.dataset.updateUrl;
      if (!url) return;
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        credentials: 'include',
        body: JSON.stringify({ value: this.value })
      });
    });
  }

  const inputAllowed = document.getElementById('inputAllowedFiles');
  if (inputAllowed) {
    inputAllowed.addEventListener('change', function () {
      const url = this.dataset.updateUrl;
      if (!url) return;
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        credentials: 'include',
        body: JSON.stringify({ value: this.value })
      });
    });
  }

  const selectFormulario = document.getElementById('selectFormularioSubmissao');
  if (selectFormulario) {
    selectFormulario.addEventListener('change', function () {
      const url = this.dataset.updateUrl;
      if (!url) return;
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        credentials: 'include',
        body: JSON.stringify({ formulario_id: this.value || null })
      });
    });
  }
});

// Funções auxiliares
function atualizarBotao(btn, valorAtivo) {
  if (!btn) return;
  const label = btn.dataset.label;
  if (valorAtivo) {
    btn.classList.remove("btn-danger", "btn-outline-danger");
    btn.classList.add("btn-success");
    btn.textContent = label ? `${label} - Ativo` : "Ativo";
  } else {
    btn.classList.remove("btn-success", "btn-outline-success");
    btn.classList.add("btn-danger");
    btn.textContent = label ? `${label} - Desativado` : "Desativado";
  }
}


function copiarMensagem() {
  const textoRelatorioEl = document.getElementById("textoRelatorio");
  if (!textoRelatorioEl) {
    alert("Elemento do relatório não encontrado.");
    return;
  }
  let texto = textoRelatorioEl.value;
  navigator.clipboard.writeText(texto).then(() => {
    alert("Mensagem copiada com sucesso!");
  }).catch(err => {
    alert("Falha ao copiar mensagem: " + err);
    console.error("Falha ao copiar mensagem:", err);
  });
}

function enviarWhatsAppRelatorio() {
  const textoRelatorioEl = document.getElementById("textoRelatorio");
  if (!textoRelatorioEl) {
    alert("Elemento do relatório não encontrado.");
    return;
  }
  let mensagem = textoRelatorioEl.value;
  let url = "https://api.whatsapp.com/send?text=" + encodeURIComponent(mensagem);
  window.open(url, "_blank");
}

// Configuração do modal de geração de link
document.querySelectorAll('.gerar-link-btn').forEach(btn => {
  btn.addEventListener("click", function () {
    const modalElement = document.getElementById("modalLinkCadastro");
    if (modalElement) {
      const modalInstance = bootstrap.Modal.getOrCreateInstance(modalElement); // Ensure compatibility with Bootstrap 5
      modalInstance.show();
    }

    // Limpar campos e seleções atuais
    const slugInput = document.getElementById("slugInput");
    if (slugInput) slugInput.value = "";

    const linkCadastroInput = document.getElementById("linkCadastro");
    if (linkCadastroInput) linkCadastroInput.value = "";

    const linksExistentesContainer = document.getElementById("linksExistentesContainer");
    if (linksExistentesContainer) linksExistentesContainer.style.display = "none";

    const eventoSelectModal = document.getElementById("eventoSelectModal"); // Assumindo ID específico para o select no modal

    if (!eventoSelectModal) {
      console.error("Select de eventos 'eventoSelectModal' não encontrado no modal.");
      alert("Erro de configuração interna do modal de links.");
      return;
    }

    if (typeof URL_GERAR_LINK === 'undefined' && typeof URL_LISTAR_EVENTOS_MODAL === 'undefined') {
      alert("Erro de configuração: URL para carregar eventos não definida.");
      console.error("URL_GERAR_LINK ou URL_LISTAR_EVENTOS_MODAL não está definida.");
      return;
    }
    // Use URL_LISTAR_EVENTOS_MODAL se definida, senão fallback para URL_GERAR_LINK (GET)
    const urlParaListarEventos = typeof URL_LISTAR_EVENTOS_MODAL !== 'undefined' ? URL_LISTAR_EVENTOS_MODAL : URL_GERAR_LINK;

    fetch(urlParaListarEventos)
      .then(response => {
        if (!response.ok) {
          throw new Error('Erro ao carregar eventos: ' + response.statusText + ' (' + response.status + ')');
        }
        return response.json();
      })
      .then(data => {
        eventoSelectModal.options.length = 0; // Limpa opções existentes
        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = "-- Selecione um Evento --";
        eventoSelectModal.appendChild(defaultOption);

        if (data.eventos && data.eventos.length > 0) {
          data.eventos.forEach(evento => {
            const option = document.createElement("option");
            option.value = evento.id;
            option.textContent = evento.nome;
            eventoSelectModal.appendChild(option);
          });
        } else {
          console.warn("Nenhum evento disponível para gerar links ou a estrutura de dados é inesperada:", data);
          const noEventOption = document.createElement("option");
          noEventOption.value = "";
          noEventOption.textContent = "Nenhum evento encontrado";
          noEventOption.disabled = true;
          eventoSelectModal.appendChild(noEventOption);
        }
      })
      .catch(error => {
        console.error("Erro ao carregar eventos para o modal:", error);
        alert("Erro ao carregar os eventos para o modal. Tente novamente mais tarde.");
        eventoSelectModal.options.length = 0;
        const errorOption = document.createElement("option");
        errorOption.value = "";
        errorOption.textContent = "Erro ao carregar eventos";
        eventoSelectModal.appendChild(errorOption);
      });
  });
});

// Função para carregar links existentes quando um evento é selecionado no modal
// Evitamos redeclaração verificando se a variável já existe
if (typeof window.eventoSelectModalGlobal === 'undefined') {
  window.eventoSelectModalGlobal = document.getElementById("eventoSelectModal"); // ID do select de eventos DENTRO DO MODAL
}
if (window.eventoSelectModalGlobal) {
  window.eventoSelectModalGlobal.addEventListener("change", function () {
    const eventoId = this.value;
    // Passando o ID do evento para a função que atualiza a tabela
    if (eventoId) {
      atualizarTabelaLinks(eventoId, 'linksExistentesList', 'linksExistentesTable', 'linksExistentesLoader', 'linksExistentesEmpty', 'linksExistentesContainer');
    } else {
      const linksContainer = document.getElementById("linksExistentesContainer");
      if (linksContainer) linksContainer.style.display = "none";
    }
  });
} else {
  console.warn("Elemento select com ID 'eventoSelectModal' para modal de links não encontrado globalmente.");
}

// Botão para confirmar geração de link DENTRO DO MODAL
var btnConfirmarGeracaoLink = document.getElementById("gerarLinkConfirm");
if (btnConfirmarGeracaoLink) {
  btnConfirmarGeracaoLink.addEventListener("click", function () {
    const eventoSelectEl = document.getElementById("eventoSelectModal"); // Select DENTRO DO MODAL
    const slugInputEl = document.getElementById("slugInput"); // Input de slug DENTRO DO MODAL

    if (!eventoSelectEl || !slugInputEl) {
      alert("Erro: Elementos do formulário não encontrados no modal.");
      return;
    }
    const eventoId = eventoSelectEl.value;
    const slugCustomizado = slugInputEl.value;

    if (!eventoId) {
      alert("Por favor, selecione um evento!");
      return;
    }

    btnConfirmarGeracaoLink.disabled = true;
    btnConfirmarGeracaoLink.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Processando...';

    if (typeof URL_GERAR_LINK === 'undefined') {
      alert("Erro de configuração: URL para gerar link não definida.");
      console.error("URL_GERAR_LINK não está definida.");
      btnConfirmarGeracaoLink.disabled = false;
      btnConfirmarGeracaoLink.innerHTML = '<i class="bi bi-magic me-2"></i>Gerar Link';
      return;
    }

    fetch(URL_GERAR_LINK, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrfToken
      },
      body: JSON.stringify({
        evento_id: eventoId,
        slug_customizado: slugCustomizado
      })
    })
      .then(response => response.json())
      .then(data => {
        btnConfirmarGeracaoLink.disabled = false;
        btnConfirmarGeracaoLink.innerHTML = '<i class="bi bi-magic me-2"></i>Gerar Link';

        const linkCadastroInput = document.getElementById("linkCadastro"); // Input para exibir link gerado
        const linkGeradoContainer = document.getElementById("linkGeradoContainer"); // Container do link gerado

        if (!linkCadastroInput || !linkGeradoContainer) {
          console.error("Elementos 'linkCadastro' ou 'linkGeradoContainer' não encontrados.");
          return;
        }

        if (data.success) {
          linkCadastroInput.value = data.link;
          linkGeradoContainer.style.display = "block";

          atualizarTabelaLinks(eventoId,
            'linksExistentesListModal', 'linksExistentesTableModal',
            'linksExistentesLoaderModal', 'linksExistentesEmptyModal',
            'linksExistentesContainerModal');

          const alertContainer = linkGeradoContainer.parentNode; // Para inserir o alerta próximo
          const alertSuccess = document.createElement("div");
          alertSuccess.className = "alert alert-success alert-dismissible fade show mt-3";
          alertSuccess.role = "alert";
          alertSuccess.innerHTML = `
                  <strong><i class="bi bi-check-circle me-2"></i>Sucesso!</strong> Link gerado: ${data.link}
                  <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                `;
          alertContainer.insertBefore(alertSuccess, linkGeradoContainer.nextSibling);

          setTimeout(() => {
            if (alertSuccess.parentNode) { // Verifica se o alerta ainda existe antes de remover
              alertSuccess.remove();
            }
          }, 5000); // Aumentado para 5s
        } else {
          alert("Erro ao gerar link: " + (data.message || "Não foi possível gerar o link. Verifique o console para detalhes."));
          console.error("Erro ao gerar link:", data);
        }
      })
      .catch(error => {
        console.error("Erro de comunicação ao gerar o link:", error);
        btnConfirmarGeracaoLink.disabled = false;
        btnConfirmarGeracaoLink.innerHTML = '<i class="bi bi-magic me-2"></i>Gerar Link';
        alert("Erro ao comunicar com o servidor para gerar o link. Tente novamente.");
      });
  });
} else {
  console.warn("Botão com ID 'gerarLinkConfirm' não encontrado.");
}

// Função genérica para atualizar uma tabela de links
function atualizarTabelaLinks(eventoId, listId, tableId, loaderId, emptyId, containerId) {
  const linksContainer = document.getElementById(containerId);
  const linksTableBody = document.getElementById(listId);
  const linksLoader = document.getElementById(loaderId);
  const linksEmpty = document.getElementById(emptyId);
  const linksTableElement = document.getElementById(tableId);

  if (!linksContainer || !linksTableBody || !linksLoader || !linksEmpty || !linksTableElement) {
    console.error(`Um ou mais elementos para atualizar a tabela de links (container: ${containerId}) não foram encontrados.`);
    return;
  }

  linksContainer.style.display = "block";
  linksLoader.style.display = "block";
  linksTableElement.style.display = "none";
  linksEmpty.style.display = "none";
  linksTableBody.innerHTML = "";

  if (typeof URL_GERAR_LINK === 'undefined' && typeof URL_LISTAR_LINKS_EVENTO === 'undefined') {
    alert("Erro de configuração: URL para listar links não definida.");
    console.error("URL_GERAR_LINK ou URL_LISTAR_LINKS_EVENTO não está definida.");
    linksLoader.style.display = "none";
    linksEmpty.textContent = "Erro de configuração ao carregar links.";
    linksEmpty.style.display = "block";
    return;
  }
  // Use URL_LISTAR_LINKS_EVENTO se definida, senão fallback para URL_GERAR_LINK (GET com evento_id)
  const urlParaListarLinks = typeof URL_LISTAR_LINKS_EVENTO !== 'undefined' ? `${URL_LISTAR_LINKS_EVENTO}?evento_id=${eventoId}` : `${URL_GERAR_LINK}?evento_id=${eventoId}`;

  fetch(urlParaListarLinks)
    .then(response => {
      if (!response.ok) {
        throw new Error(`Erro ao carregar links existentes (${response.status}): ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
      linksLoader.style.display = "none";
      if (data.links && data.links.length > 0) {
        data.links.forEach(link => {
          const row = linksTableBody.insertRow();

          const slugCell = row.insertCell();
          const slugSpan = document.createElement("span");
          slugSpan.className = "d-inline-block text-truncate";
          slugSpan.style.maxWidth = "250px"; // Ajuste conforme necessário
          slugSpan.textContent = link.slug || `Token: ${(link.token || 'N/A').substring(0, 8)}...`;
          slugSpan.title = link.slug || link.token || 'Link sem identificador';
          slugCell.appendChild(slugSpan);

          const dataCell = row.insertCell();
          try {
            const dataCriacao = new Date(link.criado_em);
            dataCell.textContent = dataCriacao.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
          } catch (e) {
            dataCell.textContent = "Data inválida";
            console.warn("Data de criação inválida para o link:", link);
          }

          const acoesCell = row.insertCell();
          acoesCell.className = "d-flex flex-wrap gap-1 justify-content-end"; // flex-wrap para mobile

          // Botão copiar
          const btnCopiar = document.createElement("button");
          btnCopiar.className = "btn btn-sm btn-outline-primary";
          btnCopiar.innerHTML = '<i class="bi bi-clipboard"></i>';
          btnCopiar.title = "Copiar link";
          btnCopiar.addEventListener("click", function () {
            navigator.clipboard.writeText(link.url).then(() => {
              btnCopiar.innerHTML = '<i class="bi bi-check-lg"></i>'; // Ícone maior
              setTimeout(() => { btnCopiar.innerHTML = '<i class="bi bi-clipboard"></i>'; }, 2000);
            }).catch(err => console.error("Falha ao copiar link:", err));
          });

          // Botão WhatsApp
          const btnWhatsapp = document.createElement("a");
          btnWhatsapp.className = "btn btn-sm btn-outline-success";
          btnWhatsapp.innerHTML = '<i class="bi bi-whatsapp"></i>';
          btnWhatsapp.title = "Compartilhar via WhatsApp";
          btnWhatsapp.href = `https://api.whatsapp.com/send?text=${encodeURIComponent("Olá! Cadastre-se no evento através deste link: " + link.url)}`;
          btnWhatsapp.target = "_blank";

          // Botão excluir
          const btnExcluir = document.createElement("button");
          btnExcluir.className = "btn btn-sm btn-outline-danger";
          btnExcluir.innerHTML = '<i class="bi bi-trash"></i>';
          btnExcluir.title = "Excluir link";
          btnExcluir.addEventListener("click", function () {
            if (confirm("Tem certeza que deseja excluir este link? Esta ação não pode ser desfeita.")) {
              if (typeof URL_EXCLUIR_LINK === 'undefined') {
                alert("Erro de configuração: URL para excluir link não definida.");
                console.error("URL_EXCLUIR_LINK não está definida.");
                return;
              }
              fetch(URL_EXCLUIR_LINK, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                  "X-Requested-With": "XMLHttpRequest",
                  "X-CSRFToken": csrfToken
                },
                body: JSON.stringify({ link_id: link.id })
              })
                .then(response => response.json())
                .then(deleteData => {
                  if (deleteData.success) {
                    row.remove();
                    if (linksTableBody.children.length === 0) {
                      linksTableElement.style.display = "none";
                      linksEmpty.style.display = "block";
                    }
                    // Pequeno feedback visual ou log
                    console.log("Link excluído com sucesso:", link.id);
                  } else {
                    alert("Erro ao excluir o link: " + (deleteData.message || "Erro desconhecido."));
                    console.error("Erro ao excluir link:", deleteData);
                  }
                })
                .catch(error => {
                  console.error("Erro de comunicação ao excluir link:", error);
                  alert("Erro ao tentar excluir o link. Tente novamente.");
                });
            }
          });

          acoesCell.appendChild(btnCopiar);
          acoesCell.appendChild(btnWhatsapp);
          acoesCell.appendChild(btnExcluir);
        });
        linksTableElement.style.display = "table";
      } else {
        linksEmpty.textContent = "Nenhum link encontrado para este evento.";
        linksEmpty.style.display = "block";
      }
    })
    .catch(error => {
      console.error(`Erro ao carregar links para ${containerId}:`, error);
      linksLoader.style.display = "none";
      linksEmpty.textContent = "Erro ao carregar os links. Tente novamente.";
      linksEmpty.style.display = "block";
    });
}

function copiarLinkGerado() { // Renomeada para evitar conflito e ser mais específica
  const linkInput = document.getElementById("linkCadastro"); // Input onde o link gerado é exibido
  if (!linkInput) {
    console.error("Elemento 'linkCadastro' para copiar não encontrado.");
    return;
  }
  linkInput.select();
  linkInput.setSelectionRange(0, 99999); // Para mobile

  try {
    document.execCommand("copy");
    // Feedback visual no botão ao lado do input (se existir)
    const btnCopy = document.getElementById("btnCopiarLinkGerado"); // Assumindo um ID para este botão
    if (btnCopy) {
      const originalHTML = btnCopy.innerHTML;
      btnCopy.innerHTML = '<i class="bi bi-check-lg"></i> Copiado!';
      setTimeout(() => { btnCopy.innerHTML = originalHTML; }, 2000);
    } else {
      alert("Link copiado para a área de transferência!"); // Fallback se o botão não tiver ID específico
    }
  } catch (err) {
    console.error('Falha ao copiar o link automaticamente: ', err);
    alert('Falha ao copiar. Por favor, copie manualmente.');
  }
}
// Adicionar listener ao botão de copiar link gerado, se ele existir
var btnCopiarLinkGeradoEl = document.getElementById("btnCopiarLinkGerado");

// =============================================================================
// FUNCIONALIDADES PARA ENVIO DE EMAILS PARA REVISORES
// =============================================================================

// Função para copiar código do revisor
function copiarCodigoRevisor(codigo) {
  navigator.clipboard.writeText(codigo).then(() => {
    // Mostrar feedback visual
    const event = new CustomEvent('showToast', {
      detail: {
        message: 'Código copiado com sucesso!',
        type: 'success'
      }
    });
    document.dispatchEvent(event);
  }).catch(err => {
    console.error('Falha ao copiar código:', err);
    alert('Falha ao copiar código. Tente novamente.');
  });
}

// Função para enviar email individual
async function enviarEmailIndividual(candId, email) {
  try {
    const response = await fetch(`/revisor/send_email_individual/${candId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      }
    });

    const data = await response.json();

    if (data.success) {
      const event = new CustomEvent('showToast', {
        detail: {
          message: data.message,
          type: 'success'
        }
      });
      document.dispatchEvent(event);
    } else {
      const event = new CustomEvent('showToast', {
        detail: {
          message: data.message || 'Erro ao enviar email',
          type: 'error'
        }
      });
      document.dispatchEvent(event);
    }
  } catch (error) {
    console.error('Erro ao enviar email individual:', error);
    const event = new CustomEvent('showToast', {
      detail: {
        message: 'Erro de conexão. Tente novamente.',
        type: 'error'
      }
    });
    document.dispatchEvent(event);
  }
}

// Função para enviar email em massa
async function enviarEmailMassa() {
  const btn = document.getElementById('btnEnviarEmailMassa');
  const originalText = btn.innerHTML;

  // Desabilitar botão e mostrar loading
  btn.disabled = true;
  btn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Enviando...';

  try {
    const response = await fetch('/revisor/send_email_mass', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      }
    });

    const data = await response.json();

    if (data.success) {
      const event = new CustomEvent('showToast', {
        detail: {
          message: data.message,
          type: 'success'
        }
      });
      document.dispatchEvent(event);
    } else {
      const event = new CustomEvent('showToast', {
        detail: {
          message: data.message || 'Erro ao enviar emails',
          type: 'error'
        }
      });
      document.dispatchEvent(event);
    }
  } catch (error) {
    console.error('Erro ao enviar emails em massa:', error);
    const event = new CustomEvent('showToast', {
      detail: {
        message: 'Erro de conexão. Tente novamente.',
        type: 'error'
      }
    });
    document.dispatchEvent(event);
  } finally {
    // Reabilitar botão
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}

// Event listeners para os botões de email
document.addEventListener('DOMContentLoaded', function () {
  // Listener para botões de copiar código
  document.addEventListener('click', function (e) {
    if (e.target.closest('.copiar-codigo')) {
      const codigo = e.target.closest('.copiar-codigo').dataset.codigo;
      copiarCodigoRevisor(codigo);
    }
  });

  // Listener para botões de enviar email individual
  document.addEventListener('click', function (e) {
    if (e.target.closest('.enviar-email-individual')) {
      const btn = e.target.closest('.enviar-email-individual');
      const candId = btn.dataset.candId;
      const email = btn.dataset.email;

      if (confirm(`Enviar email de aprovação para ${email}?`)) {
        enviarEmailIndividual(candId, email);
      }
    }
  });

  // Listener para botão de enviar email em massa
  const btnEnviarEmailMassa = document.getElementById('btnEnviarEmailMassa');
  if (btnEnviarEmailMassa) {
    btnEnviarEmailMassa.addEventListener('click', function () {
      if (confirm('Enviar email de aprovação para todos os revisores aprovados?')) {
        enviarEmailMassa();
      }
    });
  }
});

// Sistema de toast notifications (se não existir)
if (!window.showToast) {
  window.showToast = function (message, type = 'info') {
    // Criar elemento de toast se não existir
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'toast-container';
      toastContainer.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
      `;
      document.body.appendChild(toastContainer);
    }

    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show`;
    toast.style.cssText = `
      margin-bottom: 10px;
      min-width: 300px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    `;

    toast.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    toastContainer.appendChild(toast);

    // Auto-remover após 5 segundos
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 5000);
  };
}

// Listener para eventos de toast customizados
document.addEventListener('showToast', function (e) {
  showToast(e.detail.message, e.detail.type);
});
if (btnCopiarLinkGeradoEl) {
  btnCopiarLinkGeradoEl.addEventListener("click", copiarLinkGerado);
}


// Efeitos e funcionalidade para o botão Exportar Filtrado (PDF de Check-ins)
document.addEventListener('DOMContentLoaded', function () {
  const exportBtn = document.getElementById('btnExportarFiltrado');
  if (exportBtn) {
    exportBtn.addEventListener('mouseover', function () {
      this.classList.add('shadow-sm'); // Efeito sutil de sombra
    });
    exportBtn.addEventListener('mouseout', function () {
      this.classList.remove('shadow-sm');
    });

    exportBtn.addEventListener('click', function (e) {
      e.preventDefault(); // Prevenir comportamento padrão se for um link <a>

      const originalContent = this.innerHTML;
      this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Exportando...';
      this.disabled = true;

      const filtroEventoEl = document.getElementById('filtroEvento'); // Select de filtro de evento
      const filtroTipoEl = document.getElementById('filtroTipo');   // Select de filtro de tipo

      if (!filtroEventoEl || !filtroTipoEl) {
        console.error("Elementos de filtro 'filtroEvento' ou 'filtroTipo' não encontrados.");
        alert("Erro: Filtros não encontrados para exportação.");
        this.innerHTML = originalContent;
        this.disabled = false;
        return;
      }

      const eventoId = filtroEventoEl.value;
      const tipo = filtroTipoEl.value;

      // A URL de exportação deve ser definida no HTML, por exemplo, em um atributo data-export-url no botão
      // ou através de uma variável global como URL_EXPORTAR_CHECKINS_PDF
      let url;
      if (this.dataset.exportUrl) {
        url = `${this.dataset.exportUrl}?evento_id=${encodeURIComponent(eventoId)}&tipo=${encodeURIComponent(tipo)}`;
      } else if (typeof URL_EXPORTAR_CHECKINS_PDF !== 'undefined') {
        url = `${URL_EXPORTAR_CHECKINS_PDF}?evento_id=${encodeURIComponent(eventoId)}&tipo=${encodeURIComponent(tipo)}`;
      } else {
        console.error("URL de exportação não definida (nem data-export-url nem URL_EXPORTAR_CHECKINS_PDF).");
        alert("Erro de configuração: URL de exportação não definida.");
        this.innerHTML = originalContent;
        this.disabled = false;
        return;
      }

      // Usar window.location.href para GET request que resulta em download
      // O timeout é apenas para UX, o navegador cuidará do download.
      setTimeout(() => {
        window.location.href = url;
        // Resetar o botão após um tempo, caso o download falhe ou o usuário cancele
        // (o navegador não dá feedback direto para o JS sobre o status do download)
        setTimeout(() => {
          this.innerHTML = originalContent;
          this.disabled = false;
        }, 3000); // Tempo para o usuário perceber a tentativa de download
      }, 800); // Pequeno delay para o spinner ser visível
    });
  }

  const exportPartBtn = document.getElementById('btnExportarParticipantes');
  if (exportPartBtn) {
    exportPartBtn.addEventListener('click', function (e) {
      e.preventDefault();
      const eventoId = document.getElementById('eventoExportParticipantes').value;
      const formato = document.getElementById('formatoExportParticipantes').value;
      let url;
      if (this.dataset.exportUrl) {
        url = `${this.dataset.exportUrl}?evento_id=${encodeURIComponent(eventoId)}&formato=${encodeURIComponent(formato)}`;
      } else if (typeof URL_EXPORTAR_PARTICIPANTES !== 'undefined') {
        url = `${URL_EXPORTAR_PARTICIPANTES}?evento_id=${encodeURIComponent(eventoId)}&formato=${encodeURIComponent(formato)}`;
      } else {
        console.error('URL de exportação não definida.');
        return;
      }
      window.location.href = url;
    });
  }

  const placasBtn = document.getElementById('btnGerarPlacasOficinas');
  if (placasBtn) {
    placasBtn.addEventListener('click', function (e) {
      e.preventDefault();
      const eventoId = document.getElementById('eventoPlacasOficinas').value;
      const base = this.dataset.baseUrl;
      if (!base) {
        console.error('Base URL não definida.');
        return;
      }
      window.location.href = `${base}${encodeURIComponent(eventoId)}`;
    });
  }

  const eventoCampoSelect = document.getElementById('evento_campo');
  const previewCamposBtn = document.getElementById('previewCamposBtn');
  if (eventoCampoSelect && previewCamposBtn) {
    const updatePreview = () => {
      const base = previewCamposBtn.dataset.baseUrl;
      previewCamposBtn.href = `${base}?evento_id=${encodeURIComponent(eventoCampoSelect.value)}`;
    };
    eventoCampoSelect.addEventListener('change', updatePreview);
    updatePreview();
  }

  // Melhorar estilo dos selects ao focar/desfocar
  const selects = document.querySelectorAll('.form-select');
  selects.forEach(select => {
    select.addEventListener('focus', function () {
      this.classList.add('shadow-sm');
    });
    select.addEventListener('blur', function () {
      this.classList.remove('shadow-sm');
    });
  });
});

// Geração dinâmica de campos de upload para patrocinadores
function gerarCamposUploads() {
  const container = document.getElementById('containerPatrocinadores');
  if (!container) {
    console.error("Container 'containerPatrocinadores' não encontrado.");
    return;
  }
  container.innerHTML = ''; // Limpa campos anteriores

  const categorias = [
    { id: 'realizacao', label: 'Realização', icon: 'fa-star', color: 'text-primary' },
    { id: 'patrocinio', label: 'Patrocínio', icon: 'fa-handshake', color: 'text-success' },
    { id: 'organizacao', label: 'Organização', icon: 'fa-users-cog', color: 'text-info' },
    { id: 'apoio', label: 'Apoio', icon: 'fa-thumbs-up', color: 'text-secondary' },
  ];

  categorias.forEach(cat => {
    const qtdInput = document.getElementById(`qtd_${cat.id}`);
    if (!qtdInput) {
      console.warn(`Input de quantidade 'qtd_${cat.id}' não encontrado.`);
      return;
    }
    const qtd = parseInt(qtdInput.value) || 0;

    if (qtd > 0) {
      const divCategoria = document.createElement('div');
      divCategoria.className = 'card shadow-sm mb-4'; // Aumentado margin-bottom

      const headerCategoria = document.createElement('div');
      headerCategoria.className = 'card-header bg-light py-2 px-3 d-flex align-items-center'; // Estilo no header
      headerCategoria.innerHTML = `<i class="fas ${cat.icon} ${cat.color} me-2 fa-fw"></i>
                                         <strong class="text-dark">${cat.label} (${qtd})</strong>`;

      const bodyCategoria = document.createElement('div');
      bodyCategoria.className = 'card-body p-3'; // Padding no body

      for (let i = 0; i < qtd; i++) {
        const formGroup = document.createElement('div'); // Agrupar label e input
        formGroup.className = 'mb-3';

        const label = document.createElement('label');
        label.className = 'form-label fw-normal small'; // Estilo no label
        label.innerText = `Logo ${cat.label} ${i + 1}`;
        label.htmlFor = `${cat.id}_${i}`; // Associar label ao input

        const input = document.createElement('input');
        input.type = 'file';
        input.name = `${cat.id}_${i}`; // Nome do campo para o backend
        input.id = `${cat.id}_${i}`;   // ID para o label
        input.className = 'form-control form-control-sm'; // Input menor
        input.accept = 'image/png, image/jpeg, image/svg+xml, image/webp'; // Tipos de imagem comuns

        formGroup.appendChild(label);
        formGroup.appendChild(input);
        bodyCategoria.appendChild(formGroup);
      }
      divCategoria.appendChild(headerCategoria);
      divCategoria.appendChild(bodyCategoria);
      container.appendChild(divCategoria);
    }
  });
}
// Adicionar listener para o botão que chama gerarCamposUploads, se ele existir
var btnGerarCampos = document.getElementById('btnGerarCamposPatrocinio'); // Exemplo de ID
if (btnGerarCampos) {
  btnGerarCampos.addEventListener('click', gerarCamposUploads);
} else {
  // Ou, se os campos devem ser gerados quando os inputs de quantidade mudam:
  ['qtd_realizacao', 'qtd_patrocinio', 'qtd_organizacao', 'qtd_apoio'].forEach(idQtd => {
    const inputQtd = document.getElementById(idQtd);
    if (inputQtd) {
      inputQtd.addEventListener('change', gerarCamposUploads);
    }
  });
  // Gerar campos inicialmente se já houver valores nos inputs de quantidade (ex: ao recarregar página com formulário preenchido)
  // gerarCamposUploads(); // Descomente se necessário após o DOM estar pronto
}


// Filtragem de check-ins por oficina na tabela
document.addEventListener('DOMContentLoaded', function () {
  const filterOficina = document.getElementById('filterOficina'); // Select de filtro de oficina
  const checkinsTable = document.getElementById('checkinsTable');   // Tabela de check-ins
  const resetFilter = document.getElementById('resetFilterOficina'); // Botão para limpar filtro de oficina

  if (filterOficina && checkinsTable) {
    const noDataRow = checkinsTable.querySelector('#noDataRowCheckins'); // Linha de "nenhum dado" específica para esta tabela

    function filterCheckins() {
      const selectedOficina = filterOficina.value;
      let visibleRows = 0;

      const rows = checkinsTable.querySelectorAll('tbody tr:not(#noDataRowCheckins)');

      rows.forEach(row => {
        // Assumindo que cada linha <tr> tem um atributo data-oficina-id com o ID da oficina
        const oficinaIdNaLinha = row.dataset.oficinaId;
        const matchOficina = !selectedOficina || oficinaIdNaLinha === selectedOficina;

        if (matchOficina) {
          row.style.display = ''; // Exibe a linha
          visibleRows++;
        } else {
          row.style.display = 'none'; // Oculta a linha
        }
      });

      if (noDataRow) {
        noDataRow.style.display = visibleRows === 0 ? '' : 'none';
      }
    }

    filterOficina.addEventListener('change', filterCheckins);

    if (resetFilter) {
      resetFilter.addEventListener('click', function () {
        filterOficina.value = ''; // Limpa a seleção do filtro
        filterCheckins();      // Reaplica o filtro (que mostrará tudo)
      });
    }
    // Aplicar filtro inicial caso haja valor pré-selecionado
    // filterCheckins(); // Descomente se necessário
  }
});


// Adicionar botão para gerar link
var buttonContainer = document.getElementById('buttonContainer'); // Replace with the appropriate container ID
if (buttonContainer) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'btn btn-warning mt-2 w-100 gerar-link-btn';
  button.innerHTML = '<i class="bi bi-link-45deg me-2"></i> Gerar Link';
  buttonContainer.appendChild(button);
}

// Configuração do limite máximo de revisores
document.addEventListener('DOMContentLoaded', function () {
  const inputLimiteRevisores = document.getElementById('inputLimiteMaxRevisores');
  if (inputLimiteRevisores) {
    inputLimiteRevisores.addEventListener('change', function () {
      const url = this.dataset.updateUrl;
      if (!url) return;

      const valor = parseInt(this.value);
      if (valor < 1) {
        alert('O limite deve ser pelo menos 1');
        this.value = 1;
        return;
      }

      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        credentials: 'include',
        body: JSON.stringify({ limite: valor })
      })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            // Opcional: mostrar feedback visual de sucesso
            const originalBorder = this.style.border;
            this.style.border = '2px solid #28a745';
            setTimeout(() => {
              this.style.border = originalBorder;
            }, 1000);
          } else {
            alert('Erro ao atualizar limite: ' + (data.message || 'Erro desconhecido'));
          }
        })
        .catch(error => {
          console.error('Erro na requisição:', error);
          alert('Erro ao atualizar limite de revisores');
        });
    });
  }
});

console.log("dashboard_cliente.js carregado e pronto.");
