from database.mongo import get_db


def _col():
    return get_db()["inventory_items"]


async def add_items(product_id: int, secrets_list: list[str]) -> int:
    docs = [
        {"product_id": product_id, "secret": s, "status": "AVAILABLE"}
        for s in secrets_list
    ]
    result = await _col().insert_many(docs)
    return len(result.inserted_ids)


async def take_items(product_id: int, qty: int) -> list[str]:
    """Claim `qty` AVAILABLE items atomically one-by-one. Returns secrets."""
    claimed: list[str] = []
    for _ in range(qty):
        doc = await _col().find_one_and_update(
            {"product_id": product_id, "status": "AVAILABLE"},
            {"$set": {"status": "SOLD"}},
        )
        if doc is None:
            break
        claimed.append(doc["secret"])
    return claimed


async def count_available(product_id: int) -> int:
    return await _col().count_documents(
        {"product_id": product_id, "status": "AVAILABLE"}
    )
