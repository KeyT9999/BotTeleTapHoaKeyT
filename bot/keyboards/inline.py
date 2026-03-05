from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def product_list_kb(products: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        label = f"{p['name']} — {p['price']:,}đ"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"product:{p['_id']}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Mua hàng", callback_data="menu:buy")],
        [InlineKeyboardButton(text="💰 Nạp tiền", callback_data="menu:topup")],
        [InlineKeyboardButton(text="👛 Số dư", callback_data="menu:balance")],
    ])


def payment_method_kb(balance: int, amount: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="💳 Thanh toán QR (payOS)", callback_data="pay:payos")],
        [InlineKeyboardButton(
            text=f"👛 Thanh toán bằng ví ({balance:,}đ)",
            callback_data="pay:wallet",
        )],
        [InlineKeyboardButton(text="❌ Hủy", callback_data="pay:cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_order_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Xác nhận", callback_data="confirm:yes"),
            InlineKeyboardButton(text="❌ Hủy", callback_data="confirm:no"),
        ],
    ])


def admin_product_list_kb(products: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        buttons.append([InlineKeyboardButton(text=p["name"], callback_data=f"astock:{p['_id']}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_all_products_kb(products: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        status = "🟢" if p.get("active") else "🔴"
        stock = p.get("stock", 0)
        label = f"{status} {p['name']} — {p['price']:,}đ | Stock: {stock}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"aproduct:{p['_id']}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_product_manage_kb(product: dict) -> InlineKeyboardMarkup:
    pid = product["_id"]
    is_active = product.get("active", True)
    toggle_text = "⏸ Tạm dừng bán" if is_active else "▶️ Mở bán lại"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Sửa tên", callback_data=f"apedit_name:{pid}"),
            InlineKeyboardButton(text="💰 Sửa giá", callback_data=f"apedit_price:{pid}"),
        ],
        [
            InlineKeyboardButton(text="🎁 Sửa KM", callback_data=f"apedit_promo:{pid}"),
            InlineKeyboardButton(text="📖 Sửa HDSD", callback_data=f"apedit_guide:{pid}"),
        ],
        [InlineKeyboardButton(text="📦 Thêm stock", callback_data=f"apedit_stock:{pid}")],
        [InlineKeyboardButton(text=toggle_text, callback_data=f"aptoggle:{pid}")],
        [InlineKeyboardButton(text="🗑 Xóa sản phẩm", callback_data=f"apdelete:{pid}")],
        [InlineKeyboardButton(text="◀️ Quay lại", callback_data="aproduct:back")],
    ])


def admin_delete_confirm_kb(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Xác nhận xóa", callback_data=f"apdelete_yes:{product_id}"),
            InlineKeyboardButton(text="❌ Hủy", callback_data=f"aproduct:{product_id}"),
        ],
    ])
