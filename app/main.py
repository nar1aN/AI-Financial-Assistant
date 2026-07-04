from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from core.ml_client import check_health
from api.v1.endpoints.router import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    ml_ok = await check_health()
    if not ml_ok:
        # TODO: заменить на logging
        print("[main] WARNING: ML-сервис недоступен, категоризация не будет работать")
    else:
        print("[main] ML-сервис доступен, всё готово к работе")

    yield  # сервер работает

    # TODO: добавить сюда закрытие соединений с БД и Redis при остановке
    print("[main] Сервер остановлен")


app = FastAPI(
    title="AI Financial Assistant",
    description="Анализ банковских выписок и оптимизация расходов",
    version="1.0.0",
    lifespan=lifespan,
    # TODO: отключить docs в продакшене
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS — разрешаем запросы с фронтенда
# TODO: заменить ["*"] на конкретный домен фронтенда в продакшене
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем все роутеры
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )