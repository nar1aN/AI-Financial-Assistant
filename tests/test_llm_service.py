import pytest
from unittest.mock import patch, MagicMock
from llm_service.categorizer import categorize, categorize_batch, CATEGORIES
from llm_service.recommendations import build_stats, format_stats_for_prompt, get_recommendations
from llm_service.news_pipeline import filter_by_category, format_news_for_prompt, run_pipeline

# Тестовые данные

SAMPLE_TRANSACTIONS = [
    {"description": "Pyaterochka supermarket", "amount": 1500.0, "currency": "RUB", "category": "Groceries"},
    {"description": "Yandex.Taxi", "amount": 350.0, "currency": "RUB", "category": "Transport"},
    {"description": "Netflix subscription", "amount": 799.0, "currency": "RUB", "category": "Subscriptions"},
    {"description": "Starbucks coffee", "amount": 450.0, "currency": "RUB", "category": "Cafes & Restaurants"},
    {"description": "Pyaterochka supermarket", "amount": 2200.0, "currency": "RUB", "category": "Groceries"},
]

SAMPLE_ARTICLES = [
    {
        "source": "RBC",
        "title": "Цены на продукты выросли на 5% за месяц",
        "summary": "Инфляция в секторе продовольственных товаров продолжает расти.",
        "link": "https://rbc.ru/test1",
    },
    {
        "source": "Kommersant",
        "title": "Бензин подорожает в следующем квартале",
        "summary": "Эксперты прогнозируют рост цен на топливо из-за налоговых изменений.",
        "link": "https://kommersant.ru/test2",
    },
    {
        "source": "RBC",
        "title": "Новости технологий — выход нового смартфона",
        "summary": "Крупный производитель представил новую модель.",
        "link": "https://rbc.ru/test3",
    },
]


# Тесты categorizer

class TestCategorizer:

    @patch("llm_service.categorizer.ask_ollama")
    def test_categorize_returns_valid_category(self, mock_ollama):
        """Модель вернула валидную категорию — должны её принять."""
        mock_ollama.return_value = {"category": "Groceries", "confidence": 0.95}
        result = categorize({"description": "Pyaterochka", "amount": 500, "currency": "RUB"})
        assert result["category"] == "Groceries"
        assert result["confidence"] == 0.95

    @patch("llm_service.categorizer.ask_ollama")
    def test_categorize_invalid_category_falls_back(self, mock_ollama):
        """Модель придумала категорию не из списка — должны вернуть Other."""
        mock_ollama.return_value = {"category": "Космос", "confidence": 0.8}
        result = categorize({"description": "Some store", "amount": 100, "currency": "RUB"})
        assert result["category"] == "Other"
        assert result["confidence"] == 0.0

    @patch("llm_service.categorizer.ask_ollama")
    def test_categorize_ollama_error_falls_back(self, mock_ollama):
        """Ollama недоступна — должны вернуть Other с нулевой уверенностью."""
        mock_ollama.return_value = {"error": "ollama_unavailable"}
        result = categorize({"description": "Some store", "amount": 100, "currency": "RUB"})
        assert result["category"] == "Other"
        assert result["confidence"] == 0.0

    @patch("llm_service.categorizer.ask_ollama")
    def test_categorize_batch_adds_fields(self, mock_ollama):
        """Батч-категоризация — все транзакции должны получить поля category и confidence."""
        mock_ollama.return_value = {"category": "Groceries", "confidence": 0.9}
        results = categorize_batch(SAMPLE_TRANSACTIONS[:2])
        assert len(results) == 2
        for tx in results:
            assert "category" in tx
            assert "confidence" in tx

    def test_all_categories_in_list(self):
        """Проверяем что список категорий не пустой и содержит Other."""
        assert len(CATEGORIES) > 0
        assert "Other" in CATEGORIES


# Тесты recommendations

class TestRecommendations:

    def test_build_stats_aggregates_correctly(self):
        """Статистика должна правильно суммировать суммы по категориям."""
        stats = build_stats(SAMPLE_TRANSACTIONS)
        assert "Groceries" in stats
        assert stats["Groceries"]["total"] == 3700.0
        assert stats["Groceries"]["count"] == 2

    def test_build_stats_empty_input(self):
        """Пустой список транзакций — должны получить пустую статистику."""
        stats = build_stats([])
        assert stats == {}

    def test_format_stats_contains_categories(self):
        """Текст для промпта должен содержать все категории из статистики."""
        stats = build_stats(SAMPLE_TRANSACTIONS)
        text = format_stats_for_prompt(stats)
        assert "Groceries" in text
        assert "Transport" in text
        assert "Total spending" in text

    @patch("llm_service.recommendations.ask_ollama")
    def test_get_recommendations_returns_sorted(self, mock_ollama):
        """Рекомендации должны быть отсортированы high → medium → low."""
        mock_ollama.return_value = {
            "recommendations": [
                {"title": "Cut subscriptions", "detail": "...", "potential_saving": "800", "priority": "low"},
                {"title": "Cook at home", "detail": "...", "potential_saving": "3000", "priority": "high"},
                {"title": "Use public transport", "detail": "...", "potential_saving": "1500", "priority": "medium"},
            ]
        }
        results = get_recommendations(SAMPLE_TRANSACTIONS)
        assert results[0]["priority"] == "high"
        assert results[1]["priority"] == "medium"
        assert results[2]["priority"] == "low"

    @patch("llm_service.recommendations.ask_ollama")
    def test_get_recommendations_empty_transactions(self, mock_ollama):
        """Пустой список транзакций — должны вернуть пустой список без вызова LLM."""
        results = get_recommendations([])
        mock_ollama.assert_not_called()
        assert results == []



# Тесты news_pipeline

class TestNewsPipeline:

    def test_filter_by_category_groceries(self):
        """Фильтрация должна найти статью про продукты."""
        relevant = filter_by_category(SAMPLE_ARTICLES, "Groceries")
        assert len(relevant) == 1
        assert "продукты" in relevant[0]["title"].lower() or \
               "инфляция" in relevant[0]["summary"].lower()

    def test_filter_by_category_no_match(self):
        """Категория без совпадений — должны получить пустой список."""
        relevant = filter_by_category(SAMPLE_ARTICLES, "Clothing")
        assert relevant == []

    def test_format_news_limits_articles(self):
        """Форматирование должно ограничивать количество статей."""
        text = format_news_for_prompt(SAMPLE_ARTICLES, max_articles=1)
        assert "RBC" in text
        # Проверяем что только одна статья попала в текст
        assert text.count("[RBC]") + text.count("[Kommersant]") == 1

    @patch("llm_service.news_pipeline.fetch_news")
    @patch("llm_service.news_pipeline.ask_ollama")
    def test_run_pipeline_returns_forecasts(self, mock_ollama, mock_fetch):
        mock_fetch.return_value = SAMPLE_ARTICLES
        mock_ollama.return_value = {
            "category": "Groceries",
            "direction": "up",
            "confidence": 0.75,
            "forecast_period": "1-4 weeks",
            "key_factors": ["инфляция"],
            "recommendation": "buy now",
            "summary": "Ожидается рост цен на продукты.",
        }
        results = run_pipeline(categories=["Groceries"])
        assert len(results) == 1
        assert results[0]["category"] == "Groceries"