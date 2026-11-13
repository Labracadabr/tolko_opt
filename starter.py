"""Учебный фрагмент для тестового задания ТОЛЬКООПТ.

Python 3.10+, только стандартная библиотека. Запуск примера: python starter.py
В функции recommend_price намеренно есть ошибки. Исправьте её по правилам ниже.
sample_fetch_offers имитирует внешний источник: реальные запросы не нужны.

Контракт fetch_offers(): async-функция без аргументов, возвращает словарь
со status (success / partial / error) и offers (список предложений).
Все суммы на входе — положительные Decimal с точностью до копейки.
seller — строка; delivery_days — неотрицательное целое число или None.
Формат входных данных корректен; дополнительных проверок типов не требуется.
fetch_offers может завершиться исключением или долго ожидать ответа.
current_price — текущая цена; min_price — минимально допустимая цена.
timeout_s — положительное число секунд, по умолчанию 2.

ПРАВИЛА В ПОРЯДКЕ ПРИМЕНЕНИЯ
1. Ограничьте ожидание fetch_offers значением timeout_s. При ошибке источника,
   тайм-ауте или status != success верните текущую цену и HOLD.
2. Учитывайте предложения с известной доставкой не более 6 дней.
   Исключайте собственный магазин MYSHOP независимо от регистра букв.
3. Если подходящих предложений нет, верните текущую цену и HOLD,
   даже если текущая цена ниже min_price.
4. Минимальную цену подходящего конкурента уменьшите на 1,5% и округлите
   вниз до копейки. Рекомендация — максимум из этой суммы и min_price.
5. Если рекомендация отличается от текущей цены более чем на 30% в любую
   сторону, верните рекомендацию и REVIEW. Иначе — рекомендацию и APPLY.
   Ровно 30% допускается. REVIEW означает, что автоматическое применение
   запрещено до ручной проверки.

РЕЗУЛЬТАТ
Словарь с полями price (Decimal), decision (APPLY / REVIEW / HOLD),
reason (короткая понятная причина). Сохраните интерфейс recommend_price;
вспомогательные функции допустимы. Пример ниже после исправления должен
вернуть price = Decimal("4728.00"), decision = "APPLY".

ПРОВЕРКА
Добавьте минимум два автоматических теста: обычный расчёт и один сбой
или граничный случай на ваш выбор. Укажите команду запуска тестов.
Достаточно стандартной библиотеки; pytest также допустим.
"""

import asyncio
from decimal import ROUND_FLOOR, Decimal

# константы
OWN_SELLER = "myshop"
MAX_DELIVERY_DAYS = 6
DISCOUNT_FACTOR = Decimal("0.985")  # минус 1,5%
MAX_AUTO_DEVIATION = Decimal("0.30")  # ровно 30% ещё допускается
CENT = Decimal("0.01")


def _result(price, decision, reason):
    return {"price": price, "decision": decision, "reason": reason}


def _is_suitable(offer):
    """Правило 2: доставка известна и не более 6 дней, не наш магазин."""
    days = offer["delivery_days"]
    if days is None or days > MAX_DELIVERY_DAYS:
        return False
    return offer["seller"].casefold() != OWN_SELLER


async def recommend_price(fetch_offers, current_price, min_price, timeout_s=2.0):
    # Правило 1: ограничиваем ожидание источника; любой сбой -> HOLD.
    try:
        result = await asyncio.wait_for(fetch_offers(), timeout=timeout_s)
    except asyncio.TimeoutError:
        return _result(current_price, "HOLD", f"Источник не ответил за {timeout_s} с, цена не изменена")
    except Exception as exc:  # ошибка источника любого типа
        return _result(current_price, "HOLD", f"Ошибка источника ({type(exc).__name__}), цена не изменена")

    status = result.get("status")
    if status != "success":
        return _result(current_price, "HOLD",
                       f"Статус источника {status!r}, данные неполные, цена не изменена")

    # Правила 2-3: отбор подходящих предложений.
    prices = [offer["price"] for offer in result.get("offers") or [] if _is_suitable(offer)]
    if not prices:
        return _result(current_price, "HOLD", "Нет подходящих предложений конкурентов, цена не изменена")

    # Правило 4: минус 1,5%, округление вниз до копейки, не ниже min_price.
    competitor_price = min(prices)
    discounted = (competitor_price * DISCOUNT_FACTOR).quantize(CENT, rounding=ROUND_FLOOR)
    price = max(discounted, min_price)
    if price == min_price and discounted < min_price:
        basis = f"ограничено минимальной ценой {min_price}"
    else:
        basis = f"конкурент {competitor_price} минус 1,5%"

    # Правило 5: сравнение без деления, точно в Decimal.
    if abs(price - current_price) > current_price * MAX_AUTO_DEVIATION:
        return _result(price, "REVIEW",
                       f"Изменение более 30% от текущей цены {current_price} ({basis}), нужна ручная проверка")
    return _result(price, "APPLY", f"Рекомендация: {basis}")


async def sample_fetch_offers():
    return {
        "status": "success",
        "offers": [
            {"seller": "myshop", "price": Decimal("4300.00"), "delivery_days": 2},
            {"seller": "PARTS", "price": Decimal("4800.00"), "delivery_days": 3},
            {"seller": "SLOW", "price": Decimal("4700.00"), "delivery_days": 8},
        ],
    }


if __name__ == "__main__":
    print(asyncio.run(recommend_price(
        sample_fetch_offers,
        current_price=Decimal("4900.00"),
        min_price=Decimal("4500.00"),
    )))
