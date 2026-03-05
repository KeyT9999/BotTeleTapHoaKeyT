from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

from database import user_repo, order_repo
from bot.states.order_state import TopupState
from bot.keyboards.inline import main_menu_kb
from backend.payment import create_payment_link
from utils.qr import generate_qr_bytes
from utils.logger import logger
from config import ORDER_EXPIRE_MINUTES

router = Router()


@router.callback_query(F.data == "menu:balance")
async def show_balance(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    balance = await user_repo.get_balance(callback.from_user.id)
    await callback.message.edit_text(
        f"👛 Số dư ví: <b>{balance:,}đ</b>\n\nChọn chức năng:",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:topup")
async def start_topup(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(TopupState.enter_amount)
    balance = await user_repo.get_balance(callback.from_user.id)
    await callback.message.edit_text(
        f"💰 NẠP TIỀN VÀO VÍ\n\n"
        f"👛 Số dư hiện tại: {balance:,}đ\n\n"
        f"Nhập số tiền cần nạp (VNĐ):\n"
        f"(Tối thiểu 10,000đ)",
    )
    await callback.answer()


@router.message(Command("naptien"))
async def cmd_topup(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(TopupState.enter_amount)
    balance = await user_repo.get_balance(message.from_user.id)
    await message.answer(
        f"💰 NẠP TIỀN VÀO VÍ\n\n"
        f"👛 Số dư hiện tại: {balance:,}đ\n\n"
        f"Nhập số tiền cần nạp (VNĐ):\n"
        f"(Tối thiểu 10,000đ)",
    )


@router.message(TopupState.enter_amount)
async def enter_topup_amount(message: Message, state: FSMContext):
    text = message.text.strip().replace(",", "").replace(".", "")
    if not text.isdigit() or int(text) < 10000:
        await message.answer("⚠️ Vui lòng nhập số tiền hợp lệ (tối thiểu 10,000đ):")
        return

    amount = int(text)
    tg_user_id = message.from_user.id
    now = datetime.utcnow()

    topup_id = order_repo.generate_topup_id()
    order_code = int(now.timestamp() * 1000) % 2_147_483_647

    topup = {
        "_id": topup_id,
        "order_code": order_code,
        "tg_user_id": tg_user_id,
        "amount": amount,
        "status": "CREATED",
        "payment_link_id": None,
        "checkout_url": None,
        "created_at": now,
        "expired_at": now + timedelta(minutes=ORDER_EXPIRE_MINUTES),
    }
    await order_repo.create_topup(topup)

    try:
        pay_info = await create_payment_link(
            order_code=order_code,
            amount=amount,
            description=f"Nap {topup_id}",
        )
    except Exception as e:
        logger.error(f"payOS topup create failed: {e}")
        await order_repo.update_topup_status(topup_id, "CANCELLED")
        await message.answer("❌ Lỗi tạo thanh toán. Vui lòng thử lại.")
        await state.clear()
        return

    await order_repo.update_topup(topup_id, {
        "status": "WAITING_PAYMENT",
        "payment_link_id": pay_info["paymentLinkId"],
        "checkout_url": pay_info["checkoutUrl"],
    })

    qr_data = pay_info.get("qrCode") or pay_info["checkoutUrl"]
    qr_buf = generate_qr_bytes(qr_data)

    caption = (
        f"💰 Nạp tiền <b>{topup_id}</b>\n\n"
        f"💵 Số tiền: <b>{amount:,}đ</b>\n\n"
        f"Quét QR hoặc nhấn link để thanh toán:\n"
        f"{pay_info['checkoutUrl']}\n\n"
        f"⏰ Hết hạn sau {ORDER_EXPIRE_MINUTES} phút."
    )
    await message.answer_photo(
        BufferedInputFile(qr_buf.read(), filename="qr.png"),
        caption=caption,
        parse_mode="HTML",
    )
    await state.clear()
    logger.info(f"topup_created id={topup_id} user={tg_user_id} amount={amount}")
