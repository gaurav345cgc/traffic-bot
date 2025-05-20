import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

HEADLESS = os.getenv("HEADLESS", "True").lower() == "true"
PROXY_LIST = os.getenv("PROXY_LIST", "proxies.txt")
TIMEOUT = int(os.getenv("TIMEOUT", 10))
LOG_FILE = os.getenv("LOG_FILE", "logs/bot_log.log")
