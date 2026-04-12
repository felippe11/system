export interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  error?: ApiErrorPayload;
}

export interface ApiErrorPayload {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface EventoResumo {
  id: number;
  cliente_id: number;
  nome: string;
  descricao: string | null;
  localizacao: string | null;
  status: string;
  publico: boolean;
  inscricao_gratuita: boolean;
  data_inicio: string | null;
  data_fim: string | null;
}

export interface EventoDetalhado extends EventoResumo {
  link_mapa: string | null;
  oficinas_quantidade: number;
  inscricao_disponivel: boolean;
  resumo: {
    data_formatada: string;
    requer_pagamento: boolean;
  };
  tipos_inscricao: TipoInscricao[];
  lotes: LoteInscricao[];
}

export interface TipoInscricao {
  id: number;
  nome: string;
  preco: number;
  submission_only: boolean;
  lotes: Array<{
    lote_id: number;
    lote_nome: string;
    preco: number;
    ativo: boolean;
  }>;
}

export interface LoteInscricao {
  id: number;
  nome: string;
  ativo: boolean;
  qtd_maxima: number | null;
  data_inicio: string | null;
  data_fim: string | null;
}

export interface ParticipanteResumo {
  id: number;
  nome: string;
  cpf: string;
  email: string;
  formacao?: string;
}

export interface RegistrationRecord {
  id: number;
  protocolo: string;
  usuario: ParticipanteResumo;
  evento: {
    id: number | null;
    nome: string | null;
    localizacao: string | null;
    data_inicio: string | null;
    data_fim: string | null;
  };
  tipo_inscricao: {
    id: number;
    nome: string;
    preco: number;
  } | null;
  lote: LoteInscricao | null;
  status_pagamento: string;
  status_inscricao: string;
  payment_required: boolean;
  boleto_url?: string | null;
  comprovante_disponivel: boolean;
  comprovante_endpoint: string;
  created_at: string | null;
}

export interface CreateRegistrationResult {
  created: boolean;
  payment_required: boolean;
  temporary_password_generated: boolean;
  registration: RegistrationRecord;
}

export interface ReceiptMetadata {
  inscricao_id: number;
  protocolo: string;
  status_pagamento: string;
  download_url: string;
  arquivo_nome: string;
  registration: RegistrationRecord;
}

export interface RegistrationStatus {
  inscricao_id: number;
  protocolo: string;
  status_pagamento: string;
  status_inscricao: string;
  payment_required: boolean;
  comprovante_disponivel: boolean;
  registration: RegistrationRecord;
}

export interface RegistrationsByCpfResult {
  participant: ParticipanteResumo;
  registrations: RegistrationRecord[];
}

export interface PaymentLinkResult {
  payment_required: boolean;
  status_pagamento: string;
  message?: string;
  payment_url?: string;
  registration: RegistrationRecord;
}

export interface ParticipantLookupResult extends ParticipanteResumo {
  ativo: boolean;
  registrations: RegistrationRecord[];
}

export interface OpenClawPluginConfig {
  apiBaseUrl: string;
  apiToken: string;
  requestTimeoutMs: number;
  defaultClienteId?: number;
  publicOnly: boolean;
}

export enum ConversationState {
  IDLE = "idle",
  AWAITING_EVENT_SELECTION = "awaiting_event_selection",
  AWAITING_CPF = "awaiting_cpf",
  AWAITING_NAME = "awaiting_name",
  AWAITING_EMAIL = "awaiting_email",
  AWAITING_FORMACAO = "awaiting_formacao",
  READY_TO_CREATE = "ready_to_create",
  REGISTRATION_CREATED = "registration_created",
  AWAITING_PAYMENT_LINK = "awaiting_payment_link",
  COMPLETED = "completed",
  ERROR = "error"
}

export interface ParticipantDraft {
  cpf?: string;
  nome?: string;
  email?: string;
  formacao?: string;
  senha?: string;
  telefone_whatsapp?: string;
}

export interface UserConversationState {
  userKey: string;
  state: ConversationState;
  selectedEventId?: number;
  registrationId?: number;
  protocolo?: string;
  lastError?: string;
  lastTool?: string;
  updatedAt: string;
  draft: ParticipantDraft;
}

export interface ToolConversationPayload {
  userKey?: string;
}
