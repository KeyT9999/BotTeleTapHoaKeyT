from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import product_repo, order_repo, user_repo, inventory_repo
from bot.states.order_state import AdminAddProduct, AdminAddStock, AdminBroadcast, AdminEditProduct
from bot.keyboards.inline import (
    admin_product_list_kb, admin_all_products_kb,
    admin_product_manage_kb, admin_delete_confirm_kb,
)
from utils.logger import logger
from config import ADMIN_ID

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ── /addproduct ──────────────────────────────────────────

@router.message(Command("addproduct"))
async def cmd_add_product(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await state.set_state(AdminAddProduct.enter_name)
    await message.answer("📝 Nhập tên sản phẩm:")


@router.message(AdminAddProduct.enter_name)
async def ap_enter_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminAddProduct.enter_price)
    await message.answer("💰 Nhập giá sản phẩm (VNĐ):")


@router.message(AdminAddProduct.enter_price)
async def ap_enter_price(message: Message, state: FSMContext):
    text = message.text.strip().replace(",", "")
    if not text.isdigit() or int(text) <= 0:
        await message.answer("⚠️ Nhập giá hợp lệ:")
        return
    await state.update_data(price=int(text))
    await state.set_state(AdminAddProduct.enter_promo_buy)
    await message.answer(
        "🎁 Nhập số lượng mua để khuyến mãi (ví dụ: 10):\n"
        "Gửi 0 nếu không khuyến mãi."
    )


