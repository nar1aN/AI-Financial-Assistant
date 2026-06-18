from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from llm_service.categorizer import categorize_batch
from llm_service.recommendations import get_recommendations
from llm_service.news_pipeline import run_pipeline
from llm_service.ollama_client import is_available

app = FastAPI(
    title="ML Service",
    description="LLM-сервис для категоризации транзакций, рекомендаций и прогнозов цен",
    version="1.0.0",
)

class Transaction(BaseModel):
    description: str
    amount: float
    currency: str = "RUB"

class PredictRequest(BaseModel):
    transactions: list[Transaction]

class RecommendationRequest(BaseModel):
    transactions: list[dict]
    period: str = "month"

class ForecastRequest(BaseModel):
    categories: list[str] | None = None


@app.get("/health")
def health():
    ollama_ok = is_available()
    return{
        "status": "ok" if ollama_ok else "unavailable",
        "ollama": ollama_ok,
    }

@app.post("/predict")
def predict(body: PredictRequest):
    if not body.transactions:
        raise HTTPException(status_code=400, detail="Transactions list is empty")

    results = categorize_batch([tx.model_dump() for tx in body.transactions])

    return {
        "categories": [
            {"category": tx["category"], "confidence": tx["confidence"]}
            for tx in results
        ]
    }

@app.post("/recommendations")
def recommendations(body: RecommendationRequest):
    if not body.transactions:
        raise HTTPException(status_code=400, detail="Transactions list is empty")

    results = get_recommendations(body.transactions)
    return {"recommendations": results}

@app.post("/forecast")
def forecast(body: ForecastRequest):
    results = run_pipeline(categories=body.categories)
    return {"forecasts": results}

if __name__ == "__main__":
    import uvicorn
    # TODO: host, port, debug вынести в .env / config.py
    uvicorn.run("llm_service.server:app", host="0.0.0.0", port=5001, reload=True)