from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

from database import product_repo, order_repo, user_repo
from bot.states.order_state import OrderState
from bot.keyboards.inline import main_menu_kb
from backend.payment import create_payment_link
from backend.delivery import deliver_order
from utils.qr import generate_qr_bytes
from utils.logger import logger
from config import ORDER_EXPIRE_MINUTES

router = Router()


async def _create_and_save_order(state_data: dict, tg_user_id: int, pay_method: str) -> dict:
    order_id = order_repo.generate_order_id()
    now = datetime.utcnow()
    order_code = int(now.timestamp() * 1000) % 2_147_483_647

    order = {
        "_id": order_id,
        "order_code": order_code,
        "tg_user_id": tg_user_id,
        "product_id": state_data["product_id"],
        "qty": state_data["qty"],
        "bonus": state_data["bonus"],
        "deliver_qty": state_data["deliver_qty"],
        "amount": state_data["amount"],
        "pay_method": pay_method,
        "status": "CREATED",
        "payment_link_id": None,
        "checkout_url": None,
        "created_at": now,
        "expired_at": now + timedelta(minutes=ORDER_EXPIRE_MINUTES),
    }
    await order_repo.create_order(order)
    logger.info(f"order_created id={order_id} user={tg_user_id} amount={order['amount']}")
    return order


async def do_payos_payment(callback: CallbackQuery, state: FSMContext):
    """Create payOS payment and send QR. Called from order confirm or pay:payos button."""
    data = await state.get_data()
    product = await product_repo.get_by_id(data["product_id"])
    if not product:
        await callback.message.edit_text("❌ Sản phẩm không tồn tại.")
        await state.clear()
        return

    order = await _create_and_save_order(data, callback.from_user.id, "payos")
    try:
        pay_info = await create_payment_link(
            order_code=order["order_code"],
            amount=order["amount"],
            description=f"DH {order['_id']}",
        )
    except Exception as e:
        logger.error(f"payOS create failed: {e}")
        await order_repo.update_order_status(order["_id"], "CANCELLED")
        await callback.message.edit_text("❌ Lỗi tạo thanh toán. Vui lòng thử lại.")
        await state.clear()
        return

    await order_repo.update_order(order["_id"], {
        "status": "WAITING_PAYMENT",
        "payment_link_id": pay_info["paymentLinkId"],
        "checkout_url": pay_info["checkoutUrl"],
    })

    qr_data = pay_info.get("qrCode") or pay_info["checkoutUrl"]
    qr_buf = generate_qr_bytes(qr_data)

    text = (
        f"💳 Thanh toán đơn <b>{order['_id']}</b>\n\n"
        f"🛒 {product['name']} x{order['qty']}\n"
        f"💰 Số tiền: <b>{order['amount']:,}đ</b>\n\n"
        f"Quét QR hoặc nhấn link để thanh toán:\n"
        f"{pay_info['checkoutUrl']}\n\n"
        f"⏰ Đơn hàng hết hạn sau {ORDER_EXPIRE_MINUTES} phút."
    )

    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer_photo(
        BufferedInputFile(qr_buf.read(), filename="qr.png"),
        caption=text,
        parse_mode="HTML",
    )
    await state.clear()


@router.callback_query(OrderState.wait_payment, F.data == "pay:payos")
async def pay_via_payos(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await do_payos_payment(callback, state)


@router.callback_query(OrderState.wait_payment, F.data == "pay:wallet")
async def pay_via_wallet(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount = data["amount"]

    success = await user_repo.deduct_balance(callback.from_user.id, amount)
    if not success:
        await callback.answer("❌ Số dư không đủ!", show_alert=True)
        return

    order = await _create_and_save_order(data, callback.from_user.id, "wallet")
    await order_repo.update_order_status(order["_id"], "PAID")
    logger.info(f"payment_success id={order['_id']} method=wallet user={callback.from_user.id}")

    product = await product_repo.get_by_id(data["product_id"])
    await state.clear()

    from bot.bot import bot
    await deliver_order(order, product, bot)

    balance = await user_repo.get_balance(callback.from_user.id)
    await callback.message.edit_text(
        f"✅ Thanh toán thành công bằng ví!\n\n"
        f"Đơn hàng <b>{order['_id']}</b> đang được xử lý.\n"
        f"👛 Số dư còn lại: {balance:,}đ",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(OrderState.wait_payment, F.data == "pay:cancel")
async def pay_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Đã hủy đơn hàng.\n\nChọn chức năng bên dưới:",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
