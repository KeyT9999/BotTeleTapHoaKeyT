from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from database import product_repo
from bot.states.order_state import OrderState
from utils.logger import logger

router = Router()


@router.callback_query(F.data.startswith("product:"))
async def select_product(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    product = await product_repo.get_by_id(product_id)
    if not product:
        await callback.answer("Sản phẩm không tồn tại!", show_alert=True)
        return

    await state.set_state(OrderState.enter_qty)
    await state.update_data(product_id=product_id)

    promo_text = ""
    if product.get("promo_buy") and product.get("promo_bonus"):
        promo_text = f"\n🎁 Khuyến mãi: mua {product['promo_buy']} tặng {product['promo_bonus']}"

    text = (
        f"🛒 Bạn chọn: <b>{product['name']}</b>\n"
        f"💰 Giá: {product['price']:,}đ / cái\n"
        f"📦 Còn: {product['stock']} cái"
        f"{promo_text}\n\n"
        f"Nhập số lượng cần mua:"
    )
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()
    logger.info(f"User {callback.from_user.id} selected product {product_id}")
