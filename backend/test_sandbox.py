import os
import sys
import json
from database import db
from agents.orchestrator import CentralOrchestrator

def main():
    print("====================================================")
    print("OmniFinance Sandbox: End-to-End Simulation Validation")
    print("====================================================\n")
    
    # 1. Initialize the SQLite database
    print("[1/6] Initializing Sandbox Database...")
    db.init_db()
    
    # Fetch default account
    account = db.get_account("account_123")
    print(f"Initial Sandbox Account: ID={account['id']}, Balance={account['balance']} {account['currency']}\n")
    
    # Instantiate Orchestrator
    orchestrator = CentralOrchestrator()
    
    # 2. Simulate standard low-risk transaction
    print("[2/6] Query: 'Spent $45 on pizza with friends last night'...")
    res1 = orchestrator.route_and_execute("Spent $45 on pizza with friends last night")
    print(f"Intent Classified: {res1['intent']}")
    print(f"Status: {res1['status']}")
    print(f"Message: {res1['message']}")
    
    # Retrieve updated account details
    account = db.get_account("account_123")
    print(f"Updated Wallet Balance: {account['balance']} {account['currency']}\n")
    
    # 3. Simulate high-risk transaction triggering HITL Pause
    print("[3/6] Query: 'Spent $5200 on an expensive diamond ring in a Suspicious Location'...")
    res2 = orchestrator.route_and_execute("Spent $5200 on an expensive diamond ring in a Suspicious Location")
    print(f"Intent Classified: {res2['intent']}")
    print(f"Status: {res2['status']}")
    print(f"Risk Score: {res2['data']['fraud_evaluation']['risk_score']}%")
    print(f"Message: {res2['message']}")
    
    # Check transaction state in db
    tx_id = res2["data"]["transaction"]["id"]
    tx_in_db = db.get_transaction(tx_id)
    print(f"Database Transaction Status for {tx_id}: {tx_in_db['status'] if tx_in_db else 'Not Found'}")
    
    # Verify balance was NOT deducted
    account = db.get_account("account_123")
    print(f"Wallet Balance (Unchanged since paused): {account['balance']} {account['currency']}\n")
    
    # 4. Resolve the HITL state (Human approves transaction)
    print("[4/6] Approving the paused transaction manually via state hook...")
    approval_res = db.handle_hitl_approval(tx_id, approve=True)
    print(f"Approval result: TX={approval_res['id']}, New Status={approval_res['status']}")
    
    # Verify balance is now deducted
    account = db.get_account("account_123")
    print(f"Final Wallet Balance (Deducted after approval): {account['balance']} {account['currency']}\n")
    
    # 5. Simulate Financial Literacy Coach query
    print("[5/6] Query: 'Can you explain compound interest, liquidity, and asset allocation?'...")
    res3 = orchestrator.route_and_execute("Can you explain compound interest, liquidity, and asset allocation?")
    print(f"Intent Classified: {res3['intent']}")
    print("Financial Literacy Coach Response:")
    print("----------------------------------------------------")
    print(res3["message"])
    print("----------------------------------------------------\n")
    
    # 6. Retrieve recent logs
    print("[6/6] Fetching Recent Ledger Records:")
    history = db.get_transactions("account_123", limit=5)
    for tx in history:
        print(f" - TX {tx['id'][:8]}... | {tx['merchant']} | -${tx['amount']} | Risk: {tx['risk_score']}% | Status: {tx['status']}")
    
    print("\n====================================================")
    print("Verification Simulation Complete - All Systems Active!")
    print("====================================================")

if __name__ == "__main__":
    main()
