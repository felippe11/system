import { randomUUID } from "node:crypto";

import {
  FRIENDLY_FAILURE_MESSAGES_PT_BR,
  STATE_HINTS_PT_BR,
} from "../intents/flows-ptbr.js";
import {
  buildResumeSummary,
  inferConversationState,
} from "../intents/state-machine.js";
import { BackendApiError, OpenClawBackendClient } from "../http/api-client.js";
import {
  ConversationState,
  type CreateRegistrationResult,
  type OpenClawPluginConfig,
  type PaymentLinkResult,
  type ReceiptMetadata,
  type RegistrationRecord,
  type RegistrationStatus,
  type RegistrationsByCpfResult,
  type ToolConversationPayload,
  type UserConversationState,
} from "../types.js";
import {
  FileConversationStateStore,
  defaultConversationState,
} from "./state-store.js";

export class WhatsAppEnrollmentService {
  constructor(
    private readonly apiClient: OpenClawBackendClient,
    private readonly stateStore: FileConversationStateStore,
    private readonly config: OpenClawPluginConfig,
  ) {}

  async listarEventos(input?: {
    clienteId?: number;
    somentePublicos?: boolean;
  }): Promise<Record<string, unknown>> {
    const eventos = await this.apiClient.listEvents({
      clienteId: input?.clienteId ?? this.config.defaultClienteId,
      publicOnly:
        typeof input?.somentePublicos === "boolean"
          ? input.somentePublicos
          : this.config.publicOnly,
    });
    return {
      eventos,
      total: eventos.length,
    };
  }

  async detalharEvento(input: {
    eventoId: number;
    userKey?: string;
  }): Promise<Record<string, unknown>> {
    const evento = await this.apiClient.getEvent(input.eventoId);
    const conversation = input.userKey
      ? await this.patchConversation(input.userKey, {
          selectedEventId: input.eventoId,
          state: ConversationState.AWAITING_CPF,
          lastTool: "detalhar_evento",
        })
      : undefined;

    return {
      evento,
      conversation,
    };
  }

  async buscarParticipantePorCpf(input: {
    cpf: string;
    userKey?: string;
  }): Promise<Record<string, unknown>> {
    try {
      const participante = await this.apiClient.getParticipantByCpf(input.cpf);
      const conversation = input.userKey
        ? await this.patchConversation(input.userKey, {
            lastTool: "buscar_participante_por_cpf",
            draft: {
              cpf: input.cpf,
              nome: participante.nome,
              email: participante.email,
              formacao: participante.formacao,
            },
            state: ConversationState.READY_TO_CREATE,
          })
        : undefined;

      return {
        participante,
        conversation,
      };
    } catch (error) {
      if (
        error instanceof BackendApiError &&
        error.code === "participant_not_found" &&
        input.userKey
      ) {
        const conversation = await this.patchConversation(input.userKey, {
          lastTool: "buscar_participante_por_cpf",
          draft: { cpf: input.cpf },
          state: ConversationState.AWAITING_NAME,
        });
        return {
          participante: null,
          conversation,
          friendlyMessage:
            FRIENDLY_FAILURE_MESSAGES_PT_BR.participant_not_found,
        };
      }
      throw this.decorateError(error);
    }
  }

  async criarInscricao(input: {
    userKey?: string;
    eventoId: number;
    cpf: string;
    nome: string;
    email: string;
    formacao: string;
    senha?: string;
    loteId?: number;
    tipoInscricaoId?: number;
  }): Promise<Record<string, unknown>> {
    try {
      const result = await this.apiClient.createRegistration(
        {
          evento_id: input.eventoId,
          cpf: input.cpf,
          nome: input.nome,
          email: input.email,
          formacao: input.formacao,
          senha: input.senha,
          lote_id: input.loteId,
          tipo_inscricao_id: input.tipoInscricaoId,
        },
        { idempotencyKey: randomUUID() },
      );

      const conversation = input.userKey
        ? await this.patchConversationFromRegistration(
            input.userKey,
            result,
            result.payment_required
              ? ConversationState.AWAITING_PAYMENT_LINK
              : ConversationState.COMPLETED,
            "criar_inscricao",
          )
        : undefined;

      return {
        ...result,
        conversation,
      };
    } catch (error) {
      if (
        error instanceof BackendApiError &&
        error.code === "duplicate_registration"
      ) {
        const existingRegistration =
          (error.details?.registration as RegistrationRecord | undefined) ?? null;
        const conversation = input.userKey
          ? await this.patchConversation(input.userKey, {
              registrationId: existingRegistration?.id,
              protocolo: existingRegistration?.protocolo,
              lastTool: "criar_inscricao",
              state: ConversationState.COMPLETED,
              draft: {
                cpf: input.cpf,
                nome: input.nome,
                email: input.email,
                formacao: input.formacao,
              },
            })
          : undefined;

        return {
          duplicate: true,
          existingRegistration,
          friendlyMessage:
            FRIENDLY_FAILURE_MESSAGES_PT_BR.duplicate_registration,
          conversation,
        };
      }
      throw this.decorateError(error);
    }
  }

