---
title: OmniFinance API
emoji: 🏦
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# OmniFinance API

FastAPI backend for the OmniFinance autonomous banking sandbox.

## Authentication

Protected endpoints require an API key in the request header:

```
X-API-Key: your-api-key
```

**Protected endpoints** (require `X-API-Key` header):
- `POST /chat`
- `POST /tools/execute`
- `POST /transactions/approve`
- `POST /reset`

**Public endpoints** (no auth required):
- `GET /`
- `GET /health`
- `GET /wallet`
- `GET /transactions`
- `GET /skills`
- `GET /api/telemetry`
- `GET /docs`

* **Live API Documentation:** [OmniFinance API Docs](https://afsheenkhi-omnifinance-api.hf.space/docs)


Example curl request:

```bash
curl -X POST https://Afsheekhi-omnifinance-api.hf.space/chat \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Spent $45 on pizza", "session_id": "test"}'
```

## Skills

See [skills.md](skills.md) for the full agent skills registry.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key for AI routing |
| `HUGGING_FACE_TOKEN` | Hugging Face token for gated models |

## API Endpoints

- `GET /api/telemetry` - Sandbox telemetry
- `POST /chat` - Main orchestrator endpoint
- `GET /wallet` - Account balance
- `GET /transactions` - Transaction history
- `POST /transactions/approve` - HITL approval
- `POST /tools/execute` - MCP tool execution
- `POST /reset` - Reset sandbox


