import type { OpenClawPluginConfig } from "./types.js";

export function parsePluginConfig(
  rawConfig: Record<string, unknown>,
): OpenClawPluginConfig {
  const apiBaseUrl = String(rawConfig.apiBaseUrl ?? "").trim();
  const apiToken = String(rawConfig.apiToken ?? "").trim();

  if (!apiBaseUrl) {
    throw new Error("plugins.entries.whatsapp-inscricoes.config.apiBaseUrl is required");
  }
  if (!apiToken) {
    throw new Error("plugins.entries.whatsapp-inscricoes.config.apiToken is required");
  }

  const timeout = Number(rawConfig.requestTimeoutMs ?? 15000);
  const defaultClienteId = rawConfig.defaultClienteId;
  const publicOnly = rawConfig.publicOnly;

  return {
    apiBaseUrl,
    apiToken,
    requestTimeoutMs: Number.isFinite(timeout) && timeout > 0 ? timeout : 15000,
    defaultClienteId:
      typeof defaultClienteId === "number" ? defaultClienteId : undefined,
    publicOnly: typeof publicOnly === "boolean" ? publicOnly : true,
  };
}
