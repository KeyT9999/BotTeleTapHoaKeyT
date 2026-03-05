import math
from typing import Optional


def calc_promo(qty: int, promo_buy: Optional[int], promo_bonus: Optional[int]) -> tuple[int, int]:
    """Calculate bonus and total deliver quantity.

    Returns (bonus, deliver_qty).
    """
    if not promo_buy or not promo_bonus or promo_buy <= 0:
        return 0, qty

    bonus = math.floor(qty / promo_buy) * promo_bonus
    return bonus, qty + bonus