@router.message(AdminAddProduct.enter_promo_buy)
async def ap_enter_promo_buy(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("⚠️ Nhập số hợp lệ:")
        return
    val = int(text)
    await state.update_data(promo_buy=val if val > 0 else None)
    if val > 0:
        await state.set_state(AdminAddProduct.enter_promo_bonus)
        await message.answer(f"🎁 Mua {val} thì tặng bao nhiêu?")
    else:
        await state.update_data(promo_bonus=None)
        await state.set_state(AdminAddProduct.enter_guide)
        await message.answer(
            "📖 Nhập hướng dẫn sử dụng cho sản phẩm:\n"
            "(Gửi 0 nếu không cần hướng dẫn)"
        )


@router.message(AdminAddProduct.enter_promo_bonus)
async def ap_enter_promo_bonus(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("⚠️ Nhập số hợp lệ:")
        return
    await state.update_data(promo_bonus=int(text))
    await state.set_state(AdminAddProduct.enter_guide)
    await message.answer(
        "📖 Nhập hướng dẫn sử dụng cho sản phẩm:\n"
        "(Gửi 0 nếu không cần hướng dẫn)"
    )


@router.message(AdminAddProduct.enter_guide)
async def ap_enter_guide(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "0":
        await state.update_data(guide=None)
    else:
        await state.update_data(guide=text)
    await _save_product(message, state)


async def _save_product(message: Message, state: FSMContext):
    data = await state.get_data()
    pid = await product_repo.next_id()
    product = {
        "_id": pid,
        "name": data["name"],
        "price": data["price"],
        "stock": 0,
        "active": True,
        "promo_buy": data.get("promo_buy"),
        "promo_bonus": data.get("promo_bonus"),
        "guide": data.get("guide"),
    }
    await product_repo.create(product)
    await state.clear()

    promo_text = ""
    if product["promo_buy"] and product["promo_bonus"]:
        promo_text = f"\n🎁 KM: mua {product['promo_buy']} tặng {product['promo_bonus']}"

    guide_text = ""
    if product["guide"]:
        guide_text = f"\n📖 HDSD: {product['guide'][:80]}..."

    await message.answer(
        f"✅ Đã thêm sản phẩm!\n\n"
        f"🆔 ID: {pid}\n"
        f"📦 Tên: {product['name']}\n"
        f"💰 Giá: {product['price']:,}đ"
        f"{promo_text}"
        f"{guide_text}"
    )
    logger.info(f"admin add_product id={pid} name={product['name']}")


# ── /products (manage) ────────────────────────────────────

def _product_detail_text(product: dict) -> str:
    status = "🟢 Đang bán" if product.get("active") else "🔴 Tạm dừng"
    promo = ""
    if product.get("promo_buy") and product.get("promo_bonus"):
        promo = f"\n🎁 KM: mua {product['promo_buy']} tặng {product['promo_bonus']}"
    guide = ""
    if product.get("guide"):
        guide = f"\n📖 HDSD: {product['guide'][:120]}"
    return (
        f"📦 <b>{product['name']}</b>\n\n"
        f"🆔 ID: {product['_id']}\n"
        f"💰 Giá: {product['price']:,}đ\n"
        f"📊 Stock: {product.get('stock', 0)}\n"
        f"📌 Trạng thái: {status}"
        f"{promo}"
        f"{guide}"
    )


@router.message(Command("products"))
async def cmd_products(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    products = await product_repo.get_all_admin()
    if not products:
        await message.answer("🚫 Chưa có sản phẩm nào.")
        return
    await message.answer(
        "📋 QUẢN LÝ SẢN PHẨM\n\nChọn sản phẩm để quản lý:",
        reply_markup=admin_all_products_kb(products),
    )


@router.callback_query(F.data == "aproduct:back")
async def aproduct_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    products = await product_repo.get_all_admin()
    if not products:
        await callback.message.edit_text("🚫 Chưa có sản phẩm nào.")
        return
    await callback.message.edit_text(
        "📋 QUẢN LÝ SẢN PHẨM\n\nChọn sản phẩm để quản lý:",
        reply_markup=admin_all_products_kb(products),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("aproduct:") & ~F.data.in_({"aproduct:back"}))
async def aproduct_detail(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    product_id = int(callback.data.split(":")[1])
    product = await product_repo.get_by_id(product_id)
    if not product:
        await callback.answer("Sản phẩm không tồn tại!", show_alert=True)
        return
    await callback.message.edit_text(
        _product_detail_text(product),
        parse_mode="HTML",
        reply_markup=admin_product_manage_kb(product),
    )
    await callback.answer()


# ── Toggle active ────────────────────────────────────────

@router.callback_query(F.data.startswith("aptoggle:"))
async def aptoggle(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    product = await product_repo.get_by_id(product_id)
    if not product:
        await callback.answer("Sản phẩm không tồn tại!", show_alert=True)
        return
    new_active = not product.get("active", True)
    await product_repo.update_product(product_id, {"active": new_active})
    product["active"] = new_active
    status_text = "mở bán" if new_active else "tạm dừng"
    logger.info(f"admin toggle product={product_id} active={new_active}")
    await callback.message.edit_text(
        _product_detail_text(product),
        parse_mode="HTML",
        reply_markup=admin_product_manage_kb(product),
    )
    await callback.answer(f"Đã {status_text} sản phẩm!", show_alert=False)


# ── Delete (soft) ────────────────────────────────────────

@router.callback_query(F.data.startswith("apdelete:"))
async def apdelete_ask(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    product = await product_repo.get_by_id(product_id)
    if not product:
        await callback.answer("Sản phẩm không tồn tại!", show_alert=True)
        return
    await callback.message.edit_text(
        f"⚠️ Bạn có chắc muốn xóa sản phẩm <b>{product['name']}</b>?\n\n"
        f"Sản phẩm sẽ bị ẩn khỏi danh sách và không thể khôi phục.",
        parse_mode="HTML",
        reply_markup=admin_delete_confirm_kb(product_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("apdelete_yes:"))
async def apdelete_confirm(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    product = await product_repo.get_by_id(product_id)
    name = product["name"] if product else f"#{product_id}"
    await product_repo.soft_delete(product_id)
    logger.info(f"admin soft_delete product={product_id}")
    products = await product_repo.get_all_admin()
    if products:
        await callback.message.edit_text(
            f"✅ Đã xóa sản phẩm <b>{name}</b>.\n\n"
            f"📋 QUẢN LÝ SẢN PHẨM\n\nChọn sản phẩm để quản lý:",
            parse_mode="HTML",
            reply_markup=admin_all_products_kb(products),
        )
    else:
        await callback.message.edit_text(
            f"✅ Đã xóa sản phẩm <b>{name}</b>.\n\n🚫 Không còn sản phẩm nào.",
            parse_mode="HTML",
        )
    await callback.answer()


# ── Edit name ────────────────────────────────────────────

@router.callback_query(F.data.startswith("apedit_name:"))
async def apedit_name_start(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    await state.set_state(AdminEditProduct.enter_name)
    await state.update_data(edit_product_id=product_id)
    product = await product_repo.get_by_id(product_id)
    await callback.message.edit_text(
        f"✏️ Sửa tên sản phẩm <b>{product['name']}</b>\n\nNhập tên mới:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminEditProduct.enter_name)
async def apedit_name_done(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data["edit_product_id"]
    new_name = message.text.strip()
    await product_repo.update_product(product_id, {"name": new_name})
    await state.clear()
    product = await product_repo.get_by_id(product_id)
    logger.info(f"admin edit_name product={product_id} new={new_name}")
    await message.answer(
        f"✅ Đã đổi tên!\n\n{_product_detail_text(product)}",
        parse_mode="HTML",
        reply_markup=admin_product_manage_kb(product),
    )


# ── Edit price ───────────────────────────────────────────

@router.callback_query(F.data.startswith("apedit_price:"))
async def apedit_price_start(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    await state.set_state(AdminEditProduct.enter_price)
    await state.update_data(edit_product_id=product_id)
    product = await product_repo.get_by_id(product_id)
    await callback.message.edit_text(
        f"💰 Sửa giá sản phẩm <b>{product['name']}</b>\n"
        f"Giá hiện tại: {product['price']:,}đ\n\nNhập giá mới (VNĐ):",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminEditProduct.enter_price)
async def apedit_price_done(message: Message, state: FSMContext):
    text = message.text.strip().replace(",", "")
    if not text.isdigit() or int(text) <= 0:
        await message.answer("⚠️ Nhập giá hợp lệ:")
        return
    data = await state.get_data()
    product_id = data["edit_product_id"]
    new_price = int(text)
    await product_repo.update_product(product_id, {"price": new_price})
    await state.clear()
    product = await product_repo.get_by_id(product_id)
    logger.info(f"admin edit_price product={product_id} new={new_price}")
    await message.answer(
        f"✅ Đã đổi giá!\n\n{_product_detail_text(product)}",
        parse_mode="HTML",
        reply_markup=admin_product_manage_kb(product),
    )


# ── Edit promo ───────────────────────────────────────────

@router.callback_query(F.data.startswith("apedit_promo:"))
async def apedit_promo_start(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    await state.set_state(AdminEditProduct.enter_promo_buy)
    await state.update_data(edit_product_id=product_id)
    product = await product_repo.get_by_id(product_id)
    current = ""
    if product.get("promo_buy") and product.get("promo_bonus"):
        current = f"\nHiện tại: mua {product['promo_buy']} tặng {product['promo_bonus']}"
    await callback.message.edit_text(
        f"🎁 Sửa KM sản phẩm <b>{product['name']}</b>{current}\n\n"
        f"Nhập số lượng mua để KM (gửi 0 để tắt KM):",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminEditProduct.enter_promo_buy)
async def apedit_promo_buy_done(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("⚠️ Nhập số hợp lệ:")
        return
    val = int(text)
    data = await state.get_data()
    product_id = data["edit_product_id"]
    if val <= 0:
        await product_repo.update_product(product_id, {"promo_buy": None, "promo_bonus": None})
        await state.clear()
        product = await product_repo.get_by_id(product_id)
        logger.info(f"admin edit_promo product={product_id} disabled")
        await message.answer(
            f"✅ Đã tắt khuyến mãi!\n\n{_product_detail_text(product)}",
            parse_mode="HTML",
            reply_markup=admin_product_manage_kb(product),
        )
    else:
        await state.update_data(new_promo_buy=val)
        await state.set_state(AdminEditProduct.enter_promo_bonus)
        await message.answer(f"🎁 Mua {val} thì tặng bao nhiêu?")


@router.message(AdminEditProduct.enter_promo_bonus)
async def apedit_promo_bonus_done(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("⚠️ Nhập số hợp lệ:")
        return
    data = await state.get_data()
    product_id = data["edit_product_id"]
    promo_buy = data["new_promo_buy"]
    promo_bonus = int(text)
    await product_repo.update_product(product_id, {"promo_buy": promo_buy, "promo_bonus": promo_bonus})
    await state.clear()
    product = await product_repo.get_by_id(product_id)
    logger.info(f"admin edit_promo product={product_id} buy={promo_buy} bonus={promo_bonus}")
    await message.answer(
        f"✅ Đã cập nhật KM!\n\n{_product_detail_text(product)}",
        parse_mode="HTML",
        reply_markup=admin_product_manage_kb(product),
    )


# ── Edit guide ───────────────────────────────────────────

@router.callback_query(F.data.startswith("apedit_guide:"))
async def apedit_guide_start(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    await state.set_state(AdminEditProduct.enter_guide)
    await state.update_data(edit_product_id=product_id)
    product = await product_repo.get_by_id(product_id)
    current = product.get("guide") or "(chưa có)"
    await callback.message.edit_text(
        f"📖 Sửa HDSD sản phẩm <b>{product['name']}</b>\n\n"
        f"Hiện tại:\n{current}\n\n"
        f"Nhập hướng dẫn mới (gửi 0 để xóa HDSD):",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminEditProduct.enter_guide)
async def apedit_guide_done(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data["edit_product_id"]
    text = message.text.strip()
    new_guide = None if text == "0" else text
    await product_repo.update_product(product_id, {"guide": new_guide})
    await state.clear()
    product = await product_repo.get_by_id(product_id)
    logger.info(f"admin edit_guide product={product_id}")
    await message.answer(
        f"✅ Đã cập nhật HDSD!\n\n{_product_detail_text(product)}",
        parse_mode="HTML",
        reply_markup=admin_product_manage_kb(product),
    )


# ── Edit stock (from /products) ──────────────────────────

@router.callback_query(F.data.startswith("apedit_stock:"))
async def apedit_stock_start(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    await state.set_state(AdminEditProduct.enter_keys)
    await state.update_data(edit_product_id=product_id)
    product = await product_repo.get_by_id(product_id)
    current = await inventory_repo.count_available(product_id)
    await callback.message.edit_text(
        f"📦 Thêm stock cho <b>{product['name']}</b>\n"
        f"📊 Stock hiện tại: {current}\n\n"
        f"Gửi danh sách key/account (mỗi dòng 1 cái):",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminEditProduct.enter_keys)
async def apedit_stock_done(message: Message, state: FSMContext):
    data = await state.get_data()
    lines = [line.strip() for line in message.text.strip().split("\n") if line.strip()]
    if not lines:
        await message.answer("⚠️ Danh sách trống. Gửi lại:")
        return

    product_id = data["edit_product_id"]
    count = await inventory_repo.add_items(product_id, lines)
    await product_repo.update_stock(product_id, count)
    await state.clear()
    product = await product_repo.get_by_id(product_id)
    logger.info(f"admin add_stock_inline product={product_id} count={count}")
    await message.answer(
        f"✅ Đã thêm {count} key!\n\n{_product_detail_text(product)}",
        parse_mode="HTML",
        reply_markup=admin_product_manage_kb(product),
    )


# ── /addstock ────────────────────────────────────────────

@router.message(Command("addstock"))
async def cmd_add_stock(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    products = await product_repo.get_all_active()
    if not products:
        await message.answer("🚫 Chưa có sản phẩm nào.")
        return
    await state.set_state(AdminAddStock.select_product)
    await message.answer(
        "📦 Chọn sản phẩm để thêm stock:",
        reply_markup=admin_product_list_kb(products),
    )


@router.callback_query(AdminAddStock.select_product, F.data.startswith("astock:"))
async def as_select_product(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    await state.update_data(product_id=product_id)
    await state.set_state(AdminAddStock.enter_keys)
    product = await product_repo.get_by_id(product_id)
    current = await inventory_repo.count_available(product_id)
    await callback.message.edit_text(
        f"📦 Sản phẩm: {product['name']}\n"
        f"📊 Stock hiện tại: {current}\n\n"
        f"Gửi danh sách key/account (mỗi dòng 1 cái):"
    )
    await callback.answer()


@router.message(AdminAddStock.enter_keys)
async def as_enter_keys(message: Message, state: FSMContext):
    data = await state.get_data()
    lines = [line.strip() for line in message.text.strip().split("\n") if line.strip()]
    if not lines:
        await message.answer("⚠️ Danh sách trống. Gửi lại:")
        return

    product_id = data["product_id"]
    count = await inventory_repo.add_items(product_id, lines)
    await product_repo.update_stock(product_id, count)
    await state.clear()
    await message.answer(f"✅ Đã thêm {count} key vào kho!")
    logger.info(f"admin add_stock product={product_id} count={count}")


# ── /orders ──────────────────────────────────────────────

@router.message(Command("orders"))
async def cmd_orders(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()

    args = message.text.split(maxsplit=1)
    status_filter = args[1].upper() if len(args) > 1 else None

    orders = await order_repo.get_recent_orders(limit=20, status=status_filter)
    if not orders:
        await message.answer("📭 Không có đơn hàng nào.")
        return

    lines = ["📋 ĐƠN HÀNG GẦN ĐÂY\n"]
    for o in orders:
        created = o["created_at"].strftime("%d/%m %H:%M") if o.get("created_at") else "?"
        lines.append(
            f"• {o['_id']} | {o['status']} | {o['amount']:,}đ | {o.get('pay_method', '?')} | {created}"
        )
    await message.answer("\n".join(lines))


# ── /users ───────────────────────────────────────────────

@router.message(Command("users"))
async def cmd_users(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()

    total = await user_repo.count_users()
    users = await user_repo.get_all_users()
    lines = [f"👥 USERS ({total})\n"]
    for u in users[:30]:
        uname = u.get("username") or "?"
        lines.append(f"• {u['tg_user_id']} | @{uname} | 👛 {u.get('balance', 0):,}đ")
    if total > 30:
        lines.append(f"\n... và {total - 30} users khác.")
    await message.answer("\n".join(lines))


# ── /broadcast ───────────────────────────────────────────

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await state.set_state(AdminBroadcast.enter_message)
    await message.answer("📢 Nhập nội dung tin nhắn broadcast:")


@router.message(AdminBroadcast.enter_message)
async def broadcast_send(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("⚠️ Nội dung trống. Nhập lại:")
        return

    users = await user_repo.get_all_users()
    await state.clear()

    from bot.bot import bot

    success = 0
    fail = 0
    for u in users:
        try:
            await bot.send_message(u["tg_user_id"], text)
            success += 1
        except Exception:
            fail += 1

    await message.answer(
        f"📢 Broadcast hoàn tất!\n\n"
        f"✅ Thành công: {success}\n"
        f"❌ Thất bại: {fail}"
    )
    logger.info(f"admin broadcast success={success} fail={fail}")
