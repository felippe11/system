/**
 * Canva-like Editor - Advanced Drag & Drop System
 * Sistema de edição visual com funcionalidades avançadas
 */

class CanvaEditor {
    constructor() {
        this.canvas = null;
        this.selectedElement = null;
        this.elements = [];
        this.layers = [];
        this.history = [];
        this.historyIndex = -1;
        this.zoom = 1;
        this.isDragging = false;
        this.dragOffset = { x: 0, y: 0 };
        
        this.init();
    }

    init() {
        this.initCanvas();
        this.initEventListeners();
        this.initTabs();
        this.initDragAndDrop();
        this.initKeyboardShortcuts();
        this.updateLayersPanel();
        
        // Carregar elementos da biblioteca
        this.loadElementLibrary();
        
        // Carregar templates
        this.loadTemplates();
        
        // Carregar paletas de cores
        this.loadColorPalettes();
        
        // Carregar fontes
        this.loadFonts();
    }

    async loadElementLibrary() {
        try {
            const response = await fetch('/editor/elements');
            const elements = await response.json();
            
            this.renderElementLibrary(elements);
        } catch (error) {
            console.error('Erro ao carregar elementos:', error);
        }
    }
    
    renderElementLibrary(elements) {
        const elementsContainer = document.getElementById('elements-list');
        if (!elementsContainer) return;
        
        elementsContainer.innerHTML = '';
        
        // Renderizar formas
        if (elements.shapes) {
            const shapesSection = this.createElementSection('Formas', elements.shapes.items);
            elementsContainer.appendChild(shapesSection);
        }
        
        // Renderizar texto
        if (elements.text) {
            const textSection = this.createElementSection('Texto', elements.text.items);
            elementsContainer.appendChild(textSection);
        }
        
        // Renderizar ícones
        if (elements.icons) {
            const iconsSection = this.createIconsSection(elements.icons);
            elementsContainer.appendChild(iconsSection);
        }
        
        // Renderizar gráficos
        if (elements.graphics) {
            const graphicsSection = this.createElementSection('Gráficos', elements.graphics.items);
            elementsContainer.appendChild(graphicsSection);
        }
    }
    
