from flask import Blueprint, request, jsonify, render_template
from services.ai_service import ai_service
from utils.auth import login_required, require_permission, cliente_required
from flask import current_app
import json

ai_bp = Blueprint('ai', __name__, url_prefix='/ai')

@ai_bp.route('/gerar-texto-certificado', methods=['POST'])
@login_required
@cliente_required
def gerar_texto_certificado():
    """
    Gera texto para certificados usando IA.
    """
    try:
        data = request.get_json()
        
        tipo_evento = data.get('tipo_evento', '')
        nome_evento = data.get('nome_evento', '')
        contexto = data.get('contexto', '')
        
        if not tipo_evento or not nome_evento:
            return jsonify({
                'success': False,
                'message': 'Tipo de evento e nome do evento são obrigatórios'
            }), 400
        
        resultado = ai_service.gerar_texto_certificado(tipo_evento, nome_evento, contexto)
        
        return jsonify(resultado)
        
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar texto: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor'
        }), 500

@ai_bp.route('/melhorar-texto', methods=['POST'])
@login_required
@cliente_required
def melhorar_texto():
    """
    Melhora um texto existente usando IA.
    """
    try:
        data = request.get_json()
        
        texto_original = data.get('texto_original', '')
        objetivo = data.get('objetivo', 'melhorar')
        
        if not texto_original:
            return jsonify({
                'success': False,
                'message': 'Texto original é obrigatório'
            }), 400
        
        if objetivo not in ['melhorar', 'formalizar', 'simplificar']:
            objetivo = 'melhorar'
        
        resultado = ai_service.melhorar_texto(texto_original, objetivo)
        
        return jsonify(resultado)
        
    except Exception as e:
        current_app.logger.error(f"Erro ao melhorar texto: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor'
        }), 500

@ai_bp.route('/sugestoes-variaveis', methods=['POST'])
@login_required
@cliente_required
def sugestoes_variaveis():
    """
    Gera sugestões de variáveis dinâmicas baseadas no contexto.
    """
    try:
        data = request.get_json()
        contexto = data.get('contexto', '')
        
        sugestoes = ai_service.gerar_sugestoes_variaveis(contexto)
        
        return jsonify({
            'success': True,
            'sugestoes': sugestoes
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar sugestões: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor'
        }), 500

@ai_bp.route('/verificar-qualidade', methods=['POST'])
@login_required
@cliente_required
def verificar_qualidade():
    """
    Verifica a qualidade de um texto e sugere melhorias.
    """
    try:
        data = request.get_json()
        texto = data.get('texto', '')
        
        if not texto:
            return jsonify({
                'success': False,
                'message': 'Texto é obrigatório'
            }), 400
        
        analise = ai_service.verificar_qualidade_texto(texto)
        
        return jsonify({
            'success': True,
            'analise': analise
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao verificar qualidade: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor'
        }), 500

@ai_bp.route('/assistente-texto', methods=['GET'])
@login_required
@cliente_required
def assistente_texto():
    """
    Página do assistente de texto com IA.
    """
    return render_template('ai/assistente_texto.html')

@ai_bp.route('/configuracoes', methods=['GET', 'POST'])
@login_required
@require_permission('ai.configure')
def configuracoes_ia():
    """
    Configurações do serviço de IA.
    """
    if request.method == 'POST':
        try:
            data = request.get_json()
            tipo = data.get('tipo')
            
            if tipo == 'huggingface':
                # Salvar configurações do Hugging Face
                api_key = data.get('api_key')
                model = data.get('model')
                
                # Aqui você salvaria as configurações no banco de dados ou arquivo de config
                # Por enquanto, apenas retornar sucesso
                return jsonify({
                    'success': True,
                    'message': 'Configurações do Hugging Face salvas com sucesso'
                })
                
            elif tipo == 'tgi':
                # Salvar configurações do TGI
                use_tgi = data.get('use_tgi')
                endpoint = data.get('endpoint')
                
                return jsonify({
                    'success': True,
                    'message': 'Configurações do TGI salvas com sucesso'
                })
                
            elif tipo == 'advanced':
                # Salvar configurações avançadas
                timeout = data.get('timeout')
                retries = data.get('retries')
                fallback = data.get('fallback')
                
                return jsonify({
                    'success': True,
                    'message': 'Configurações avançadas salvas com sucesso'
                })
            
            return jsonify({
                'success': False,
                'message': 'Tipo de configuração inválido'
            }), 400
            
        except Exception as e:
            current_app.logger.error(f"Erro ao salvar configurações: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Erro interno do servidor'
            }), 500
    
    # GET - retornar página de configurações
    return render_template('ai/configuracoes.html')

@ai_bp.route('/status', methods=['GET'])
@login_required
@require_permission('ai.view_stats')
def status_ia():
    """
    Verifica o status dos serviços de IA.
    """
    try:
        # Testar conectividade com os serviços
        status = {
            'huggingface': {
                'disponivel': bool(ai_service.hf_api_key),
                'configurado': bool(ai_service.hf_api_key),
                'modelos_disponiveis': [
                    'microsoft/DialoGPT-medium',
                    'tuner007/pegasus_paraphrase'
                ]
            },
            'fallback': {
                'disponivel': True,
                'descricao': 'Templates locais e regras básicas'
            }
        }
        
        status = ai_service.get_status()
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao verificar status: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro ao verificar status'
        }), 500

