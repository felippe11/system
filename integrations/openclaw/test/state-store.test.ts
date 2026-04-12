import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  FileConversationStateStore,
  resolveStateFile,
} from "../src/services/state-store.js";
import { ConversationState } from "../src/types.js";

test("FileConversationStateStore persists and patches user state", async () => {
  const dir = await mkdtemp(join(tmpdir(), "openclaw-state-"));
  const store = new FileConversationStateStore(resolveStateFile(dir));

  const initial = await store.get("5511999999999");
  assert.equal(initial.state, ConversationState.IDLE);

  await store.patch("5511999999999", {
    selectedEventId: 42,
    state: ConversationState.AWAITING_CPF,
  });

  const saved = await store.get("5511999999999");
  assert.equal(saved.selectedEventId, 42);
  assert.equal(saved.state, ConversationState.AWAITING_CPF);

  await store.clear("5511999999999");
  const cleared = await store.get("5511999999999");
  assert.equal(cleared.state, ConversationState.IDLE);
});
