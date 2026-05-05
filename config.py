import os
from dotenv import load_dotenv

load_dotenv()

class config:
    TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN', '')
    DB_HOST: str = os.getenv('DB_HOST', '')
    DB_NAME: str = os.getenv('DB_NAME', '')
    DB_USER: str = os.getenv('DB_USER', '')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', '')
    DB_PORT: str = os.getenv('DB_PORT', '')