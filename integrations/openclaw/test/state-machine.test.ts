import test from "node:test";
import assert from "node:assert/strict";

import {
  buildResumeSummary,
  inferConversationState,
} from "../src/intents/state-machine.js";
import { ConversationState, type UserConversationState } from "../src/types.js";

function makeState(
  patch: Partial<UserConversationState>,
): UserConversationState {
  const draft = patch.draft ?? {};
  const base: UserConversationState = {
    userKey: "5511999999999",
    state: ConversationState.IDLE,
    updatedAt: new Date().toISOString(),
    draft: {},
  };
  return {
    ...base,
    ...patch,
    draft,
  };
}

test("inferConversationState walks through missing data", () => {
  assert.equal(
    inferConversationState(makeState({})),
    ConversationState.AWAITING_EVENT_SELECTION,
  );
  assert.equal(
    inferConversationState(makeState({ selectedEventId: 10 })),
    ConversationState.AWAITING_CPF,
  );
  assert.equal(
    inferConversationState(
      makeState({ selectedEventId: 10, draft: { cpf: "52998224725" } }),
    ),
    ConversationState.AWAITING_NAME,
  );
  assert.equal(
    inferConversationState(
      makeState({
        selectedEventId: 10,
        draft: {
          cpf: "52998224725",
          nome: "Ana",
          email: "ana@example.com",
          formacao: "Graduacao",
        },
      }),
    ),
    ConversationState.READY_TO_CREATE,
  );
});

test("buildResumeSummary reflects the latest saved step", () => {
  const ready = makeState({
    state: ConversationState.READY_TO_CREATE,
    selectedEventId: 7,
    draft: {
      cpf: "52998224725",
      nome: "Ana",
      email: "ana@example.com",
      formacao: "Graduacao",
    },
  });
  const completed = makeState({
    state: ConversationState.COMPLETED,
    registrationId: 22,
    protocolo: "abc123",
  });

  assert.match(buildResumeSummary(ready), /criar_inscricao/);
  assert.match(buildResumeSummary(completed), /Fluxo concluido/);
});
