from typing import Dict, Any, List
import re
import os
import json
import httpx
from database.vector_store import seed_knowledge_base, search_knowledge

# Vetted financial knowledge base containing core concepts and analogies
KNOWLEDGE_BASE = {
    "compound interest": {
        "definition": "Earning interest on your interest over time.",
        "analogy": "compound interest (earning interest on your interest, like a snowball rolling downhill that gathers more snow and grows bigger the further it goes)",
        "explanation": "When we talk about compound interest, we are looking at the engine of wealth building. Instead of just earning interest on your initial savings once, you earn interest on top of the interest you already gained. Over time, this compounding effect acts like a force multiplier for your bank balance. For example, if you invest $1,000 at 5% annual interest, after year one you have $1,050. In year two, you earn 5% on $1,050, not just your original $1,000. This seemingly small difference becomes huge over decades."
    },
    "liquidity": {
        "definition": "How quickly you can turn an asset into cash without losing value.",
        "analogy": "liquidity (how quickly you can turn an asset into cash without losing value, like cash in your wallet vs. trying to sell a house to buy groceries)",
        "explanation": "Liquidity is all about accessibility. It tells us how easily you can convert what you own into cash. Cash in your bank account is highly liquid—you can use it immediately. A house is not liquid—it takes months to sell. Having high liquidity is essential for an emergency fund, so you can cover sudden expenses without friction or loss."
    },
    "diversification": {
        "definition": "Spreading investments across different assets to manage risk.",
        "analogy": "diversification (spreading your investments across different assets to manage risk—essentially, not putting all your eggs in one basket)",
        "explanation": "Diversification is a cornerstone of smart investing. By spreading your money across various categories (stocks, bonds, real estate, etc.), you ensure that a dip in one area doesn't wipe out your entire portfolio. It is your shield against volatility. If tech stocks fall 20%, but your real estate investments are stable, you don't lose everything."
    },
    "inflation": {
        "definition": "The general increase in prices and fall in the purchasing value of money.",
        "analogy": "inflation (the general increase in prices over time, meaning your money loses purchasing power—like a dollar buying a full slice of pizza today but only half a slice in the future)",
        "explanation": "Inflation is the background rate at which prices rise. It is the reason why holding all your savings in physical cash can actually lose you money in terms of purchasing power over the long haul. If inflation is 3% per year and your savings earn 1% interest, you're losing 2% in real value. We invest to outpace inflation and preserve wealth."
    },
    "budgeting": {
        "definition": "Creating a plan to spend and save your money.",
        "analogy": "budgeting (creating a roadmap for your money, so you know exactly where every dollar is going instead of wondering where it went)",
        "explanation": "Budgeting is the foundation of financial health. It isn't about restricting yourself, but rather about taking control of where your money goes. By tracking your spending, you make room for your long-term goals. A common approach is the 50/30/20 rule: 50% for needs, 30% for wants, and 20% for savings and debt repayment."
    },
    "yield": {
        "definition": "The earnings generated on an investment over a period of time, expressed as a percentage.",
        "analogy": "yield (the earnings generated on an investment over a period of time—like the harvest you get from planting a seed)",
        "explanation": "Yield is the return you get on your investment. If you buy a bond that pays 4% annually, that 4% is your yield. If you own a dividend stock that pays $2 per share and the stock costs $50, your yield is 4%. Understanding yield helps you compare different investments and decide which gives you the best return for your risk."
    },
    "asset allocation": {
        "definition": "Balancing your investment portfolio between categories like stocks and bonds.",
        "analogy": "asset allocation (balancing your investment portfolio between different categories based on your risk tolerance—like deciding how much of your plate is vegetables versus protein)",
        "explanation": "Asset allocation is how you divide your investments among different categories. A young investor might do 80% stocks, 20% bonds for growth. Someone nearing retirement might do 40% stocks, 60% bonds for stability. Your allocation should match your risk tolerance, time horizon, and financial goals."
    },
    "emergency fund": {
        "definition": "Money saved for unexpected expenses or loss of income.",
        "analogy": "emergency fund (a financial airbag that deploys when life throws you a curveball—like car repairs or job loss)",
        "explanation": "An emergency fund is typically 3-6 months of living expenses kept in a liquid, accessible account. It protects you from going into debt when unexpected expenses arise. Without it, a car breakdown or medical emergency can force you to use high-interest credit cards. Start small if needed—even $500-$1000 can prevent a financial crisis."
    },
    "debt": {
        "definition": "Money you owe to a lender that must be repaid with interest.",
        "analogy": "debt (like a weight dragging you down, but sometimes necessary—the key is not carrying more than you can handle)",
        "explanation": "Not all debt is bad. Low-interest debt like mortgages or student loans can be investments in your future. High-interest debt like credit cards is dangerous—a $5,000 credit card balance at 20% interest costs you $1,000/year just in interest. Focus on paying off high-interest debt first, then use low-interest debt strategically."
    },
    "risk tolerance": {
        "definition": "Your ability and willingness to handle fluctuations in investment value.",
        "analogy": "risk tolerance (how well you can sleep at night when your investments go down—some people panic, others see opportunity)",
        "explanation": "Risk tolerance depends on your age, income stability, and time horizon. A 25-year-old can afford to take more risk because they have decades to recover from losses. A 65-year-old needs stability. Higher risk often means higher potential returns, but also bigger possible losses. Understand yourself before investing."
    },
    "passive income": {
        "definition": "Money earned with minimal ongoing effort, like dividends or rental income.",
        "analogy": "passive income (planting a money tree that keeps producing fruit without you having to climb the tree each day)",
        "explanation": "Passive income is money you earn without actively working for it each hour. Examples include dividend payments from stocks, interest from savings, rental income from property, or royalties from creative work. Building passive income streams reduces your dependence on a single job and creates financial flexibility."
    },
    "compound growth": {
        "definition": "The exponential growth that occurs when returns are reinvested.",
        "analogy": "compound growth (like bacteria doubling every hour—slow at first, but eventually explosive)",
        "explanation": "Compound growth is the magic of reinvesting your earnings. If you invest $100 and earn 10% ($10), then next year you earn 10% on $110, not just $100. After 10 years at 10% annual returns, $100 becomes $260. After 30 years, it becomes $1,744. Time and consistency are your greatest tools."
    }
}

