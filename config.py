"""Конфигурация бота."""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токен бота из BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Yandex Dictionary API Key
YANDEX_DICT_API_KEY = os.getenv("YANDEX_DICT_API_KEY")

# Проверка наличия токена
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден! Создайте файл .env с токеном бота.")

# ========== ЗАЩИТА ОТ ЗЛОУПОТРЕБЛЕНИЙ ==========

# Rate limiting (ограничение частоты запросов)
RATE_LIMIT_MESSAGES = int(os.getenv("RATE_LIMIT_MESSAGES", "10"))  # сообщений
RATE_LIMIT_SECONDS = int(os.getenv("RATE_LIMIT_SECONDS", "60"))    # за N секунд

# Максимум слов в базе на пользователя
MAX_WORDS_PER_USER = int(os.getenv("MAX_WORDS_PER_USER", "1000"))

# Белый список user_id (если пуст — доступ всем)
# Формат: "123456,789012,345678"
ALLOWED_USERS = os.getenv("ALLOWED_USERS", "")
ALLOWED_USER_IDS = set(int(x) for x in ALLOWED_USERS.split(",") if x.strip())

# Чёрный список user_id
BANNED_USERS = os.getenv("BANNED_USERS", "")
BANNED_USER_IDS = set(int(x) for x in BANNED_USERS.split(",") if x.strip())

# Максимальная длина слова для поиска
MAX_WORD_LENGTH = int(os.getenv("MAX_WORD_LENGTH", "50"))