    createElementSection(title, items) {
        const section = document.createElement('div');
        section.className = 'element-section mb-3';
        
        const header = document.createElement('h6');
        header.className = 'element-section-title';
        header.textContent = title;
        section.appendChild(header);
        
        const grid = document.createElement('div');
        grid.className = 'element-grid';
        
        items.forEach(item => {
            const element = document.createElement('div');
            element.className = 'element-item';
            element.draggable = true;
            element.dataset.elementType = item.id;
            element.dataset.elementName = item.name;
            
            if (item.icon) {
                element.innerHTML = `<i class="fas fa-${item.icon}"></i><span>${item.name}</span>`;
            } else if (item.preview) {
                element.innerHTML = `<span class="preview">${item.preview}</span>`;
            } else {
                element.innerHTML = `<span>${item.name}</span>`;
            }
            
            // Adicionar evento de drag
            element.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', JSON.stringify({
                    type: item.id,
                    name: item.name,
                    category: title.toLowerCase()
                }));
            });
            
            // Adicionar evento de clique
            element.addEventListener('click', () => {
                this.addElementToCanvas(item, title.toLowerCase());
            });
            
            grid.appendChild(element);
        });
        
        section.appendChild(grid);
        return section;
    }
    
    createIconsSection(iconsData) {
        const section = document.createElement('div');
        section.className = 'element-section mb-3';
        
        const header = document.createElement('h6');
        header.className = 'element-section-title';
        header.textContent = 'Ícones';
        section.appendChild(header);
        
        iconsData.categories.forEach(category => {
            const categoryDiv = document.createElement('div');
            categoryDiv.className = 'icon-category mb-2';
            
            const categoryTitle = document.createElement('div');
            categoryTitle.className = 'icon-category-title';
            categoryTitle.textContent = category.name;
            categoryDiv.appendChild(categoryTitle);
            
            const grid = document.createElement('div');
            grid.className = 'element-grid';
            
            category.items.forEach(icon => {
                const element = document.createElement('div');
                element.className = 'element-item icon-item';
                element.draggable = true;
                element.dataset.elementType = 'icon';
                element.dataset.iconClass = icon.id;
                element.title = icon.name;
                
                element.innerHTML = `<i class="${icon.id}"></i>`;
                
                // Adicionar evento de drag
                element.addEventListener('dragstart', (e) => {
                    e.dataTransfer.setData('text/plain', JSON.stringify({
                        type: 'icon',
                        iconClass: icon.id,
                        name: icon.name
                    }));
                });
                
                // Adicionar evento de clique
                element.addEventListener('click', () => {
                    this.addIconToCanvas(icon);
                });
                
                grid.appendChild(element);
            });
            
            categoryDiv.appendChild(grid);
            section.appendChild(categoryDiv);
        });
        
        return section;
    }
    
    addElementToCanvas(item, category) {
        let fabricObject;
        
        switch (category) {
            case 'formas':
                fabricObject = this.createShape(item.id);
                break;
            case 'texto':
                fabricObject = this.createText(item.id);
                break;
            case 'gráficos':
                fabricObject = this.createGraphic(item.id);
                break;
            default:
                return;
        }
        
        if (fabricObject) {
            this.canvas.add(fabricObject);
            this.canvas.setActiveObject(fabricObject);
            this.updateLayersPanel();
            this.saveState();
        }
    }
    
    createShape(shapeType) {
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        
        switch (shapeType) {
            case 'rectangle':
                return new fabric.Rect({
                    left: centerX - 50,
                    top: centerY - 25,
                    width: 100,
                    height: 50,
                    fill: '#3498db',
                    stroke: '#2980b9',
                    strokeWidth: 2
                });
            case 'circle':
                return new fabric.Circle({
                    left: centerX - 25,
                    top: centerY - 25,
                    radius: 25,
                    fill: '#e74c3c',
                    stroke: '#c0392b',
                    strokeWidth: 2
                });
            case 'triangle':
                return new fabric.Triangle({
                    left: centerX - 25,
                    top: centerY - 25,
                    width: 50,
                    height: 50,
                    fill: '#f39c12',
                    stroke: '#e67e22',
                    strokeWidth: 2
                });
            case 'line':
                return new fabric.Line([centerX - 50, centerY, centerX + 50, centerY], {
                    stroke: '#34495e',
                    strokeWidth: 3
                });
            case 'arrow':
                // Criar uma seta usando Path
                const arrowPath = 'M 0 0 L 40 0 L 35 -5 M 40 0 L 35 5';
                return new fabric.Path(arrowPath, {
                    left: centerX - 20,
                    top: centerY,
                    stroke: '#9b59b6',
                    strokeWidth: 3,
                    fill: ''
                });
            default:
                return null;
        }
    }
    
    createText(textType) {
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        
        const textStyles = {
            heading: { fontSize: 32, fontWeight: 'bold', text: 'Título Principal' },
            subtitle: { fontSize: 24, fontWeight: 'normal', text: 'Subtítulo' },
            body: { fontSize: 16, fontWeight: 'normal', text: 'Texto do corpo' },
            caption: { fontSize: 12, fontWeight: 'normal', text: 'Legenda pequena' }
        };
        
        const style = textStyles[textType] || textStyles.body;
        
        return new fabric.Text(style.text, {
            left: centerX,
            top: centerY,
            fontSize: style.fontSize,
            fontWeight: style.fontWeight,
            fill: '#2c3e50',
            fontFamily: 'Inter, sans-serif',
            originX: 'center',
            originY: 'center'
        });
    }
    
    addIconToCanvas(icon) {
        // Criar um elemento temporário para renderizar o ícone
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = `<i class="${icon.id}" style="font-size: 48px; color: #2c3e50;"></i>`;
        document.body.appendChild(tempDiv);
        
        // Converter para SVG e adicionar ao canvas
        const iconElement = tempDiv.querySelector('i');
        const computedStyle = window.getComputedStyle(iconElement);
        
        // Criar texto com a fonte de ícone
        const iconText = new fabric.Text(iconElement.textContent || '\\' + icon.id.split(' ').pop(), {
            left: this.canvas.width / 2,
            top: this.canvas.height / 2,
            fontSize: 48,
            fill: '#2c3e50',
            fontFamily: icon.id.startsWith('fab') ? 'Font Awesome 6 Brands' : 'Font Awesome 6 Free',
            fontWeight: icon.id.includes('fas') ? '900' : '400',
            originX: 'center',
            originY: 'center'
        });
        
        this.canvas.add(iconText);
        this.canvas.setActiveObject(iconText);
        this.updateLayersPanel();
        this.saveState();
        
        document.body.removeChild(tempDiv);
    }
    
    async loadTemplates() {
        try {
            const response = await fetch('/editor/templates');
            const templates = await response.json();
            
            this.renderTemplates(templates);
        } catch (error) {
            console.error('Erro ao carregar templates:', error);
        }
    }
    
    renderTemplates(templates) {
        const templatesContainer = document.getElementById('templates-list');
        if (!templatesContainer) return;
        
        templatesContainer.innerHTML = '';
        
        Object.entries(templates).forEach(([key, template]) => {
            const templateItem = document.createElement('div');
            templateItem.className = 'template-item';
            templateItem.innerHTML = `
                <div class="template-thumbnail">
                    <img src="${template.thumbnail}" alt="${template.name}" onerror="this.style.display='none'">
                    <div class="template-overlay">
                        <i class="fas fa-plus"></i>
                    </div>
                </div>
                <div class="template-info">
                    <h6>${template.name}</h6>
                    <p>${template.description}</p>
                    <span class="template-category">${template.category}</span>
                </div>
            `;
            
            templateItem.addEventListener('click', () => {
                this.loadTemplate(key, template);
            });
            
            templatesContainer.appendChild(templateItem);
        });
    }
    
    async loadColorPalettes() {
        try {
            const response = await fetch('/editor/colors');
            const palettes = await response.json();
            
            this.renderColorPalettes(palettes);
        } catch (error) {
            console.error('Erro ao carregar paletas:', error);
        }
    }
    
    renderColorPalettes(palettes) {
        const colorsContainer = document.getElementById('colors-list');
        if (!colorsContainer) return;
        
        colorsContainer.innerHTML = '';
        
        Object.entries(palettes).forEach(([category, categoryPalettes]) => {
            const categoryDiv = document.createElement('div');
            categoryDiv.className = 'color-category mb-3';
            
            const categoryTitle = document.createElement('h6');
            categoryTitle.className = 'color-category-title';
            categoryTitle.textContent = category.charAt(0).toUpperCase() + category.slice(1);
            categoryDiv.appendChild(categoryTitle);
            
            categoryPalettes.forEach(palette => {
                const paletteDiv = document.createElement('div');
                paletteDiv.className = 'color-palette';
                
                const paletteTitle = document.createElement('div');
                paletteTitle.className = 'palette-title';
                paletteTitle.textContent = palette.name;
                paletteDiv.appendChild(paletteTitle);
                
                const colorsDiv = document.createElement('div');
                colorsDiv.className = 'palette-colors';
                
                palette.colors.forEach(color => {
                    const colorDiv = document.createElement('div');
                    colorDiv.className = 'color-swatch';
                    colorDiv.style.backgroundColor = color;
                    colorDiv.title = color;
                    
                    colorDiv.addEventListener('click', () => {
                        this.applyColorToSelected(color);
                    });
                    
                    colorsDiv.appendChild(colorDiv);
                });
                
                paletteDiv.appendChild(colorsDiv);
                categoryDiv.appendChild(paletteDiv);
            });
            
            colorsContainer.appendChild(categoryDiv);
        });
    }
    
    async loadFonts() {
        try {
            const response = await fetch('/editor/fonts');
            const fonts = await response.json();
            
            this.renderFonts(fonts);
        } catch (error) {
            console.error('Erro ao carregar fontes:', error);
        }
    }
    
    renderFonts(fonts) {
        const fontsSelect = document.getElementById('font-family');
        if (!fontsSelect) return;
        
        fontsSelect.innerHTML = '';
        
        // Adicionar fontes do sistema
        if (fonts.system_fonts) {
            const systemGroup = document.createElement('optgroup');
            systemGroup.label = 'Fontes do Sistema';
            
            fonts.system_fonts.forEach(font => {
                const option = document.createElement('option');
                option.value = font.family;
                option.textContent = font.name;
                option.style.fontFamily = font.family;
                systemGroup.appendChild(option);
            });
            
            fontsSelect.appendChild(systemGroup);
        }
        
        // Adicionar Google Fonts
        if (fonts.google_fonts) {
            const googleGroup = document.createElement('optgroup');
            googleGroup.label = 'Google Fonts';
            
            fonts.google_fonts.forEach(font => {
                const option = document.createElement('option');
                option.value = font.family;
                option.textContent = font.name;
                option.style.fontFamily = font.family;
                googleGroup.appendChild(option);
            });
            
            fontsSelect.appendChild(googleGroup);
        }
    }
    
    applyColorToSelected(color) {
        const activeObject = this.canvas.getActiveObject();
        if (activeObject) {
            if (activeObject.type === 'text') {
                activeObject.set('fill', color);
            } else {
                activeObject.set('fill', color);
            }
            this.canvas.renderAll();
            this.updatePropertiesPanel();
            this.saveState();
        }
    }

    initCanvas() {
        const canvasElement = document.getElementById('main-canvas');
        this.canvas = new fabric.Canvas('main-canvas', {
            width: 800,
            height: 600,
            backgroundColor: '#ffffff',
            selection: true,
            preserveObjectStacking: true
        });

        // Remove placeholder when canvas is ready
        const placeholder = canvasElement.querySelector('.canvas-placeholder');
        if (placeholder) {
            placeholder.style.display = 'none';
        }

        // Canvas event listeners
        this.canvas.on('selection:created', (e) => this.onElementSelected(e.selected[0]));
        this.canvas.on('selection:updated', (e) => this.onElementSelected(e.selected[0]));
        this.canvas.on('selection:cleared', () => this.onElementDeselected());
        this.canvas.on('object:modified', () => this.saveState());
        this.canvas.on('object:added', () => this.updateLayersPanel());
        this.canvas.on('object:removed', () => this.updateLayersPanel());
    }

    initEventListeners() {
        // Header buttons
        document.getElementById('undo-btn').addEventListener('click', () => this.undo());
        document.getElementById('redo-btn').addEventListener('click', () => this.redo());
        document.getElementById('zoom-in').addEventListener('click', () => this.zoomIn());
        document.getElementById('zoom-out').addEventListener('click', () => this.zoomOut());
        document.getElementById('fit-to-screen').addEventListener('click', () => this.fitToScreen());
        document.getElementById('actual-size').addEventListener('click', () => this.actualSize());
        document.getElementById('save-btn').addEventListener('click', () => this.saveProject());
        document.getElementById('preview-btn').addEventListener('click', () => this.preview());
        document.getElementById('share-btn').addEventListener('click', () => this.share());

        // Project name
        document.querySelector('.project-name').addEventListener('blur', (e) => {
            this.projectName = e.target.value;
        });

        // Image upload
        document.getElementById('image-upload').addEventListener('change', (e) => {
            this.handleImageUpload(e.target.files);
        });

        // Upload area click
        document.querySelector('.upload-area').addEventListener('click', () => {
            document.getElementById('image-upload').click();
        });

        // Layers panel toggle
        document.getElementById('toggle-layers').addEventListener('click', () => {
            this.toggleLayersPanel();
        });
    }

    initTabs() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');

        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabId = button.dataset.tab;
                
                // Update active tab button
                tabButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                
                // Update active tab content
                tabContents.forEach(content => content.classList.remove('active'));
                document.getElementById(`${tabId}-tab`).classList.add('active');
            });
        });
    }

    initDragAndDrop() {
        // Template items
        document.querySelectorAll('.template-item').forEach(item => {
            this.makeDraggable(item, 'template');
        });

        // Element items
        document.querySelectorAll('.element-item').forEach(item => {
            this.makeDraggable(item, 'element');
        });

        // Text buttons
        document.querySelectorAll('.text-btn').forEach(item => {
            this.makeDraggable(item, 'text');
        });

        // Icon items
        document.querySelectorAll('.icon-item').forEach(item => {
            this.makeDraggable(item, 'icon');
        });

        // Canvas drop zone
        this.initCanvasDropZone();
    }

    makeDraggable(element, type) {
        element.draggable = true;
        
        element.addEventListener('dragstart', (e) => {
            element.classList.add('dragging');
            e.dataTransfer.setData('text/plain', JSON.stringify({
                type: type,
                data: this.getElementData(element, type)
            }));
        });

        element.addEventListener('dragend', () => {
            element.classList.remove('dragging');
        });

        // Also add click handler for direct addition
        element.addEventListener('click', () => {
            this.addElementToCanvas(type, this.getElementData(element, type));
        });
    }

    getElementData(element, type) {
        switch (type) {
            case 'template':
                return { template: element.dataset.template };
            case 'element':
                return { element: element.dataset.element };
            case 'text':
                return { textType: element.dataset.text };
            case 'icon':
                return { icon: element.dataset.icon };
            default:
                return {};
        }
    }

    initCanvasDropZone() {
        const canvasContainer = document.querySelector('.canvas-container');
        
        canvasContainer.addEventListener('dragover', (e) => {
            e.preventDefault();
            canvasContainer.classList.add('drop-zone');
        });

        canvasContainer.addEventListener('dragleave', (e) => {
            if (!canvasContainer.contains(e.relatedTarget)) {
                canvasContainer.classList.remove('drop-zone');
            }
        });

        canvasContainer.addEventListener('drop', (e) => {
            e.preventDefault();
            canvasContainer.classList.remove('drop-zone');
            
            const data = JSON.parse(e.dataTransfer.getData('text/plain'));
            const rect = this.canvas.getElement().getBoundingClientRect();
            const x = (e.clientX - rect.left) / this.zoom;
            const y = (e.clientY - rect.top) / this.zoom;
            
            this.addElementToCanvas(data.type, data.data, { x, y });
        });
    }

    addElementToCanvas(type, data, position = null) {
        let element;
        const pos = position || { x: 100, y: 100 };

        switch (type) {
            case 'template':
                this.loadTemplate(data.template);
                break;
            case 'element':
                element = this.createElement(data.element, pos);
                break;
            case 'text':
                element = this.createText(data.textType, pos);
                break;
            case 'icon':
                element = this.createIcon(data.icon, pos);
                break;
        }

        if (element) {
            this.canvas.add(element);
            this.canvas.setActiveObject(element);
            this.saveState();
        }
    }

    createElement(elementType, position) {
        let element;
        
        switch (elementType) {
            case 'rectangle':
                element = new fabric.Rect({
                    left: position.x,
                    top: position.y,
                    width: 100,
                    height: 60,
                    fill: '#8b5cf6',
                    stroke: '#7c3aed',
                    strokeWidth: 2,
                    rx: 8,
                    ry: 8
                });
                break;
            case 'circle':
                element = new fabric.Circle({
                    left: position.x,
                    top: position.y,
                    radius: 40,
                    fill: '#06b6d4',
                    stroke: '#0891b2',
                    strokeWidth: 2
                });
                break;
            case 'triangle':
                element = new fabric.Triangle({
                    left: position.x,
                    top: position.y,
                    width: 80,
                    height: 80,
                    fill: '#f59e0b',
                    stroke: '#d97706',
                    strokeWidth: 2
                });
                break;
            case 'line':
                element = new fabric.Line([0, 0, 100, 0], {
                    left: position.x,
                    top: position.y,
                    stroke: '#1f2937',
                    strokeWidth: 3,
                    strokeLineCap: 'round'
                });
                break;
        }

        if (element) {
            element.set({
                id: this.generateId(),
                name: `${elementType}_${this.elements.length + 1}`
            });
            this.elements.push(element);
        }

        return element;
    }

    createText(textType, position) {
        let text, fontSize, fontWeight;
        
        switch (textType) {
            case 'heading':
                text = 'Título Principal';
                fontSize = 32;
                fontWeight = 'bold';
                break;
            case 'subtitle':
                text = 'Subtítulo';
                fontSize = 24;
                fontWeight = '600';
                break;
            case 'body':
                text = 'Texto do corpo';
                fontSize = 16;
                fontWeight = 'normal';
                break;
        }

        const textElement = new fabric.Text(text, {
            left: position.x,
            top: position.y,
            fontSize: fontSize,
            fontWeight: fontWeight,
            fontFamily: 'Inter, sans-serif',
            fill: '#1f2937',
            editable: true
        });

        textElement.set({
            id: this.generateId(),
            name: `text_${this.elements.length + 1}`
        });
        
        this.elements.push(textElement);
        return textElement;
    }

    createIcon(iconClass, position) {
        // For icons, we'll create a text element with the icon font
        const iconElement = new fabric.Text('', {
            left: position.x,
            top: position.y,
            fontSize: 32,
            fontFamily: 'Font Awesome 6 Free',
            fontWeight: '900',
            fill: '#6b7280'
        });

        // Set the icon character based on the class
        const iconMap = {
            'fas fa-heart': '\uf004',
            'fas fa-star': '\uf005',
            'fas fa-home': '\uf015',
            'fas fa-user': '\uf007'
        };

        iconElement.set('text', iconMap[iconClass] || '\uf005');
        iconElement.set({
            id: this.generateId(),
            name: `icon_${this.elements.length + 1}`
        });
        
        this.elements.push(iconElement);
        return iconElement;
    }

    loadTemplate(templateType) {
        this.canvas.clear();
        this.elements = [];
        
        switch (templateType) {
            case 'blank':
                // Already cleared
                break;
            case 'presentation':
                this.loadPresentationTemplate();
                break;
            case 'poster':
                this.loadPosterTemplate();
                break;
            case 'social':
                this.loadSocialTemplate();
                break;
        }
        
        this.saveState();
    }

    loadPresentationTemplate() {
        // Add background
        const bg = new fabric.Rect({
            left: 0,
            top: 0,
            width: 800,
            height: 600,
            fill: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            selectable: false
        });
        
        // Add title
        const title = new fabric.Text('Título da Apresentação', {
            left: 50,
            top: 100,
            fontSize: 48,
            fontWeight: 'bold',
            fontFamily: 'Inter, sans-serif',
            fill: '#ffffff'
        });
        
        // Add subtitle
        const subtitle = new fabric.Text('Subtítulo ou descrição', {
            left: 50,
            top: 180,
            fontSize: 24,
            fontFamily: 'Inter, sans-serif',
            fill: '#e2e8f0'
        });
        
        this.canvas.add(bg, title, subtitle);
    }

    loadPosterTemplate() {
        // Add colorful background
        const bg = new fabric.Rect({
            left: 0,
            top: 0,
            width: 800,
            height: 600,
            fill: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            selectable: false
        });
        
        // Add main title
        const title = new fabric.Text('EVENTO', {
            left: 400,
            top: 150,
            fontSize: 64,
            fontWeight: 'bold',
            fontFamily: 'Inter, sans-serif',
            fill: '#ffffff',
            textAlign: 'center',
            originX: 'center'
        });
        
        // Add date
        const date = new fabric.Text('25 DE DEZEMBRO', {
            left: 400,
            top: 250,
            fontSize: 24,
            fontFamily: 'Inter, sans-serif',
            fill: '#ffffff',
            textAlign: 'center',
            originX: 'center'
        });
        
        this.canvas.add(bg, title, date);
    }

    loadSocialTemplate() {
        // Add gradient background
        const bg = new fabric.Rect({
            left: 0,
            top: 0,
            width: 800,
            height: 600,
            fill: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
            selectable: false
        });
        
        // Add content area
        const contentBg = new fabric.Rect({
            left: 100,
            top: 100,
            width: 600,
            height: 400,
            fill: '#ffffff',
            rx: 20,
            ry: 20,
            shadow: 'rgba(0,0,0,0.1) 0px 10px 30px'
        });
        
        // Add text
        const text = new fabric.Text('Sua mensagem aqui', {
            left: 400,
            top: 300,
            fontSize: 32,
            fontFamily: 'Inter, sans-serif',
            fill: '#1f2937',
            textAlign: 'center',
            originX: 'center'
        });
        
        this.canvas.add(bg, contentBg, text);
    }

    onElementSelected(element) {
        this.selectedElement = element;
        this.updatePropertiesPanel(element);
        this.highlightLayerItem(element);
    }

    onElementDeselected() {
        this.selectedElement = null;
        this.showNoSelectionMessage();
        this.removeLayerHighlight();
    }

    updatePropertiesPanel(element) {
        const panel = document.getElementById('properties-panel');
        
        if (!element) {
            this.showNoSelectionMessage();
            return;
        }

        const properties = this.getElementProperties(element);
        panel.innerHTML = this.generatePropertiesHTML(properties, element);
        this.bindPropertyEvents(element);
    }

    getElementProperties(element) {
        const baseProperties = {
            x: Math.round(element.left),
            y: Math.round(element.top),
            width: Math.round(element.width * element.scaleX),
            height: Math.round(element.height * element.scaleY),
            rotation: Math.round(element.angle),
            opacity: Math.round(element.opacity * 100)
        };

        if (element.type === 'text') {
            return {
                ...baseProperties,
                text: element.text,
                fontSize: element.fontSize,
                fontFamily: element.fontFamily,
                fontWeight: element.fontWeight,
                fill: element.fill,
                textAlign: element.textAlign
            };
        } else if (element.fill) {
            return {
                ...baseProperties,
                fill: element.fill,
                stroke: element.stroke,
                strokeWidth: element.strokeWidth
            };
        }

        return baseProperties;
    }

    generatePropertiesHTML(properties, element) {
        let html = `
            <div class="property-section">
                <h4>Posição e Tamanho</h4>
                <div class="property-row">
                    <div class="property-group">
                        <label>X</label>
                        <input type="number" id="prop-x" value="${properties.x}">
                    </div>
                    <div class="property-group">
                        <label>Y</label>
                        <input type="number" id="prop-y" value="${properties.y}">
                    </div>
                </div>
                <div class="property-row">
                    <div class="property-group">
                        <label>Largura</label>
                        <input type="number" id="prop-width" value="${properties.width}">
                    </div>
                    <div class="property-group">
                        <label>Altura</label>
                        <input type="number" id="prop-height" value="${properties.height}">
                    </div>
                </div>
                <div class="property-row">
                    <div class="property-group">
                        <label>Rotação</label>
                        <input type="number" id="prop-rotation" value="${properties.rotation}" min="0" max="360">
                    </div>
                    <div class="property-group">
                        <label>Opacidade</label>
                        <input type="range" id="prop-opacity" value="${properties.opacity}" min="0" max="100">
                    </div>
                </div>
            </div>
        `;

        if (element.type === 'text') {
            html += `
                <div class="property-section">
                    <h4>Texto</h4>
                    <div class="property-group">
                        <label>Conteúdo</label>
                        <textarea id="prop-text" rows="3">${properties.text}</textarea>
                    </div>
                    <div class="property-row">
                        <div class="property-group">
                            <label>Tamanho</label>
                            <input type="number" id="prop-fontsize" value="${properties.fontSize}" min="8" max="200">
                        </div>
                        <div class="property-group">
                            <label>Peso</label>
                            <select id="prop-fontweight">
                                <option value="normal" ${properties.fontWeight === 'normal' ? 'selected' : ''}>Normal</option>
                                <option value="bold" ${properties.fontWeight === 'bold' ? 'selected' : ''}>Negrito</option>
                                <option value="600" ${properties.fontWeight === '600' ? 'selected' : ''}>Semi-negrito</option>
                            </select>
                        </div>
                    </div>
                    <div class="property-group">
                        <label>Cor</label>
                        <input type="color" id="prop-textcolor" value="${this.rgbToHex(properties.fill)}">
                    </div>
                </div>
            `;
        } else if (properties.fill) {
            html += `
                <div class="property-section">
                    <h4>Aparência</h4>
                    <div class="property-group">
                        <label>Cor de Preenchimento</label>
                        <input type="color" id="prop-fill" value="${this.rgbToHex(properties.fill)}">
                    </div>
                    ${properties.stroke ? `
                        <div class="property-row">
                            <div class="property-group">
                                <label>Cor da Borda</label>
                                <input type="color" id="prop-stroke" value="${this.rgbToHex(properties.stroke)}">
                            </div>
                            <div class="property-group">
                                <label>Espessura</label>
                                <input type="number" id="prop-strokewidth" value="${properties.strokeWidth}" min="0" max="20">
                            </div>
                        </div>
                    ` : ''}
                </div>
            `;
        }

        html += `
            <div class="property-section">
                <h4>Ações</h4>
                <div class="action-buttons">
                    <button class="btn-action" id="duplicate-element">
                        <i class="fas fa-copy"></i> Duplicar
                    </button>
                    <button class="btn-action delete" id="delete-element">
                        <i class="fas fa-trash"></i> Excluir
                    </button>
                </div>
            </div>
        `;

        return html;
    }

    bindPropertyEvents(element) {
        // Position and size
        this.bindPropertyInput('prop-x', (value) => {
            element.set('left', parseInt(value));
            this.canvas.renderAll();
        });

        this.bindPropertyInput('prop-y', (value) => {
            element.set('top', parseInt(value));
            this.canvas.renderAll();
        });

        this.bindPropertyInput('prop-width', (value) => {
            const scale = parseInt(value) / element.width;
            element.set('scaleX', scale);
            this.canvas.renderAll();
        });

        this.bindPropertyInput('prop-height', (value) => {
            const scale = parseInt(value) / element.height;
            element.set('scaleY', scale);
            this.canvas.renderAll();
        });

        this.bindPropertyInput('prop-rotation', (value) => {
            element.set('angle', parseInt(value));
            this.canvas.renderAll();
        });

        this.bindPropertyInput('prop-opacity', (value) => {
            element.set('opacity', parseInt(value) / 100);
            this.canvas.renderAll();
        });

        // Text properties
        if (element.type === 'text') {
            this.bindPropertyInput('prop-text', (value) => {
                element.set('text', value);
                this.canvas.renderAll();
            });

            this.bindPropertyInput('prop-fontsize', (value) => {
                element.set('fontSize', parseInt(value));
                this.canvas.renderAll();
            });

            this.bindPropertyInput('prop-fontweight', (value) => {
                element.set('fontWeight', value);
                this.canvas.renderAll();
            });

            this.bindPropertyInput('prop-textcolor', (value) => {
                element.set('fill', value);
                this.canvas.renderAll();
            });
        }

        // Appearance properties
        if (document.getElementById('prop-fill')) {
            this.bindPropertyInput('prop-fill', (value) => {
                element.set('fill', value);
                this.canvas.renderAll();
            });
        }

        if (document.getElementById('prop-stroke')) {
            this.bindPropertyInput('prop-stroke', (value) => {
                element.set('stroke', value);
                this.canvas.renderAll();
            });
        }

        if (document.getElementById('prop-strokewidth')) {
            this.bindPropertyInput('prop-strokewidth', (value) => {
                element.set('strokeWidth', parseInt(value));
                this.canvas.renderAll();
            });
        }

        // Action buttons
        document.getElementById('duplicate-element')?.addEventListener('click', () => {
            this.duplicateElement(element);
        });

        document.getElementById('delete-element')?.addEventListener('click', () => {
            this.deleteElement(element);
        });
    }

    bindPropertyInput(id, callback) {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener('input', (e) => {
                callback(e.target.value);
                this.saveState();
            });
        }
    }

    showNoSelectionMessage() {
        const panel = document.getElementById('properties-panel');
        panel.innerHTML = `
            <div class="no-selection">
                <i class="fas fa-mouse-pointer"></i>
                <p>Selecione um elemento para editar suas propriedades</p>
            </div>
        `;
    }

    updateLayersPanel() {
        const layersList = document.getElementById('layers-list');
        const objects = this.canvas.getObjects();
        
        layersList.innerHTML = '';
        
        objects.forEach((obj, index) => {
            const layerItem = document.createElement('div');
            layerItem.className = 'layer-item';
            layerItem.dataset.objectId = obj.id || index;
            
            const name = obj.name || `${obj.type}_${index + 1}`;
            const isVisible = obj.visible !== false;
            
            layerItem.innerHTML = `
                <div class="layer-content">
                    <i class="layer-icon fas fa-${this.getLayerIcon(obj.type)}"></i>
                    <span class="layer-name">${name}</span>
                    <button class="layer-visibility ${isVisible ? 'visible' : 'hidden'}" 
                            title="${isVisible ? 'Ocultar' : 'Mostrar'}">
                        <i class="fas fa-${isVisible ? 'eye' : 'eye-slash'}"></i>
                    </button>
                </div>
            `;
            
            // Layer click to select
            layerItem.addEventListener('click', () => {
                this.canvas.setActiveObject(obj);
                this.canvas.renderAll();
            });
            
            // Visibility toggle
            layerItem.querySelector('.layer-visibility').addEventListener('click', (e) => {
                e.stopPropagation();
                obj.set('visible', !obj.visible);
                this.canvas.renderAll();
                this.updateLayersPanel();
            });
            
            layersList.appendChild(layerItem);
        });
    }

    getLayerIcon(type) {
        const icons = {
            'text': 'font',
            'rect': 'square',
            'circle': 'circle',
            'triangle': 'play',
            'line': 'minus',
            'image': 'image'
        };
        return icons[type] || 'square';
    }

    highlightLayerItem(element) {
        document.querySelectorAll('.layer-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const layerItem = document.querySelector(`[data-object-id="${element.id}"]`);
        if (layerItem) {
            layerItem.classList.add('active');
        }
    }

    removeLayerHighlight() {
        document.querySelectorAll('.layer-item').forEach(item => {
            item.classList.remove('active');
        });
    }

    toggleLayersPanel() {
        const panel = document.getElementById('layers-panel');
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }

    // Utility methods
    generateId() {
        return 'element_' + Math.random().toString(36).substr(2, 9);
    }

    rgbToHex(rgb) {
        if (rgb.startsWith('#')) return rgb;
        const result = rgb.match(/\d+/g);
        if (!result) return '#000000';
        return '#' + result.map(x => parseInt(x).toString(16).padStart(2, '0')).join('');
    }

    duplicateElement(element) {
        element.clone((cloned) => {
            cloned.set({
                left: element.left + 20,
                top: element.top + 20,
                id: this.generateId()
            });
            this.canvas.add(cloned);
            this.canvas.setActiveObject(cloned);
            this.saveState();
        });
    }

    deleteElement(element) {
        this.canvas.remove(element);
        this.elements = this.elements.filter(el => el.id !== element.id);
        this.saveState();
    }

    // History management
    saveState() {
        const state = JSON.stringify(this.canvas.toJSON(['id', 'name']));
        this.history = this.history.slice(0, this.historyIndex + 1);
        this.history.push(state);
        this.historyIndex++;
        
        // Limit history size
        if (this.history.length > 50) {
            this.history.shift();
            this.historyIndex--;
        }
    }

    undo() {
        if (this.historyIndex > 0) {
            this.historyIndex--;
            this.loadState(this.history[this.historyIndex]);
        }
    }

    redo() {
        if (this.historyIndex < this.history.length - 1) {
            this.historyIndex++;
            this.loadState(this.history[this.historyIndex]);
        }
    }

    loadState(state) {
        this.canvas.loadFromJSON(state, () => {
            this.canvas.renderAll();
            this.updateLayersPanel();
        });
    }

    // Zoom controls
    zoomIn() {
        this.zoom = Math.min(this.zoom * 1.2, 5);
        this.updateZoom();
    }

    zoomOut() {
        this.zoom = Math.max(this.zoom / 1.2, 0.1);
        this.updateZoom();
    }

    fitToScreen() {
        const container = document.querySelector('.canvas-container');
        const containerWidth = container.clientWidth - 80;
        const containerHeight = container.clientHeight - 80;
        
        const scaleX = containerWidth / this.canvas.width;
        const scaleY = containerHeight / this.canvas.height;
        this.zoom = Math.min(scaleX, scaleY);
        
        this.updateZoom();
    }

    actualSize() {
        this.zoom = 1;
        this.updateZoom();
    }

    updateZoom() {
        this.canvas.setZoom(this.zoom);
        document.querySelector('.zoom-level').textContent = Math.round(this.zoom * 100) + '%';
    }

    // Keyboard shortcuts
    initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'z':
                        e.preventDefault();
                        if (e.shiftKey) {
                            this.redo();
                        } else {
                            this.undo();
                        }
                        break;
                    case 's':
                        e.preventDefault();
                        this.saveProject();
                        break;
                    case 'd':
                        e.preventDefault();
                        if (this.selectedElement) {
                            this.duplicateElement(this.selectedElement);
                        }
                        break;
                }
            } else if (e.key === 'Delete' && this.selectedElement) {
                this.deleteElement(this.selectedElement);
            }
        });
    }

    // File operations
    handleImageUpload(files) {
        Array.from(files).forEach(file => {
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    fabric.Image.fromURL(e.target.result, (img) => {
                        img.set({
                            left: 100,
                            top: 100,
                            scaleX: 0.5,
                            scaleY: 0.5,
                            id: this.generateId(),
                            name: `image_${this.elements.length + 1}`
                        });
                        this.canvas.add(img);
                        this.saveState();
                    });
                };
                reader.readAsDataURL(file);
            }
        });
    }

    saveProject() {
        const projectData = {
            name: document.querySelector('.project-name').value,
            canvas: this.canvas.toJSON(['id', 'name']),
            timestamp: new Date().toISOString()
        };
        
        // Save to localStorage for demo
        localStorage.setItem('canva_project', JSON.stringify(projectData));
        
        // Show success message
        this.showNotification('Projeto salvo com sucesso!', 'success');
    }

    preview() {
        const dataURL = this.canvas.toDataURL('image/png');
        const newWindow = window.open();
        newWindow.document.write(`
            <html>
                <head><title>Preview - ${document.querySelector('.project-name').value}</title></head>
                <body style="margin:0;padding:20px;background:#f0f0f0;display:flex;justify-content:center;align-items:center;min-height:100vh;">
                    <img src="${dataURL}" style="max-width:100%;max-height:100%;box-shadow:0 10px 30px rgba(0,0,0,0.3);">
                </body>
            </html>
        `);
    }

    share() {
        const dataURL = this.canvas.toDataURL('image/png');
        
        // Create download link
        const link = document.createElement('a');
        link.download = `${document.querySelector('.project-name').value || 'design'}.png`;
        link.href = dataURL;
        link.click();
        
        this.showNotification('Design exportado com sucesso!', 'success');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '12px 20px',
            borderRadius: '8px',
            color: 'white',
            fontWeight: '500',
            zIndex: '10000',
            transform: 'translateX(100%)',
            transition: 'transform 0.3s ease'
        });
        
        if (type === 'success') {
            notification.style.background = '#10b981';
        } else if (type === 'error') {
            notification.style.background = '#ef4444';
        } else {
            notification.style.background = '#3b82f6';
        }
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }
}

