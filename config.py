import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "votingbot")

AI_API_URL = os.getenv("AI_API_URL", "")
AI_MODEL = os.getenv("AI_MODEL", "")
AI_API_KEYS = []
_key_index = 1
while True:
    key = os.getenv(f"AI_API_KEY_{_key_index}", "")
    if not key:
        break
    AI_API_KEYS.append(key)
    _key_index += 1

FREE_PLAN_MAX_GIVEAWAYS = 0

QR_IMAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qr", "payment_qr.png")

PURCHASE_COOLDOWN_HOURS = 24
