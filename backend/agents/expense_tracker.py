import re
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
import os
import json
import httpx

class ExpenseTrackerAgent:
    def __init__(self, name: str = "Autonomous Expense Tracker"):
        self.name = name
        self.instruction = (
            "You are an expense tracker agent. Your job is to extract transaction details "
            "from raw user text: amount, merchant, category, and timestamp. Then, call the "
            "log_transaction tool."
        )

    def log_transaction_tool(
        self,
        amount: float,
        merchant: str,
        category: str,
        timestamp: str,
        location: str = "Home Location",
        account_id: str = "account_123"
    ) -> Dict[str, Any]:
        """Tool definition for logging a transaction."""
        # Note: In our multi-agent workflow, we route through the fraud detector
        # BEFORE inserting a completed transaction to the database.
        # This function returns the formatted payload ready for execution.
        return {
            "action": "log_transaction",
            "payload": {
                "id": str(uuid.uuid4()),
                "account_id": account_id,
                "amount": amount,
                "merchant": merchant,
                "category": category,
                "location": location,
                "timestamp": timestamp or datetime.utcnow().isoformat()
            }
        }

    def parse_query(self, query: str) -> Dict[str, Any]:
        """
        Parses unstructured queries. Uses Gemini API if GEMINI_API_KEY is in env,
        otherwise falls back to a robust rule-based parsing engine.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                return self._parse_with_gemini(query, api_key)
            except Exception as e:
                # Fallback to rule-based parser on any LLM API error
                pass
        return self._parse_rule_based(query)

    def _parse_with_gemini(self, query: str, api_key: str) -> Dict[str, Any]:
        # Simple REST call to Gemini 1.5 Flash
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        prompt = (
            "You are a structured parser. Parse this financial transaction text:\n"
            f"\"{query}\"\n\n"
            "Extract amount (float), merchant (string), category (string), location (string), and timestamp (ISO-8601 string or null if not specified). "
            "Location is where the transaction took place (e.g., 'New York', 'Online', 'North Korea'). Use null if not mentioned. "
            "Return ONLY a raw JSON block matching this schema:\n"
            "{\n"
            "  \"amount\": float,\n"
            "  \"merchant\": \"string\",\n"
            "  \"category\": \"string\",\n"
            "  \"location\": \"string or null\",\n"
            "  \"timestamp\": \"string or null\"\n"
            "}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        
        response = httpx.post(url, headers=headers, json=payload, timeout=10.0)
        response.raise_for_status()
        result_json = response.json()
        text_content = result_json["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text_content.strip())

    def _parse_rule_based(self, query: str) -> Dict[str, Any]:
        # 1. Extract Amount
        amount = 0.0
        amount_match = re.search(r"\$(\d+(?:\.\d{2})?)", query)
        if amount_match:
            amount = float(amount_match.group(1))
        else:
            # Fallback to numbers without dollar sign if accompanied by context
            numbers = re.findall(r"\b\d+(?:\.\d{2})?\b", query)
            if numbers:
                amount = float(numbers[0])

        # 2. Extract Merchant
        merchant = "Unknown Merchant"
        
        # Try to find "at [Merchant]", "from [Merchant]", "to [Merchant]" (strong indicators)
        merchant_match = re.search(
            r"\b(?:at|from|to)\s+([A-Za-z0-9\s'&]+?)(?:\s+(?:last|yesterday|for|with|in|today|\$)\b|$)",
            query,
            re.IGNORECASE
        )
        if merchant_match:
            merchant = merchant_match.group(1).strip()
        else:
            # Check for "on [Item]"
            on_match = re.search(
                r"\bon\s+([A-Za-z0-9\s'&]+?)(?:\s+(?:last|yesterday|for|with|in|today|\$)\b|$)",
                query,
                re.IGNORECASE
            )
            if on_match:
                item_candidate = on_match.group(1).strip().lower()
                # If the item candidate is a known item type, we use a generic merchant
                if any(kw in item_candidate for kw in ["pizza", "burger", "dinner", "lunch", "food", "coffee"]):
                    merchant = "Domino's" if "pizza" in item_candidate else "Restaurant"
                elif any(kw in item_candidate for kw in ["diamond", "ring", "watch", "jewelry"]):
                    merchant = "Rolex" if "watch" in item_candidate else "Jeweler"
                elif any(kw in item_candidate for kw in ["groceries", "milk", "eggs"]):
                    merchant = "Grocery Store"
                else:
                    merchant = on_match.group(1).strip()
            else:
                # Guess merchant from words after spent/bought/paid
                words = query.split()
                if len(words) > 1:
                    for i, w in enumerate(words):
                        if w.lower() in ["spent", "bought", "paid"] and i + 1 < len(words):
                            next_w = words[i + 1]
                            if not next_w.startswith("$") and not next_w.isdigit():
                                merchant = next_w.strip(",.?! ")
                                break

        # 3. Categorize
        category = "General"
        query_lower = query.lower()
        
        food_keywords = ["pizza", "burger", "food", "dinner", "lunch", "starbucks", "coffee", "restaurant", "cafe", "dine"]
        transport_keywords = ["uber", "lyft", "taxi", "bus", "train", "flight", "gas", "fuel", "commute"]
        ent_keywords = ["movie", "netflix", "concert", "game", "ticket", "friends", "club", "bar", "drinks"]
        shopping_keywords = ["amazon", "target", "walmart", "shoes", "clothes", "store", "buy", "groceries"]
        utility_keywords = ["rent", "bill", "electricity", "water", "internet", "phone", "insurance"]

        if any(kw in query_lower for kw in food_keywords):
            category = "Food & Dining"
        elif any(kw in query_lower for kw in transport_keywords):
            category = "Transportation"
        elif any(kw in query_lower for kw in ent_keywords):
            category = "Entertainment"
        elif any(kw in query_lower for kw in shopping_keywords):
            category = "Shopping"
        elif any(kw in query_lower for kw in utility_keywords):
            category = "Utilities"

        # 4. Extract Location
        location = "Home Location"
        if "online" in query_lower or "website" in query_lower or "internet" in query_lower:
            location = "Unknown Online"
        elif "suspicious" in query_lower or "unusual" in query_lower:
            location = "Suspicious Location"
        elif "north korea" in query_lower:
            location = "North Korea"
        elif "unknown" in query_lower:
            location = "Unknown Location"
        else:
            in_match = re.search(r'\bin\s+([A-Za-z\s]+?)(?:\s+(?:last|yesterday|today|for|with|\$)\b|$)', query, re.IGNORECASE)
            if in_match:
                location = in_match.group(1).strip().title()

        # 5. Parse Timestamp
        timestamp = datetime.utcnow()
        if "yesterday" in query_lower:
            timestamp -= timedelta(days=1)
        elif "last night" in query_lower:
            timestamp -= timedelta(days=1)
            # Adjust to evening time
            timestamp = timestamp.replace(hour=20, minute=0, second=0, microsecond=0)
        elif "last week" in query_lower:
            timestamp -= timedelta(days=7)

        return {
            "amount": amount,
            "merchant": merchant,
            "category": category,
            "location": location,
            "timestamp": timestamp.isoformat()
        }

    def execute(self, query: str) -> Dict[str, Any]:
        """Main execution method for the Agent."""
        parsed_data = self.parse_query(query)
        tool_call = self.log_transaction_tool(
            amount=parsed_data.get("amount", 0.0),
            merchant=parsed_data.get("merchant", "Unknown Merchant"),
            category=parsed_data.get("category", "General"),
            location=parsed_data.get("location", "Home Location"),
            timestamp=parsed_data.get("timestamp")
        )
        return {
            "agent": self.name,
            "parsed_details": parsed_data,
            "tool_call": tool_call
        }
