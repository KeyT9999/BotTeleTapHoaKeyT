from aiogram import Bot

from database import inventory_repo, order_repo, product_repo
from utils.logger import logger
from config import ADMIN_ID


async def deliver_order(order: dict, product: dict | None, bot: Bot) -> bool:
    """Deliver inventory items for a PAID order. Returns True on success."""
    order_id = order["_id"]
    tg_user_id = order["tg_user_id"]
    deliver_qty = order["deliver_qty"]
    product_id = order["product_id"]

    if product is None:
        product = await product_repo.get_by_id(product_id)

    items = await inventory_repo.take_items(product_id, deliver_qty)

    if len(items) < deliver_qty:
        missing = deliver_qty - len(items)
        await bot.send_message(
            ADMIN_ID,
            f"⚠️ THIẾU HÀNG\n\n"
            f"Đơn {order_id}: cần {deliver_qty}, chỉ lấy được {len(items)}.\n"
            f"Thiếu {missing} cái cho sản phẩm {product['name'] if product else product_id}.\n"
            f"Hãy bổ sung stock rồi giao tay.",
        )

    if items:
        items_text = "\n".join(items)
        product_name = product["name"] if product else f"SP #{product_id}"

        guide_text = ""
        if product and product.get("guide"):
            guide_text = f"\n📖 <b>Hướng dẫn sử dụng:</b>\n{product['guide']}\n"

        await bot.send_message(
            tg_user_id,
            f"🎉 Thanh toán thành công!\n\n"
            f"📦 Đơn hàng: {order_id}\n"
            f"🛒 Sản phẩm: {product_name}\n"
            f"📬 Số lượng: {len(items)} cái\n"
            f"{guide_text}\n"
            f"Tài khoản của bạn:\n\n"
            f"<pre>{items_text}</pre>",
            parse_mode="HTML",
        )
        await order_repo.update_order_status(order_id, "DELIVERED")
        await product_repo.update_stock(product_id, -len(items))
        logger.info(f"delivery_success id={order_id} delivered={len(items)}")
        return True
    else:
        await bot.send_message(
            tg_user_id,
            f"⚠️ Đơn hàng {order_id} đã thanh toán nhưng kho tạm hết hàng.\n"
            f"Admin sẽ bổ sung và giao sớm nhất có thể.",
        )
        logger.warning(f"delivery_failed id={order_id} no_stock")
        return False
