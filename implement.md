# OmniFinance UI: Next.js Conversion Plan

This document outlines the architecture and execution steps to convert the existing Vanilla HTML/CSS/JS frontend dashboard under [static/](file:///F:/bank-ai/static) into a modern **Next.js** application.

---

## 🎯 Architecture Overview

To maintain the ease of running the sandbox (a single command starting both FastAPI and serving the UI), we will use a **Static Export** architecture:

```
+--------------------------------------------------------------+
|                        FastAPI Backend                       |
|  - API endpoints (/chat, /wallet, /transactions, /telemetry) |
|  - Serves static SPA build from `frontend/out`               |
+--------------------------------------------------------------+
                               ^
                               | (Local REST API Requests)
                               v
+--------------------------------------------------------------+
|                         Next.js App                          |
|  - React Components (Telemetry cards, Live Ledger, Chat)     |
|  - Styled using custom CSS / modules ported from style.css  |
|  - Compiled to HTML/CSS/JS via `next build` (output: export) |
+--------------------------------------------------------------+
```

1. **Next.js Subfolder:** All Next.js source code will live in a new `frontend/` directory. This keeps Node.js package dependencies (`package.json`, `node_modules`) completely separate from the Python backend dependencies.
2. **Static HTML Export:** The Next.js application will be configured with `output: 'export'` in `next.config.js`. Running `npm run build` will generate a standalone directory (`frontend/out`) containing only static HTML, CSS, and JS assets.
3. **FastAPI Mounting:** We will update [main.py](file:///F:/bank-ai/main.py) to mount the `frontend/out` folder at the root `/` using FastAPI's `StaticFiles` mount with `html=True`. This ensures API endpoints are resolved first, and any remaining request is routed to the Next.js static files (such as `_next/...` and `index.html`).

---

## 📁 Proposed Folder Structure

```
F:\bank-ai\
├── main.py                     # Updated FastAPI backend to serve next.js build
...
└── frontend/                   # New Next.js Project Directory
    ├── package.json            # Node dependencies
    ├── next.config.js          # Next.js configurations (output: 'export')
    ├── public/                 # Static assets (icons, images)
    │
    └── src/
        ├── app/
        │   ├── layout.tsx      # Main layout (fonts, metadata, icons)
        │   ├── page.tsx        # Dashboard root page (holds application state)
        │   └── globals.css     # Global styles & premium styling variables
        │
        └── components/         # Reusable React components
            ├── ChatSection.tsx # Chat interface & Orchestrator routing status
            ├── WalletCard.tsx  # Wallet balance visualizer
            ├── Telemetry.tsx   # Real-time transaction stats
            └── LedgerTable.tsx # Live ledger database list & HITL approval triggers
```

---

## ⚙️ Step-by-Step Implementation Plan

### Step 1: Create the Next.js Project Structure
We will initialize the Next.js application in the `frontend` folder using `npx create-next-app@latest` with the following configuration:
* App Router: **Yes**
* TypeScript: **Yes**
* Tailwind CSS: **No** (we will use Vanilla CSS variables and global styling to retain full premium visual design control and meet the workspace guidelines)
* `src/` directory: **Yes**
* Import Alias: **Yes** (`@/*`)

### Step 2: Configure Next.js for Static Export
Create/edit `frontend/next.config.js` to enable static export and disable image optimization (since it requires a running Node server):
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: {
    unoptimized: true,
  },
};
module.exports = nextConfig;
```

### Step 3: Implement CSS Design Tokens
Create `frontend/src/app/globals.css` and port the entire premium dark theme system (colors, glassmorphism, animations, scrollbars) from the current `static/style.css`.

### Step 4: Build React Components
Implement the following states and interactive UI logic in React:
1. **Chat Workspace (`ChatSection`):** 
   - State for `messages` (user, orchestrator, fraud, coach, system).
   - Async query processing state with spinning indicator.
   - Text parsing highlights for financial jargon.
   - Automatic scroll-to-bottom on new messages.
2. **Dashboard Cards (`WalletCard` & `Telemetry`):**
   - Poll telemetry endpoint `/api/telemetry` and `/wallet` every 5 seconds.
   - Live transitions when balances update.
3. **Transaction Table (`LedgerTable`):**
   - Poll or refresh transaction list.
   - Render HITL buttons (Approve / Reject) for transactions with `PENDING_HITL` status.
   - Dispatch `/transactions/approve` POST requests when clicked, updating status in real-time.
4. **Header Panel:**
   - Reset Sandbox button requesting `/reset` endpoint, triggering local state resets.

### Step 5: Update FastAPI Mount in Backend
Modify [main.py](file:///F:/bank-ai/main.py):
* Remove original static folder mount (`/static`).
* Remove index route returning `static/index.html`.
* Mount the `frontend/out` folder at the bottom of the middleware stack:
  ```python
  from fastapi.staticfiles import StaticFiles
  # ... (All API endpoints) ...
  app.mount("/", StaticFiles(directory="frontend/out", html=True), name="static")
  ```

---

---

## 🧠 ChromaDB RAG Integration

The literacy coach (Agent D) uses a **ChromaDB vector store** for semantic knowledge retrieval, but this runs entirely server-side. The frontend only needs to handle:

1. **Chat messages** — User queries are sent to `/chat` and the response from the orchestrator (which internally calls Agent D → RAG) is streamed back.
2. **Jargon highlighting** — Financial terms in chat messages that come from the RAG knowledge base should be visually highlighted (e.g. tooltip with analogy). This is purely a frontend rendering concern — the backend already tags terms in the response.

No direct frontend API calls to ChromaDB are needed.

### RAG Response Format (from `/chat` endpoint)

When the orchestrator routes to Agent D (Literacy Coach), the chat response includes metadata:

```json
{
  "response": "Compound interest grows like a snowball effect...",
  "agent": "literacy_coach",
  "rag_results": [
    {"term": "compound_interest", "definition": "...", "score": 0.95},
    {"term": "liquidity", "definition": "...", "score": 0.87}
  ]
}
```

The frontend can optionally render `rag_results` as a reference panel beneath the coach's response.

---

## 🚀 How to Run the Updated App

### Development Mode (Concurrent dev servers)
1. **Backend:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```
2. **Frontend:**
   ```bash
   cd frontend
   npm run dev
   # Runs on http://localhost:3000
   ```

### Production / Compiled Sandbox Mode
1. Build the Next.js static site:
   ```bash
   cd frontend
   npm run build
   ```
2. Start the unified FastAPI server:
   ```bash
   cd ..
   
   ```
3. Open `http://localhost:8000` to view the fully compiled Next.js application served natively by FastAPI.
