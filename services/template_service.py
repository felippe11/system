from models.certificado import CertificadoTemplateAvancado, DeclaracaoTemplate, VariavelDinamica
from extensions import db
from datetime import datetime
import json


class TemplateService:
    """Serviço para gerenciar templates pré-definidos"""
    
    @staticmethod
    def criar_templates_predefinidos_certificados(cliente_id):
        """Criar templates pré-definidos de certificados para um cliente"""
        templates_predefinidos = [
            {
                'nome': 'Certificado Clássico',
                'tipo': 'geral',
                'descricao': 'Template clássico com bordas elegantes e layout tradicional',
                'orientacao': 'landscape',
                'tamanho_papel': 'A4',
                'conteudo_html': '''
                <div class="certificate-container">
                    <div class="certificate-border">
                        <div class="certificate-header">
                            <div class="logo-container">
                                <img src="{{LOGO_EVENTO}}" alt="Logo" class="logo">
                            </div>
                            <h1 class="certificate-title">CERTIFICADO</h1>
                            <p class="certificate-subtitle">DE PARTICIPAÇÃO</p>
                        </div>
                        
                        <div class="certificate-body">
                            <p class="certificate-text">
                                Certificamos que <strong class="participant-name">{{NOME_PARTICIPANTE}}</strong>
                                participou do evento <strong>{{NOME_EVENTO}}</strong>,
                                realizado no período de {{DATA_INICIO}} a {{DATA_FIM}},
                                com carga horária total de <strong>{{CARGA_HORARIA}} horas</strong>.
                            </p>
                            
                            <div class="activities-section">
                                <h3>Atividades Realizadas:</h3>
                                <div class="activities-list">{{LISTA_ATIVIDADES}}</div>
                            </div>
                        </div>
                        
                        <div class="certificate-footer">
                            <div class="signature-section">
                                <div class="signature-line"></div>
                                <p class="signature-name">{{RESPONSAVEL_EVENTO}}</p>
                                <p class="signature-title">{{CARGO_RESPONSAVEL}}</p>
                            </div>
                            
                            <div class="validation-section">
                                <div class="qr-code">{{QR_CODE_VALIDACAO}}</div>
                                <p class="validation-text">Código de Validação: {{CODIGO_VALIDACAO}}</p>
                                <p class="emission-date">Emitido em: {{DATA_EMISSAO}}</p>
                            </div>
                        </div>
                    </div>
                </div>
                ''',
                'conteudo_css': '''
                .certificate-container {
                    width: 100%;
                    height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    font-family: 'Georgia', serif;
                }
                
                .certificate-border {
                    width: 90%;
                    height: 90%;
                    background: white;
                    border: 8px solid #2c3e50;
                    border-radius: 20px;
                    padding: 40px;
                    box-shadow: 0 0 30px rgba(0,0,0,0.3);
                    position: relative;
                }
                
                .certificate-border::before {
                    content: '';
                    position: absolute;
                    top: 20px;
                    left: 20px;
                    right: 20px;
                    bottom: 20px;
                    border: 2px solid #3498db;
                    border-radius: 10px;
                }
                
                .certificate-header {
                    text-align: center;
                    margin-bottom: 40px;
                }
                
                .logo {
                    max-height: 80px;
                    margin-bottom: 20px;
                }
                
                .certificate-title {
                    font-size: 48px;
                    color: #2c3e50;
                    margin: 0;
                    font-weight: bold;
                    letter-spacing: 3px;
                }
                
                .certificate-subtitle {
                    font-size: 24px;
                    color: #3498db;
                    margin: 10px 0;
                    letter-spacing: 2px;
                }
                
                .certificate-body {
                    text-align: center;
                    margin: 40px 0;
                }
                
                .certificate-text {
                    font-size: 18px;
                    line-height: 1.8;
                    color: #2c3e50;
                    margin-bottom: 30px;
                }
                
                .participant-name {
                    font-size: 24px;
                    color: #e74c3c;
                    text-transform: uppercase;
                }
                
                .activities-section {
                    margin: 30px 0;
                    text-align: left;
                }
                
                .activities-section h3 {
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                }
                
                .certificate-footer {
                    display: flex;
                    justify-content: space-between;
                    align-items: end;
                    margin-top: 50px;
                }
                
                .signature-section {
                    text-align: center;
                }
                
                .signature-line {
                    width: 200px;
                    height: 2px;
                    background: #2c3e50;
                    margin-bottom: 10px;
                }
                
                .signature-name {
                    font-weight: bold;
                    margin: 5px 0;
                }
                
                .validation-section {
                    text-align: center;
                    font-size: 12px;
                }
                
                .qr-code {
                    width: 80px;
                    height: 80px;
                    margin: 0 auto 10px;
                }
                '''
            },
            {
                'nome': 'Certificado Moderno',
                'tipo': 'geral',
                'descricao': 'Design moderno com gradientes e elementos visuais contemporâneos',
                'orientacao': 'landscape',
                'tamanho_papel': 'A4',
                'conteudo_html': '''
                <div class="modern-certificate">
                    <div class="background-pattern"></div>
                    <div class="content-wrapper">
                        <header class="cert-header">
                            <div class="logo-section">
                                <img src="{{LOGO_EVENTO}}" alt="Logo" class="event-logo">
                            </div>
                            <div class="title-section">
                                <h1 class="main-title">CERTIFICATE</h1>
                                <h2 class="sub-title">OF ACHIEVEMENT</h2>
                            </div>
                        </header>
                        
                        <main class="cert-main">
                            <div class="recipient-section">
                                <p class="awarded-text">This certificate is proudly awarded to</p>
                                <h3 class="recipient-name">{{NOME_PARTICIPANTE}}</h3>
                            </div>
                            
                            <div class="achievement-section">
                                <p class="achievement-text">
                                    For successfully completing <strong>{{NOME_EVENTO}}</strong><br>
                                    From {{DATA_INICIO}} to {{DATA_FIM}}<br>
                                    Total duration: <strong>{{CARGA_HORARIA}} hours</strong>
                                </p>
                            </div>
                            
                            <div class="activities-modern">
                                {{LISTA_ATIVIDADES}}
                            </div>
                        </main>
                        
                        <footer class="cert-footer">
                            <div class="signature-modern">
                                <div class="sig-line"></div>
                                <p class="sig-name">{{RESPONSAVEL_EVENTO}}</p>
                                <p class="sig-title">{{CARGO_RESPONSAVEL}}</p>
                            </div>
                            
                            <div class="validation-modern">
                                <div class="qr-modern">{{QR_CODE_VALIDACAO}}</div>
                                <p class="validation-code">{{CODIGO_VALIDACAO}}</p>
                                <p class="issue-date">{{DATA_EMISSAO}}</p>
                            </div>
                        </footer>
                    </div>
                </div>
                ''',
                'conteudo_css': '''
                .modern-certificate {
                    width: 100%;
                    height: 100vh;
                    position: relative;
                    background: linear-gradient(45deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
                    font-family: 'Arial', sans-serif;
                    overflow: hidden;
                }
                
                .background-pattern {
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-image: 
                        radial-gradient(circle at 20% 80%, rgba(255,255,255,0.1) 0%, transparent 50%),
                        radial-gradient(circle at 80% 20%, rgba(255,255,255,0.1) 0%, transparent 50%);
                }
                
                .content-wrapper {
                    position: relative;
                    z-index: 2;
                    width: 90%;
                    height: 90%;
                    margin: 5%;
                    background: rgba(255,255,255,0.95);
                    border-radius: 30px;
                    padding: 50px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    backdrop-filter: blur(10px);
                }
                
                .cert-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 50px;
                }
                
                .event-logo {
                    max-height: 100px;
                    filter: drop-shadow(0 4px 8px rgba(0,0,0,0.2));
                }
                
                .title-section {
                    text-align: right;
                }
                
                .main-title {
                    font-size: 56px;
                    font-weight: 900;
                    background: linear-gradient(45deg, #667eea, #764ba2);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin: 0;
                    letter-spacing: 4px;
                }
                
                .sub-title {
                    font-size: 24px;
                    color: #666;
                    margin: 0;
                    letter-spacing: 2px;
                }
                
                .cert-main {
                    text-align: center;
                    margin: 60px 0;
                }
                
                .awarded-text {
                    font-size: 20px;
                    color: #666;
                    margin-bottom: 20px;
                }
                
                .recipient-name {
                    font-size: 42px;
                    font-weight: bold;
                    color: #2c3e50;
                    margin: 20px 0;
                    text-transform: uppercase;
                    letter-spacing: 2px;
                    border-bottom: 3px solid #667eea;
                    display: inline-block;
                    padding-bottom: 10px;
                }
                
                .achievement-text {
                    font-size: 18px;
                    line-height: 1.8;
                    color: #444;
                    margin: 40px 0;
                }
                
                .cert-footer {
                    display: flex;
                    justify-content: space-between;
                    align-items: end;
                    margin-top: 80px;
                }
                
                .signature-modern {
                    text-align: center;
                }
                
                .sig-line {
                    width: 250px;
                    height: 3px;
                    background: linear-gradient(45deg, #667eea, #764ba2);
                    margin-bottom: 15px;
                    border-radius: 2px;
                }
                
                .sig-name {
                    font-size: 18px;
                    font-weight: bold;
                    color: #2c3e50;
                    margin: 5px 0;
                }
                
                .validation-modern {
                    text-align: center;
                }
                
                .qr-modern {
                    width: 100px;
                    height: 100px;
                    margin: 0 auto 15px;
                    border: 2px solid #667eea;
                    border-radius: 10px;
                }
                '''
            },
            {
                'nome': 'Certificado Minimalista',
                'tipo': 'individual',
                'descricao': 'Design clean e minimalista com foco na tipografia',
                'orientacao': 'portrait',
                'tamanho_papel': 'A4',
                'conteudo_html': '''
                <div class="minimal-certificate">
                    <div class="minimal-container">
                        <header class="minimal-header">
                            <img src="{{LOGO_EVENTO}}" alt="Logo" class="minimal-logo">
                            <div class="minimal-line"></div>
                        </header>
                        
                        <main class="minimal-main">
                            <h1 class="minimal-title">Certificate</h1>
                            
                            <div class="minimal-content">
                                <p class="minimal-text">This is to certify that</p>
                                <h2 class="minimal-name">{{NOME_PARTICIPANTE}}</h2>
                                <p class="minimal-text">has successfully completed</p>
                                <h3 class="minimal-event">{{NOME_EVENTO}}</h3>
                                
                                <div class="minimal-details">
                                    <p>Duration: {{CARGA_HORARIA}} hours</p>
                                    <p>Period: {{DATA_INICIO}} - {{DATA_FIM}}</p>
                                </div>
                                
                                <div class="minimal-activities">
                                    {{LISTA_ATIVIDADES}}
                                </div>
                            </div>
                        </main>
                        
                        <footer class="minimal-footer">
                            <div class="minimal-signature">
                                <div class="minimal-sig-line"></div>
                                <p class="minimal-sig-name">{{RESPONSAVEL_EVENTO}}</p>
                                <p class="minimal-sig-title">{{CARGO_RESPONSAVEL}}</p>
                            </div>
                            
                            <div class="minimal-validation">
                                <div class="minimal-qr">{{QR_CODE_VALIDACAO}}</div>
                                <p class="minimal-code">{{CODIGO_VALIDACAO}}</p>
                                <p class="minimal-date">{{DATA_EMISSAO}}</p>
                            </div>
                        </footer>
                    </div>
                </div>
                ''',
                'conteudo_css': '''
                .minimal-certificate {
                    width: 100%;
                    height: 100vh;
                    background: #fafafa;
                    font-family: 'Helvetica Neue', Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }
                
                .minimal-container {
                    width: 80%;
                    max-width: 600px;
                    background: white;
                    padding: 80px 60px;
                    box-shadow: 0 0 50px rgba(0,0,0,0.1);
                }
                
                .minimal-header {
                    text-align: center;
                    margin-bottom: 60px;
                }
                
                .minimal-logo {
                    max-height: 60px;
                    margin-bottom: 30px;
                }
                
                .minimal-line {
                    width: 100px;
                    height: 2px;
                    background: #333;
                    margin: 0 auto;
                }
                
                .minimal-main {
                    text-align: center;
                }
                
                .minimal-title {
                    font-size: 48px;
                    font-weight: 300;
                    color: #333;
                    margin: 0 0 50px 0;
                    letter-spacing: 3px;
                }
                
                .minimal-text {
                    font-size: 16px;
                    color: #666;
                    margin: 20px 0;
                    font-weight: 300;
                }
                
                .minimal-name {
                    font-size: 32px;
                    font-weight: 400;
                    color: #333;
                    margin: 30px 0;
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 15px;
                    display: inline-block;
                }
                
                .minimal-event {
                    font-size: 24px;
                    font-weight: 300;
                    color: #555;
                    margin: 30px 0;
                    font-style: italic;
                }
                
                .minimal-details {
                    margin: 40px 0;
                    padding: 20px 0;
                    border-top: 1px solid #eee;
                    border-bottom: 1px solid #eee;
                }
                
                .minimal-details p {
                    margin: 10px 0;
                    color: #777;
                    font-size: 14px;
                }
                
                .minimal-footer {
                    display: flex;
                    justify-content: space-between;
                    align-items: end;
                    margin-top: 80px;
                    padding-top: 40px;
                    border-top: 1px solid #eee;
                }
                
                .minimal-signature {
                    text-align: left;
                }
                
                .minimal-sig-line {
                    width: 150px;
                    height: 1px;
                    background: #333;
                    margin-bottom: 10px;
                }
                
                .minimal-sig-name {
                    font-size: 14px;
                    font-weight: 500;
                    color: #333;
                    margin: 5px 0;
                }
                
                .minimal-sig-title {
                    font-size: 12px;
                    color: #666;
                    margin: 0;
                }
                
                .minimal-validation {
                    text-align: right;
                    font-size: 10px;
                    color: #999;
                }
                
                .minimal-qr {
                    width: 60px;
                    height: 60px;
                    margin: 0 0 10px auto;
                    border: 1px solid #ddd;
                }
                '''
            }
        ]
        
        templates_criados = []
        for template_data in templates_predefinidos:
            # Verificar se já existe
            existing = CertificadoTemplateAvancado.query.filter_by(
                nome=template_data['nome'],
                cliente_id=cliente_id
            ).first()
            
            if not existing:
                template = CertificadoTemplateAvancado(
                    cliente_id=cliente_id,
                    nome=template_data['nome'],
                    tipo=template_data['tipo'],
                    descricao=template_data['descricao'],
                    orientacao=template_data['orientacao'],
                    tamanho_papel=template_data['tamanho_papel'],
                    conteudo_html=template_data['conteudo_html'],
                    conteudo_css=template_data['conteudo_css'],
                    ativo=False,
                    padrao=True
                )
                db.session.add(template)
                templates_criados.append(template)
        
        db.session.commit()
        return templates_criados
    
    @staticmethod
    def criar_templates_predefinidos_declaracoes(cliente_id):
        """Criar templates pré-definidos de declarações para um cliente"""
        templates_predefinidos = [
            {
                'nome': 'Declaração Formal',
                'descricao': 'Template formal para declarações de participação',
                'conteudo': '''
                <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 40px;">
                    <div style="text-align: center; margin-bottom: 40px;">
                        <img src="{{LOGO_INSTITUICAO}}" alt="Logo" style="max-height: 80px; margin-bottom: 20px;">
                        <h1 style="color: #2c3e50; font-size: 28px; margin: 0;">{{NOME_INSTITUICAO}}</h1>
                        <p style="color: #7f8c8d; margin: 5px 0;">{{ENDERECO_INSTITUICAO}}</p>
                    </div>
                    
                    <div style="text-align: center; margin: 50px 0;">
                        <h2 style="color: #2c3e50; font-size: 32px; margin: 0; letter-spacing: 2px;">DECLARAÇÃO</h2>
                    </div>
                    
                    <div style="text-align: justify; line-height: 1.8; font-size: 16px; color: #2c3e50;">
                        <p style="margin-bottom: 30px;">
                            Declaramos para os devidos fins que <strong>{{NOME_PARTICIPANTE}}</strong>, 
                            portador(a) do documento de identidade nº <strong>{{DOCUMENTO_PARTICIPANTE}}</strong>, 
                            participou do evento <strong>{{NOME_EVENTO}}</strong>, realizado no período de 
                            <strong>{{DATA_INICIO}}</strong> a <strong>{{DATA_FIM}}</strong>, 
                            com carga horária total de <strong>{{CARGA_HORARIA}} horas</strong>.
                        </p>
                        
                        <div style="margin: 30px 0;">
                            <h3 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">Atividades Realizadas:</h3>
                            <div style="margin-left: 20px;">{{LISTA_ATIVIDADES}}</div>
                        </div>
                        
                        <p style="margin-top: 40px;">
                            Por ser verdade, firmamos a presente declaração.
                        </p>
                    </div>
                    
                    <div style="margin-top: 80px; display: flex; justify-content: space-between; align-items: end;">
                        <div style="text-align: center;">
                            <div style="width: 200px; height: 2px; background: #2c3e50; margin-bottom: 10px;"></div>
                            <p style="margin: 5px 0; font-weight: bold;">{{RESPONSAVEL_EVENTO}}</p>
                            <p style="margin: 0; color: #7f8c8d;">{{CARGO_RESPONSAVEL}}</p>
                        </div>
                        
                        <div style="text-align: center; font-size: 12px; color: #7f8c8d;">
                            <p style="margin: 5px 0;">{{CIDADE}}, {{DATA_EMISSAO}}</p>
                            <p style="margin: 5px 0;">Código de Validação: {{CODIGO_VALIDACAO}}</p>
                        </div>
                    </div>
                </div>
                '''
            },
            {
                'nome': 'Declaração Simples',
                'descricao': 'Template simples e direto para declarações',
                'conteudo': '''
                <div style="font-family: 'Times New Roman', serif; max-width: 700px; margin: 0 auto; padding: 60px 40px;">
                    <div style="text-align: center; margin-bottom: 60px;">
                        <h1 style="color: #333; font-size: 36px; margin: 0; font-weight: bold;">DECLARAÇÃO</h1>
                    </div>
                    
                    <div style="text-align: justify; line-height: 2; font-size: 18px; color: #333;">
                        <p style="margin-bottom: 40px; text-indent: 50px;">
                            Declaro para os devidos fins que <strong>{{NOME_PARTICIPANTE}}</strong> 
                            participou do <strong>{{NOME_EVENTO}}</strong>, realizado no período de 
                            {{DATA_INICIO}} a {{DATA_FIM}}, totalizando <strong>{{CARGA_HORARIA}} horas</strong> 
                            de atividades.
                        </p>
                        
                        <p style="margin: 40px 0; text-indent: 50px;">
                            {{LISTA_ATIVIDADES}}
                        </p>
                        
                        <p style="margin-top: 60px; text-indent: 50px;">
                            Por ser expressão da verdade, firmo a presente declaração.
                        </p>
                    </div>
                    
                    <div style="margin-top: 100px; text-align: right;">
                        <p style="margin: 5px 0;">{{CIDADE}}, {{DATA_EMISSAO}}</p>
                        
                        <div style="margin-top: 60px; text-align: center;">
                            <div style="width: 250px; height: 1px; background: #333; margin: 0 auto 15px;"></div>
                            <p style="margin: 5px 0; font-weight: bold;">{{RESPONSAVEL_EVENTO}}</p>
                            <p style="margin: 0;">{{CARGO_RESPONSAVEL}}</p>
                        </div>
                    </div>
                    
                    <div style="margin-top: 40px; text-align: center; font-size: 10px; color: #666;">
                        <p>Código de Validação: {{CODIGO_VALIDACAO}}</p>
                    </div>
                </div>
                '''
            },
            {
                'nome': 'Declaração Acadêmica',
                'descricao': 'Template específico para declarações acadêmicas e educacionais',
                'conteudo': '''
                <div style="font-family: 'Georgia', serif; max-width: 800px; margin: 0 auto; padding: 50px; border: 2px solid #2c3e50;">
                    <div style="text-align: center; margin-bottom: 40px; border-bottom: 3px solid #3498db; padding-bottom: 20px;">
                        <img src="{{LOGO_INSTITUICAO}}" alt="Logo" style="max-height: 100px; margin-bottom: 15px;">
                        <h1 style="color: #2c3e50; font-size: 24px; margin: 0;">{{NOME_INSTITUICAO}}</h1>
                        <p style="color: #7f8c8d; margin: 5px 0; font-style: italic;">{{ENDERECO_INSTITUICAO}}</p>
                    </div>
                    
                    <div style="text-align: center; margin: 40px 0;">
                        <h2 style="color: #2c3e50; font-size: 28px; margin: 0; letter-spacing: 1px;">DECLARAÇÃO DE PARTICIPAÇÃO</h2>
                        <p style="color: #7f8c8d; font-size: 14px; margin: 10px 0;">Para fins acadêmicos e profissionais</p>
                    </div>
                    
                    <div style="text-align: justify; line-height: 1.8; font-size: 16px; color: #2c3e50; margin: 40px 0;">
                        <p style="margin-bottom: 25px;">
                            A <strong>{{NOME_INSTITUICAO}}</strong> declara que o(a) participante 
                            <strong style="color: #e74c3c;">{{NOME_PARTICIPANTE}}</strong>, 
                            portador(a) do documento {{DOCUMENTO_PARTICIPANTE}}, 
                            participou integralmente do evento acadêmico 
                            <strong>"{{NOME_EVENTO}}"</strong>.
                        </p>
                        
                        <div style="background: #ecf0f1; padding: 20px; border-left: 4px solid #3498db; margin: 30px 0;">
                            <h3 style="color: #2c3e50; margin: 0 0 15px 0; font-size: 18px;">Detalhes do Evento:</h3>
                            <ul style="margin: 0; padding-left: 20px;">
                                <li><strong>Período:</strong> {{DATA_INICIO}} a {{DATA_FIM}}</li>
                                <li><strong>Carga Horária:</strong> {{CARGA_HORARIA}} horas</li>
                                <li><strong>Modalidade:</strong> {{MODALIDADE_EVENTO}}</li>
                            </ul>
                        </div>
                        
                        <div style="margin: 30px 0;">
                            <h3 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 8px; font-size: 18px;">Atividades Desenvolvidas:</h3>
                            <div style="margin-left: 15px; margin-top: 15px;">{{LISTA_ATIVIDADES}}</div>
                        </div>
                        
                        <p style="margin-top: 30px; font-style: italic;">
                            Esta declaração é emitida para comprovação de participação em atividades 
                            de extensão universitária e desenvolvimento profissional.
                        </p>
                    </div>
                    
                    <div style="margin-top: 60px; display: flex; justify-content: space-between; align-items: end;">
                        <div>
                            <p style="margin: 5px 0; font-size: 14px;">{{CIDADE}}, {{DATA_EMISSAO}}</p>
                            <p style="margin: 5px 0; font-size: 12px; color: #7f8c8d;">Documento emitido eletronicamente</p>
                        </div>
                        
                        <div style="text-align: center;">
                            <div style="width: 200px; height: 2px; background: #2c3e50; margin-bottom: 15px;"></div>
                            <p style="margin: 5px 0; font-weight: bold; font-size: 16px;">{{RESPONSAVEL_EVENTO}}</p>
                            <p style="margin: 0; color: #7f8c8d; font-size: 14px;">{{CARGO_RESPONSAVEL}}</p>
                            <p style="margin: 5px 0; color: #7f8c8d; font-size: 12px;">{{INSTITUICAO_RESPONSAVEL}}</p>
                        </div>
                    </div>
                    
                    <div style="margin-top: 40px; text-align: center; padding-top: 20px; border-top: 1px solid #bdc3c7;">
                        <p style="font-size: 10px; color: #7f8c8d; margin: 5px 0;">Código de Validação: {{CODIGO_VALIDACAO}}</p>
                        <p style="font-size: 10px; color: #7f8c8d; margin: 5px 0;">Verifique a autenticidade em: {{URL_VALIDACAO}}</p>
                    </div>
                </div>
                '''
            }
        ]
        
        templates_criados = []
        for template_data in templates_predefinidos:
            # Verificar se já existe
            existing = DeclaracaoTemplate.query.filter_by(
                nome=template_data['nome'],
                cliente_id=cliente_id
            ).first()
            
            if not existing:
                template = DeclaracaoTemplate(
                    cliente_id=cliente_id,
                    nome=template_data['nome'],
                    descricao=template_data['descricao'],
                    conteudo=template_data['conteudo'],
                    ativo=False
                )
                db.session.add(template)
                templates_criados.append(template)
        
        db.session.commit()
        return templates_criados
    
    @staticmethod
    def criar_variaveis_padrao(template_id, tipo_template):
        """Criar variáveis padrão para um template"""
        variaveis_certificado = [
            {'nome': 'NOME_PARTICIPANTE', 'tipo': 'texto', 'descricao': 'Nome completo do participante', 'obrigatoria': True},
            {'nome': 'NOME_EVENTO', 'tipo': 'texto', 'descricao': 'Nome do evento', 'obrigatoria': True},
            {'nome': 'DATA_INICIO', 'tipo': 'data', 'descricao': 'Data de início do evento', 'obrigatoria': True},
            {'nome': 'DATA_FIM', 'tipo': 'data', 'descricao': 'Data de fim do evento', 'obrigatoria': True},
            {'nome': 'CARGA_HORARIA', 'tipo': 'numero', 'descricao': 'Carga horária total', 'obrigatoria': True},
            {'nome': 'LISTA_ATIVIDADES', 'tipo': 'html', 'descricao': 'Lista de atividades realizadas', 'obrigatoria': False},
            {'nome': 'RESPONSAVEL_EVENTO', 'tipo': 'texto', 'descricao': 'Nome do responsável pelo evento', 'obrigatoria': True},
            {'nome': 'CARGO_RESPONSAVEL', 'tipo': 'texto', 'descricao': 'Cargo do responsável', 'obrigatoria': True},
            {'nome': 'LOGO_EVENTO', 'tipo': 'imagem', 'descricao': 'Logo do evento', 'obrigatoria': False},
            {'nome': 'QR_CODE_VALIDACAO', 'tipo': 'qrcode', 'descricao': 'QR Code para validação', 'obrigatoria': False},
            {'nome': 'CODIGO_VALIDACAO', 'tipo': 'texto', 'descricao': 'Código de validação', 'obrigatoria': False},
            {'nome': 'DATA_EMISSAO', 'tipo': 'data', 'descricao': 'Data de emissão do certificado', 'obrigatoria': True}
        ]
        
        variaveis_declaracao = [
            {'nome': 'NOME_PARTICIPANTE', 'tipo': 'texto', 'descricao': 'Nome completo do participante', 'obrigatoria': True},
            {'nome': 'DOCUMENTO_PARTICIPANTE', 'tipo': 'texto', 'descricao': 'Documento de identidade', 'obrigatoria': False},
            {'nome': 'NOME_EVENTO', 'tipo': 'texto', 'descricao': 'Nome do evento', 'obrigatoria': True},
            {'nome': 'DATA_INICIO', 'tipo': 'data', 'descricao': 'Data de início', 'obrigatoria': True},
            {'nome': 'DATA_FIM', 'tipo': 'data', 'descricao': 'Data de fim', 'obrigatoria': True},
            {'nome': 'CARGA_HORARIA', 'tipo': 'numero', 'descricao': 'Carga horária total', 'obrigatoria': True},
            {'nome': 'LISTA_ATIVIDADES', 'tipo': 'html', 'descricao': 'Lista de atividades', 'obrigatoria': False},
            {'nome': 'RESPONSAVEL_EVENTO', 'tipo': 'texto', 'descricao': 'Responsável pelo evento', 'obrigatoria': True},
            {'nome': 'CARGO_RESPONSAVEL', 'tipo': 'texto', 'descricao': 'Cargo do responsável', 'obrigatoria': True},
            {'nome': 'CIDADE', 'tipo': 'texto', 'descricao': 'Cidade de emissão', 'obrigatoria': True},
            {'nome': 'DATA_EMISSAO', 'tipo': 'data', 'descricao': 'Data de emissão', 'obrigatoria': True},
            {'nome': 'CODIGO_VALIDACAO', 'tipo': 'texto', 'descricao': 'Código de validação', 'obrigatoria': False},
            {'nome': 'NOME_INSTITUICAO', 'tipo': 'texto', 'descricao': 'Nome da instituição', 'obrigatoria': False},
            {'nome': 'ENDERECO_INSTITUICAO', 'tipo': 'texto', 'descricao': 'Endereço da instituição', 'obrigatoria': False},
            {'nome': 'LOGO_INSTITUICAO', 'tipo': 'imagem', 'descricao': 'Logo da instituição', 'obrigatoria': False}
        ]
        
        variaveis = variaveis_certificado if tipo_template == 'certificado' else variaveis_declaracao
        
        variaveis_criadas = []
        for var_data in variaveis:
            variavel = VariavelDinamica(
                template_id=template_id,
                tipo_template=tipo_template,
                nome=var_data['nome'],
                tipo=var_data['tipo'],
                descricao=var_data['descricao'],
                obrigatoria=var_data['obrigatoria']
            )
            db.session.add(variavel)
            variaveis_criadas.append(variavel)
        
        db.session.commit()
        return variaveis_criadas
    
    @staticmethod
    def inicializar_templates_cliente(cliente_id):
        """Inicializar templates pré-definidos para um novo cliente"""
        templates_certificados = TemplateService.criar_templates_predefinidos_certificados(cliente_id)
        templates_declaracoes = TemplateService.criar_templates_predefinidos_declaracoes(cliente_id)
        
        # Criar variáveis para os templates de certificados
        for template in templates_certificados:
            TemplateService.criar_variaveis_padrao(template.id, 'certificado')
        
        return {
            'certificados': len(templates_certificados),
            'declaracoes': len(templates_declaracoes)
        }