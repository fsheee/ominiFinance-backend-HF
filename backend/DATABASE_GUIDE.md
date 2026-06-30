# OmniFinance Database Guide

## Overview
`omnifinance.db` is a **SQLite3 database** that stores all financial data, transactions, and agent state for the OmniFinance sandbox.

**Location**: `F:\bank-ai\omnifinance.db`
**Created**: Automatically on first startup via `db.init_db()`
**Connection**: Python `sqlite3` module with row factory for dict-like access

---

## Database Schema

### Table 1: `accounts`
Stores user/sandbox wallet information.

```
id (TEXT, PRIMARY KEY)        - Unique account identifier
currency (TEXT)               - Currency code (default: USD)
balance (REAL)                - Current balance (-ve if overdraft)
created_at (TIMESTAMP)        - Account creation timestamp
```

**Example:**
```
id           | currency | balance  | created_at
account_123  | USD      | -5000.0  | 2026-06-30 01:20:00
```

**Operations:**
- `get_account(account_id)` - Fetch current balance
- `log_transaction()` - Deducts balance if status=COMPLETED
- `handle_hitl_approval()` - Deducts balance if user approves

---

### Table 2: `transactions`
Live ledger of all transactions with fraud risk scores.

```
id (TEXT, PRIMARY KEY)            - UUID transaction ID
account_id (TEXT, FOREIGN KEY)    - Link to accounts table
amount (REAL)                     - Transaction amount
merchant (TEXT)                   - Merchant/vendor name
category (TEXT)                   - Transaction category (e.g., Food, Jewelry)
location (TEXT)                   - Transaction location
velocity_mins (INTEGER)           - Time since last transaction (minutes)
risk_score (REAL)                 - Fraud risk percentage (0-100%)
status (TEXT)                     - Transaction state (see below)
timestamp (TIMESTAMP)             - When transaction occurred
```

**Transaction Status Enum:**
```
PENDING_HITL  → Transaction paused, waiting for human approval (risk > 75%)
APPROVED      → User approved via HITL endpoint
REJECTED      → User rejected via HITL endpoint
COMPLETED     → Auto-completed (risk ≤ 75%), balance deducted
```

**Example:**
```
id                                   | account_id  | amount | merchant | category       | location            | velocity_mins | risk_score | status        | timestamp
29f4de1c-fe00-48ac-817f-c9c869490fc2 | account_123 | 5200   | Jeweler  | Jewelry        | Suspicious Location | 1             | 81.0       | PENDING_HITL  | 2026-06-30 01:20:15
```

---

### Table 3: `agent_memory`
Persists agent state and conversation context across turns (session continuity).

```
session_id (TEXT)           - User session ID
agent_id (TEXT)             - Agent identifier
memory_key (TEXT)           - Memory variable name
memory_value (TEXT)         - Stored value (JSON-serialized if needed)
updated_at (TIMESTAMP)      - Last update timestamp
PRIMARY KEY: (session_id, agent_id, memory_key)
```

**Example:**
```
session_id        | agent_id                | memory_key  | memory_value | updated_at
sandbox_session   | central_orchestrator    | last_intent | EXPENSE      | 2026-06-30 01:20:10
sandbox_session   | expense_tracker_agent   | last_amount | 5200         | 2026-06-30 01:20:15
```

---

## Core Operations

### 1. Initialize Database
```python
from database import db

db.init_db()
```
- Creates 3 tables if they don't exist
- Seeds default account: `account_123` with $5000 balance

### 2. Log a Transaction (Low-Risk)
```python
logged_tx = db.log_transaction(
    tx_id="uuid-here",
    account_id="account_123",
    amount=45.0,
    merchant="Domino's",
    category="Food & Dining",
    location="Home Location",
    velocity_mins=1,
    risk_score=26.0,
    status="COMPLETED"
)
```
**Result**: 
- ✅ Inserted into transactions table
- ✅ Balance automatically deducted: $5000 → $4955

### 3. Log a Transaction (High-Risk - HITL Pause)
```python
logged_tx = db.log_transaction(
    tx_id="uuid-here",
    account_id="account_123",
    amount=5200.0,
    merchant="Jeweler",
    category="Jewelry",
    location="Suspicious Location",
    velocity_mins=1,
    risk_score=81.0,
    status="PENDING_HITL"  # Transaction paused!
)
```
**Result**: 
- ✅ Inserted into transactions table
- ❌ Balance NOT deducted (waiting for approval)
- ⏸️ Transaction locked in PENDING_HITL state

### 4. Human-in-the-Loop (HITL) Approval
```python
# User approves the transaction
result = db.handle_hitl_approval(
    tx_id="uuid-here",
    approve=True
)
```
**Result**: 
- ✅ Transaction status: PENDING_HITL → APPROVED
- ✅ Balance deducted: $4955 → -$245

Or if user rejects:
```python
result = db.handle_hitl_approval(
    tx_id="uuid-here",
    approve=False
)
```
**Result**: 
- ✅ Transaction status: PENDING_HITL → REJECTED
- ❌ Balance unchanged (funds not deducted)

### 5. Fetch Account Details
```python
account = db.get_account("account_123")
# Returns: {'id': 'account_123', 'currency': 'USD', 'balance': -5245.0}
```

### 6. Fetch Recent Transactions
```python
transactions = db.get_transactions("account_123", limit=5)
# Returns list of 5 most recent transactions (ordered by timestamp DESC)
```

