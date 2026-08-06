import assert from "node:assert/strict";
import test from "node:test";
import {
  buildChatMessages,
  generateAssistantReply,
  isEchoReply,
} from "./index.js";

test("isEchoReply catches prefixed and bare echoes", () => {
  assert.equal(isEchoReply("hello", "Kala says: hello"), true);
  assert.equal(isEchoReply("hello", "hello"), true);
  assert.equal(isEchoReply("hello", ""), true);
  assert.equal(isEchoReply("hello", "Try sharpening the image with a concrete detail."), false);
});

test("buildChatMessages bounds history and keeps system prompt", () => {
  const history = Array.from({ length: 10 }, (_, i) => ({
    message: `u${i}`,
    reply: `a${i}`,
  }));
  const msgs = buildChatMessages(history, "new question");
  assert.equal(msgs[0].role, "system");
  assert.equal(msgs[msgs.length - 1].content, "new question");
  // system + 6 turns * 2 + user
  assert.equal(msgs.length, 1 + 6 * 2 + 1);
});

test("generateAssistantReply returns null without a provider", async () => {
  const reply = await generateAssistantReply({}, "How do I improve imagery?", []);
  assert.equal(reply, null);
});

test("generateAssistantReply uses Workers AI and rejects nothing valid", async () => {
  const env = {
    AI: {
      async run(_model, { messages }) {
        assert.equal(messages[0].role, "system");
        assert.equal(messages.at(-1).content, "Improve this metaphor");
        return { response: "Anchor the metaphor in a physical sensation." };
      },
    },
  };
  const reply = await generateAssistantReply(env, "Improve this metaphor", []);
  assert.equal(reply, "Anchor the metaphor in a physical sensation.");
  assert.equal(isEchoReply("Improve this metaphor", reply), false);
});

test("successful reply must not equal the submitted message", async () => {
  const env = {
    AI: {
      async run() {
        return { response: "Improve this metaphor" };
      },
    },
  };
  const message = "Improve this metaphor";
  const reply = await generateAssistantReply(env, message, []);
  assert.equal(isEchoReply(message, reply), true);
});
