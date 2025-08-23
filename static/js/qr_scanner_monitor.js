// QR Scanner para Monitores
class QRScannerMonitor {
    constructor() {
        this.scanner = null;
        this.isScanning = false;
        this.agendamentoId = null;
    }

    // Inicializar scanner
    async init(agendamentoId) {
        this.agendamentoId = agendamentoId;
        
        try {
            // Verificar se o navegador suporta getUserMedia
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('Câmera não suportada neste navegador');
            }

            // Solicitar permissão para câmera
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment' // Câmera traseira preferencial
                }
            });

            // Configurar elemento de vídeo
            const video = document.getElementById('qr-video');
            if (video) {
                video.srcObject = stream;
                video.play();
                
                // Iniciar detecção quando o vídeo estiver pronto
                video.addEventListener('loadedmetadata', () => {
                    this.startDetection(video);
                });
            }

            this.isScanning = true;
            this.updateScannerStatus('Escaneando... Aponte a câmera para o QR Code');
            
        } catch (error) {
            console.error('Erro ao inicializar scanner:', error);
            this.updateScannerStatus('Erro: ' + error.message);
        }
    }

    // Iniciar detecção de QR Code
    startDetection(video) {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        
        const detectQR = () => {
            if (!this.isScanning) return;
            
            if (video.readyState === video.HAVE_ENOUGH_DATA) {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                context.drawImage(video, 0, 0, canvas.width, canvas.height);
                
                const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
                
                // Usar biblioteca jsQR para detectar QR Code
                if (typeof jsQR !== 'undefined') {
                    const code = jsQR(imageData.data, imageData.width, imageData.height);
                    
                    if (code) {
                        this.processQRCode(code.data);
                        return;
                    }
                }
            }
            
            // Continuar escaneando
            requestAnimationFrame(detectQR);
        };
        
        detectQR();
    }

    // Processar QR Code detectado
    async processQRCode(qrData) {
        try {
            this.updateScannerStatus('QR Code detectado! Processando...');
            
            // Parse dos dados do QR Code
            let parsedData;
            try {
                // Tentar fazer parse como JSON
                parsedData = JSON.parse(qrData.replace(/'/g, '"'));
            } catch {
                // Se não for JSON, tentar extrair IDs
                const match = qrData.match(/aluno_id["']?:\s*([0-9]+)/);
                if (match) {
                    parsedData = {
                        aluno_id: parseInt(match[1]),
                        agendamento_id: this.agendamentoId,
                        type: 'presenca_aluno'
                    };
                } else {
                    throw new Error('Formato de QR Code inválido');
                }
            }

            // Validar dados
            if (!parsedData.aluno_id || !parsedData.agendamento_id) {
                throw new Error('QR Code não contém dados válidos');
            }

            // Enviar para o servidor
            const response = await fetch('/monitor/processar-qrcode', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    qr_data: qrData,
                    aluno_id: parsedData.aluno_id,
                    agendamento_id: parsedData.agendamento_id
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.updateScannerStatus(`✅ ${result.message}`, 'success');
                
                // Atualizar lista de alunos se existir
                this.updateAlunoStatus(parsedData.aluno_id, true);
                
                // Parar scanner temporariamente
                this.pauseScanning(3000);
                
            } else {
                this.updateScannerStatus(`❌ ${result.message}`, 'error');
                this.pauseScanning(2000);
            }
            
        } catch (error) {
            console.error('Erro ao processar QR Code:', error);
            this.updateScannerStatus(`❌ Erro: ${error.message}`, 'error');
            this.pauseScanning(2000);
        }
    }

    // Pausar escaneamento temporariamente
    pauseScanning(duration) {
        this.isScanning = false;
        
        setTimeout(() => {
            if (!this.isScanning) {
                this.isScanning = true;
                this.updateScannerStatus('Escaneando... Aponte a câmera para o QR Code');
            }
        }, duration);
    }

    // Parar scanner
    stop() {
        this.isScanning = false;
        
        const video = document.getElementById('qr-video');
        if (video && video.srcObject) {
            const tracks = video.srcObject.getTracks();
            tracks.forEach(track => track.stop());
            video.srcObject = null;
        }
        
        this.updateScannerStatus('Scanner parado');
    }

    // Atualizar status do scanner
    updateScannerStatus(message, type = 'info') {
        const statusElement = document.getElementById('scanner-status');
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.className = `scanner-status ${type}`;
        }
    }

    // Atualizar status do aluno na lista
    updateAlunoStatus(alunoId, presente) {
        const alunoRow = document.querySelector(`[data-aluno-id="${alunoId}"]`);
        if (alunoRow) {
            const statusBadge = alunoRow.querySelector('.status-badge');
            const presencaBtn = alunoRow.querySelector('.btn-presenca');
            
            if (statusBadge) {
                statusBadge.textContent = presente ? 'Presente' : 'Ausente';
                statusBadge.className = `badge status-badge ${presente ? 'bg-success' : 'bg-danger'}`;
            }
            
            if (presencaBtn) {
                presencaBtn.textContent = presente ? 'Marcar Ausente' : 'Marcar Presente';
                presencaBtn.className = `btn btn-sm ${presente ? 'btn-outline-danger' : 'btn-outline-success'} btn-presenca`;
            }
        }
        
        // Atualizar contadores
        this.updateContadores();
    }

    // Atualizar contadores de presença
    updateContadores() {
        const totalAlunos = document.querySelectorAll('[data-aluno-id]').length;
        const presentes = document.querySelectorAll('.status-badge.bg-success').length;
        const ausentes = totalAlunos - presentes;
        
        const contadorPresentes = document.getElementById('contador-presentes');
        const contadorAusentes = document.getElementById('contador-ausentes');
        const contadorTotal = document.getElementById('contador-total');
        
        if (contadorPresentes) contadorPresentes.textContent = presentes;
        if (contadorAusentes) contadorAusentes.textContent = ausentes;
        if (contadorTotal) contadorTotal.textContent = totalAlunos;
    }

    // Obter CSRF Token
    getCSRFToken() {
        const token = document.querySelector('meta[name=csrf-token]');
        return token ? token.getAttribute('content') : '';
    }
}

// Instância global do scanner
let qrScanner = null;

// Funções globais para controle do scanner
function iniciarScanner(agendamentoId) {
    if (qrScanner) {
        qrScanner.stop();
    }
    
    qrScanner = new QRScannerMonitor();
    qrScanner.init(agendamentoId);
    
    // Mostrar modal do scanner
    const modal = document.getElementById('qrScannerModal');
    if (modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // Parar scanner quando modal for fechado
        modal.addEventListener('hidden.bs.modal', () => {
            if (qrScanner) {
                qrScanner.stop();
            }
        });
    }
}

function pararScanner() {
    if (qrScanner) {
        qrScanner.stop();
        qrScanner = null;
    }
}

// Função para registro manual de presença
async function registrarPresencaManual(alunoId, agendamentoId, presente) {
    try {
        const response = await fetch('/monitor/registrar-presenca', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': qrScanner ? qrScanner.getCSRFToken() : ''
            },
            body: JSON.stringify({
                aluno_id: alunoId,
                agendamento_id: agendamentoId,
                presente: presente
            })
        });

        const result = await response.json();
        
        if (result.success) {
            // Atualizar interface
            if (qrScanner) {
                qrScanner.updateAlunoStatus(alunoId, presente);
            }
            
            // Mostrar notificação
            mostrarNotificacao(result.message, 'success');
        } else {
            mostrarNotificacao(result.message, 'error');
        }
        
    } catch (error) {
        console.error('Erro ao registrar presença:', error);
        mostrarNotificacao('Erro ao registrar presença', 'error');
    }
}

// Função para mostrar notificações
function mostrarNotificacao(message, type) {
    // Criar elemento de notificação
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Remover após 5 segundos
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Inicialização quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Adicionar event listeners para botões de presença
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('btn-presenca')) {
            const alunoId = e.target.getAttribute('data-aluno-id');
            const agendamentoId = e.target.getAttribute('data-agendamento-id');
            const isPresente = e.target.textContent.includes('Marcar Presente');
            
            if (alunoId && agendamentoId) {
                registrarPresencaManual(parseInt(alunoId), parseInt(agendamentoId), isPresente);
            }
        }
    });
});