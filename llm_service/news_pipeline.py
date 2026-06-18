import feedparser
import requests
from datetime import datetime, timedelta
from llm_service.ollama_client import ask_ollama

# RSS-источники новостей — добавляй новые сюда
NEWS_SOURCES = {
    "RBC": "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
    "Kommersant": "https://www.kommersant.ru/RSS/news.xml",
    # TODO: добавить Telegram-каналы через telegraph или tg-rss прокси
    # TODO: добавить Reuters/Bloomberg для международного фона
}

# Категории трат которые мы мониторим в новостях
WATCHLIST_CATEGORIES = [
    "Groceries",
    "Transport",
    "Utilities",
    "Health",
    "Clothing",
]

# Ключевые слова для фильтрации релевантных новостей по категории
# TODO: расширить список слов для каждой категории
CATEGORY_KEYWORDS = {
    "Groceries": ["продукты", "еда", "инфляция", "цены", "магазин", "ритейл"],
    "Transport": ["бензин", "топливо", "транспорт", "авиа", "билеты", "такси"],
    "Utilities": ["тарифы", "ЖКХ", "электроэнергия", "газ", "коммунальные"],
    "Health": ["лекарства", "медицина", "фармацевтика", "аптека"],
    "Clothing": ["одежда", "текстиль", "импорт", "пошлины"],
}

FORECAST_PROMPT = """
You are a financial analyst specializing in consumer price forecasting.
Based on the news summaries below, forecast how prices in the "{category}" 
category will change in the next 1-4 weeks.
Respond ONLY with valid JSON, no explanations.

News:
{news_text}

Respond strictly in this format:
{{
    "category": "{category}",
    "direction": "up | down | stable",
    "confidence": <float 0.0 to 1.0>,
    "forecast_period": "1-4 weeks",
    "key_factors": ["factor 1", "factor 2"],
    "recommendation": "buy now | wait | no action",
    "summary": "2-3 sentence explanation in Russian"
}}
"""


def fetch_news(max_per_source: int = 20) -> list[dict]:
    """
    Собирает новости из RSS-источников.
    Возвращает список статей за последние 48 часов.

    TODO: добавить кэширование результатов в Redis
          чтобы не долбить источники при каждом запросе
    """
    articles = []
    cutoff = datetime.now() - timedelta(hours=48)

    for source_name, url in NEWS_SOURCES.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_per_source]:
                # TODO: добавить парсинг даты публикации и фильтрацию по cutoff
                articles.append({
                    "source": source_name,
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "link": entry.get("link", ""),
                })
        except Exception as e:
            # TODO: заменить на logging
            print(f"[news_pipeline] Failed to fetch {source_name}: {e}")

    return articles


def filter_by_category(articles: list[dict], category: str) -> list[dict]:
    """
    Фильтрует новости по ключевым словам категории.
    Простой keyword-матчинг — быстро и без LLM.

    TODO: заменить на эмбеддинги (sentence-transformers) для лучшей точности
          когда keyword-матчинг начнёт давать много шума
    """
    keywords = CATEGORY_KEYWORDS.get(category, [])
    if not keywords:
        return []

    relevant = []
    for article in articles:
        text = (article["title"] + " " + article["summary"]).lower()
        if any(kw.lower() in text for kw in keywords):
            relevant.append(article)

    return relevant


def format_news_for_prompt(articles: list[dict], max_articles: int = 10) -> str:
    """
    Форматирует список статей в текст для промпта.
    Берём не больше max_articles чтобы не раздувать контекст.
    """
    lines = []
    for i, article in enumerate(articles[:max_articles], 1):
        lines.append(f"{i}. [{article['source']}] {article['title']}")
        if article["summary"]:
            # Обрезаем длинные summary
            summary = article["summary"][:300]
            lines.append(f"   {summary}")
    return "\n".join(lines)


def forecast_for_category(category: str, articles: list[dict]) -> dict:
    """
    Генерирует прогноз изменения цен для одной категории на основе новостей.

    TODO: сохранять прогнозы в БД с датой генерации
          для отслеживания точности модели со временем (критерий приёмки 65%)
    """
    relevant = filter_by_category(articles, category)

    if not relevant:
        return {
            "category": category,
            "direction": "stable",
            "confidence": 0.0,
            "forecast_period": "1-4 weeks",
            "key_factors": [],
            "recommendation": "no action",
            "summary": "Недостаточно новостей для прогноза по данной категории.",
        }

    news_text = format_news_for_prompt(relevant)
    prompt = FORECAST_PROMPT.format(category=category, news_text=news_text)
    result = ask_ollama(prompt)

    if "error" in result:
        return {"category": category, "error": "llm_unavailable"}

    return result


def run_pipeline(categories: list[str] = None) -> list[dict]:
    """
    Основная функция модуля.
    Запускает полный пайплайн: сбор новостей → фильтрация → прогнозы.

    categories — список категорий для прогноза.
    Если None — берём все из WATCHLIST_CATEGORIES.

    TODO: запускать через APScheduler каждые 6 часов автоматически
    TODO: добавить уведомления через Telegram Bot API
          если direction="up" и confidence > 0.7
    """
    if categories is None:
        categories = WATCHLIST_CATEGORIES

    articles = fetch_news()

    if not articles:
        print("[news_pipeline] No articles fetched, aborting.")
        return []

    forecasts = []
    for category in categories:
        forecast = forecast_for_category(category, articles)
        forecasts.append(forecast)
        # TODO: заменить на logging
        print(f"[news_pipeline] Forecast for {category}: {forecast.get('direction')} "
              f"(confidence: {forecast.get('confidence', 0):.0%})")

    return forecasts