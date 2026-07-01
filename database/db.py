import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "omnifinance.db")

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema and seeds a default sandbox account."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Accounts Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                currency TEXT NOT NULL DEFAULT 'USD',
                balance REAL NOT NULL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Transactions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                amount REAL NOT NULL,
                merchant TEXT NOT NULL,
                category TEXT NOT NULL,
                location TEXT NOT NULL,
                velocity_mins INTEGER NOT NULL,
                risk_score REAL NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('PENDING_HITL', 'APPROVED', 'REJECTED', 'COMPLETED')),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(account_id) REFERENCES accounts(id)
            )
        """)
        
        # 3. Agent Memory Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_memory (
                session_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                memory_key TEXT NOT NULL,
                memory_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (session_id, agent_id, memory_key)
            )
        """)
        
        conn.commit()
        
        # Seed default sandbox account if empty
        cursor.execute("SELECT COUNT(*) FROM accounts")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO accounts (id, currency, balance) VALUES (?, ?, ?)",
                ("account_123", "USD", 5000.0)
            )
            conn.commit()

def get_account(account_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, currency, balance FROM accounts WHERE id = ?", (account_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_transactions(account_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM transactions WHERE account_id = ? ORDER BY timestamp DESC LIMIT ?",
            (account_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]

def get_transaction(tx_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def log_transaction(
    tx_id: str,
    account_id: str,
    amount: float,
    merchant: str,
    category: str,
    location: str,
    velocity_mins: int,
    risk_score: float,
    status: str
) -> Dict[str, Any]:
    """Logs a transaction and atomically updates the account balance if completed/approved."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Insert transaction
        cursor.execute(
            """
            INSERT INTO transactions (id, account_id, amount, merchant, category, location, velocity_mins, risk_score, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tx_id, account_id, amount, merchant, category, location, velocity_mins, risk_score, status)
        )
        
        # Deduct balance if completed immediately
        if status == "COMPLETED":
            cursor.execute(
                "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                (amount, account_id)
            )
            
        conn.commit()
        
    return {
        "id": tx_id,
        "account_id": account_id,
        "amount": amount,
        "merchant": merchant,
        "category": category,
        "location": location,
        "velocity_mins": velocity_mins,
        "risk_score": risk_score,
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    }

def handle_hitl_approval(tx_id: str, approve: bool) -> Dict[str, Any]:
    """Approves or rejects a pending HITL transaction, adjusting balances if approved."""
    new_status = "APPROVED" if approve else "REJECTED"
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Retrieve original transaction
        cursor.execute("SELECT account_id, amount, status FROM transactions WHERE id = ?", (tx_id,))
        tx = cursor.fetchone()
        if not tx:
            raise ValueError(f"Transaction {tx_id} not found")
        
        account_id, amount, current_status = tx["account_id"], tx["amount"], tx["status"]
        
        if current_status != "PENDING_HITL":
            raise ValueError(f"Transaction {tx_id} is not in PENDING_HITL state (current: {current_status})")
            
        # Update transaction status
        cursor.execute(
            "UPDATE transactions SET status = ? WHERE id = ?",
            (new_status, tx_id)
        )
        
        # Deduct balance if approved
        if approve:
            cursor.execute(
                "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                (amount, account_id)
            )
            
        conn.commit()
        
    return {
        "id": tx_id,
        "status": new_status,
        "amount": amount,
        "account_id": account_id
    }

def save_agent_memory(session_id: str, agent_id: str, key: str, value: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO agent_memory (session_id, agent_id, memory_key, memory_value, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id, agent_id, memory_key) DO UPDATE SET
                memory_value = excluded.memory_value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (session_id, agent_id, key, value)
        )
        conn.commit()

def get_agent_memory(session_id: str, agent_id: str, key: str) -> Optional[str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT memory_value FROM agent_memory WHERE session_id = ? AND agent_id = ? AND memory_key = ?",
            (session_id, agent_id, key)
        )
        row = cursor.fetchone()
        return row[0] if row else None

def reset_db():
    """Resets the database by dropping tables and reinitializing them."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS accounts")
        cursor.execute("DROP TABLE IF EXISTS transactions")
        cursor.execute("DROP TABLE IF EXISTS agent_memory")
        conn.commit()
    init_db()
