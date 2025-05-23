#!/bin/bash

# Caminho base
BASE_DIR="templates"

# Criação das pastas (caso não existam)
mkdir -p $BASE_DIR/{auth,dashboard,evento,inscricao,oficina,sorteio,trabalho,agendamento,certificado,formulario,patrocinador,professor,checkin,links,config,relatorio,emails/api}

# Mapeamento e movimentação
mv -v $BASE_DIR/login.html                            $BASE_DIR/auth/
mv -v $BASE_DIR/cadastro.html                         $BASE_DIR/auth/
mv -v $BASE_DIR/esqueci_senha_cpf.html                $BASE_DIR/auth/
mv -v $BASE_DIR/reset_senha_cpf.html                  $BASE_DIR/auth/
mv -v $BASE_DIR/cadastro_participante.html            $BASE_DIR/auth/
mv -v $BASE_DIR/cadastro_ministrante.html             $BASE_DIR/auth/
mv -v $BASE_DIR/cadastro_professor.html               $BASE_DIR/auth/
mv -v $BASE_DIR/cadastro_usuario.html                 $BASE_DIR/auth/
mv -v $BASE_DIR/cadastrar_cliente.html                $BASE_DIR/auth/

mv -v $BASE_DIR/dashboard_admin.html                  $BASE_DIR/dashboard/
mv -v $BASE_DIR/dashboard_participante.html           $BASE_DIR/dashboard/
mv -v $BASE_DIR/dashboard_ministrante.html            $BASE_DIR/dashboard/
mv -v $BASE_DIR/dashboard_professor.html              $BASE_DIR/dashboard/
mv -v $BASE_DIR/dashboard_cliente.html                $BASE_DIR/dashboard/
mv -v $BASE_DIR/dashboard_superadmin.html             $BASE_DIR/dashboard/

mv -v $BASE_DIR/criar_evento.html                     $BASE_DIR/evento/
mv -v $BASE_DIR/configurar_evento.html                $BASE_DIR/evento/
mv -v $BASE_DIR/listar_inscritos_evento.html          $BASE_DIR/evento/
mv -v $BASE_DIR/eventos_disponiveis.html              $BASE_DIR/evento/

mv -v $BASE_DIR/gerenciar_inscricoes.html             $BASE_DIR/inscricao/
mv -v $BASE_DIR/preencher_formulario.html             $BASE_DIR/inscricao/

mv -v $BASE_DIR/criar_oficina.html                    $BASE_DIR/oficina/
mv -v $BASE_DIR/editar_oficina.html                   $BASE_DIR/oficina/
mv -v $BASE_DIR/feedback_oficina.html                 $BASE_DIR/oficina/

mv -v $BASE_DIR/criar_sorteio.html                    $BASE_DIR/sorteio/
mv -v $BASE_DIR/gerenciar_sorteios.html               $BASE_DIR/sorteio/

mv -v $BASE_DIR/meus_trabalhos.html                   $BASE_DIR/trabalho/
mv -v $BASE_DIR/avaliar_trabalho.html                 $BASE_DIR/trabalho/
mv -v $BASE_DIR/avaliar_trabalhos.html                $BASE_DIR/trabalho/
mv -v $BASE_DIR/submeter_trabalho.html                $BASE_DIR/trabalho/
mv -v $BASE_DIR/definir_status_resposta.html          $BASE_DIR/trabalho/
mv -v $BASE_DIR/listar_respostas.html                 $BASE_DIR/trabalho/
mv -v $BASE_DIR/dar_feedback_resposta.html            $BASE_DIR/trabalho/
mv -v $BASE_DIR/visualizar_resposta.html              $BASE_DIR/trabalho/

mv -v $BASE_DIR/criar_agendamento.html                $BASE_DIR/agendamento/
mv -v $BASE_DIR/editar_agendamento.html               $BASE_DIR/agendamento/
mv -v $BASE_DIR/configurar_agendamentos.html          $BASE_DIR/agendamento/
mv -v $BASE_DIR/configurar_horarios_agendamento.html  $BASE_DIR/agendamento/
mv -v $BASE_DIR/gerar_horarios_agendamento.html       $BASE_DIR/agendamento/
mv -v $BASE_DIR/eventos_agendamento.html              $BASE_DIR/agendamento/
mv -v $BASE_DIR/relatorio_geral_agendamentos.html     $BASE_DIR/agendamento/
mv -v $BASE_DIR/listar_agendamentos.html              $BASE_DIR/agendamento/

mv -v $BASE_DIR/templates_certificado.html            $BASE_DIR/certificado/
mv -v $BASE_DIR/upload_personalizacao_cert.html       $BASE_DIR/certificado/
mv -v $BASE_DIR/usar_template.html                    $BASE_DIR/certificado/

mv -v $BASE_DIR/criar_formulario.html                 $BASE_DIR/formulario/
mv -v $BASE_DIR/templates_formulario.html             $BASE_DIR/formulario/
mv -v $BASE_DIR/editar_formulario.html                $BASE_DIR/formulario/
mv -v $BASE_DIR/formularios.html                      $BASE_DIR/formulario/
mv -v $BASE_DIR/formularios_participante.html         $BASE_DIR/formulario/
mv -v $BASE_DIR/gerenciar_campos.html                 $BASE_DIR/formulario/
mv -v $BASE_DIR/gerenciar_campos_template.html        $BASE_DIR/formulario/
mv -v $BASE_DIR/editar_campo.html                     $BASE_DIR/formulario/

mv -v $BASE_DIR/gerenciar_patrocinadores.html         $BASE_DIR/patrocinador/
mv -v $BASE_DIR/listar_patrocinadores.html            $BASE_DIR/patrocinador/
mv -v $BASE_DIR/upload_material.html                  $BASE_DIR/patrocinador/

mv -v $BASE_DIR/checkin.html                          $BASE_DIR/checkin/
mv -v $BASE_DIR/checkin_qr_agendamento.html           $BASE_DIR/checkin/
mv -v $BASE_DIR/lista_checkins.html                   $BASE_DIR/checkin/
mv -v $BASE_DIR/confirmar_checkin.html                $BASE_DIR/checkin/
mv -v $BASE_DIR/scan_qr.html                          $BASE_DIR/checkin/

mv -v $BASE_DIR/links/gerar.html                      $BASE_DIR/links/

mv -v $BASE_DIR/config_system.html                    $BASE_DIR/config/

mv -v $BASE_DIR/enviar_relatorio.html                 $BASE_DIR/relatorio/

mv -v $BASE_DIR/emails/confirmacao_agendamento.html   $BASE_DIR/emails/
mv -v $BASE_DIR/emails/api/horarios_disponiveis.html  $BASE_DIR/emails/api/
