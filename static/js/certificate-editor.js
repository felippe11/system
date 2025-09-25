/**
 * Editor Avançado de Certificado
 * Sistema de arrastar e soltar para criação de certificados
 */

class CertificateEditor {
  constructor() {
    this.canvas = null;
    this.selectedElement = null;
    this.elements = [];
    this.history = [];
    this.historyIndex = -1;
    this.isGridEnabled = false;
    this.isSnapEnabled = false;
    this.gridSize = 10;
    this.zoom = 1;
    this.isLivePreview = false;
    this.guidelines = [];
    this.init();
  }

  init() {
    this.canvas = document.getElementById('canvas');
    if (!this.canvas) {
      console.error('Canvas não encontrado!');
      return;
    }
    
    this.setupEventListeners();
    this.setupDragAndDrop();
    this.setupGrid();
    this.setupGuidelines();
    this.setupSidebarTabs();
    this.loadTemplate();
    this.saveState();
  }

  setupEventListeners() {
    // Event listeners para elementos da biblioteca
    document.querySelectorAll('.element-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const type = item.dataset.type;
        if (type) {
          this.addElement(type, e);
        }
      });
    });

    // Event listeners para toolbar
    this.setupToolbarEvents();
    
    // Event listeners para propriedades
    this.setupPropertyEvents();
    
    // Event listener para canvas
    this.canvas.addEventListener('click', (e) => {
      if (e.target === this.canvas) {
        this.deselectElement();
      }
    });

    // Event listeners para botões de alinhamento
    document.querySelectorAll('[data-align]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const align = e.currentTarget.dataset.align;
        this.applyTextAlignment(align);
      });
    });
  }

  setupToolbarEvents() {
    const saveBtn = document.getElementById('saveTemplate');
    const previewBtn = document.getElementById('previewTemplate');
    const livePreviewBtn = document.getElementById('livePreviewToggle');
    const exportBtn = document.getElementById('exportTemplate');
    const undoBtn = document.getElementById('undoAction');
    const redoBtn = document.getElementById('redoAction');
    const gridBtn = document.getElementById('toggleGrid');
    const snapBtn = document.getElementById('toggleSnap');
    const zoomSelect = document.getElementById('zoomLevel');

    if (saveBtn) saveBtn.addEventListener('click', () => this.saveTemplate());
    if (previewBtn) previewBtn.addEventListener('click', () => this.previewTemplate());
    if (livePreviewBtn) livePreviewBtn.addEventListener('click', () => this.toggleLivePreview());
    if (exportBtn) exportBtn.addEventListener('click', () => this.exportTemplate());
    if (undoBtn) undoBtn.addEventListener('click', () => this.undo());
    if (redoBtn) redoBtn.addEventListener('click', () => this.redo());
    if (gridBtn) gridBtn.addEventListener('click', () => this.toggleGrid());
    if (snapBtn) snapBtn.addEventListener('click', () => this.toggleSnap());
    if (zoomSelect) zoomSelect.addEventListener('change', (e) => this.setZoom(parseFloat(e.target.value)));
  }

  setupPropertyEvents() {
    // Text properties
    const textInput = document.getElementById('elementText');
    const fontFamily = document.getElementById('fontFamily');
    const fontSize = document.getElementById('fontSize');
    const fontWeight = document.getElementById('fontWeight');
    const textAlign = document.getElementById('textAlign');
    const textColor = document.getElementById('textColor');

    if (textInput) textInput.addEventListener('input', () => this.applyTextProperties());
    if (fontFamily) fontFamily.addEventListener('change', () => this.applyTextProperties());
    if (fontSize) fontSize.addEventListener('input', () => this.applyTextProperties());
    if (fontWeight) fontWeight.addEventListener('change', () => this.applyTextProperties());
    if (textAlign) textAlign.addEventListener('change', () => this.applyTextProperties());
    if (textColor) textColor.addEventListener('change', () => this.applyTextProperties());

    // Logo properties
    const logoUrl = document.getElementById('logoUrl');
    const logoSize = document.getElementById('logoSize');
    if (logoUrl) logoUrl.addEventListener('input', () => this.applyLogoProperties());
    if (logoSize) logoSize.addEventListener('change', () => this.applyLogoProperties());

    // Border properties
    const borderWidth = document.getElementById('borderWidth');
    const borderStyle = document.getElementById('borderStyle');
    const borderColor = document.getElementById('borderColor');
    if (borderWidth) borderWidth.addEventListener('input', () => this.applyBorderProperties());
    if (borderStyle) borderStyle.addEventListener('change', () => this.applyBorderProperties());
    if (borderColor) borderColor.addEventListener('change', () => this.applyBorderProperties());

    // QR Code properties
    const qrCodeSize = document.getElementById('qrCodeSize');
    const qrCodeContent = document.getElementById('qrCodeContent');
    if (qrCodeSize) qrCodeSize.addEventListener('change', () => this.applyQRCodeProperties());
    if (qrCodeContent) qrCodeContent.addEventListener('input', () => this.applyQRCodeProperties());

    // Custom variable properties
    const variableSelect = document.getElementById('customVariableSelect');
    const variableFormat = document.getElementById('customVariableFormat');
    const variableDefault = document.getElementById('customVariableDefault');
    if (variableSelect) variableSelect.addEventListener('change', () => this.applyCustomVariableProperties());
    if (variableFormat) variableFormat.addEventListener('change', () => this.applyCustomVariableProperties());
    if (variableDefault) variableDefault.addEventListener('input', () => this.applyCustomVariableProperties());
  }

  setupDragAndDrop() {
    if (typeof interact === 'undefined') {
      console.error('Interact.js não está carregado!');
      return;
    }

    // Configurar elementos arrastáveis
    interact('.draggable-element')
      .draggable({
        inertia: true,
        modifiers: [
          interact.modifiers.restrictRect({
            restriction: 'parent',
            endOnly: true
          })
        ],
        autoScroll: true,
        listeners: {
          start: (event) => {
            this.selectElement(event.target);
            event.target.style.zIndex = 1000;
          },
          move: this.dragMoveListener.bind(this),
          end: (event) => {
            event.target.style.zIndex = '';
            this.saveState();
            this.hideGuidelines();
          }
        }
      })
      .resizable({
        edges: { left: true, right: true, bottom: true, top: true },
        listeners: {
          start: (event) => {
            this.selectElement(event.target);
          },
          move: this.resizeMoveListener.bind(this),
          end: (event) => {
            this.saveState();
          }
        },
        modifiers: [
          interact.modifiers.restrictEdges({
            outer: 'parent'
          }),
          interact.modifiers.restrictSize({
            min: { width: 20, height: 20 }
          })
        ],
        inertia: true
      });

    // Configurar zona de drop para elementos da biblioteca
    interact('#canvas').dropzone({
      accept: '.element-item',
      overlap: 0.75,
      ondrop: (event) => {
        const elementType = event.relatedTarget.dataset.type;
        if (elementType) {
          const rect = this.canvas.getBoundingClientRect();
          const x = event.dragEvent.client.x - rect.left;
          const y = event.dragEvent.client.y - rect.top;
          this.addElement(elementType, null, x, y);
        }
      }
    });

    // Configurar drag and drop para elementos da biblioteca
    interact('.element-item')
      .draggable({
        inertia: true,
        autoScroll: true,
        listeners: {
          start: (event) => {
            event.target.style.opacity = '0.5';
          },
          end: (event) => {
            event.target.style.opacity = '';
          }
        }
      });
  }

  dragMoveListener(event) {
    const target = event.target;
    const x = (parseFloat(target.getAttribute('data-x')) || 0) + event.dx;
    const y = (parseFloat(target.getAttribute('data-y')) || 0) + event.dy;

    // Aplicar snap se habilitado
    let snapX = x;
    let snapY = y;
    
    if (this.isSnapEnabled) {
      snapX = Math.round(x / this.gridSize) * this.gridSize;
      snapY = Math.round(y / this.gridSize) * this.gridSize;
    }

    target.style.transform = `translate(${snapX}px, ${snapY}px)`;
    target.setAttribute('data-x', snapX);
    target.setAttribute('data-y', snapY);

    // Mostrar guidelines
    this.showGuidelines(target, snapX, snapY);
  }

  resizeMoveListener(event) {
    const target = event.target;
    let x = (parseFloat(target.getAttribute('data-x')) || 0);
    let y = (parseFloat(target.getAttribute('data-y')) || 0);

    target.style.width = event.rect.width + 'px';
    target.style.height = event.rect.height + 'px';

    x += event.deltaRect.left;
    y += event.deltaRect.top;

    target.style.transform = `translate(${x}px, ${y}px)`;
    target.setAttribute('data-x', x);
    target.setAttribute('data-y', y);
  }

  setupGrid() {
    // Grid overlay is already in the HTML template
    const gridOverlay = document.getElementById('gridOverlay');
    if (!gridOverlay) {
      const gridOverlay = document.createElement('div');
      gridOverlay.id = 'gridOverlay';
      gridOverlay.className = 'grid-overlay';
      this.canvas.appendChild(gridOverlay);
    }
  }

  setupGuidelines() {
    this.guidelines = [];
  }

  setupSidebarTabs() {
    const tabs = document.querySelectorAll('.sidebar-tab');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        // Remove active class from all tabs and contents
        tabs.forEach(t => t.classList.remove('active'));
        tabContents.forEach(tc => tc.style.display = 'none');
        
        // Add active class to clicked tab
        tab.classList.add('active');
        
        // Show corresponding content
        const tabId = tab.dataset.tab + 'Tab';
        const content = document.getElementById(tabId);
        if (content) {
          content.style.display = 'block';
        }
      });
    });
  }

  showGuidelines(element, x, y) {
    this.hideGuidelines();
    
    const elements = this.canvas.querySelectorAll('.draggable-element');
    const threshold = 5;
    
    elements.forEach(el => {
      if (el === element) return;
      
      const elRect = el.getBoundingClientRect();
      const canvasRect = this.canvas.getBoundingClientRect();
      const elX = elRect.left - canvasRect.left;
      const elY = elRect.top - canvasRect.top;
      
      // Verificar alinhamento horizontal
      if (Math.abs(y - elY) < threshold) {
        this.createGuideline('horizontal', elY);
      }
      
      // Verificar alinhamento vertical
      if (Math.abs(x - elX) < threshold) {
        this.createGuideline('vertical', elX);
      }
    });
  }

  createGuideline(type, position) {
    const guideline = document.createElement('div');
    guideline.className = `guideline guideline-${type}`;
    
    if (type === 'horizontal') {
      guideline.style.top = position + 'px';
      guideline.style.left = '0';
      guideline.style.width = '100%';
      guideline.style.height = '1px';
    } else {
      guideline.style.left = position + 'px';
      guideline.style.top = '0';
      guideline.style.width = '1px';
      guideline.style.height = '100%';
    }
    
    this.canvas.appendChild(guideline);
    this.guidelines.push(guideline);
  }

  hideGuidelines() {
    this.guidelines.forEach(guideline => {
      if (guideline.parentNode) {
        guideline.parentNode.removeChild(guideline);
      }
    });
    this.guidelines = [];
  }

  toggleGrid() {
    this.isGridEnabled = !this.isGridEnabled;
    const gridOverlay = document.getElementById('gridOverlay');
    const gridBtn = document.getElementById('toggleGrid');
    
    if (this.isGridEnabled) {
      if (gridOverlay) {
        gridOverlay.classList.add('active');
      }
      if (gridBtn) {
        gridBtn.classList.add('active');
      }
    } else {
      if (gridOverlay) {
        gridOverlay.classList.remove('active');
      }
      if (gridBtn) {
        gridBtn.classList.remove('active');
      }
    }
  }

  toggleSnap() {
    this.isSnapEnabled = !this.isSnapEnabled;
    const snapBtn = document.getElementById('toggleSnap');
    
    if (this.isSnapEnabled) {
      snapBtn.classList.add('active');
    } else {
      snapBtn.classList.remove('active');
    }
  }

  setGridSize(size) {
    this.gridSize = size;
    const gridOverlay = document.getElementById('grid-overlay');
    gridOverlay.style.backgroundSize = `${size}px ${size}px`;
  }

  setZoom(zoom) {
    this.zoom = zoom;
    this.canvas.style.transform = `scale(${zoom})`;
    this.canvas.style.transformOrigin = 'top left';
  }

  addElement(type, event, x = null, y = null) {
    const element = this.createElement(type);
    
    if (x !== null && y !== null) {
      element.style.left = x + 'px';
      element.style.top = y + 'px';
      element.setAttribute('data-x', x);
      element.setAttribute('data-y', y);
    } else {
      const centerX = this.canvas.offsetWidth / 2 - 50;
      const centerY = this.canvas.offsetHeight / 2 - 25;
      element.style.left = centerX + 'px';
      element.style.top = centerY + 'px';
      element.setAttribute('data-x', centerX);
      element.setAttribute('data-y', centerY);
    }
    
    this.canvas.appendChild(element);
    this.elements.push({
      id: element.id,
      type: type,
      properties: this.getDefaultProperties(type)
    });
    
    this.selectElement(element);
    this.saveState();
    
    // Reconfigurar interact.js para o novo elemento
    this.setupElementInteractions(element);
  }

  setupElementInteractions(element) {
    if (typeof interact === 'undefined') return;

    // Configurar drag and drop para o elemento específico
    interact(element)
      .draggable({
        inertia: true,
        modifiers: [
          interact.modifiers.restrictRect({
            restriction: 'parent',
            endOnly: true
          })
        ],
        autoScroll: true,
        listeners: {
          start: (event) => {
            this.selectElement(event.target);
            event.target.style.zIndex = 1000;
          },
          move: this.dragMoveListener.bind(this),
          end: (event) => {
            event.target.style.zIndex = '';
            this.saveState();
            this.hideGuidelines();
          }
        }
      })
      .resizable({
        edges: { left: true, right: true, bottom: true, top: true },
        listeners: {
          start: (event) => {
            this.selectElement(event.target);
          },
          move: this.resizeMoveListener.bind(this),
          end: (event) => {
            this.saveState();
          }
        },
        modifiers: [
          interact.modifiers.restrictEdges({
            outer: 'parent'
          }),
          interact.modifiers.restrictSize({
            min: { width: 20, height: 20 }
          })
        ],
        inertia: true
      });
  }

  createElement(type) {
    const element = document.createElement('div');
    element.className = 'draggable-element';
    element.id = 'element_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    const defaultProps = this.getDefaultProperties(type);
    
    switch (type) {
      case 'text':
        element.innerHTML = defaultProps.text || 'Clique para editar';
        element.style.fontSize = defaultProps.fontSize || '16px';
        element.style.fontFamily = defaultProps.fontFamily || 'Arial';
        element.style.color = defaultProps.color || '#000000';
        element.style.textAlign = defaultProps.textAlign || 'left';
        element.style.fontWeight = defaultProps.fontWeight || 'normal';
        element.style.padding = '8px';
        element.style.minWidth = '100px';
        element.style.minHeight = '30px';
        element.contentEditable = true;
        break;
        
      case 'logo':
        element.innerHTML = '<img src="' + (defaultProps.src || '/static/img/placeholder-logo.png') + '" alt="Logo" style="width: 100%; height: 100%; object-fit: contain;">';
        element.style.width = defaultProps.width || '100px';
        element.style.height = defaultProps.height || '100px';
        element.style.padding = '4px';
        break;
        
      case 'signature':
        element.innerHTML = '<div style="border-bottom: 2px solid #000; padding-bottom: 5px; text-align: center; font-style: italic;">Assinatura</div>';
        element.style.width = defaultProps.width || '200px';
        element.style.height = defaultProps.height || '50px';
        element.style.padding = '8px';
        break;
        
      case 'qrcode':
        element.innerHTML = '<div style="width: 100%; height: 100%; background: #f0f0f0; display: flex; align-items: center; justify-content: center; border: 1px dashed #ccc; border-radius: 4px; font-size: 12px; color: #666;">QR Code</div>';
        element.style.width = defaultProps.width || '100px';
        element.style.height = defaultProps.height || '100px';
        element.style.padding = '4px';
        break;
        
      case 'variable':
        element.innerHTML = '{NOME_PARTICIPANTE}';
        element.style.fontSize = defaultProps.fontSize || '16px';
        element.style.fontFamily = defaultProps.fontFamily || 'Arial';
        element.style.color = defaultProps.color || '#000000';
        element.style.padding = '8px';
        element.style.minWidth = '120px';
        element.style.minHeight = '30px';
        element.style.background = '#f0f8ff';
        element.style.border = '1px dashed #3b82f6';
        element.style.borderRadius = '4px';
        break;
        
      default:
        element.innerHTML = 'Elemento';
        element.style.padding = '8px';
    }
    
    // Adicionar controles
    this.addElementControls(element);
    
    // Event listener para seleção
    element.addEventListener('click', (e) => {
      e.stopPropagation();
      this.selectElement(element);
    });

    // Event listener para edição de texto
    if (type === 'text') {
      element.addEventListener('blur', () => {
        this.saveState();
      });
    }
    
    return element;
  }

  addElementControls(element) {
    const controls = document.createElement('div');
    controls.className = 'element-controls';
    controls.innerHTML = `
      <button class="control-btn delete-btn" title="Excluir">
        <i class="fas fa-trash"></i>
      </button>
    `;
    
    const deleteBtn = controls.querySelector('.delete-btn');
    deleteBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.deleteElement(element);
    });
    
    element.appendChild(controls);
    
    // Adicionar handles de redimensionamento
    const resizeHandles = ['nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w'];
    resizeHandles.forEach(handle => {
      const handleEl = document.createElement('div');
      handleEl.className = `resize-handle resize-${handle}`;
      element.appendChild(handleEl);
    });

    // Adicionar indicador de tipo de elemento
    const typeIndicator = document.createElement('div');
    typeIndicator.className = 'element-type-indicator';
    typeIndicator.style.cssText = `
      position: absolute;
      top: -20px;
      left: 0;
      background: var(--canva-purple);
      color: white;
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 10px;
      font-weight: 500;
      opacity: 0;
      transition: opacity 0.2s ease;
      pointer-events: none;
    `;
    typeIndicator.textContent = this.getElementTypeName(element);
    element.appendChild(typeIndicator);

    // Mostrar indicador no hover
    element.addEventListener('mouseenter', () => {
      typeIndicator.style.opacity = '1';
    });
    element.addEventListener('mouseleave', () => {
      typeIndicator.style.opacity = '0';
    });
  }

  getElementTypeName(element) {
    if (element.contentEditable === 'true') return 'Texto';
    if (element.querySelector('img')) return 'Logo';
    if (element.innerHTML.includes('QR Code')) return 'QR Code';
    if (element.innerHTML.includes('Assinatura')) return 'Assinatura';
    if (element.innerHTML.includes('{')) return 'Variável';
    return 'Elemento';
  }

  getDefaultProperties(type) {
    const defaults = {
      text: {
        text: 'Texto',
        fontSize: '16px',
        fontFamily: 'Arial',
        color: '#000000',
        textAlign: 'left',
        fontWeight: 'normal'
      },
      logo: {
        src: '/static/img/placeholder-logo.png',
        width: '100px',
        height: '100px'
      },
      signature: {
        width: '200px',
        height: '50px',
        borderColor: '#000000',
        borderWidth: '2px'
      },
      qrcode: {
        width: '100px',
        height: '100px',
        content: 'https://example.com'
      },
      variable: {
        variable: 'NOME_PARTICIPANTE',
        fontSize: '16px',
        fontFamily: 'Arial',
        color: '#000000'
      }
    };
    
    return defaults[type] || {};
  }

  selectElement(element) {
    this.deselectElement();
    this.selectedElement = element;
    element.classList.add('selected');
    this.updatePropertiesPanel();
  }

  deselectElement() {
    if (this.selectedElement) {
      this.selectedElement.classList.remove('selected');
      this.selectedElement = null;
    }
    this.hidePropertiesPanel();
  }

  updatePropertiesPanel() {
    if (!this.selectedElement) return;
    
    const elementData = this.elements.find(el => el.id === this.selectedElement.id);
    if (!elementData) return;
    
    // Mostrar painel de propriedades
    document.getElementById('propertiesPanel').style.display = 'block';
    
    // Esconder todas as seções
    document.querySelectorAll('.property-section').forEach(section => {
      section.style.display = 'none';
    });
    
    // Mostrar seção relevante
    const section = document.getElementById(`${elementData.type}Properties`);
    if (section) {
      section.style.display = 'block';
    }
    
    // Preencher valores atuais
    this.populatePropertyValues(elementData);
  }

  populatePropertyValues(elementData) {
    const type = elementData.type;
    const props = elementData.properties;
    
    if (type === 'text' || type === 'variable') {
      const textInput = document.getElementById('elementText');
      const fontFamily = document.getElementById('fontFamily');
      const fontSize = document.getElementById('fontSize');
      const fontWeight = document.getElementById('fontWeight');
      const textAlign = document.getElementById('textAlign');
      const textColor = document.getElementById('textColor');
      
      if (textInput) textInput.value = this.selectedElement.textContent || '';
      if (fontFamily) fontFamily.value = props.fontFamily || 'Arial';
      if (fontSize) fontSize.value = parseInt(props.fontSize) || 16;
      if (fontWeight) fontWeight.value = props.fontWeight || 'normal';
      if (textAlign) textAlign.value = props.textAlign || 'left';
      if (textColor) textColor.value = props.color || '#000000';
    }
    
    if (type === 'logo') {
      const logoUrl = document.getElementById('logoUrl');
      const logoSize = document.getElementById('logoSize');
      
      if (logoUrl) logoUrl.value = props.src || '';
      if (logoSize) logoSize.value = props.width === '100px' ? 'small' : props.width === '150px' ? 'medium' : 'large';
    }
  }

  hidePropertiesPanel() {
    document.getElementById('propertiesPanel').style.display = 'none';
  }

  applyTextProperties() {
    if (!this.selectedElement) return;
    
    const textInput = document.getElementById('elementText');
    const fontFamily = document.getElementById('fontFamily');
    const fontSize = document.getElementById('fontSize');
    const fontWeight = document.getElementById('fontWeight');
    const textAlign = document.getElementById('textAlign');
    const textColor = document.getElementById('textColor');
    
    if (textInput) this.selectedElement.textContent = textInput.value;
    if (fontFamily) this.selectedElement.style.fontFamily = fontFamily.value;
    if (fontSize) this.selectedElement.style.fontSize = fontSize.value + 'px';
    if (fontWeight) this.selectedElement.style.fontWeight = fontWeight.value;
    if (textAlign) this.selectedElement.style.textAlign = textAlign.value;
    if (textColor) this.selectedElement.style.color = textColor.value;
    
    this.saveState();
  }

  applyTextAlignment(align) {
    if (!this.selectedElement) return;
    
    this.selectedElement.style.textAlign = align;
    
    // Update visual state of alignment buttons
    document.querySelectorAll('[data-align]').forEach(btn => {
      btn.classList.remove('active');
      if (btn.dataset.align === align) {
        btn.classList.add('active');
      }
    });
    
    this.saveState();
  }

  applyLogoProperties() {
    if (!this.selectedElement) return;
    
    const logoUrl = document.getElementById('logoUrl');
    const logoSize = document.getElementById('logoSize');
    
    if (logoUrl && logoUrl.value) {
      const img = this.selectedElement.querySelector('img');
      if (img) {
        img.src = logoUrl.value;
      }
    }
    
    if (logoSize) {
      let size;
      switch(logoSize.value) {
        case 'small': size = '100px'; break;
        case 'medium': size = '150px'; break;
        case 'large': size = '200px'; break;
        default: size = '100px';
      }
      this.selectedElement.style.width = size;
      this.selectedElement.style.height = size;
    }
    
    this.saveState();
  }

  applyBorderProperties() {
    if (!this.selectedElement) return;
    
    const borderWidth = document.getElementById('borderWidth');
    const borderStyle = document.getElementById('borderStyle');
    const borderColor = document.getElementById('borderColor');
    
    if (borderStyle && borderWidth && borderColor) {
      this.selectedElement.style.border = `${borderWidth.value}px ${borderStyle.value} ${borderColor.value}`;
      const borderWidthValue = document.getElementById('borderWidthValue');
      if (borderWidthValue) {
        borderWidthValue.textContent = `${borderWidth.value}px`;
      }
    }
    
    this.saveState();
  }

  applyQRCodeProperties() {
    if (!this.selectedElement) return;
    
    const qrCodeSize = document.getElementById('qrCodeSize');
    
    if (qrCodeSize) {
      let size;
      switch(qrCodeSize.value) {
        case 'small': size = '100px'; break;
        case 'medium': size = '150px'; break;
        case 'large': size = '200px'; break;
        default: size = '100px';
      }
      this.selectedElement.style.width = size;
      this.selectedElement.style.height = size;
    }
    
    this.saveState();
  }

  applyCustomVariableProperties() {
    if (!this.selectedElement) return;
    
    const variableSelect = document.getElementById('customVariableSelect');
    const variableFormat = document.getElementById('customVariableFormat');
    const variableDefault = document.getElementById('customVariableDefault');
    
    if (variableSelect && variableSelect.value) {
      let content = `{${variableSelect.value}}`;
      
      if (variableDefault && variableDefault.value) {
        content += ` (padrão: ${variableDefault.value})`;
      }
      
      this.selectedElement.innerHTML = content;
      
      // Salvar propriedades específicas
      const elementData = this.elements.find(el => el.id === this.selectedElement.id);
      if (elementData) {
        elementData.variavel = variableSelect.value;
        elementData.formato = variableFormat ? variableFormat.value : 'text';
        elementData.valorPadrao = variableDefault ? variableDefault.value : '';
      }
    }
    
    this.saveState();
  }

  deleteElement(element) {
    if (element === this.selectedElement) {
      this.deselectElement();
    }
    
    this.elements = this.elements.filter(el => el.id !== element.id);
    element.remove();
    this.saveState();
  }

  saveState() {
    const state = {
      elements: this.elements.map(el => {
        const domElement = document.getElementById(el.id);
        return {
          ...el,
          style: domElement ? domElement.style.cssText : '',
          innerHTML: domElement ? domElement.innerHTML : '',
          position: {
            x: domElement ? parseFloat(domElement.getAttribute('data-x')) || 0 : 0,
            y: domElement ? parseFloat(domElement.getAttribute('data-y')) || 0 : 0
          }
        };
      })
    };
    
    this.history = this.history.slice(0, this.historyIndex + 1);
    this.history.push(JSON.stringify(state));
    this.historyIndex++;
    
    if (this.history.length > 50) {
      this.history.shift();
      this.historyIndex--;
    }
  }

  undo() {
    if (this.historyIndex > 0) {
      this.historyIndex--;
      this.loadState(JSON.parse(this.history[this.historyIndex]));
    }
  }

  redo() {
    if (this.historyIndex < this.history.length - 1) {
      this.historyIndex++;
      this.loadState(JSON.parse(this.history[this.historyIndex]));
    }
  }

  loadState(state) {
    this.canvas.innerHTML = '';
    this.elements = [];
    
    state.elements.forEach(elementData => {
      const element = document.createElement('div');
      element.className = 'draggable-element';
      element.id = elementData.id;
      element.style.cssText = elementData.style;
      element.innerHTML = elementData.innerHTML;
      element.setAttribute('data-x', elementData.position.x);
      element.setAttribute('data-y', elementData.position.y);
      
      this.addElementControls(element);
      
      element.addEventListener('click', (e) => {
        e.stopPropagation();
        this.selectElement(element);
      });
      
      this.canvas.appendChild(element);
      this.elements.push(elementData);
    });
    
    this.setupDragAndDrop();
    this.setupGrid();
  }

  saveTemplate() {
    const templateName = document.getElementById('templateName').value || 'Novo Template';
    const templateOrientation = document.getElementById('templateOrientation').value || 'landscape';
    
    const templateData = {
      name: templateName,
      orientation: templateOrientation,
      elements: this.elements.map(el => {
        const domElement = document.getElementById(el.id);
        return {
          ...el,
          style: domElement ? domElement.style.cssText : '',
          innerHTML: domElement ? domElement.innerHTML : '',
          position: {
            x: domElement ? parseFloat(domElement.getAttribute('data-x')) || 0 : 0,
            y: domElement ? parseFloat(domElement.getAttribute('data-y')) || 0 : 0
          }
        };
      })
    };
    
    fetch('/certificado/salvar_template', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(templateData)
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        alert('Template salvo com sucesso!');
      } else {
        alert('Erro ao salvar template: ' + data.message);
      }
    })
    .catch(error => {
      console.error('Erro:', error);
      alert('Erro ao salvar template');
    });
  }

  previewTemplate() {
    const previewModal = document.getElementById('previewModal');
    const previewContent = document.getElementById('previewContent');
    
    if (!previewModal || !previewContent) {
      // Criar modal se não existir
      this.createPreviewModal();
      return;
    }
    
    const canvasClone = this.canvas.cloneNode(true);
    canvasClone.id = 'preview-canvas';
    canvasClone.querySelectorAll('.element-controls, .resize-handle').forEach(el => el.remove());
    canvasClone.querySelectorAll('.draggable-element').forEach(el => {
      el.classList.remove('selected', 'draggable-element');
    });
    
    this.replaceVariablesForPreview(canvasClone);
    
    previewContent.innerHTML = '';
    previewContent.appendChild(canvasClone);
    
    const modal = new bootstrap.Modal(previewModal);
    modal.show();
  }

  createPreviewModal() {
    // Modal já existe no template, apenas mostrar
    const modal = new bootstrap.Modal(document.getElementById('previewModal'));
    modal.show();
  }

  toggleLivePreview() {
    this.isLivePreview = !this.isLivePreview;
    const btn = document.getElementById('livePreviewToggle');
    
    if (this.isLivePreview) {
      btn.classList.add('active');
      btn.textContent = 'Desativar Preview';
    } else {
      btn.classList.remove('active');
      btn.textContent = 'Preview Dinâmico';
    }
  }

  exportTemplate() {
    const templateData = {
      name: document.getElementById('templateName').value || 'Template',
      orientation: document.getElementById('templateOrientation').value || 'landscape',
      elements: this.elements
    };
    
    const dataStr = JSON.stringify(templateData, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    const url = URL.createObjectURL(dataBlob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `${templateData.name}.json`;
    link.click();
    
    URL.revokeObjectURL(url);
  }

  exportToPDF() {
    const templateData = {
      name: document.getElementById('templateName').value || 'Template',
      orientation: document.getElementById('templateOrientation').value || 'landscape',
      elements: this.elements.map(el => {
        const domElement = document.getElementById(el.id);
        return {
          ...el,
          style: domElement ? domElement.style.cssText : '',
          innerHTML: domElement ? domElement.innerHTML : '',
          position: {
            x: domElement ? parseFloat(domElement.getAttribute('data-x')) || 0 : 0,
            y: domElement ? parseFloat(domElement.getAttribute('data-y')) || 0 : 0
          }
        };
      })
    };
    
    // Enviar dados para o servidor para gerar PDF
    fetch('/certificado/gerar_pdf_template', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(templateData)
    })
    .then(response => {
      if (response.ok) {
        return response.blob();
      }
      throw new Error('Erro ao gerar PDF');
    })
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${templateData.name}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
    })
    .catch(error => {
      console.error('Erro:', error);
      alert('Erro ao gerar PDF: ' + error.message);
    });
  }

  loadTemplate() {
    // Carregar template existente se houver
    const templateId = new URLSearchParams(window.location.search).get('template_id');
    if (templateId) {
      fetch(`/certificado/carregar_template/${templateId}`)
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            this.loadState(data.template);
          }
        })
        .catch(error => {
          console.error('Erro ao carregar template:', error);
        });
    }
  }

  loadDynamicVariables() {
    fetch('/certificado/variaveis_dinamicas')
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          this.populateVariableSelects(data.variables);
        }
      })
      .catch(error => {
        console.error('Erro ao carregar variáveis:', error);
      });
  }

  populateVariableSelects(variables) {
    const select = document.getElementById('customVariableSelect');
    if (select) {
      select.innerHTML = '<option value="">Selecione uma variável</option>';
      variables.forEach(variable => {
        const option = document.createElement('option');
        option.value = variable.nome;
        option.textContent = `${variable.nome} - ${variable.descricao}`;
        select.appendChild(option);
      });
    }
  }

  replaceVariablesForPreview(container) {
    const sampleData = {
      'NOME_PARTICIPANTE': 'João Silva Santos',
      'CARGA_HORARIA': '40',
      'LISTA_OFICINAS': 'Oficina de Programação, Oficina de Design, Oficina de Marketing Digital',
      'DATA_EMISSAO': new Date().toLocaleDateString('pt-BR'),
      'NOME_INSTITUICAO': 'Instituto de Tecnologia',
      'NOME_CURSO': 'Curso de Desenvolvimento Web',
      'PERIODO': '01/01/2024 a 31/01/2024'
    };
    
    container.querySelectorAll('*').forEach(element => {
      if (element.innerHTML) {
        let content = element.innerHTML;
        Object.keys(sampleData).forEach(variable => {
          const regex = new RegExp(`\\{${variable}\\}`, 'g');
          content = content.replace(regex, sampleData[variable]);
        });
        element.innerHTML = content;
      }
    });
  }

  addDefaultVariables() {
    const defaultVariables = [
      { nome: 'NOME_INSTITUICAO', descricao: 'Nome da Instituição' },
      { nome: 'NOME_CURSO', descricao: 'Nome do Curso' },
      { nome: 'PERIODO', descricao: 'Período do Curso' }
    ];
    
    const container = document.getElementById('dynamicVariables');
    if (container) {
      defaultVariables.forEach(variavel => {
        const item = document.createElement('div');
        item.className = 'element-item';
        item.innerHTML = `
          <i class="fas fa-tag me-2"></i>
          <strong>{${variavel.nome}}</strong>
          <small class="d-block text-muted">${variavel.descricao}</small>
        `;
        item.addEventListener('click', () => {
          this.addVariableElement(variavel);
        });
        container.appendChild(item);
      });
    }
  }

  addVariableElement(variavel) {
    const element = this.createElement('variable');
    element.innerHTML = `{${variavel.nome}}`;
    
    const centerX = this.canvas.offsetWidth / 2 - 50;
    const centerY = this.canvas.offsetHeight / 2 - 25;
    element.style.left = centerX + 'px';
    element.style.top = centerY + 'px';
    element.setAttribute('data-x', centerX);
    element.setAttribute('data-y', centerY);
    
    this.canvas.appendChild(element);
    this.elements.push({
      id: element.id,
      type: 'variable',
      variavel: variavel.nome,
      properties: this.getDefaultProperties('variable')
    });
    
    this.selectElement(element);
    this.saveState();
    this.setupDragAndDrop();
  }
}

// Inicialização global
let editor;

document.addEventListener('DOMContentLoaded', function() {
  editor = new CertificateEditor();
  
  // Carregar variáveis dinâmicas
  editor.loadDynamicVariables();
  editor.addDefaultVariables();
});

// Exportar para uso global
window.CertificateEditor = CertificateEditor;
window.editor = editor;