"""Обработчики тренировки."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import Database

db = Database()


async def start_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало тренировки."""
    user_id = update.effective_user.id
    
    # Получаем случайное слово
    word_data = db.get_random_word(user_id)
    
    if not word_data:
        await update.message.reply_text(
            "📭 У тебя пока нет слов для тренировки.\n"
            "Сначала добавь несколько слов!"
        )
        return
    
    word_id, word, translation, example, phonetic = word_data
    
    # Сохраняем данные для проверки ответа
    context.user_data["training"] = {
        "word_id": word_id,
        "word": word,
        "translation": translation,
        "example": example,
        "phonetic": phonetic
    }
    
    # Кнопки для тренировки
    keyboard = [
        [InlineKeyboardButton("👀 Показать ответ", callback_data="show_answer")],
        [
            InlineKeyboardButton("✅ Знаю", callback_data="know"),
            InlineKeyboardButton("❌ Не знаю", callback_data="dont_know")
        ],
        [InlineKeyboardButton("⏭ Пропустить", callback_data="skip")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎯 **Тренировка**\n\n"
        f"Как переводится слово:\n\n"
        f"*{word}*",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def handle_training_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответа в тренировке (через callback)."""
    query = update.callback_query
    await query.answer()
    
    training_data = context.user_data.get("training")
    
    if not training_data:
        await query.edit_message_text("⚠️ Сессия тренировки истекла. Начни заново: /train")
        return
    
    action = query.data
    word_id = training_data["word_id"]
    word = training_data["word"]
    translation = training_data["translation"]
    example = training_data.get("example", "")
    
    if action == "show_answer":
        # Показываем ответ
        keyboard = [
            [
                InlineKeyboardButton("✅ Знал", callback_data="know"),
                InlineKeyboardButton("❌ Не знал", callback_data="dont_know")
            ],
            [InlineKeyboardButton("➡️ Следующее слово", callback_data="next")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        answer_text = f"*{word}* — {translation}"
        if example:
            answer_text += f"\n\n📝 Пример: _{example}_"
        
        await query.edit_message_text(
            f"📖 **Ответ:**\n\n{answer_text}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    elif action == "know":
        # Пользователь знал слово
        db.update_word_stats(word_id, is_correct=True)
        await send_next_word(query, context, "✅ Отлично! Слово засчитано как выученное.")
    
    elif action == "dont_know":
        # Пользователь не знал слово
        db.update_word_stats(word_id, is_correct=False)
        await send_next_word(query, context, f"📝 Запомни: *{word}* — {translation}")
    
    elif action in ["skip", "next"]:
        # Пропуск или следующее слово
        await send_next_word(query, context)


async def send_next_word(query, context: ContextTypes.DEFAULT_TYPE, message: str = None):
    """Отправка следующего слова для тренировки."""
    user_id = query.from_user.id
    
    # Получаем новое слово
    word_data = db.get_random_word(user_id)
    
    if not word_data:
        final_text = "🎉 Тренировка завершена!\n\n"
        if message:
            final_text = f"{message}\n\n{final_text}"
        final_text += "Добавь ещё слов для продолжения."
        await query.edit_message_text(final_text, parse_mode="Markdown")
        return
    
    word_id, word, translation, example, phonetic = word_data
    
    # Сохраняем данные
    context.user_data["training"] = {
        "word_id": word_id,
        "word": word,
        "translation": translation,
        "example": example,
        "phonetic": phonetic
    }
    
    # Кнопки
    keyboard = [
        [InlineKeyboardButton("👀 Показать ответ", callback_data="show_answer")],
        [
            InlineKeyboardButton("✅ Знаю", callback_data="know"),
            InlineKeyboardButton("❌ Не знаю", callback_data="dont_know")
        ],
        [InlineKeyboardButton("⏭ Пропустить", callback_data="skip")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Формируем текст с транскрипцией
    word_display = f"*{word}*"
    if phonetic:
        word_display += f" `{phonetic}`"
    
    text = f"🎯 **Тренировка**\n\n"
    if message:
        text = f"{message}\n\n" + text
    text += f"Как переводится слово:\n\n{word_display}"
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
