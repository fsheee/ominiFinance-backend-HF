from typing import Dict, Any

class FraudDetectionAgent:
    HIGH_RISK_COUNTRIES = {
        "north korea", "iran", "syria", "cuba", "russia", "myanmar", "sudan", "venezuela"
    }
    
    def __init__(self, name: str = "AI Fraud Detection Agent"):
        self.name = name
        self.instruction = (
            "You are an AI Fraud Detection Agent. You evaluate behavioral risk metrics for "
            "incoming transactions. If the risk score exceeds 75%, trigger a human-in-the-loop "
            "approval hook."
        )

    def evaluate_fraud_risk(self, amount: float, location: str, velocity_mins: int) -> Dict[str, Any]:
        """
        Calculates a composite risk score based on transaction size, location patterns, and velocity.
        """
        risk_components = {}
        
        # 1. Amount Risk (larger amounts are riskier)
        if amount >= 5000.0:
            amount_risk = 0.9
        elif amount >= 1000.0:
            amount_risk = 0.5
        elif amount >= 500.0:
            amount_risk = 0.3
        else:
            amount_risk = 0.05
        risk_components["amount_risk"] = amount_risk

        # 2. Velocity Risk (very short intervals between transactions)
        if velocity_mins <= 2:
            velocity_risk = 0.8
        elif velocity_mins <= 10:
            velocity_risk = 0.5
        elif velocity_mins <= 30:
            velocity_risk = 0.2
        else:
            velocity_risk = 0.0
        risk_components["velocity_risk"] = velocity_risk

        # 3. Location Risk (suspicious, international, or unknown locations)
        loc_lower = location.lower()
        if any(country in loc_lower for country in self.HIGH_RISK_COUNTRIES):
            location_risk = 0.9
        elif "suspicious" in loc_lower or "unknown" in loc_lower or "unusual" in loc_lower:
            location_risk = 0.7
        elif "foreign" in loc_lower or "international" in loc_lower:
            location_risk = 0.5
        else:
            location_risk = 0.0
        risk_components["location_risk"] = location_risk

        # Composite risk calculation: Weighted average or combined probability
        # Let's use a weighted formula to calculate the composite score.
        # Max out individual factors if they are extreme (e.g. extremely high velocity + high amount)
        composite_score = min(1.0, amount_risk * 0.4 + velocity_risk * 0.35 + location_risk * 0.35)
        
        # Ensure we cap and represent it as percentage
        risk_pct = round(composite_score * 100, 2)
        
        is_fraudulent = risk_pct > 75.0
        
        return {
            "risk_score": risk_pct,
            "is_high_risk": is_fraudulent,
            "metrics": risk_components,
            "decision": "PAUSE_FOR_HITL" if is_fraudulent else "ALLOW"
        }

    def execute(self, transaction_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates a potential transaction for fraud risk before ledger entry."""
        amount = transaction_payload.get("amount", 0.0)
        location = transaction_payload.get("location", "Home Location")
        velocity_mins = transaction_payload.get("velocity_mins", 60)  # Default 60 mins
        
        evaluation = self.evaluate_fraud_risk(amount, location, velocity_mins)
        
        return {
            "agent": self.name,
            "evaluation": evaluation,
            "transaction_id": transaction_payload.get("id")
        }
