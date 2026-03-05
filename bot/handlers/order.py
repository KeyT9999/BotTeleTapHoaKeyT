from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import product_repo, user_repo
from bot.states.order_state import OrderState
from bot.keyboards.inline import payment_method_kb, confirm_order_kb, main_menu_kb
from utils.promo import calc_promo
from utils.logger import logger

router = Router()


@router.message(OrderState.enter_qty)
async def enter_quantity(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("⚠️ Vui lòng nhập số lượng hợp lệ (số nguyên > 0):")
        return

    qty = int(text)
    data = await state.get_data()
    product = await product_repo.get_by_id(data["product_id"])
    if not product:
        await message.answer("❌ Sản phẩm không tồn tại.")
        await state.clear()
        return

    if qty > product["stock"]:
        await message.answer(
            f"⚠️ Kho chỉ còn {product['stock']} cái. Nhập lại số lượng:"
        )
        return

    bonus, deliver_qty = calc_promo(qty, product.get("promo_buy"), product.get("promo_bonus"))
    amount = qty * product["price"]

    if deliver_qty > product["stock"]:
        await message.answer(
            f"⚠️ Kho không đủ hàng cho đơn + khuyến mãi ({deliver_qty} cái). "
            f"Chỉ còn {product['stock']} cái. Nhập lại số lượng:"
        )
        return

    await state.update_data(qty=qty, bonus=bonus, deliver_qty=deliver_qty, amount=amount)
    await state.set_state(OrderState.confirm)

    promo_line = f"\n🎁 Khuyến mãi: +{bonus} cái" if bonus > 0 else ""
    text = (
        f"📝 XÁC NHẬN ĐƠN HÀNG\n\n"
        f"🛒 Sản phẩm: {product['name']}\n"
        f"📦 Số lượng: {qty}\n"
        f"{promo_line}\n"
        f"📬 Tổng nhận: {deliver_qty} cái\n"
        f"💰 Thành tiền: {amount:,}đ\n\n"
        f"Bạn muốn tiếp tục?"
    )
    await message.answer(text, reply_markup=confirm_order_kb())
    logger.info(f"User {message.from_user.id} order preview: {qty}x product {data['product_id']} = {amount}")


@router.callback_query(OrderState.confirm, F.data == "confirm:yes")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    product = await product_repo.get_by_id(data["product_id"])
    if not product:
        await callback.message.edit_text("❌ Sản phẩm không tồn tại.")
        await state.clear()
        return

    user = await user_repo.get_or_create(callback.from_user.id, callback.from_user.username)
    balance = user.get("balance", 0)
    amount = data["amount"]

    if balance >= amount:
        await state.set_state(OrderState.wait_payment)
        text = (
            f"💳 Chọn phương thức thanh toán:\n\n"
            f"👛 Số dư ví: {balance:,}đ\n"
            f"💰 Cần trả: {amount:,}đ"
        )
        await callback.message.edit_text(
            text,
            reply_markup=payment_method_kb(balance=balance, amount=amount),
        )
        await callback.answer()
    else:
        await state.set_state(OrderState.wait_payment)
        await callback.answer()
        from bot.handlers.payment import do_payos_payment
        await do_payos_payment(callback, state)


@router.callback_query(OrderState.confirm, F.data == "confirm:no")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Đã hủy đơn hàng.\n\nChọn chức năng bên dưới:",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
