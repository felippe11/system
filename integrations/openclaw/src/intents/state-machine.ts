import { ConversationState, type UserConversationState } from "../types.js";

export function inferConversationState(
  current: UserConversationState,
): ConversationState {
  if (current.registrationId && current.state !== ConversationState.ERROR) {
    if (current.state === ConversationState.AWAITING_PAYMENT_LINK) {
      return ConversationState.AWAITING_PAYMENT_LINK;
    }
    return current.state === ConversationState.COMPLETED
      ? ConversationState.COMPLETED
      : ConversationState.REGISTRATION_CREATED;
  }
  if (!current.selectedEventId) {
    return ConversationState.AWAITING_EVENT_SELECTION;
  }
  if (!current.draft.cpf) {
    return ConversationState.AWAITING_CPF;
  }
  if (!current.draft.nome) {
    return ConversationState.AWAITING_NAME;
  }
  if (!current.draft.email) {
    return ConversationState.AWAITING_EMAIL;
  }
  if (!current.draft.formacao) {
    return ConversationState.AWAITING_FORMACAO;
  }
  return ConversationState.READY_TO_CREATE;
}

export function buildResumeSummary(state: UserConversationState): string {
  switch (state.state) {
    case ConversationState.AWAITING_EVENT_SELECTION:
      return "Conversa pausada aguardando a selecao do evento.";
    case ConversationState.AWAITING_CPF:
      return "Conversa pausada aguardando o CPF do participante.";
    case ConversationState.AWAITING_NAME:
      return "Conversa pausada aguardando o nome completo do participante.";
    case ConversationState.AWAITING_EMAIL:
      return "Conversa pausada aguardando o email do participante.";
    case ConversationState.AWAITING_FORMACAO:
      return "Conversa pausada aguardando a formacao do participante.";
    case ConversationState.READY_TO_CREATE:
      return "Todos os dados basicos foram coletados. A proxima chamada segura e criar_inscricao.";
    case ConversationState.AWAITING_PAYMENT_LINK:
      return "A inscricao existe, mas o pagamento ainda esta pendente. Gere o link oficial.";
    case ConversationState.REGISTRATION_CREATED:
      return "A inscricao foi criada. Consulte status ou comprovante conforme a necessidade.";
    case ConversationState.COMPLETED:
      return "Fluxo concluido. Use as tools de consulta para status, comprovante ou pagamento.";
    case ConversationState.ERROR:
      return `Ultima falha registrada: ${state.lastError ?? "erro nao identificado"}.`;
    case ConversationState.IDLE:
    default:
      return "Nenhum fluxo em andamento para este usuario.";
  }
}
