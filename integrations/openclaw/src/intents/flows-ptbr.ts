export const FRIENDLY_FAILURE_MESSAGES_PT_BR: Record<string, string> = {
  authentication_failed:
    "Nao consegui autenticar na API oficial agora. Verifique o token configurado no OpenClaw.",
  backend_timeout:
    "A API oficial demorou demais para responder. Peça para o usuario aguardar e tente novamente.",
  backend_network_error:
    "Houve uma falha de rede ao falar com a API oficial. Nao assuma sucesso.",
  validation_error:
    "Os dados enviados estao incompletos ou invalidos. Corrija o campo apontado pela API.",
  participant_not_found:
    "Nao localizei cadastro para esse CPF. Continue o fluxo coletando os dados do participante.",
  duplicate_registration:
    "Ja existe uma inscricao para esse CPF no evento selecionado. Continue a conversa a partir da inscricao existente.",
  participant_conflict:
    "O CPF ou email informado conflita com um cadastro ja existente. Nao force a inscricao sem validacao humana.",
  external_service_failure:
    "A API oficial criou a inscricao, mas o servico externo nao respondeu como esperado. Informe a falha sem prometer pagamento ou comprovante."
};

export const STATE_HINTS_PT_BR: Record<string, string> = {
  idle: "Comece listando eventos ou perguntando qual evento o usuario deseja.",
  awaiting_event_selection:
    "Pergunte qual evento deve ser usado e registre o ID escolhido antes de prosseguir.",
  awaiting_cpf:
    "Solicite apenas o CPF com 11 digitos.",
  awaiting_name:
    "Solicite o nome completo exatamente como deve constar na inscricao.",
  awaiting_email:
    "Solicite o email principal para comunicacoes oficiais.",
  awaiting_formacao:
    "Solicite a formacao ou categoria profissional do participante.",
  ready_to_create:
    "Revise o resumo dos dados coletados e chame criar_inscricao.",
  registration_created:
    "A inscricao foi criada. Se houver pagamento pendente, chame gerar_link_pagamento.",
  awaiting_payment_link:
    "O backend marcou a inscricao como pendente. Gere o link de pagamento oficial.",
  completed:
    "A conversa pode ser retomada para consultar status, comprovante ou pagamento.",
  error:
    "Explique a falha com base no codigo retornado pela API e diga o proximo passo."
};