### 7. Save Agent Memory (Session Continuity)
```python
db.save_agent_memory(
    session_id="sandbox_session",
    agent_id="central_orchestrator",
    key="last_intent",
    value="EXPENSE"
)
```
Enables multi-turn conversations where agents remember previous context.

### 8. Retrieve Agent Memory
```python
last_intent = db.get_agent_memory(
    session_id="sandbox_session",
    agent_id="central_orchestrator",
    key="last_intent"
)
# Returns: "EXPENSE"
```

### 9. Reset Database (Testing)
```python
db.reset_db()
```
Drops all tables and reinitializes with fresh schema + seeded account.

---

## Transaction Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ User Input: "Spent $5200 on jewelry in Suspicious Location"    │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ Orchestrator: Classify Intent → EXPENSE                         │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ Expense Tracker: Extract (amount=$5200, merchant=Jeweler, ...)  │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ Fraud Detector: Calculate Risk Score = 81%                      │
│ Decision: risk_score > 75% → PAUSE_FOR_HITL                    │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ db.log_transaction(status="PENDING_HITL")                       │
│ - INSERT into transactions table ✓                              │
│ - DO NOT deduct balance (waiting for human approval)            │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ API Response to Frontend: "Transaction PAUSED - Awaiting HITL"   │
│ Display high-risk warning to user                               │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
        ┌──────────────────┴──────────────────┐
        ↓                                     ↓
    User Approves                         User Rejects
        ↓                                     ↓
┌──────────────────┐                 ┌──────────────────┐
│ db.handle_hitl   │                 │ db.handle_hitl   │
│ (approve=True)   │                 │ (approve=False)  │
│                  │                 │                  │
│ Status:          │                 │ Status:          │
│ PENDING→APPROVED │                 │ PENDING→REJECTED │
│                  │                 │                  │
│ Balance Deducted │                 │ Balance Unchanged│
│ $5000 → -$200    │                 │ $5000 (kept)     │
└──────────────────┘                 └──────────────────┘
```

---

## Example Query: Inspect Database

### Using Python
```python
from database import db
import sqlite3

# Get connection directly
conn = db.get_connection()
cursor = conn.cursor()

# Query all transactions
cursor.execute("SELECT id, merchant, amount, risk_score, status FROM transactions")
for row in cursor.fetchall():
    print(f"{row['merchant']}: ${row['amount']} (Risk: {row['risk_score']}%) - {row['status']}")

conn.close()
```

### Using SQLite CLI
```bash
cd F:\bank-ai
sqlite3 omnifinance.db

# View all transactions
SELECT id, merchant, amount, risk_score, status FROM transactions;

# View account balance
SELECT id, balance, currency FROM accounts WHERE id='account_123';

# View agent memory for session
SELECT agent_id, memory_key, memory_value FROM agent_memory 
WHERE session_id='sandbox_session';
```

---

## Key Design Patterns

### 1. **Atomic Transactions**
Balance deduction only happens when:
- `status="COMPLETED"` (low-risk auto-complete), OR
- User approves via HITL endpoint

Prevents accidental double-charging or inconsistent state.

### 2. **Foreign Key Constraint**
```sql
FOREIGN KEY(account_id) REFERENCES accounts(id)
```
Ensures transactions always link to valid accounts.

### 3. **Status Enum Validation**
```sql
CHECK(status IN ('PENDING_HITL', 'APPROVED', 'REJECTED', 'COMPLETED'))
```
Prevents invalid transaction states.

### 4. **Session Continuity**
`agent_memory` table enables:
- Multi-turn conversations
- Context preservation across API calls
- Agent state persistence (e.g., "what was the last intent?")

### 5. **Timestamp Tracking**
All transactions & updates are timestamped for:
- Audit trails
- Velocity calculations (minutes since last transaction)
- Historical analysis

---

## Testing the Database

### Run Full Simulation
```bash
cd F:\bank-ai
python test_sandbox.py
```

Expected output shows:
- Account balance updates
- Transactions logged with risk scores
- HITL pause/approval workflow
- Agent memory persistence

### Manual Testing
```python
from database import db

# Initialize
db.init_db()

# Check initial balance
account = db.get_account("account_123")
print(f"Initial Balance: ${account['balance']}")  # $5000.0

# Log a low-risk transaction
db.log_transaction(
    tx_id="tx_001",
    account_id="account_123",
    amount=100.0,
    merchant="Coffee Shop",
    category="Food",
    location="Downtown",
    velocity_mins=30,
    risk_score=10.0,
    status="COMPLETED"
)

# Verify balance decreased
account = db.get_account("account_123")
print(f"Updated Balance: ${account['balance']}")  # $4900.0

# View transaction
tx = db.get_transaction("tx_001")
print(f"Transaction: {tx['merchant']} - {tx['status']}")  # Coffee Shop - COMPLETED
```

---

## Summary

| Component | Purpose |
|-----------|---------|
| **accounts** | Wallet balances per user |
| **transactions** | Live ledger with fraud scores & status |
| **agent_memory** | Session state & conversation context |
| **Atomic balance logic** | Ensures consistency (deduct only on COMPLETED or APPROVED) |
| **HITL integration** | Pauses high-risk transactions for human review |
| **Timestamp tracking** | Audit trail & velocity calculations |

The database is the **backbone of OmniFinance**, coordinating between agents, enforcing business rules, and maintaining audit-ready financial records. ✅
