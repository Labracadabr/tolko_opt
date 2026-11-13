"""Тесты recommend_price. Запуск: python -m unittest -v test_starter"""

import asyncio
import unittest
from decimal import Decimal

from starter import recommend_price, sample_fetch_offers


def make_source(*offers, status="success"):
    async def fetch():
        return {"status": status, "offers": list(offers)}
    return fetch


def offer(price, seller="PARTS", days=1):
    return {"seller": seller, "price": Decimal(price), "delivery_days": days}


def run(fetch, current="1000.00", minimum="1.00", **kwargs):
    return asyncio.run(recommend_price(
        fetch, current_price=Decimal(current), min_price=Decimal(minimum), **kwargs))


class NormalCalculationTest(unittest.TestCase):
    def test_sample_from_task(self):
        res = run(sample_fetch_offers, current="4900.00", minimum="4500.00")
        self.assertEqual(res["price"], Decimal("4728.00"))
        self.assertIsInstance(res["price"], Decimal)
        self.assertEqual(res["decision"], "APPLY")
        self.assertTrue(res["reason"])

    def test_rounds_down_to_cent(self):
        # 1000.33 * 0.985 = 985.32505 -> 985.32 (обычное округление дало бы 985.33)
        res = run(make_source(offer("1000.33")), current="1000.00")
        self.assertEqual(res["price"], Decimal("985.32"))

    def test_min_price_is_floor(self):
        res = run(make_source(offer("900.00")), current="1000.00", minimum="950.00")
        self.assertEqual((res["price"], res["decision"]), (Decimal("950.00"), "APPLY"))

    def test_filters_own_shop_delivery_and_unknown_delivery(self):
        fetch = make_source(
            offer("100.00", seller="MyShop"),
            offer("200.00", days=None),
            offer("300.00", days=7),
            offer("1000.00", days=6),   # граница: 6 дней подходит
            offer("1010.00", days=0),
        )
        res = run(fetch, current="1000.00")
        self.assertEqual(res["price"], Decimal("985.00"))  # 1000.00 * 0.985


class DeviationBoundaryTest(unittest.TestCase):
    # Цена конкурента низкая, рекомендацию задаёт min_price — так граница точная.
    def check(self, minimum, expected):
        res = run(make_source(offer("10.00")), current="1000.00", minimum=minimum)
        self.assertEqual((res["price"], res["decision"]), (Decimal(minimum), expected))

    def test_exactly_30_percent_up_is_applied(self):
        self.check("1300.00", "APPLY")

    def test_over_30_percent_up_needs_review(self):
        self.check("1300.01", "REVIEW")

    def test_exactly_30_percent_down_is_applied(self):
        res = run(make_source(offer("710.66")), current="1000.00")  # -> 700.00
        self.assertEqual((res["price"], res["decision"]), (Decimal("700.00"), "APPLY"))

    def test_over_30_percent_down_needs_review(self):
        res = run(make_source(offer("710.65")), current="1000.00")  # -> 699.99
        self.assertEqual((res["price"], res["decision"]), (Decimal("699.99"), "REVIEW"))


class SourceFailureTest(unittest.TestCase):
    def assert_hold(self, res, current="1000.00"):
        self.assertEqual(res["price"], Decimal(current))
        self.assertEqual(res["decision"], "HOLD")
        self.assertTrue(res["reason"])

    def test_timeout(self):
        async def slow():
            await asyncio.sleep(10)
        res = run(slow, timeout_s=0.05)
        self.assert_hold(res)

    def test_exception(self):
        async def broken():
            raise ConnectionError("площадка недоступна")
        self.assert_hold(run(broken))

    def test_partial_status(self):
        self.assert_hold(run(make_source(offer("900.00"), status="partial")))

    def test_error_status(self):
        self.assert_hold(run(make_source(status="error")))

    def test_no_suitable_offers_even_below_min_price(self):
        fetch = make_source(offer("500.00", seller="MYSHOP"), offer("500.00", days=9))
        res = run(fetch, current="400.00", minimum="450.00")
        self.assert_hold(res, current="400.00")


if __name__ == "__main__":
    unittest.main()
