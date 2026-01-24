"""Основные команды бота."""
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database import Database
from services import DictionaryService
from config import YANDEX_DICT_API_KEY

# Инициализация
db = Database()
dictionary = DictionaryService(yandex_api_key=YANDEX_DICT_API_KEY)

# Состояния для ConversationHandler
WAITING_WORD = 0

# Главная клавиатура
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📚 Мои слова", "🔍 Найти слово"],
        ["🎯 Тренировка", "📊 Статистика"],
        ["❓ Помощь"]
    ],
    resize_keyboard=True
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start."""
    user = update.effective_user
    
    # Сохраняем пользователя в БД
    db.add_user(user.id, user.username, user.first_name)
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот для изучения английских слов. Помогу тебе:

🔍 Искать слова с транскрипцией и переводами
📝 Сохранять слова в свой словарь
🎯 Тренироваться и запоминать
📊 Отслеживать прогресс

*Как начать:*
Просто отправь мне любое английское слово — и я покажу его значения!

Или используй команды:
/find — найти слово
/words — мои слова  
/train — тренировка
/stats — статистика
"""
    
    await update.message.reply_text(
        welcome_text, 
        reply_markup=MAIN_KEYBOARD,
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help."""
    help_text = """
📖 *Как пользоваться ботом:*

*Поиск слова:*
• Просто напиши любое английское слово
• Или нажми "🔍 Найти слово"
• Бот покажет транскрипцию, все значения и примеры
• Нажми "💾 Сохранить" чтобы добавить в словарь

*Что показывает бот:*
• 📖 Транскрипция (как произносится)
• 📦 Noun / ⚡ Verb / 🎨 Adjective — части речи
• 📝 Формы глаголов (past, -ing)
• 💬 Примеры использования
• 🔄 Синонимы

*Тренировка:*
• Нажми "🎯 Тренировка" или /train
• Бот покажет слово — вспомни перевод
• Отмечай знаешь/не знаешь

*Просмотр слов:*
• Нажми "📚 Мои слова" или /words

*Статистика:*
• Нажми "📊 Статистика" или /stats

💡 *Совет:* Добавляй слова с примерами — так легче запомнить!
"""
    
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def find_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало поиска слова."""
    await update.message.reply_text(
        "🔍 Введи английское слово для поиска:"
    )
    return WAITING_WORD


async def lookup_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск слова в словаре."""
    word = update.message.text.strip().lower()
    user_id = update.effective_user.id
    
    # Проверяем, не команда ли это или кнопка меню
    menu_buttons = ["📚 мои слова", "🔍 найти слово", "🎯 тренировка", "📊 статистика", "❓ помощь"]
    if word.startswith("/") or word in menu_buttons:
        return ConversationHandler.END
    
    # Показываем, что ищем
    searching_msg = await update.message.reply_text(f"🔍 Ищу *{word}*...", parse_mode="Markdown")
    
    # Ищем в словаре
    word_info = await dictionary.lookup(word)
    
    if not word_info:
        await searching_msg.edit_text(
            f"❌ Слово *{word}* не найдено в словаре.\n\n"
            f"Проверь правильность написания и попробуй ещё раз.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    # Сохраняем данные для возможного сохранения
    context.user_data["current_word"] = {
        "word": word_info.word,
        "phonetic": word_info.phonetic,
        "parts_of_speech": word_info.parts_of_speech,
        "phonetic_audio": word_info.phonetic_audio,
    }
    
    # Форматируем ответ
    response_text = word_info.format_for_telegram()
    
    # Кнопки действий
    keyboard = [
        [InlineKeyboardButton("💾 Сохранить в словарь", callback_data=f"save_word:{word}")],
    ]
    
    # Если есть аудио — добавляем кнопку
    if word_info.phonetic_audio:
        keyboard.append([InlineKeyboardButton("🔊 Произношение", callback_data=f"audio:{word}")])
    
    keyboard.append([InlineKeyboardButton("🔍 Искать другое слово", callback_data="search_another")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await searching_msg.edit_text(
        response_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END


async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена поиска."""
    await update.message.reply_text(
        "❌ Поиск отменён.",
        reply_markup=MAIN_KEYBOARD
    )
    return ConversationHandler.END


async def my_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список слов пользователя."""
    user_id = update.effective_user.id
    words = db.get_user_words(user_id, limit=20)
    
    if not words:
        await update.message.reply_text(
            "📭 У тебя пока нет сохранённых слов.\n\n"
            "Отправь мне любое английское слово — и я покажу его значения!",
            reply_markup=MAIN_KEYBOARD
        )
        return
    
    text = "📚 *Твои слова:*\n\n"
    for i, row in enumerate(words, 1):
        word_id, word, translation, example, shown, correct, phonetic = row
        accuracy = f" ({correct}/{shown})" if shown > 0 else ""
        phonetic_str = f" `{phonetic}`" if phonetic else ""
        text += f"{i}. *{word}*{phonetic_str}{accuracy}\n"
        # Укорачиваем перевод если слишком длинный
        short_translation = translation[:80] + "..." if len(translation) > 80 else translation
        text += f"    _{short_translation}_\n"
    
    total = db.get_word_count(user_id)
    if total > 20:
        text += f"\n_...и ещё {total - 20} слов_"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику пользователя."""
    user_id = update.effective_user.id
    user_stats = db.get_user_stats(user_id)
    
    if user_stats["total_words"] == 0:
        await update.message.reply_text(
            "📊 Статистика пока пуста.\n\n"
            "Найди и сохрани несколько слов, чтобы начать!"
        )
        return
    
    text = f"""
📊 *Твоя статистика:*

📚 Слов в словаре: {user_stats['total_words']}
🔄 Тренировок: {user_stats['total_reviews']}
✅ Правильных: {user_stats['total_correct']}
🎯 Точность: {user_stats['accuracy']}%
"""
    
    # Мотивационное сообщение
    if user_stats['accuracy'] >= 80:
        text += "\n🌟 Отличный результат! Так держать!"
    elif user_stats['accuracy'] >= 50:
        text += "\n💪 Хороший прогресс! Продолжай тренироваться!"
    elif user_stats['total_reviews'] > 0:
        text += "\n📖 Повторяй слова чаще — и результат улучшится!"
    
    await update.message.reply_text(text, parse_mode="Markdown")
