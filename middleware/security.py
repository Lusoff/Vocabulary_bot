"""
Middleware для защиты бота от злоупотреблений.
"""
import time
import logging
from collections import defaultdict
from functools import wraps
from telegram import Update

from config import (
    RATE_LIMIT_MESSAGES,
    RATE_LIMIT_SECONDS,
    ALLOWED_USER_IDS,
    BANNED_USER_IDS,
    MAX_WORD_LENGTH,
)

logger = logging.getLogger(__name__)

# Хранилище для rate limiting: {user_id: [timestamp1, timestamp2, ...]}
_user_requests: dict[int, list[float]] = defaultdict(list)

# Счётчик заблокированных запросов для статистики
_blocked_requests: dict[int, int] = defaultdict(int)


def is_rate_limited(user_id: int) -> bool:
    """Проверяет, превысил ли пользователь лимит запросов."""
    now = time.time()
    window_start = now - RATE_LIMIT_SECONDS
    
    # Удаляем старые запросы за пределами окна
    _user_requests[user_id] = [
        ts for ts in _user_requests[user_id] if ts > window_start
    ]
    
    # Проверяем количество запросов в окне
    if len(_user_requests[user_id]) >= RATE_LIMIT_MESSAGES:
        _blocked_requests[user_id] += 1
        return True
    
    # Добавляем текущий запрос
    _user_requests[user_id].append(now)
    return False


def is_user_allowed(user_id: int) -> bool:
    """Проверяет, разрешён ли доступ пользователю."""
    # Проверяем чёрный список
    if user_id in BANNED_USER_IDS:
        return False
    
    # Если белый список пуст — разрешаем всем
    if not ALLOWED_USER_IDS:
        return True
    
    # Проверяем белый список
    return user_id in ALLOWED_USER_IDS


def validate_word(word: str) -> tuple[bool, str]:
    """Валидация слова перед поиском."""
    if not word:
        return False, "Слово не может быть пустым."
    
    if len(word) > MAX_WORD_LENGTH:
        return False, f"Слово слишком длинное (макс. {MAX_WORD_LENGTH} символов)."
    
    # Проверяем на подозрительные символы (инъекции)
    suspicious_chars = ['<', '>', '{', '}', '`', '$', '\\']
    if any(char in word for char in suspicious_chars):
        return False, "Слово содержит недопустимые символы."
    
    return True, ""


def protected(func):
    """
    Декоратор для защиты обработчиков.
    Проверяет: доступ пользователя + rate limiting.
    """
    @wraps(func)
    async def wrapper(update: Update, context, *args, **kwargs):
        # Получаем user_id
        user = update.effective_user
        if not user:
            return
        
        user_id = user.id
        
        # Проверяем доступ
        if not is_user_allowed(user_id):
            logger.warning(f"Заблокирован доступ для user_id={user_id}")
            if update.message:
                await update.message.reply_text(
                    "⛔ Доступ запрещён."
                )
            return
        
        # Проверяем rate limit
        if is_rate_limited(user_id):
            logger.warning(f"Rate limit для user_id={user_id}")
            if update.message:
                await update.message.reply_text(
                    f"⏳ Слишком много запросов. "
                    f"Подождите {RATE_LIMIT_SECONDS} секунд."
                )
            return
        
        # Выполняем оригинальную функцию
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def get_security_stats() -> dict:
    """Возвращает статистику безопасности."""
    return {
        "active_users": len(_user_requests),
        "blocked_requests": dict(_blocked_requests),
        "total_blocked": sum(_blocked_requests.values()),
    }


def cleanup_old_data():
    """Очистка старых данных (вызывать периодически)."""
    now = time.time()
    window_start = now - RATE_LIMIT_SECONDS * 2
    
    # Удаляем пользователей без активности
    inactive_users = [
        user_id for user_id, timestamps in _user_requests.items()
        if not timestamps or max(timestamps) < window_start
    ]
    
    for user_id in inactive_users:
        del _user_requests[user_id]
