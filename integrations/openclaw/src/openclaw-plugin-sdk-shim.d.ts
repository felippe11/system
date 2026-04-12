declare module "openclaw/plugin-sdk/plugin-entry" {
  export interface TextToolResult {
    content: Array<{ type: "text"; text: string }>;
  }

  export interface PluginApi {
    pluginConfig: Record<string, unknown>;
    runtime: {
      state: {
        resolveStateDir(): string;
      };
    };
    logger: {
      info(message: string): void;
      error?(message: string): void;
      warn?(message: string): void;
      debug?(message: string): void;
    };
    registerTool(
      tool: {
        name: string;
        description: string;
        parameters: unknown;
        execute(id: string, params: unknown): Promise<TextToolResult> | TextToolResult;
      },
      options?: { optional?: boolean },
    ): void;
  }

  export function definePluginEntry(entry: {
    id: string;
    name: string;
    description?: string;
    configSchema?: unknown;
    register(api: PluginApi): void;
  }): unknown;
}
