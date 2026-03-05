from database.mongo import get_db
from datetime import datetime
from typing import Optional


def _col():
    return get_db()["users"]


async def get_or_create(tg_user_id: int, username: Optional[str] = None) -> dict:
    user = await _col().find_one({"tg_user_id": tg_user_id})
    if user is None:
        user = {
            "tg_user_id": tg_user_id,
            "username": username,
            "balance": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        await _col().insert_one(user)
    return user


async def get_balance(tg_user_id: int) -> int:
    user = await _col().find_one({"tg_user_id": tg_user_id})
    return user["balance"] if user else 0


async def add_balance(tg_user_id: int, amount: int) -> int:
    result = await _col().find_one_and_update(
        {"tg_user_id": tg_user_id},
        {
            "$inc": {"balance": amount},
            "$set": {"updated_at": datetime.utcnow()},
        },
        return_document=True,
    )
    return result["balance"] if result else 0


async def deduct_balance(tg_user_id: int, amount: int) -> bool:
    """Atomically deduct if sufficient balance. Returns True on success."""
    result = await _col().find_one_and_update(
        {"tg_user_id": tg_user_id, "balance": {"$gte": amount}},
        {
            "$inc": {"balance": -amount},
            "$set": {"updated_at": datetime.utcnow()},
        },
        return_document=True,
    )
    return result is not None


async def get_all_users() -> list[dict]:
    cursor = _col().find({}).sort("created_at", -1)
    return await cursor.to_list(length=10000)


async def count_users() -> int:
    return await _col().count_documents({})
