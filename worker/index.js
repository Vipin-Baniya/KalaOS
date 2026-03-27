const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...CORS_HEADERS },
  });
}

function errorResponse(message, status = 400) {
  return jsonResponse({ error: message }, status);
}

export default {
  async fetch(request, env) {
    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS_HEADERS });
    }

    const url = new URL(request.url);

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

    // POST /chat — receive a chat message, store it, return a reply
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
      // TODO: Replace with AI response (e.g. Workers AI or OpenAI) when available
      const reply = "Kala says: " + message;

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
