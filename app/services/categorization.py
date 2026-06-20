import json
import logging
from typing import List, Dict
from app.config import settings
from app.models.expense import EXPENSE_CATEGORIES

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a financial transaction categorizer.
Classify each bank transaction into exactly one of these categories:
Housing, Transportation, Food & Dining, Utilities, Insurance, Healthcare, Entertainment, Shopping, Education, Travel, Subscriptions, Salary, Freelance, Investment, Other Income, Other Expense.

Rules:
- Supermarkets, food shops (ATB, Silpo, Novus), restaurants, cafes, food delivery - Food & Dining
- Gas stations, parking (WOG, OKKO, Shell), taxis, Uber, Bolt, buses, metro - Transportation
- Flights, hotel, Airbnb, car rental - Travel
- Electricity, water, gas, internet, mobile - Utilities
- Rent, apartment, housing, mortgage, property tax - Housing
- Pharmacies, hospitals, gym, fitness - Healthcare
- Netflix, Spotify, Apple, subscriptions, monthly fee - Subscriptions
- Movie, cinema, theater, concert, game - Entertainment
- Book, course, tutorial, class - Education
- Insurance - Insurance
- Salary - Salary
- Freelance, gig, contract - Freelance
- Dividend, stock, investment, crypto - Investment
- Other income (if the transaction is an income and does not fit anywhere else) - Other Income
- Other expense (if the transaction is an expense and does not fit anywhere else) - Other Expense

Return ONLY a JSON array. No preamble, no markdown fences. Example:
[{"id": 1, "category": "Food & Dining", "confidence": 0.95}]"""


class CategorizationService:
    def __init__(self):
        self._anthropic_client = None
        self._openai_client = None

    def _get_anthropic(self):
        if self._anthropic_client is None:
            import anthropic
            key = settings.ANTHROPIC_API_KEY
            if not key:
                raise ValueError("ANTHROPIC_API_KEY is not set in environment")
            self._anthropic_client = anthropic.Anthropic(api_key=key)
        return self._anthropic_client

    def _get_openai(self):
        if self._openai_client is None:
            import openai
            key = settings.OPENAI_API_KEY
            if not key:
                raise ValueError("OPENAI_API_KEY is not set in environment")
            # base_url lets this drive any OpenAI-compatible endpoint
            # (LM Studio locally, or Groq's /openai/v1 in the cloud).
            self._openai_client = openai.OpenAI(
                api_key=key,
                base_url=settings.LLM_BASE_URL or None,
            )
        return self._openai_client

    def _call_llm(self, user_message: str) -> str:
        provider = settings.LLM_PROVIDER

        if provider == "anthropic":
            client = self._get_anthropic()
            resp = client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=settings.LLM_MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            return resp.content[0].text

        elif provider == "openai":
            client = self._get_openai()
            resp = client.chat.completions.create(
                model=settings.LLM_MODEL or "gpt-4o-mini",
                max_tokens=settings.LLM_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )
            return resp.choices[0].message.content

        raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")

    def _parse_response(self, raw: str, fallback_transactions: List[Dict]) -> List[Dict]:
        raw = raw.strip()
        # Strip markdown fences if the model added them anyway
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        fallback_map = {t["id"]: t for t in fallback_transactions}

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed: {e}. Raw: {raw[:200]}")
            return [
                {
                    "id": t["id"],
                    "category": "Other Income" if t.get("is_income") else "Other Expense",
                    "confidence": 0.0
                }
                for t in fallback_transactions
            ]

        if not isinstance(data, list):
            logger.warning("LLM response was not a JSON array. Raw: %s", raw[:200])
            return [
                {
                    "id": t["id"],
                    "category": "Other Income" if t.get("is_income") else "Other Expense",
                    "confidence": 0.0
                }
                for t in fallback_transactions
            ]

        valid_set = set(EXPENSE_CATEGORIES)
        parsed_by_id: Dict[int, Dict] = {}
        for item in data:
            if not isinstance(item, dict) or item.get("id") not in fallback_map:
                continue
            cat = item.get("category")
            t = fallback_map[item["id"]]
            if cat not in valid_set:
                cat = "Other Income" if t.get("is_income") else "Other Expense"
            item["confidence"] = float(max(0.0, min(1.0, item.get("confidence", 0.5))))
            parsed_by_id[item["id"]] = {
                "id": item["id"],
                "category": cat,
                "confidence": item["confidence"],
            }

        return [
            parsed_by_id.get(
                t["id"],
                {
                    "id": t["id"],
                    "category": "Other Income" if t.get("is_income") else "Other Expense",
                    "confidence": 0.0
                }
            )
            for t in fallback_transactions
        ]

    def categorize_batch(self, transactions: List[Dict]) -> List[Dict]:
        """
        transactions: list of {id, raw_text, amount, currency, is_income}
        returns:      list of {id, category, confidence}
        """
        if not transactions:
            return []

        payload = json.dumps(
            [
                {
                    "id": t["id"],
                    "text": t["raw_text"],
                    "amount": t.get("amount"),
                    "currency": t.get("currency", "USD"),
                    "is_income": t.get("is_income", False),
                }
                for t in transactions
            ],
            ensure_ascii=False,
        )

        try:
            raw = self._call_llm(f"Categorize these transactions:\n{payload}")
            return self._parse_response(raw, fallback_transactions=transactions)
        except Exception as exc:
            logger.error(f"LLM categorization error: {exc}")
            return [
                {
                    "id": t["id"],
                    "category": "Other Income" if t.get("is_income") else "Other Expense",
                    "confidence": 0.0
                }
                for t in transactions
            ]

    def categorize_all_pending(self, repo) -> Dict:
        """Process all PENDING expenses from the repository in batches."""
        batch_size = settings.LLM_BATCH_SIZE
        total_processed = 0
        total_failed = 0

        while True:
            pending = repo.get_pending_categorization(limit=batch_size)
            if not pending:
                break

            transactions = [
                {
                    "id": e.id,
                    "raw_text": e.raw_text,
                    "amount": e.amount,
                    "currency": e.currency,
                    "is_income": e.is_income
                }
                for e in pending
            ]

            results = self.categorize_batch(transactions)

            updates, failed = [], 0
            for r in results:
                if r.get("category"):
                    updates.append({"id": r["id"], "category": r["category"], "confidence": r["confidence"]})
                else:
                    failed += 1

            try:
                if updates:
                    repo.bulk_update_categories(updates)
                    total_processed += len(updates)
                total_failed += failed
            except Exception as exc:
                logger.error("Failed to persist categorization batch: %s", exc)
                total_failed += len(pending)
                break

        return {"processed": total_processed, "failed": total_failed}
