from decimal import Decimal
from llm_service.ollama_client import ask_ollama

categories = [
    "Groceries",
    "Transport",
    "Entertainment",
    "Utilities",
    "Cares and Restaurants",
    "Clothing",
    "Health",
    "Subscriptions",
    "Other"
]
prompt_template = """
You are a bank transaction categorization system.
Classify the transaction into one of the categories below.
Respond ONLY with valid JSON, no explanations.

Categories: {categories}

Transaction:
- Description: {description}
- Amount: {amount} {currency}

Respond strictly in this format:
{{"category": "<one of the categories>", "confidence": <float between 0.0 and 1.0>}}
"""

def categorize(transaction: dict) -> dict:
    """
        Takes a transaction dict, returns category and model confidence.

        Input format:
            {
                "description": str,
                "amount": Decimal | float,
                "currency": str,  # e.g. "USD" or "RUB"
            }

        Returns:
            {"category": str, "confidence": float}
        """
    prompt = prompt_template.format(
        categories=", ".join(categories),
        description=transaction.get("description", ""),
        amount=transaction.get("amount", ""),
        currency=transaction.get("currency", "RUB"),
    )

    result = ask_ollama(prompt)

    if "error" in result:
        return {"category": "Other", "cofidence": 0.0}

    category = result.get("category", "Other")
    confidence = float(result.get("confidence", 0.0))

    if category not in categories:
        category = "Other"
        confidence = 0.0
    return {"category": category, "confidence": confidence}

def categorize_batch(transactions: list[dict]) ->list[dict]:
    results = []
    for tx in transactions:
        cat = categorize(tx)
        results.append({
            **tx,
            "category": cat["category"],
            "confidence": cat["confidence"],
        })
    return results