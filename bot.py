"""
Vocabulary Bot — бот для изучения новых слов.

Запуск: python bot.py
"""
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)

from config import BOT_TOKEN
from handlers.commands import (
    start,
    help_command,
    find_word,
    lookup_word,
    cancel_search,
    my_words,
    stats,
    WAITING_WORD,
    MAIN_KEYBOARD
)
from handlers.training import (
    start_training, 
    check_training_answer, 
    cancel_training,
    handle_training_answer,
    WAITING_ANSWER
)
from handlers.callbacks import button_callback
from middleware.security import protected

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


@protected
async def handle_text(update, context):
    """Обработка текстовых сообщений (кнопки главного меню)."""
    text = update.message.text
    
    if text == "📚 Мои слова":
        await my_words(update, context)
    elif text == "🔍 Найти слово":
        return await find_word(update, context)
    elif text == "🎯 Тренировка":
        return await start_training(update, context)
    elif text == "📊 Статистика":
        await stats(update, context)
    elif text == "❓ Помощь":
        await help_command(update, context)
    else:
        # Любой другой текст — ищем как слово
        return await lookup_word(update, context)


def main():
    """Запуск бота."""
    # Создаём приложение с увеличенным таймаутом
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .build()
    )
    
    # Обработчик поиска слова (ConversationHandler)
    search_word_handler = ConversationHandler(
        entry_points=[
            CommandHandler("find", find_word),
            MessageHandler(filters.Regex("^🔍 Найти слово$"), find_word)
        ],
        states={
            WAITING_WORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, lookup_word)],
        },
        fallbacks=[CommandHandler("cancel", cancel_search)],
        name="search_conversation",
        persistent=False,
    )
    
    # Обработчик тренировки (ConversationHandler)
    training_handler = ConversationHandler(
        entry_points=[
            CommandHandler("train", start_training),
            MessageHandler(filters.Regex("^🎯 Тренировка$"), start_training)
        ],
        states={
            WAITING_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_training_answer)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_training),
            MessageHandler(filters.Regex("^🛑 Завершить$"), cancel_training),
        ],
        name="training_conversation",
        persistent=False,
    )
    
    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("words", my_words))
    app.add_handler(CommandHandler("stats", stats))
    
    # Обработчик поиска слова
    app.add_handler(search_word_handler)
    
    # Обработчик тренировки
    app.add_handler(training_handler)
    
    # Обработчик callback-кнопок (включая старые кнопки тренировки)
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик текстовых сообщений (главное меню)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    
    # Запуск бота через webhook
    logger.info("Бот запущен через webhook!")
    app.run_webhook(
        listen="0.0.0.0",
        port=8000,
        webhook_url="https://bots4max.duckdns.org/telegram/webhook",
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
