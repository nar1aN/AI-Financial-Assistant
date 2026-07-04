import httpx
from core.config import settings

ml_service_url = settings.ml_service_url

async def check_health() -> bool:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(ml_service_url, timeout=5)
            return response.status_code == 200
        except httpx.RequestError:
            return False

async def categorize_transactions(transactions: list[dict]) -> list[dict]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{ML_SERVICE_URL}/predict",
                json={"transactions": transactions},
                timeout=60,  # Qwen может думать долго на большом батче
            )
            response.raise_for_status()
            return response.json()["categories"]

        except httpx.RequestError as e:
            # TODO: заменить на logging
            print(f"[ml_client] ML-сервис недоступен: {e}")
            # Возвращаем Other для всех транзакций чтобы не ронять пайплайн
            return [{"category": "Other", "confidence": 0.0}] * len(transactions)

        except httpx.HTTPStatusError as e:
            print(f"[ml_client] Ошибка от ML-сервиса: {e.response.status_code}")
            return [{"category": "Other", "confidence": 0.0}] * len(transactions)

async def get_recommendations(transactions: list[dict]) -> list[dict]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{ML_SERVICE_URL}/recommendations",
                json={"transactions": transactions},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()["recommendations"]

        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            print(f"[ml_client] Ошибка получения рекомендаций: {e}")
            return []


async def get_forecast(categories: list[str] | None = None) -> list[dict]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{ML_SERVICE_URL}/forecast",
                json={"categories": categories},
                timeout=120,
            )
            response.raise_for_status()
            return response.json()["forecasts"]

        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            print(f"[ml_client] Ошибка получения прогноза: {e}")
            return []