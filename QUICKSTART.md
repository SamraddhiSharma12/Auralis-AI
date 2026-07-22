# Auralis AI — Quickstart Guide

Auralis AI is a customer support agent that answers questions using a knowledge base of support documentation. It combines retrieval-augmented generation (RAG) with an LLM-powered reasoning agent to ground its answers in real content, detect when a query is out of scope, and recognize when a user wants to speak with a human agent.

This guide covers the `/chat/text` endpoint — the core text-based interaction with the agent. Voice interaction and authentication are covered in separate guides (coming soon).

---

## Base URL

```
http://localhost:8000
```

*(Replace with your deployed URL once the service is hosted.)*

## Authentication

This API currently runs without authentication for local development. Auth will be added in a future version — check back or see the [Auth Guide](#) once available.

---

## Sending a query

Send a `POST` request to `/chat/text` with a JSON body containing your query as the `text` field.

```bash
curl -X POST http://localhost:8000/chat/text \
  -H "Content-Type: application/json" \
  -d '{"text": "What is your refund policy?"}'
```

> **Note:** the request field is named `text`, not `query` or `message` — using the wrong field name will return a `422` validation error (see [Errors](#errors) below).

### Example response

```json
{
  "response_text": "We offer a 30-day return policy for all products purchased from our store. Items must be in original condition with all tags and packaging intact. Returns are processed within 5-7 business days of receiving the returned item. Refunds are issued to the original payment method.",
  "audio_available": true,
  "processing_time_ms": 5793
}
```

### Response fields

| Field | Type | Description |
|---|---|---|
| `response_text` | `string` | The agent's natural-language answer, synthesized from retrieved knowledge base content. |
| `audio_available` | `boolean` | Whether a spoken (TTS) version of this response can be requested via the voice endpoint. |
| `processing_time_ms` | `number` | Server-side processing time in milliseconds, measured from query receipt to response generation. |

---

## Special response behaviors

The agent handles two cases beyond straightforward Q&A:

**Escalation requests.** If your query indicates you want to speak with a human (e.g. contains phrases like "speak to a manager" or "human agent"), the agent skips retrieval and returns an escalation message directly:

```bash
curl -X POST http://localhost:8000/chat/text \
  -H "Content-Type: application/json" \
  -d '{"text": "I was charged twice, can I speak to a manager?"}'
```

```json
{
  "response_text": "It sounds like you'd like to speak with a human support agent. I'm connecting you now - a representative will be with you shortly. In the meantime, is there anything I can look up for you?",
  "audio_available": true,
  "processing_time_ms": 1511
}
```

**Out-of-scope queries.** If nothing in the knowledge base is a close enough match to your query, the agent returns a fallback instead of guessing:

```bash
curl -X POST http://localhost:8000/chat/text \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the capital of France?"}'
```

```json
{
  "response_text": "I couldn't find relevant information to answer that. Could you rephrase your question, or would you like to speak with a human support agent?",
  "audio_available": true,
  "processing_time_ms": 1889
}
```

---

## Errors

| Status | Cause | Example |
|---|---|---|
| `422` | Missing or misnamed request field | `{"detail":[{"type":"missing","loc":["body","text"],"msg":"Field required"}]}` |
| `429` | LLM provider rate limit reached (applies to underlying inference, not this API directly) | `{"error":{"message":"Rate limit reached... tokens per minute (TPM)...","type":"tokens","code":"rate_limit_exceeded"}}` |
| `500` | Internal error (e.g. misconfigured LLM model name) | `{"detail":"Error code: 404 - The model \`gpt-3.5-turbo\` does not exist..."}` |

---

## Known limitations

- **Escalation detection is keyword-based**, not intent-based. Phrases that don't match the built-in keyword list (e.g. "this is ridiculous, I want my money back") may not trigger escalation even when a human agent would be appropriate.
- **Out-of-scope detection uses a fixed relevance-distance threshold**, tuned against a small internal test set (5 query categories). It may not generalize perfectly to all possible out-of-scope inputs.
- **LLM inference runs via Groq's free tier**, which enforces a token-per-minute rate limit. Rapid, repeated requests (e.g. automated testing) may trigger `429` responses with automatic retry delays.

---

## Next steps

- Voice interaction guide (coming soon)
- Authentication guide (coming soon)
- [Source code](#)
