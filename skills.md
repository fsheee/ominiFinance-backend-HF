# OmniFinance Sandbox: Skills & Capabilities

## Backend Skills

### FastAPI (Python)
- REST API development with automatic OpenAPI docs
- Static file serving with `StaticFiles` mount
- CORS middleware configuration
- Async endpoint handlers
- Request/response model validation via Pydantic

### SQLite Database
- Atomic balance deductions and transaction logging
- Schema: `accounts`, `transactions`, `agent_memory` tables
- Status-based workflow: `PENDING_HITL` → `APPROVED` / `REJECTED` / `COMPLETED`
- Foreign key relationships and CHECK constraints

### ChromaDB Vector Store
- Persistent local vector store (`.chroma/` directory)
- `DefaultEmbeddingFunction` (ONNX all-MiniLM-L6-v2, 384-d embeddings)
- Cosine similarity search with score thresholds
- Idempotent seeding via `seed_knowledge_base()`
- Collection: `financial_knowledge` with metadata `{term, definition, analogy, explanation}`

### Multi-Agent Architecture
| Agent | Role | Key Capability |
|-------|------|----------------|
| **A: Central Orchestrator** | Intent classification & routing | Routes to Expense/Literacy/Wallet/Fraud sub-agents |
| **B: Expense Tracker** | Natural language parsing | Extracts `{amount, merchant, category, timestamp}` from text |
| **C: Fraud Detector** | Risk scoring | Computes composite risk (amount + velocity + location), manages HITL pauses |
| **D: Literacy Coach** | RAG-based financial education | Semantic search + inline analogy injection (e.g. "snowball effect") |

### Fraud Detection Pipeline
- Risk score thresholds (75% triggers `PENDING_HITL`)
- HITL (Human-In-The-Loop) approval workflow
- Transaction status lifecycle management
- `/transactions/approve` endpoint for manual intervention

### Chat API (`/chat`)
- Streams orchestrator responses with agent metadata
- Returns `rag_results` for literacy queries (term, definition, score)
- Structured JSON response format with agent identification

### Wallet & Telemetry
- Balance queries and transaction ledger
- `/wallet`, `/telemetry` endpoints
- 5-second polling design for live dashboard updates

---

## Frontend Skills

### Next.js (Static Export)
- App Router with TypeScript
- `output: 'export'` for static HTML/CSS/JS generation
- No Tailwind CSS — custom CSS design tokens
- `@/*` import alias pattern

### React Components
| Component | Responsibility |
|-----------|----------------|
| `ChatSection` | Message state, async query processing, auto-scroll, jargon highlighting |
| `WalletCard` | Balance visualization with live transitions |
| `Telemetry` | Real-time transaction stats polling |
| `LedgerTable` | HITL approve/reject buttons, live status updates |

### UI/UX Patterns
- Dark theme with glassmorphism and CSS animations
- Custom scrollbars and premium visual design
- Async state indicators (spinning loaders)
- Polling-based live data refresh (5s intervals)
- Automatic scroll-to-bottom on new chat messages
- Jargon term highlighting with tooltip analogies

---

## DevOps & Tooling

### Development Workflow
- Backend: `uvicorn main:app --reload --port 8000`
- Frontend: `npm run dev` (port 3000)
- Production build: `npm run build` + uvicorn serves from `frontend/out`

### Python Dependencies
- FastAPI + uvicorn (async server)
- ChromaDB (vector store)
- Google ADK routing principles (agent orchestration)
- Pydantic (data validation)

### Node Dependencies
- Next.js (static export)
- TypeScript
- Custom CSS (no Tailwind)

---

## Data Flow Patterns

```
User Input → Agent A (Orchestrator)
  ├─ Wallet  → Direct SQLite Query
  ├─ Expense → Agent B (Parse) → Agent C (Fraud Check)
  │             └─ Risk > 75% → PENDING_HITL → /transactions/approve
  │             └─ Risk ≤ 75% → COMPLETED → Deduct balance
  ├─ Fraud   → Agent C (Direct Risk Query)
  └─ Literacy → Agent D (RAG Search → ChromaDB)
                 └─ Inject analogies → Return coach response
```
