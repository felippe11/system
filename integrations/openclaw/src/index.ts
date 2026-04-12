import { Type } from "@sinclair/typebox";
import {
  definePluginEntry,
  type PluginApi,
  type TextToolResult,
} from "openclaw/plugin-sdk/plugin-entry";

import { parsePluginConfig } from "./config.js";
import { OpenClawBackendClient } from "./http/api-client.js";
import {
  SAFE_TOOL_SYSTEM_PROMPT_PT_BR,
  TOOL_USAGE_CHECKLIST_PT_BR,
} from "./prompts/safe-tool-prompts.js";
import { WhatsAppEnrollmentService } from "./services/registration-service.js";
import {
  FileConversationStateStore,
  resolveStateFile,
} from "./services/state-store.js";

function textResult(data: unknown): TextToolResult {
  return {
    content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
  };
}

export default definePluginEntry({
  id: "whatsapp-inscricoes",
  name: "WhatsApp Inscricoes",
  description:
    "Tools tipadas para inscricoes oficiais via WhatsApp usando a API oficial.",
  configSchema: Type.Object({
    apiBaseUrl: Type.String({ minLength: 1 }),
    apiToken: Type.String({ minLength: 1 }),
    requestTimeoutMs: Type.Optional(Type.Integer({ minimum: 1000, maximum: 60000 })),
    defaultClienteId: Type.Optional(Type.Integer({ minimum: 1 })),
    publicOnly: Type.Optional(Type.Boolean())
  }),
  register(api: PluginApi) {
    const config = parsePluginConfig(api.pluginConfig as Record<string, unknown>);
    const stateFile = resolveStateFile(api.runtime.state.resolveStateDir());
    const stateStore = new FileConversationStateStore(stateFile);
    const client = new OpenClawBackendClient(config);
    const service = new WhatsAppEnrollmentService(client, stateStore, config);

    api.logger.info(SAFE_TOOL_SYSTEM_PROMPT_PT_BR);
    api.logger.info(TOOL_USAGE_CHECKLIST_PT_BR);

    api.registerTool({
      name: "listar_eventos",
      description: "Lista eventos disponiveis na API oficial.",
      parameters: Type.Object({
        clienteId: Type.Optional(Type.Integer({ minimum: 1 })),
        somentePublicos: Type.Optional(Type.Boolean())
      }),
      async execute(
        _id: string,
        params: { clienteId?: number; somentePublicos?: boolean },
      ) {
        return textResult(await service.listarEventos(params));
      }
    });

    api.registerTool({
      name: "detalhar_evento",
      description: "Busca o detalhe oficial de um evento e opcionalmente salva o evento no estado do usuario.",
      parameters: Type.Object({
        eventoId: Type.Integer({ minimum: 1 }),
        userKey: Type.Optional(Type.String({ minLength: 1 }))
      }),
      async execute(
        _id: string,
        params: { eventoId: number; userKey?: string },
      ) {
        return textResult(await service.detalharEvento(params));
      }
    });

    api.registerTool({
      name: "buscar_participante_por_cpf",
      description: "Consulta a API oficial pelo CPF do participante.",
      parameters: Type.Object({
        cpf: Type.String({ minLength: 11 }),
        userKey: Type.Optional(Type.String({ minLength: 1 }))
      }),
      async execute(
        _id: string,
        params: { cpf: string; userKey?: string },
      ) {
        return textResult(await service.buscarParticipantePorCpf(params));
      }
    });

    api.registerTool(
      {
        name: "criar_inscricao",
        description: "Cria uma inscricao oficial no backend e nunca assume sucesso.",
        parameters: Type.Object({
          userKey: Type.Optional(Type.String({ minLength: 1 })),
          eventoId: Type.Integer({ minimum: 1 }),
          cpf: Type.String({ minLength: 11 }),
          nome: Type.String({ minLength: 3 }),
          email: Type.String({ minLength: 5 }),
          formacao: Type.String({ minLength: 2 }),
          senha: Type.Optional(Type.String({ minLength: 8 })),
          loteId: Type.Optional(Type.Integer({ minimum: 1 })),
          tipoInscricaoId: Type.Optional(Type.Integer({ minimum: 1 }))
        }),
        async execute(
          _id: string,
          params: {
            userKey?: string;
            eventoId: number;
            cpf: string;
            nome: string;
            email: string;
            formacao: string;
            senha?: string;
            loteId?: number;
            tipoInscricaoId?: number;
          },
        ) {
          return textResult(await service.criarInscricao(params));
        }
      },
      { optional: true }
    );

    api.registerTool({
      name: "consultar_inscricao_por_cpf",
      description: "Lista inscricoes oficiais de um CPF.",
      parameters: Type.Object({
        cpf: Type.String({ minLength: 11 }),
        eventoId: Type.Optional(Type.Integer({ minimum: 1 })),
        userKey: Type.Optional(Type.String({ minLength: 1 }))
      }),
      async execute(
        _id: string,
        params: { cpf: string; eventoId?: number; userKey?: string },
      ) {
        return textResult(await service.consultarInscricaoPorCpf(params));
      }
    });

    api.registerTool({
      name: "consultar_status_inscricao",
      description: "Consulta o status oficial de uma inscricao.",
      parameters: Type.Object({
        inscricaoId: Type.Integer({ minimum: 1 }),
        userKey: Type.Optional(Type.String({ minLength: 1 }))
      }),
      async execute(
        _id: string,
        params: { inscricaoId: number; userKey?: string },
      ) {
        return textResult(await service.consultarStatusInscricao(params));
      }
    });

    api.registerTool({
      name: "consultar_comprovante",
      description: "Consulta o comprovante oficial e devolve o link gerado pela API.",
      parameters: Type.Object({
        inscricaoId: Type.Integer({ minimum: 1 }),
        userKey: Type.Optional(Type.String({ minLength: 1 }))
      }),
      async execute(
        _id: string,
        params: { inscricaoId: number; userKey?: string },
      ) {
        return textResult(await service.consultarComprovante(params));
      }
    });

    api.registerTool(
      {
        name: "gerar_link_pagamento",
        description: "Gera o link oficial de pagamento para uma inscricao pendente.",
        parameters: Type.Object({
          inscricaoId: Type.Integer({ minimum: 1 }),
          userKey: Type.Optional(Type.String({ minLength: 1 }))
        }),
        async execute(
          _id: string,
          params: { inscricaoId: number; userKey?: string },
        ) {
          return textResult(await service.gerarLinkPagamento(params));
        }
      },
      { optional: true }
    );
  }
});