  async consultarInscricaoPorCpf(input: {
    cpf: string;
    eventoId?: number;
    userKey?: string;
  }): Promise<Record<string, unknown>> {
    try {
      const result = await this.apiClient.getRegistrationsByCpf(
        input.cpf,
        input.eventoId,
      );
      const conversation = input.userKey
        ? await this.patchConversation(input.userKey, {
            lastTool: "consultar_inscricao_por_cpf",
            draft: {
              cpf: input.cpf,
              nome: result.participant.nome,
              email: result.participant.email,
            },
          })
        : undefined;
      return {
        ...result,
        conversation,
      };
    } catch (error) {
      throw this.decorateError(error);
    }
  }

  async consultarStatusInscricao(input: {
    inscricaoId: number;
    userKey?: string;
  }): Promise<Record<string, unknown>> {
    try {
      const status = await this.apiClient.getRegistrationStatus(input.inscricaoId);
      const nextState = status.status_pagamento === "approved"
        ? ConversationState.COMPLETED
        : ConversationState.AWAITING_PAYMENT_LINK;
      const conversation = input.userKey
        ? await this.patchConversation(input.userKey, {
            registrationId: status.inscricao_id,
            protocolo: status.protocolo,
            lastTool: "consultar_status_inscricao",
            state: nextState,
          })
        : undefined;
      return {
        ...status,
        conversation,
      };
    } catch (error) {
      throw this.decorateError(error);
    }
  }

  async consultarComprovante(input: {
    inscricaoId: number;
    userKey?: string;
  }): Promise<Record<string, unknown>> {
    try {
      const receipt = await this.apiClient.getReceipt(input.inscricaoId);
      const conversation = input.userKey
        ? await this.patchConversation(input.userKey, {
            registrationId: receipt.inscricao_id,
            protocolo: receipt.protocolo,
            lastTool: "consultar_comprovante",
            state: ConversationState.COMPLETED,
          })
        : undefined;
      return {
        ...receipt,
        conversation,
      };
    } catch (error) {
      throw this.decorateError(error);
    }
  }

  async gerarLinkPagamento(input: {
    inscricaoId: number;
    userKey?: string;
  }): Promise<Record<string, unknown>> {
    try {
      const result = await this.apiClient.generatePaymentLink(input.inscricaoId);
      const conversation = input.userKey
        ? await this.patchConversation(input.userKey, {
            registrationId: result.registration.id,
            protocolo: result.registration.protocolo,
            lastTool: "gerar_link_pagamento",
            state: result.payment_required
              ? ConversationState.AWAITING_PAYMENT_LINK
              : ConversationState.COMPLETED,
          })
        : undefined;
      return {
        ...result,
        conversation,
      };
    } catch (error) {
      throw this.decorateError(error);
    }
  }

  async resumeConversation(userKey: string): Promise<Record<string, unknown>> {
    const conversation = await this.stateStore.get(userKey);
    const inferredState = inferConversationState(conversation);
    const saved = await this.stateStore.save({
      ...conversation,
      state: inferredState,
    });
    return {
      conversation: saved,
      resumeSummary: buildResumeSummary(saved),
      nextHint: STATE_HINTS_PT_BR[saved.state],
    };
  }

  private async patchConversationFromRegistration(
    userKey: string,
    result: CreateRegistrationResult,
    state: ConversationState,
    lastTool: string,
  ): Promise<Record<string, unknown>> {
    return this.patchConversation(userKey, {
      registrationId: result.registration.id,
      protocolo: result.registration.protocolo,
      lastTool,
      state,
      draft: {
        cpf: result.registration.usuario.cpf,
        nome: result.registration.usuario.nome,
        email: result.registration.usuario.email,
      },
    });
  }

  private async patchConversation(
    userKey: string,
    patch: Partial<UserConversationState>,
  ): Promise<Record<string, unknown>> {
    const current = await this.stateStore.get(userKey);
    const next = await this.stateStore.patch(userKey, {
      ...current,
      ...patch,
      state: patch.state ?? inferConversationState({ ...current, ...patch }),
    });
    return {
      state: next.state,
      resumeSummary: buildResumeSummary(next),
      nextHint: STATE_HINTS_PT_BR[next.state],
      snapshot: next,
    };
  }

  private decorateError(error: unknown): never {
    if (error instanceof BackendApiError) {
      const friendlyMessage =
        FRIENDLY_FAILURE_MESSAGES_PT_BR[error.code] ??
        "A API oficial retornou uma falha que exige revisao humana.";
      const enriched = new Error(`${friendlyMessage} [${error.code}]`);
      enriched.cause = error;
      throw enriched;
    }
    throw error;
  }
}

export function emptyConversation(userKey: string): UserConversationState {
  return defaultConversationState(userKey);
}
