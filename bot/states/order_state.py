from aiogram.fsm.state import State, StatesGroup


class OrderState(StatesGroup):
    select_product = State()
    enter_qty = State()
    confirm = State()
    wait_payment = State()


class TopupState(StatesGroup):
    enter_amount = State()


class AdminAddProduct(StatesGroup):
    enter_name = State()
    enter_price = State()
    enter_promo_buy = State()
    enter_promo_bonus = State()
    enter_guide = State()


class AdminAddStock(StatesGroup):
    select_product = State()
    enter_keys = State()


class AdminEditProduct(StatesGroup):
    enter_name = State()
    enter_price = State()
    enter_promo_buy = State()
    enter_promo_bonus = State()
    enter_guide = State()
    enter_keys = State()


class AdminBroadcast(StatesGroup):
    enter_message = State()
