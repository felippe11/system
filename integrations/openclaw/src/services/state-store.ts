import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";

import { ConversationState, type UserConversationState } from "../types.js";

export class FileConversationStateStore {
  constructor(private readonly filePath: string) {}

  async get(userKey: string): Promise<UserConversationState> {
    const data = await this.readAll();
    return data[userKey] ?? defaultConversationState(userKey);
  }

  async save(state: UserConversationState): Promise<UserConversationState> {
    const data = await this.readAll();
    data[state.userKey] = {
      ...state,
      updatedAt: new Date().toISOString(),
    };
    await this.writeAll(data);
    return data[state.userKey];
  }

  async patch(
    userKey: string,
    partial: Partial<UserConversationState>,
  ): Promise<UserConversationState> {
    const current = await this.get(userKey);
    const next: UserConversationState = {
      ...current,
      ...partial,
      draft: {
        ...current.draft,
        ...partial.draft,
      },
      updatedAt: new Date().toISOString(),
    };
    return this.save(next);
  }

  async clear(userKey: string): Promise<void> {
    const data = await this.readAll();
    delete data[userKey];
    await this.writeAll(data);
  }

  async readAll(): Promise<Record<string, UserConversationState>> {
    try {
      const raw = await readFile(this.filePath, "utf-8");
      return JSON.parse(raw) as Record<string, UserConversationState>;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") {
        return {};
      }
      throw error;
    }
  }

  private async writeAll(
    data: Record<string, UserConversationState>,
  ): Promise<void> {
    await mkdir(dirname(this.filePath), { recursive: true });
    await writeFile(this.filePath, JSON.stringify(data, null, 2), "utf-8");
  }
}

export function defaultConversationState(userKey: string): UserConversationState {
  return {
    userKey,
    state: ConversationState.IDLE,
    updatedAt: new Date().toISOString(),
    draft: {},
  };
}

export function resolveStateFile(stateDir: string): string {
  return join(stateDir, "whatsapp-inscricoes", "conversation-state.json");
}
