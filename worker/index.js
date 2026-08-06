const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

const CHAT_SYSTEM_PROMPT =
  "You are Kala, a concise creative companion for writers and artists. " +
  "Answer helpfully about craft, imagery, structure, and creative process. " +
  "Do not repeat the user's message back as your answer.";

const MAX_HISTORY_TURNS = 6;
const MAX_REPLY_CHARS = 4000;

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...CORS_HEADERS },
  });
}

function errorResponse(message, status = 400) {
  return jsonResponse({ error: message }, status);
}

function isAuthorized(request, env) {
  // No key configured → auth disabled (local/dev deployments without a secret set).
  if (!env.KALAOS_API_KEY) return true;
  return request.headers.get("X-API-Key") === env.KALAOS_API_KEY;
}

/** True when the model output is empty or just echoes the user message. */
export function isEchoReply(message, reply) {
  if (typeof reply !== "string") return true;
  const m = message.trim().toLowerCase();
  const r = reply.trim().toLowerCase();
  if (!r || !m) return true;
  if (r === m) return true;
  if (r === `kala says: ${m}`) return true;
  if (r.startsWith("kala says:") && r.slice("kala says:".length).trim() === m) {
    return true;
  }
  return false;
}

export function buildChatMessages(historyRows, message) {
  const messages = [{ role: "system", content: CHAT_SYSTEM_PROMPT }];
  const turns = Array.isArray(historyRows) ? historyRows.slice(-MAX_HISTORY_TURNS) : [];
  for (const row of turns) {
    if (row?.message) messages.push({ role: "user", content: String(row.message).slice(0, 2000) });
    if (row?.reply) messages.push({ role: "assistant", content: String(row.reply).slice(0, 2000) });
  }
  messages.push({ role: "user", content: message.slice(0, 2000) });
  return messages;
}

function normalizeReply(raw) {
  if (raw == null) return "";
  if (typeof raw === "string") return raw.trim().slice(0, MAX_REPLY_CHARS);
  if (typeof raw.response === "string") return raw.response.trim().slice(0, MAX_REPLY_CHARS);
  if (typeof raw.result === "string") return raw.result.trim().slice(0, MAX_REPLY_CHARS);
  if (Array.isArray(raw.choices) && raw.choices[0]?.message?.content) {
    return String(raw.choices[0].message.content).trim().slice(0, MAX_REPLY_CHARS);
  }
  return "";
}

async function generateWithWorkersAI(env, messages) {
  if (!env.AI || typeof env.AI.run !== "function") return null;
  const model = env.KALA_CHAT_MODEL || "@cf/meta/llama-3.1-8b-instruct";
  const result = await env.AI.run(model, { messages });
  return normalizeReply(result);
}