class FinancialLiteracyCoach:
    def __init__(self, name: str = "Financial Literacy Coach"):
        self.name = name
        seed_knowledge_base(KNOWLEDGE_BASE)
        self.instruction = (
            "You are an empathetic financial coach explaining budgeting, wealth building, "
            "and interest. You fetch references from the knowledge base and insert "
            "clear analogies for financial terms."
        )

    def fetch_financial_knowledge_base(self, query: str) -> List[Dict[str, str]]:
        """
        Queries the vetted financial knowledge base using semantic vector search.
        Returns matching concepts with definitions, analogies, explanations, and relevance scores.
        """
        results = search_knowledge(query, n_results=5)
        return results

    def _replace_jargon_inline(self, text: str) -> str:
        """Helper to inject inline analogical definitions for found jargon words."""
        for term, data in KNOWLEDGE_BASE.items():
            # Match term case-insensitively, avoiding terms already containing parentheses/analogies
            pattern = re.compile(rf"\b{re.escape(term)}\b(?!\s*\()", re.IGNORECASE)
            text = pattern.sub(data["analogy"], text, count=1)
        return text

    def execute(self, query: str) -> Dict[str, Any]:
        """Runs the coaching session, generating empathetic text containing analogies."""
        kb_matches = self.fetch_financial_knowledge_base(query)
        
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                explanation = self._generate_with_gemini(query, kb_matches, api_key)
            except Exception:
                explanation = self._generate_rule_based(query, kb_matches)
        else:
            explanation = self._generate_rule_based(query, kb_matches)

        # Ensure all jargon has inline definitions
        final_text = self._replace_jargon_inline(explanation)
        
        return {
            "agent": self.name,
            "response": final_text,
            "knowledge_base_references": kb_matches
        }

    def _generate_with_gemini(self, query: str, references: List[Dict[str, str]], api_key: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        ref_text = "\n".join([
            f"- {ref['term'].upper()}: {ref['definition']}\n  {ref.get('explanation', ref['analogy'])}" 
            for ref in references
        ])
        prompt = (
            "You are an empathetic, accessible financial literacy coach. "
            f"A user is asking: \"{query}\"\n\n"
            "Use the following vetted knowledge base references if applicable:\n"
            f"{ref_text}\n\n"
            "Explain the concepts in simple, accessible, friendly language. Use clear analogies. "
            "Provide actionable takeaways where relevant. Write a concise response (2-3 paragraphs)."
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        response = httpx.post(url, headers=headers, json=payload, timeout=10.0)
        response.raise_for_status()
        result_json = response.json()
        return result_json["candidates"][0]["content"]["parts"][0]["text"].strip()

    def _generate_rule_based(self, query: str, references: List[Dict[str, str]]) -> str:
        # Fallback generator for standard questions
        query_lower = query.lower()
        
        if not references:
            return (
                "That is a great question! Budgeting and understanding wealth building can "
                "feel overwhelming, but it is all about taking small, consistent steps. "
                "Could you tell me more about what specific concept you're looking to explore, "
                "such as compound interest, diversification, risk tolerance, emergency funds, or passive income?"
            )
            
        intro = "Hello! Let's break this down together. It is actually much simpler than it sounds.\n\n"
        details = []
        for ref in references:
            term = ref["term"]
            explanation = ref.get("explanation", ref["definition"])
            details.append(explanation)

        conclusion = "\n\nRemember, building financial confidence is a journey. Let me know if you want to dive deeper into any of these concepts!"
        return intro + "\n\n".join(details) + conclusion
