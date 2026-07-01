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
