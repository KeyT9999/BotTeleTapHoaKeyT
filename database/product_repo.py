from database.mongo import get_db
from typing import Optional


def _col():
    return get_db()["products"]


async def get_all_active() -> list[dict]:
    cursor = _col().find({"active": True}).sort("_id", 1)
    return await cursor.to_list(length=100)


async def get_by_id(product_id: int) -> Optional[dict]:
    return await _col().find_one({"_id": product_id})


async def create(product: dict) -> None:
    await _col().insert_one(product)


async def update_stock(product_id: int, delta: int) -> None:
    await _col().update_one(
        {"_id": product_id},
        {"$inc": {"stock": delta}},
    )


async def get_all_admin() -> list[dict]:
    """All products except soft-deleted, for admin management."""
    cursor = _col().find({"deleted": {"$ne": True}}).sort("_id", 1)
    return await cursor.to_list(length=100)


async def update_product(product_id: int, data: dict) -> None:
    await _col().update_one({"_id": product_id}, {"$set": data})


async def soft_delete(product_id: int) -> None:
    await _col().update_one(
        {"_id": product_id},
        {"$set": {"active": False, "deleted": True}},
    )


async def next_id() -> int:
    last = await _col().find_one(sort=[("_id", -1)])
    return (last["_id"] + 1) if last else 1
