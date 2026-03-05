from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.payment import get_payos
from database import order_repo, user_repo
from backend.delivery import deliver_order
from utils.logger import logger

webhook_router = APIRouter()


@webhook_router.post("/webhook/payos")
async def payos_webhook(request: Request):
    raw_body = await request.body()
    client = get_payos()

    try:
        webhook_data = client.webhooks.verify(raw_body)
    except Exception as e:
        logger.warning(f"webhook_received invalid signature: {e}")
        return JSONResponse({"error": "invalid signature"}, status_code=400)

    order_code = webhook_data.order_code
    logger.info(f"webhook_received order_code={order_code}")

    order = await order_repo.get_order_by_code(order_code)
    if order:
        await _handle_order_webhook(order, webhook_data)
        return JSONResponse({"success": True})

    topup = await order_repo.get_topup_by_code(order_code)
    if topup:
        await _handle_topup_webhook(topup, webhook_data)
        return JSONResponse({"success": True})

    logger.warning(f"webhook_received unknown order_code={order_code}")
    return JSONResponse({"success": True})


async def _handle_order_webhook(order: dict, webhook_data) -> None:
    if order["status"] in ("PAID", "DELIVERED", "CANCELLED", "EXPIRED"):
        logger.info(f"webhook ignored order={order['_id']} already {order['status']}")
        return

    await order_repo.update_order_status(order["_id"], "PAID")
    logger.info(f"payment_success id={order['_id']} method=payos")

    from database import product_repo
    product = await product_repo.get_by_id(order["product_id"])

    from bot.bot import bot
    await deliver_order(order, product, bot)


async def _handle_topup_webhook(topup: dict, webhook_data) -> None:
    if topup["status"] in ("PAID", "CANCELLED", "EXPIRED"):
        logger.info(f"webhook ignored topup={topup['_id']} already {topup['status']}")
        return

    await order_repo.update_topup_status(topup["_id"], "PAID")
    new_balance = await user_repo.add_balance(topup["tg_user_id"], topup["amount"])
    logger.info(f"topup_success id={topup['_id']} amount={topup['amount']} new_balance={new_balance}")

    from bot.bot import bot
    await bot.send_message(
        topup["tg_user_id"],
        f"✅ Nạp tiền thành công!\n\n"
        f"💰 Số tiền: {topup['amount']:,}đ\n"
        f"👛 Số dư hiện tại: {new_balance:,}đ",
    )