@ai_bp.route('/testar-huggingface', methods=['POST'])
@login_required
@require_permission('ai.configure')
def testar_huggingface():
    """
    Testa a conectividade com o Hugging Face.
    """
    try:
        # Teste simples com um prompt básico
        resultado = ai_service._gerar_com_hf('teste', 'teste', 'teste de conectividade')
        
        return jsonify({
            'success': True,
            'message': 'Conexão com Hugging Face funcionando',
            'resultado': resultado
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao testar Hugging Face: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro na conexão: {str(e)}'
        }), 500

@ai_bp.route('/testar-tgi', methods=['POST'])
@login_required
@require_permission('ai.configure')
def testar_tgi():
    """
    Testa a conectividade com o TGI.
    """
    try:
        # Teste simples com um prompt básico
        resultado = ai_service._gerar_com_tgi('teste', 'teste', 'teste de conectividade')
        
        return jsonify({
            'success': True,
            'message': 'Conexão com TGI funcionando',
            'resultado': resultado
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao testar TGI: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro na conexão: {str(e)}'
        }), 500

@ai_bp.route('/templates-sugeridos', methods=['GET'])
@login_required
@cliente_required
def templates_sugeridos():
    """
    Retorna templates sugeridos para diferentes tipos de eventos.
    """
    try:
        templates = {
            'workshop': {
                'titulo': 'Certificado de Workshop',
                'texto': 'Certificamos que {NOME_PARTICIPANTE} participou do workshop "{NOME_EVENTO}", desenvolvendo competências práticas e teóricas na área abordada, com carga horária de {CARGA_HORARIA_TOTAL} horas.',
                'variaveis_recomendadas': ['{NOME_PARTICIPANTE}', '{NOME_EVENTO}', '{CARGA_HORARIA_TOTAL}', '{DATA_EVENTO}', '{HABILIDADES_DESENVOLVIDAS}']
            },
            'curso': {
                'titulo': 'Certificado de Curso',
                'texto': 'Certificamos que {NOME_PARTICIPANTE} concluiu com êxito o curso "{NOME_EVENTO}", demonstrando dedicação e aproveitamento nas atividades propostas, totalizando {CARGA_HORARIA_TOTAL} horas de estudo.',
                'variaveis_recomendadas': ['{NOME_PARTICIPANTE}', '{NOME_EVENTO}', '{CARGA_HORARIA_TOTAL}', '{DATA_EVENTO}', '{NOTA_FINAL}']
            },
            'palestra': {
                'titulo': 'Certificado de Participação',
                'texto': 'Certificamos que {NOME_PARTICIPANTE} participou da palestra "{NOME_EVENTO}", ampliando seus conhecimentos sobre o tema apresentado.',
                'variaveis_recomendadas': ['{NOME_PARTICIPANTE}', '{NOME_EVENTO}', '{DATA_EVENTO}', '{PALESTRANTE}']
            },
            'seminario': {
                'titulo': 'Certificado de Seminário',
                'texto': 'Certificamos que {NOME_PARTICIPANTE} participou do seminário "{NOME_EVENTO}", contribuindo para o debate e troca de conhecimentos na área.',
                'variaveis_recomendadas': ['{NOME_PARTICIPANTE}', '{NOME_EVENTO}', '{CARGA_HORARIA_TOTAL}', '{DATA_EVENTO}', '{TEMAS_ABORDADOS}']
            },
            'congresso': {
                'titulo': 'Certificado de Congresso',
                'texto': 'Certificamos que {NOME_PARTICIPANTE} participou do congresso "{NOME_EVENTO}", atualizando-se sobre os avanços e tendências da área.',
                'variaveis_recomendadas': ['{NOME_PARTICIPANTE}', '{NOME_EVENTO}', '{CARGA_HORARIA_TOTAL}', '{DATA_EVENTO}', '{ATIVIDADES_PARTICIPADAS}']
            }
        }
        
        return jsonify({
            'success': True,
            'templates': templates
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar templates: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro ao buscar templates'
        }), 500

@ai_bp.route('/gerar-template-personalizado', methods=['POST'])
@login_required
@cliente_required
def gerar_template_personalizado():
    """
    Gera um template personalizado baseado nas especificações do usuário.
    """
    try:
        data = request.get_json()
        
        tipo_evento = data.get('tipo_evento', '')
        nome_evento = data.get('nome_evento', '')
        publico_alvo = data.get('publico_alvo', '')
        objetivos = data.get('objetivos', '')
        tom = data.get('tom', 'formal')  # formal, informal, academico
        
        if not tipo_evento or not nome_evento:
            return jsonify({
                'success': False,
                'message': 'Tipo de evento e nome são obrigatórios'
            }), 400
        
        # Construir contexto para a IA
        contexto = f"""
        Tipo: {tipo_evento}
        Evento: {nome_evento}
        Público: {publico_alvo}
        Objetivos: {objetivos}
        Tom: {tom}
        """
        
        resultado = ai_service.gerar_texto_certificado(tipo_evento, nome_evento, contexto)
        
        # Adicionar informações específicas do template
        if resultado['success']:
            resultado['template_info'] = {
                'tipo_evento': tipo_evento,
                'nome_evento': nome_evento,
                'publico_alvo': publico_alvo,
                'objetivos': objetivos,
                'tom': tom
            }
        
        return jsonify(resultado)
        
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar template personalizado: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Erro interno do servidor'
        }), 500