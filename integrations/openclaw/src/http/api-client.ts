import { randomUUID } from "node:crypto";

import type {
  ApiEnvelope,
  EventoDetalhado,
  EventoResumo,
  OpenClawPluginConfig,
  ParticipantLookupResult,
  CreateRegistrationResult,
  PaymentLinkResult,
  ReceiptMetadata,
  RegistrationRecord,
  RegistrationStatus,
  RegistrationsByCpfResult,
} from "../types.js";

export class BackendApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: Record<string, unknown> | undefined;

  constructor(params: {
    message: string;
    code: string;
    status: number;
    details?: Record<string, unknown>;
  }) {
    super(params.message);
    this.name = "BackendApiError";
    this.code = params.code;
    this.status = params.status;
    this.details = params.details;
  }
}

export class OpenClawBackendClient {
  constructor(private readonly config: OpenClawPluginConfig) {}

  async listEvents(params?: {
    clienteId?: number;
    includeInactive?: boolean;
    publicOnly?: boolean;
  }): Promise<EventoResumo[]> {
    const search = new URLSearchParams();
    if (params?.clienteId) {
      search.set("cliente_id", String(params.clienteId));
    }
    if (params?.includeInactive) {
      search.set("incluir_inativos", "true");
    }
    if (typeof params?.publicOnly === "boolean") {
      search.set("somente_publicos", String(params.publicOnly));
    }
    const suffix = search.size > 0 ? `?${search.toString()}` : "";
    return this.request<EventoResumo[]>(`/api/eventos${suffix}`);
  }

  async getEvent(eventId: number): Promise<EventoDetalhado> {
    return this.request<EventoDetalhado>(`/api/eventos/${eventId}`);
  }

  async getParticipantByCpf(cpf: string): Promise<ParticipantLookupResult> {
    return this.request<ParticipantLookupResult>(
      `/api/participantes/cpf/${encodeURIComponent(cpf)}`,
    );
  }

  async createRegistration(
    payload: Record<string, unknown>,
    options?: { idempotencyKey?: string },
  ): Promise<CreateRegistrationResult> {
    return this.request<CreateRegistrationResult>("/api/inscricoes", {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "X-Idempotency-Key": options?.idempotencyKey ?? randomUUID(),
      },
    });
  }

  async getRegistrationsByCpf(
    cpf: string,
    eventId?: number,
  ): Promise<RegistrationsByCpfResult> {
    const search = new URLSearchParams({ cpf });
    if (eventId) {
      search.set("evento_id", String(eventId));
    }
    return this.request<RegistrationsByCpfResult>(
      `/api/inscricoes?${search.toString()}`,
    );
  }

  async getRegistrationByProtocol(protocol: string): Promise<RegistrationRecord> {
    return this.request<RegistrationRecord>(
      `/api/inscricoes/protocolo/${encodeURIComponent(protocol)}`,
    );
  }

  async getRegistrationStatus(
    registrationId: number,
  ): Promise<RegistrationStatus> {
    return this.request<RegistrationStatus>(
      `/api/inscricoes/status/${registrationId}`,
    );
  }

  async getReceipt(registrationId: number): Promise<ReceiptMetadata> {
    return this.request<ReceiptMetadata>(`/api/comprovantes/${registrationId}`);
  }

  async generatePaymentLink(
    registrationId: number,
  ): Promise<PaymentLinkResult> {
    return this.request<PaymentLinkResult>("/api/pagamentos/gerar-link", {
      method: "POST",
      body: JSON.stringify({ inscricao_id: registrationId }),
    });
  }

  private async request<T>(
    path: string,
    init: RequestInit = {},
  ): Promise<T> {
    const baseUrl = new URL(this.config.apiBaseUrl);
    const url = new URL(path, baseUrl);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.config.requestTimeoutMs);

    const headers = new Headers(init.headers ?? {});
    headers.set("Authorization", `Bearer ${this.config.apiToken}`);
    headers.set("Accept", "application/json");
    if (init.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    try {
      const response = await fetch(url, {
        ...init,
        headers,
        signal: controller.signal,
      });

      const text = await response.text();
      const envelope = this.parseEnvelope<T>(text, response.status);
      if (!response.ok || !envelope.success) {
        const error = envelope.error ?? {
          code: "backend_request_failed",
          message: `Backend returned status ${response.status}`,
          details: {},
        };
        throw new BackendApiError({
          message: error.message,
          code: error.code,
          status: response.status,
          details: error.details,
        });
      }
      return envelope.data;
    } catch (error) {
      if (error instanceof BackendApiError) {
        throw error;
      }
      if (error instanceof Error && error.name === "AbortError") {
        throw new BackendApiError({
          message: "Tempo limite excedido ao consultar a API oficial.",
          code: "backend_timeout",
          status: 504,
        });
      }
      throw new BackendApiError({
        message: "Falha de rede ao consultar a API oficial.",
        code: "backend_network_error",
        status: 502,
      });
    } finally {
      clearTimeout(timeout);
    }
  }

  private parseEnvelope<T>(body: string, status: number): ApiEnvelope<T> {
    if (!body.trim()) {
      throw new BackendApiError({
        message: "Resposta vazia da API oficial.",
        code: "empty_backend_response",
        status,
      });
    }
    try {
      return JSON.parse(body) as ApiEnvelope<T>;
    } catch {
      throw new BackendApiError({
        message: "Resposta invalida da API oficial.",
        code: "invalid_backend_response",
        status,
      });
    }
  }
}
