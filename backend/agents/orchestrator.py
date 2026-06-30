from typing import Dict, Any, Optional
import os
import json
import httpx
from database import db
from agents.expense_tracker import ExpenseTrackerAgent
from agents.fraud_detector import FraudDetectionAgent
from agents.literacy_coach import FinancialLiteracyCoach

class CentralOrchestrator:
    def __init__(self):
        self.expense_tracker = ExpenseTrackerAgent()
        self.fraud_detector = FraudDetectionAgent()
        self.literacy_coach = FinancialLiteracyCoach()
        
    def classify_intent(self, user_prompt: str) -> str:
        """
        Classifies user prompt intent to delegate to specialized sub-agents.
        Uses Gemini if key exists, otherwise falls back to keyword matching.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                return self._classify_with_gemini(user_prompt, api_key)
            except Exception:
                pass
        return self._classify_rule_based(user_prompt)

    def _classify_with_gemini(self, prompt: str, api_key: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        system_instruction = (
            "You are a routing classification system. Your job is to classify the user's intent "
            "into one of the following exact strings: 'EXPENSE', 'FRAUD', 'LITERACY', or 'WALLET'.\n\n"
            "- Choose 'EXPENSE' if the user is logging a purchase, expense, or telling you they spent money "
            "(e.g., 'spent $45 on lunch', 'log $20 Starbucks').\n"
            "- Choose 'FRAUD' if they are asking about fraud evaluation, suspicious charges, or risk scoring.\n"
            "- Choose 'LITERACY' if they are asking about financial coaching, definitions (liquidity, compound interest), "
            "wealth building, budgeting guides, etc.\n"
            "- Choose 'WALLET' if they are asking about their wallet, balance, or list of past transactions.\n\n"
            "Respond with ONLY one word: EXPENSE, FRAUD, LITERACY, or WALLET."
        )
        payload = {
            "contents": [{"parts": [{"text": f"{system_instruction}\n\nUser prompt: \"{prompt}\""}]}]
        }
        
        response = httpx.post(url, headers=headers, json=payload, timeout=10.0)
        response.raise_for_status()
        result_json = response.json()
        classification = result_json["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
        
        if classification in ["EXPENSE", "FRAUD", "LITERACY", "WALLET"]:
            return classification
        return self._classify_rule_based(prompt)

    def _classify_rule_based(self, prompt: str) -> str:
        p_lower = prompt.lower()
        
        # 1. Wallet balance and history query detection
        wallet_words = ["balance", "wallet", "transactions", "ledger", "statement", "history", "how much money"]
        if any(w in p_lower for w in wallet_words):
            return "WALLET"
            
        # 2. Expense tracking detection
        expense_words = ["spent", "spent$", "buy", "bought", "purchase", "log transaction", "pay", "paid", "$", "cost"]
        if any(w in p_lower for w in expense_words) or any(char == '$' for char in p_lower):
            return "EXPENSE"
            
        # 3. Financial coaching & education detection
        literacy_words = [
            "compound interest", "liquidity", "diversification", "inflation", 
            "budget", "yield", "allocation", "explain", "coach", "interest", "wealth",
            "emergency fund", "passive income", "risk tolerance", "asset allocation",
            "debt", "compound growth", "financial", "invest", "saving", "portfolio",
            "dividend", "bond", "stock", "retire"
        ]
        if any(w in p_lower for w in literacy_words):
            return "LITERACY"
            
        # 4. Fraud analysis detection
        fraud_words = ["fraud", "suspicious", "risk", "anomaly", "check transaction", "flagged"]
        if any(w in p_lower for w in fraud_words):
            return "FRAUD"
            
        # Default fallback
        return "LITERACY"

    def route_and_execute(self, user_prompt: str, session_id: str = "sandbox_session") -> Dict[str, Any]:
        """
        The ADK multi-agent routing loop. Resolves dependencies and delegates tasks.
        """
        intent = self.classify_intent(user_prompt)
        
        # Persist orchestrator state to agent memory
        db.save_agent_memory(session_id, "central_orchestrator", "last_intent", intent)
        
        if intent == "EXPENSE":
            # Delegate to Agent B (Expense Tracker)
            tracker_result = self.expense_tracker.execute(user_prompt)
            tool_call = tracker_result["tool_call"]
            payload = tool_call["payload"]
            
            # Sub-agent Routing: Route transaction details through Agent C (Fraud Detector)
            # Before executing the database insertion, compute risk.
            # Location already extracted by expense_tracker. Use it with fallback.
            location = payload.get("location", "Home Location")
            velocity_mins = 1  # Mock short velocity if user submits consecutive logs

            fraud_result = self.fraud_detector.execute({
                "id": payload["id"],
                "amount": payload["amount"],
                "location": location,
                "velocity_mins": velocity_mins
            })
            
            fraud_decision = fraud_result["evaluation"]["decision"]
            risk_score = fraud_result["evaluation"]["risk_score"]
            
            status = "COMPLETED"
            if fraud_decision == "PAUSE_FOR_HITL":
                status = "PENDING_HITL"
                
            # Execute database tool log_transaction
            logged_tx = db.log_transaction(
                tx_id=payload["id"],
                account_id=payload["account_id"],
                amount=payload["amount"],
                merchant=payload["merchant"],
                category=payload["category"],
                location=location,
                velocity_mins=velocity_mins,
                risk_score=risk_score,
                status=status
            )
            
            return {
                "intent": "EXPENSE",
                "status": "PAUSED_WAITING_FOR_HITL" if status == "PENDING_HITL" else "SUCCESS",
                "data": {
                    "transaction": logged_tx,
                    "fraud_evaluation": fraud_result["evaluation"]
                },
                "message": (
                    f"Transaction of ${payload['amount']} at {payload['merchant']} is PAUSED for human approval due to "
                    f"high fraud risk ({risk_score}%)." if status == "PENDING_HITL" else 
                    f"Successfully logged expense: ${payload['amount']} at {payload['merchant']} (Category: {payload['category']})."
                )
            }
            
        elif intent == "FRAUD":
            # Extract basic params for verification
            # Mock risk calculation query
            import re
            amounts = re.findall(r"\d+", user_prompt)
            amount = float(amounts[0]) if amounts else 100.0
            
            location = "Suspicious Location" if "suspicious" in user_prompt.lower() else "Home Location"
            velocity = 1 if "fast" in user_prompt.lower() or "quick" in user_prompt.lower() else 30
            
            evaluation = self.fraud_detector.evaluate_fraud_risk(amount, location, velocity)
            return {
                "intent": "FRAUD",
                "status": "SUCCESS",
                "data": {
                    "evaluation": evaluation,
                    "input_parameters": {
                        "amount": amount,
                        "location": location,
                        "velocity_mins": velocity
                    }
                },
                "message": f"Fraud risk evaluation completed. Risk Score: {evaluation['risk_score']}%. Decision: {evaluation['decision']}."
            }
            
        elif intent == "LITERACY":
            # Delegate to Agent D (Financial Literacy Coach)
            coach_result = self.literacy_coach.execute(user_prompt)
            return {
                "intent": "LITERACY",
                "status": "SUCCESS",
                "data": {
                    "response": coach_result["response"],
                    "references": coach_result["knowledge_base_references"]
                },
                "message": coach_result["response"]
            }
            
        elif intent == "WALLET":
            # Process directly via wallet tools
            account = db.get_account("account_123")
            txs = db.get_transactions("account_123", limit=5)
            
            balance_str = f"${account['balance']:.2f} {account['currency']}" if account else "$0.00 USD"
            tx_lines = []
            for tx in txs:
                tx_lines.append(f"- [{tx['timestamp']}] {tx['merchant']}: -${tx['amount']} ({tx['status']})")
                
            history_str = "\n".join(tx_lines) if tx_lines else "No transaction history found."
            
            return {
                "intent": "WALLET",
                "status": "SUCCESS",
                "data": {
                    "account": account,
                    "recent_transactions": txs
                },
                "message": f"Your current balance is {balance_str}.\n\nRecent Transactions:\n{history_str}"
            }
            
        return {
            "intent": "UNKNOWN",
            "status": "ERROR",
            "message": "Sorry, I could not classify your query. Please ask me about balance, expenses, or financial literacy."
        }
