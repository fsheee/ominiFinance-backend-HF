from typing import Dict, Any, List

SKILLS_REGISTRY: List[Dict[str, Any]] = [
    {
        "agent": "Expense Tracker",
        "class": "ExpenseTrackerAgent",
        "description": "Extracts structured transaction details from natural language text.",
        "methods": [
            {
                "name": "log_transaction_tool",
                "signature": "log_transaction_tool(amount: float, merchant: str, category: str, timestamp: str, location: str = 'Home Location', account_id: str = 'account_123') -> Dict[str, Any]",
                "description": "Builds a formatted transaction payload for logging.",
                "parameters": {
                    "amount": "float",
                    "merchant": "str",
                    "category": "str",
                    "timestamp": "str",
                    "location": "str (default: 'Home Location')",
                    "account_id": "str (default: 'account_123')"
                },
                "returns": "Dict[str, Any] — action + payload with transaction id, account_id, amount, merchant, category, location, timestamp"
            },
            {
                "name": "parse_query",
                "signature": "parse_query(query: str) -> Dict[str, Any]",
                "description": "Parses unstructured transaction text using Gemini API or rule-based fallback.",
                "parameters": {"query": "str"},
                "returns": "Dict[str, Any] — {amount, merchant, category, location, timestamp}"
            },
            {
                "name": "execute",
                "signature": "execute(query: str) -> Dict[str, Any]",
                "description": "Main entry point. Parses query and returns the tool_call payload.",
                "parameters": {"query": "str"},
                "returns": "Dict[str, Any] — {agent, parsed_details, tool_call}"
            }
        ]
    },
    {
        "agent": "Fraud Detection Agent",
        "class": "FraudDetectionAgent",
        "description": "Evaluates behavioral risk metrics for transactions and triggers HITL when risk exceeds 75%.",
        "methods": [
            {
                "name": "evaluate_fraud_risk",
                "signature": "evaluate_fraud_risk(amount: float, location: str, velocity_mins: int) -> Dict[str, Any]",
                "description": "Calculates composite risk score from amount risk, velocity risk, and location risk.",
                "parameters": {
                    "amount": "float",
                    "location": "str",
                    "velocity_mins": "int"
                },
                "returns": "Dict[str, Any] — {risk_score, is_high_risk, metrics: {amount_risk, velocity_risk, location_risk}, decision: 'PAUSE_FOR_HITL' | 'ALLOW'}"
            },
            {
                "name": "execute",
                "signature": "execute(transaction_payload: Dict[str, Any]) -> Dict[str, Any]",
                "description": "Evaluates a transaction payload for fraud risk before ledger entry.",
                "parameters": {"transaction_payload": "Dict[str, Any]"},
                "returns": "Dict[str, Any] — {agent, evaluation, transaction_id}"
            }
        ]
    },
    {
        "agent": "Financial Literacy Coach",
        "class": "FinancialLiteracyCoach",
        "description": "Provides empathetic financial education using RAG-based knowledge retrieval and inline analogies.",
        "methods": [
            {
                "name": "fetch_financial_knowledge_base",
                "signature": "fetch_financial_knowledge_base(query: str) -> List[Dict[str, str]]",
                "description": "Queries ChromaDB vector store via semantic search for matching financial concepts.",
                "parameters": {"query": "str"},
                "returns": "List[Dict[str, str]] — [{term, definition, analogy, explanation, score}]"
            },
            {
                "name": "execute",
                "signature": "execute(query: str) -> Dict[str, Any]",
                "description": "Main entry point. Retrieves knowledge, generates explanation (Gemini or rule-based), injects analogies.",
                "parameters": {"query": "str"},
                "returns": "Dict[str, Any] — {agent, response, knowledge_base_references}"
            }
        ]
    }
]
