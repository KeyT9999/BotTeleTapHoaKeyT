from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "telegram_shop")

PAYOS_CLIENT_ID: str = os.getenv("PAYOS_CLIENT_ID", "")
PAYOS_API_KEY: str = os.getenv("PAYOS_API_KEY", "")
PAYOS_CHECKSUM_KEY: str = os.getenv("PAYOS_CHECKSUM_KEY", "")

ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
WEBHOOK_BASE_URL: str = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")

ORDER_EXPIRE_MINUTES: int = 10
