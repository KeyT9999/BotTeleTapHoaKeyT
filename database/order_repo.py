from database.mongo import get_db
from datetime import datetime
from typing import Optional
import secrets


def _col():
    return get_db()["orders"]


def _topup_col():
    return get_db()["topup_orders"]


def generate_order_id() -> str:
    return "OD_" + secrets.token_hex(4).upper()


def generate_topup_id() -> str:
    return "TU_" + secrets.token_hex(4).upper()


async def create_order(order: dict) -> None:
    await _col().insert_one(order)


async def get_order(order_id: str) -> Optional[dict]:
    return await _col().find_one({"_id": order_id})


async def get_order_by_code(order_code: int) -> Optional[dict]:
    return await _col().find_one({"order_code": order_code})


async def update_order_status(order_id: str, status: str) -> None:
    await _col().update_one(
        {"_id": order_id},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}},
    )


async def update_order(order_id: str, data: dict) -> None:
    await _col().update_one({"_id": order_id}, {"$set": data})


async def get_waiting_orders() -> list[dict]:
    cursor = _col().find({"status": "WAITING_PAYMENT"})
    return await cursor.to_list(length=500)


async def get_expired_orders(now: datetime) -> list[dict]:
    cursor = _col().find({
        "status": "WAITING_PAYMENT",
        "expired_at": {"$lte": now},
    })
    return await cursor.to_list(length=500)


async def get_recent_orders(limit: int = 20, status: Optional[str] = None) -> list[dict]:
    query = {}
    if status:
        query["status"] = status
    cursor = _col().find(query).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


# --- topup orders ---

async def create_topup(topup: dict) -> None:
    await _topup_col().insert_one(topup)


async def get_topup(topup_id: str) -> Optional[dict]:
    return await _topup_col().find_one({"_id": topup_id})


async def get_topup_by_code(order_code: int) -> Optional[dict]:
    return await _topup_col().find_one({"order_code": order_code})


async def update_topup_status(topup_id: str, status: str) -> None:
    await _topup_col().update_one(
        {"_id": topup_id},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}},
    )


async def update_topup(topup_id: str, data: dict) -> None:
    await _topup_col().update_one({"_id": topup_id}, {"$set": data})


async def get_waiting_topups() -> list[dict]:
    cursor = _topup_col().find({"status": "WAITING_PAYMENT"})
    return await cursor.to_list(length=500)


async def get_expired_topups(now: datetime) -> list[dict]:
    cursor = _topup_col().find({
        "status": "WAITING_PAYMENT",
        "expired_at": {"$lte": now},
    })
    return await cursor.to_list(length=500)
