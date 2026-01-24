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