async function generateWithOpenAI(env, messages) {
  if (!env.OPENAI_API_KEY) return null;
  const model = env.OPENAI_MODEL || "gpt-4o-mini";
  const resp = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${env.OPENAI_API_KEY}`,
    },
    body: JSON.stringify({ model, messages, max_tokens: 600, temperature: 0.7 }),
  });
  if (!resp.ok) {
    const detail = await resp.text().catch(() => "");
    throw new Error(`OpenAI error ${resp.status}: ${detail.slice(0, 200)}`);
  }
  const data = await resp.json();
  return normalizeReply(data);
}

/** Returns assistant text, or null when no provider is configured. */
export async function generateAssistantReply(env, message, historyRows) {
  const messages = buildChatMessages(historyRows, message);
  const fromWorkers = await generateWithWorkersAI(env, messages);
  if (fromWorkers) return fromWorkers;
  const fromOpenAI = await generateWithOpenAI(env, messages);
  if (fromOpenAI) return fromOpenAI;
  return null;
}

export default {
  async fetch(request, env) {
    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS_HEADERS });
    }

    const url = new URL(request.url);
    const isArtworksApi =
      url.pathname === "/api/analyze" ||
      url.pathname === "/api/artworks" ||
      /^\/api\/artworks\/\d+$/.test(url.pathname);

    if (isArtworksApi && !isAuthorized(request, env)) {
      return errorResponse("Unauthorized", 401);
    }

    // POST /api/analyze — save artwork text to D1 and return confirmation
    if (url.pathname === "/api/analyze" && request.method === "POST") {
      let body;
      try {
        body = await request.json();
      } catch {
        return errorResponse("Invalid JSON body", 400);
      }

      if (!body.text) {
        return errorResponse("Missing required field: text", 400);
      }

      const title = body.title || "Untitled";

      await env.DB.prepare(
        "INSERT INTO artworks (title, content) VALUES (?, ?)"
      )
        .bind(title, body.text)
        .run();

      return jsonResponse({ message: "Saved to D1 DB", input: body });
    }

    // GET /api/artworks — list all artworks
    if (url.pathname === "/api/artworks" && request.method === "GET") {
      const { results } = await env.DB.prepare(
        "SELECT id, title, content, created_at FROM artworks ORDER BY created_at DESC"
      ).all();

      return jsonResponse({ artworks: results });
    }

    // GET /api/artworks/:id — fetch a single artwork by id
    // DELETE /api/artworks/:id — delete an artwork by id
    const artworkMatch = url.pathname.match(/^\/api\/artworks\/(\d+)$/);
    if (artworkMatch) {
      const id = parseInt(artworkMatch[1], 10);

      if (request.method === "GET") {
        const artwork = await env.DB.prepare(
          "SELECT id, title, content, created_at FROM artworks WHERE id = ?"
        )
          .bind(id)
          .first();

        if (!artwork) {
          return errorResponse("Artwork not found", 404);
        }

        return jsonResponse({ artwork });
      }

      if (request.method === "DELETE") {
        const { meta } = await env.DB.prepare(
          "DELETE FROM artworks WHERE id = ?"
        )
          .bind(id)
          .run();

        if (meta.rows_written === 0) {
          return errorResponse("Artwork not found", 404);
        }

        return jsonResponse({ message: "Artwork deleted", id });
      }
    }

    // POST /chat — generate an assistant reply (requires Workers AI or OPENAI_API_KEY)
    if (url.pathname === "/chat" && request.method === "POST") {
      let body;
      try {
        body = await request.json();
      } catch {
        return errorResponse("Invalid JSON body", 400);
      }

      if (!body.message || typeof body.message !== "string" || !body.message.trim()) {
        return errorResponse("Missing required field: message", 400);
      }

      const message = body.message.trim();

      let historyRows = [];
      try {
        const { results } = await env.DB.prepare(
          "SELECT message, reply FROM chats ORDER BY id DESC LIMIT ?"
        )
          .bind(MAX_HISTORY_TURNS)
          .all();
        historyRows = (results || []).slice().reverse();
      } catch {
        historyRows = [];
      }

      let reply;
      try {
        reply = await generateAssistantReply(env, message, historyRows);
      } catch (err) {
        return errorResponse(
          `Kala Chat generation failed: ${err?.message || "provider error"}`,
          502
        );
      }

      if (!reply) {
        return errorResponse(
          "Kala Chat is unavailable: configure Workers AI (env.AI) or set OPENAI_API_KEY.",
          503
        );
      }

      if (isEchoReply(message, reply)) {
        return errorResponse(
          "Kala Chat rejected an invalid assistant response (echo detected).",
          502
        );
      }

      await env.DB.prepare(
        "INSERT INTO chats (message, reply) VALUES (?, ?)"
      )
        .bind(message, reply)
        .run();

      return jsonResponse({ reply });
    }

    // GET /history — fetch recent chat messages
    if (url.pathname === "/history" && request.method === "GET") {
      const { results } = await env.DB.prepare(
        "SELECT id, message, reply, created_at FROM chats ORDER BY id DESC LIMIT 20"
      ).all();

      return jsonResponse({ history: results });
    }

    // Default response
    return new Response("KalaOS Worker Running 🚀", { headers: CORS_HEADERS });
  },
};
