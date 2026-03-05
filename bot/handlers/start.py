from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import user_repo, product_repo
from bot.keyboards.inline import main_menu_kb, product_list_kb
from utils.logger import logger

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await user_repo.get_or_create(
        message.from_user.id,
        message.from_user.username,
    )
    logger.info(f"User {message.from_user.id} started bot")
    await message.answer(
        "👋 Chào mừng bạn đến với Shop!\n\nChọn chức năng bên dưới:",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "menu:buy")
async def menu_buy(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    products = await product_repo.get_all_active()
    if not products:
        await callback.message.edit_text("🚫 Hiện chưa có sản phẩm nào.")
        return
    text = "📋 DANH SÁCH SẢN PHẨM\n\nChọn sản phẩm bạn muốn mua:"
    await callback.message.edit_text(text, reply_markup=product_list_kb(products))
    await callback.answer()


@router.callback_query(F.data == "menu:main")
async def menu_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "👋 Chào mừng bạn đến với Shop!\n\nChọn chức năng bên dưới:",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
