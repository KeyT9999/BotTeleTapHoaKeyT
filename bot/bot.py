from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


def setup_routers():
    from bot.handlers import start, products, order, payment, wallet, admin
    dp.include_router(start.router)
    dp.include_router(products.router)
    dp.include_router(order.router)
    dp.include_router(payment.router)
    dp.include_router(wallet.router)
    dp.include_router(admin.router)
