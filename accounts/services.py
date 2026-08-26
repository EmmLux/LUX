from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings


CENT = Decimal("0.01")


def calculate_platform_fee(price):
    price = Decimal(price)
    if price < 0:
        raise ValueError("El precio no puede ser negativo.")
    fee_percent = Decimal(str(settings.LUX_PLATFORM_FEE_PERCENT))
    return (price * fee_percent / Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_seller_amount(price):
    price = Decimal(price)
    return (price - calculate_platform_fee(price)).quantize(CENT, rounding=ROUND_HALF_UP)
