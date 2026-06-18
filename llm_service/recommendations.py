from llm_service.ollama_client import ask_ollama

PROMPT_TEMPLATE = """
You are a personal finance advisor analyzing a user's spending habits.
Based on the spending statistics below, generate 3-5 practical recommendations to reduce expenses.
Respond ONLY with valid JSON, no explanations.

Spending statistics for the period:
{stats}

Respond strictly in this format:
{{
    "recommendations": [
        {{
            "title": "short title of the recommendation",
            "detail": "specific actionable advice",
            "potential_saving": "estimated saving in RUB per month",
            "priority": "high | medium | low"
        }}
    ]
}}
"""


def build_stats(transactions: list[dict]) -> dict:
    """
    Сворачивает список транзакций в агрегированную статистику по категориям.
    LLM получает статистику, а не сырые транзакции — так промпт короче и точнее.

    Ожидает транзакции с полями: amount (float), category (str), currency (str)
    TODO: добавить сравнение с предыдущим периодом когда партнёр
          реализует хранение транзакций в БД
    """
    stats = {}

    for tx in transactions:
        category = tx.get("category", "Other")
        amount = float(tx.get("amount", 0))

        if category not in stats:
            stats[category] = {"total": 0.0, "count": 0}

        stats[category]["total"] += amount
        stats[category]["count"] += 1

    # TODO: добавить топ-3 самых дорогих транзакций по каждой категории
    # TODO: добавить процент от общей суммы расходов для каждой категории
    return stats


def format_stats_for_prompt(stats: dict) -> str:
    """
    Превращает словарь статистики в читаемый текст для промпта.
    """
    lines = []
    total = sum(v["total"] for v in stats.values())

    for category, data in sorted(stats.items(), key=lambda x: -x[1]["total"]):
        percent = (data["total"] / total * 100) if total > 0 else 0
        lines.append(
            f"- {category}: {data['total']:.0f} RUB "
            f"({data['count']} transactions, {percent:.1f}% of total)"
        )

    lines.append(f"\nTotal spending: {total:.0f} RUB")
    return "\n".join(lines)


def get_recommendations(transactions: list[dict]) -> list[dict]:
    """
    Основная функция модуля.
    Принимает список категоризированных транзакций,
    возвращает список рекомендаций от LLM.

    TODO: добавить фильтрацию по периоду (неделя / месяц / квартал)
          до передачи в эту функцию — на уровне FastAPI роутера
    """
    if not transactions:
        return []

    stats = build_stats(transactions)
    stats_text = format_stats_for_prompt(stats)

    prompt = PROMPT_TEMPLATE.format(stats=stats_text)
    result = ask_ollama(prompt)

    if "error" in result:
        return []

    recommendations = result.get("recommendations", [])

    # Сортируем по приоритету: high → medium → low
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(
        key=lambda x: priority_order.get(x.get("priority", "low"), 2)
    )

    # TODO: сохранять рекомендации в БД с датой генерации,
    #       чтобы отслеживать динамику советов со временем
    return recommendations