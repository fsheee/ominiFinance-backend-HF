from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os
from database import db
from agents.orchestrator import CentralOrchestrator
from config import settings
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="OmniFinance Digital Wallet Sandbox with AI routing, fraud checking, and financial literacy coaching.",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "OmniFinance API"
    }
# Enable CORS for local Next.js development server running on port 3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database schema on startup
@app.on_event("startup")
def startup_event():
    db.init_db()

# Pydantic Schemas
class ChatRequest(BaseModel):
    prompt: str = Field(..., description="The user query or transaction entry to process")
    session_id: str = Field("sandbox_session", description="Unique conversation session ID")

class HITLApprovalRequest(BaseModel):
    transaction_id: str = Field(..., description="The unique ID of the paused transaction")
    approve: bool = Field(..., description="Set to true to complete transaction and deduct funds, false to reject")

class ToolExecutionRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to execute")
    arguments: Dict[str, Any] = Field(..., description="Key-value arguments for the tool")

# Instantiate Orchestrator
orchestrator = CentralOrchestrator()

# Dashboard and static assets are served from frontend/out at the end of the middleware stack

@app.get("/api/telemetry")
def get_sandbox_telemetry():
    """Returns general sandbox telemetry, balance stats, and active transaction summaries."""
    account = db.get_account("account_123")
    transactions = db.get_transactions("account_123", limit=100)
    
    pending_hitl_count = sum(1 for tx in transactions if tx["status"] == "PENDING_HITL")
    completed_count = sum(1 for tx in transactions if tx["status"] in ["COMPLETED", "APPROVED"])
    
    return {
        "status": "online",
        "sandbox_account": {
            "id": account["id"] if account else None,
            "currency": account["currency"] if account else None,
            "balance": account["balance"] if account else 0.0
        },
        "telemetry": {
            "total_transactions_logged": len(transactions),
            "completed_transactions": completed_count,
            "pending_hitl_pauses": pending_hitl_count
        }
    }

@app.post("/chat")
def chat_orchestrator(request: ChatRequest):
    """
    Main orchestrator endpoint. Parses intent, delegates execution to sub-agents, 
    and handles tool integration, including fraud checking and HITL pause triggers.
    """
    try:
        result = orchestrator.route_and_execute(request.prompt, request.session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Orchestration failure: {str(e)}")

@app.get("/wallet")
def get_wallet():
    """Exposes current account balance and statistics."""
    account = db.get_account("account_123")
    if not account:
        raise HTTPException(status_code=404, detail="Sandbox account not found.")
    return account

@app.get("/transactions")
def get_transaction_history(limit: int = 50):
    """Exposes transaction logs in the sandbox ledger."""
    return db.get_transactions("account_123", limit=limit)

@app.post("/transactions/approve")
def approve_transaction(request: HITLApprovalRequest):
    """
    Resolves the Human-in-the-Loop (HITL) pause state.
    Changes status of pending transactions to APPROVED or REJECTED and adjusts balance.
    """
    try:
        result = db.handle_hitl_approval(request.transaction_id, request.approve)
        action_str = "approved" if request.approve else "rejected"
        return {
            "status": "SUCCESS",
            "message": f"Transaction {request.transaction_id} was successfully {action_str}.",
            "data": result
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System error resolving approval: {str(e)}")

@app.post("/tools/execute")
def execute_mcp_tool(request: ToolExecutionRequest):
    """
    Mock Model Context Protocol (MCP) execution bridge. Exposes the domain tools
    for external orchestrators or MCP clients.
    """
    tool = request.tool_name
    args = request.arguments
    
    if tool == "log_transaction":
        # Direct tool schema: (amount: float, merchant: str, category: str, timestamp: str)
        try:
            tracker = orchestrator.expense_tracker
            tx_id = args.get("id") or "mcp_tx_manual"
            # Call DB log
            res = db.log_transaction(
                tx_id=tx_id,
                account_id=args.get("account_id", "account_123"),
                amount=float(args["amount"]),
                merchant=str(args["merchant"]),
                category=str(args["category"]),
                location=args.get("location", "Home Location"),
                velocity_mins=int(args.get("velocity_mins", 60)),
                risk_score=float(args.get("risk_score", 0.0)),
                status=args.get("status", "COMPLETED")
            )
            return {"status": "SUCCESS", "result": res}
        except KeyError as ke:
            raise HTTPException(status_code=400, detail=f"Missing arguments: {str(ke)}")
            
    elif tool == "evaluate_fraud_risk":
        # Direct tool schema: (amount: float, location: str, velocity_mins: int)
        try:
            res = orchestrator.fraud_detector.evaluate_fraud_risk(
                amount=float(args["amount"]),
                location=str(args["location"]),
                velocity_mins=int(args["velocity_mins"])
            )
            return {"status": "SUCCESS", "result": res}
        except KeyError as ke:
            raise HTTPException(status_code=400, detail=f"Missing arguments: {str(ke)}")
            
    elif tool == "fetch_financial_knowledge_base":
        # Direct tool schema: (query: str)
        try:
            res = orchestrator.literacy_coach.fetch_financial_knowledge_base(
                query=str(args["query"])
            )
            return {"status": "SUCCESS", "result": res}
        except KeyError as ke:
            raise HTTPException(status_code=400, detail=f"Missing arguments: {str(ke)}")
            
    else:
        raise HTTPException(
            status_code=404, 
            detail=f"Tool '{tool}' not found. Available: log_transaction, evaluate_fraud_risk, fetch_financial_knowledge_base"
        )

@app.post("/reset")
def reset_sandbox():
    """Resets the digital wallet balance to $5000.00 and clears all transactions."""
    try:
        db.reset_db()
        return {"status": "SUCCESS", "message": "Sandbox database reset successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database reset failure: {str(e)}")

#