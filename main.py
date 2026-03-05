import asyncio
import uvicorn
from datetime import datetime

from config import BOT_TOKEN, ORDER_EXPIRE_MINUTES
from utils.logger import logger

POLL_INTERVAL = 5


async def expire_orders_task():
    """Background task: mark WAITING_PAYMENT orders/topups as EXPIRED every 60s."""
    from database import order_repo

    while True:
        try:
            now = datetime.utcnow()
            expired = await order_repo.get_expired_orders(now)
            for o in expired:
                await order_repo.update_order_status(o["_id"], "EXPIRED")
                logger.info(f"order_expired id={o['_id']}")

            expired_tu = await order_repo.get_expired_topups(now)
            for t in expired_tu:
                await order_repo.update_topup_status(t["_id"], "EXPIRED")
                logger.info(f"topup_expired id={t['_id']}")
        except Exception as e:
            logger.error(f"expire_orders_task error: {e}")

        await asyncio.sleep(60)


async def poll_payments_task():
    """Background task: poll payOS API every few seconds to check WAITING_PAYMENT orders/topups."""
    from database import order_repo, user_repo, product_repo
    from backend.payment import check_payment_status
    from backend.delivery import deliver_order
    from bot.bot import bot

    while True:
        try:
            now = datetime.utcnow()

            # Poll regular orders
            orders = await order_repo.get_waiting_orders()
            for order in orders:
                status = await check_payment_status(order["order_code"])
                if status == "PAID":
                    if order["status"] in ("PAID", "DELIVERED"):
                        continue
                    await order_repo.update_order_status(order["_id"], "PAID")
                    logger.info(f"payment_success id={order['_id']} method=payos (polled)")

                    product = await product_repo.get_by_id(order["product_id"])
                    await deliver_order(order, product, bot)

                elif status == "CANCELLED":
                    await order_repo.update_order_status(order["_id"], "CANCELLED")
                    logger.info(f"payment_cancelled id={order['_id']} (polled)")
                    try:
                        await bot.send_message(
                            order["tg_user_id"],
                            f"❌ Đơn hàng <b>{order['_id']}</b> đã bị hủy.",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass

            # Poll topup orders
            topups = await order_repo.get_waiting_topups()
            for topup in topups:
                status = await check_payment_status(topup["order_code"])
                if status == "PAID":
                    if topup["status"] in ("PAID",):
                        continue
                    await order_repo.update_topup_status(topup["_id"], "PAID")
                    new_balance = await user_repo.add_balance(topup["tg_user_id"], topup["amount"])
                    logger.info(f"topup_success id={topup['_id']} amount={topup['amount']} (polled)")
                    try:
                        await bot.send_message(
                            topup["tg_user_id"],
                            f"✅ Nạp tiền thành công!\n\n"
                            f"💰 Số tiền: {topup['amount']:,}đ\n"
                            f"👛 Số dư hiện tại: {new_balance:,}đ",
                        )
                    except Exception:
                        pass

                elif status == "CANCELLED":
                    await order_repo.update_topup_status(topup["_id"], "CANCELLED")
                    logger.info(f"topup_cancelled id={topup['_id']} (polled)")

        except Exception as e:
            logger.error(f"poll_payments_task error: {e}")

        await asyncio.sleep(POLL_INTERVAL)


async def run_bot():
    from bot.bot import bot, dp, setup_routers
    setup_routers()
    logger.info("Bot starting polling...")
    await dp.start_polling(bot)


async def run_api():
    from backend.api import app
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    logger.info("FastAPI server starting on :8000")
    await server.serve()


async def main():
    logger.info("=== Telegram Shop Bot starting ===")
    await asyncio.gather(
        run_bot(),
        run_api(),
        expire_orders_task(),
        poll_payments_task(),
    )


if __name__ == "__main__":
    asyncio.run(main())