// Initialize editor when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.canvaEditor = new CanvaEditor();
});

// Add CSS for properties panel and layers
const additionalCSS = `
.property-section {
    margin-bottom: 24px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--border-color);
}

.property-section:last-child {
    border-bottom: none;
}

.property-section h4 {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 12px;
}

.property-row {
    display: flex;
    gap: 12px;
    margin-bottom: 12px;
}

.property-group {
    flex: 1;
}

.property-group label {
    display: block;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    margin-bottom: 4px;
}

.property-group input,
.property-group select,
.property-group textarea {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-sm);
    font-size: 14px;
    background: white;
}

.property-group input:focus,
.property-group select:focus,
.property-group textarea:focus {
    outline: none;
    border-color: var(--primary-color);
}

.action-buttons {
    display: flex;
    gap: 8px;
}

.btn-action {
    flex: 1;
    padding: 10px 16px;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    background: white;
    color: var(--text-primary);
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
}

.btn-action:hover {
    background: var(--secondary-color);
    border-color: var(--primary-color);
}

.btn-action.delete {
    color: #ef4444;
    border-color: #fecaca;
}

.btn-action.delete:hover {
    background: #fef2f2;
    border-color: #ef4444;
}

.layer-item {
    padding: 8px 12px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all 0.2s ease;
    margin-bottom: 4px;
}

.layer-item:hover {
    background: var(--secondary-color);
}

.layer-item.active {
    background: var(--primary-color);
    color: white;
}

.layer-content {
    display: flex;
    align-items: center;
    gap: 8px;
}

.layer-icon {
    width: 16px;
    font-size: 12px;
}

.layer-name {
    flex: 1;
    font-size: 14px;
    font-weight: 500;
}

.layer-visibility {
    background: none;
    border: none;
    padding: 4px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    color: inherit;
    opacity: 0.7;
    transition: all 0.2s ease;
}

.layer-visibility:hover {
    opacity: 1;
    background: rgba(255, 255, 255, 0.1);
}
`;

// Inject additional CSS
const style = document.createElement('style');
style.textContent = additionalCSS;
document.head.appendChild(style);