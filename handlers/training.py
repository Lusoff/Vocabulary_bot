"""Обработчики тренировки."""
import re
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from database import Database
from middleware.security import protected

db = Database()

# Состояния для ConversationHandler тренировки (уникальное значение)
WAITING_ANSWER = 100

# Клавиатура во время тренировки
TRAINING_KEYBOARD = ReplyKeyboardMarkup(
    [["⏭ Пропустить", "🛑 Завершить"]],
    resize_keyboard=True
)


def normalize_text(text: str) -> str:
    """Нормализация текста для сравнения (lowercase, убираем лишние символы)."""
    text = text.lower().strip()
    # Убираем часть речи в скобках: "(verb) изменять" -> "изменять"
    text = re.sub(r'^\([^)]+\)\s*', '', text)
    # Убираем знаки препинания и лишние пробелы
    text = re.sub(r'[.,;:!?()"\'\-—]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_russian_words(translation: str) -> list[str]:
    """Извлекает все русские слова/фразы из перевода."""
    # Убираем часть речи в скобках
    text = re.sub(r'^\([^)]+\)\s*', '', translation)
    # Разбиваем по запятым и другим разделителям
    parts = re.split(r'[,;/]', text)
    words = []
    for part in parts:
        cleaned = normalize_text(part)
        if cleaned and len(cleaned) > 1:
            words.append(cleaned)
    return words


def check_answer(user_answer: str, translations: list[str]) -> tuple[bool, str]:
    """
    Проверяет ответ пользователя против всех возможных переводов.
    
    Returns:
        tuple[bool, str]: (правильно ли, правильный ответ для показа)
    """
    user_normalized = normalize_text(user_answer)
    
    all_valid_answers = []
    for translation in translations:
        # Извлекаем все варианты из каждого перевода
        variants = extract_russian_words(translation)
        all_valid_answers.extend(variants)
    
    # Проверяем точное совпадение
    if user_normalized in all_valid_answers:
        return True, ""
    
    # Проверяем частичное совпадение (если ответ содержится в правильном или наоборот)
    for valid in all_valid_answers:
        # Если пользователь ввёл часть правильного ответа (минимум 3 символа)
        if len(user_normalized) >= 3:
            if user_normalized in valid or valid in user_normalized:
                return True, ""
    
    # Неправильный ответ — возвращаем первый вариант для показа
    correct_display = translations[0] if translations else "?"
    return False, correct_display


@protected
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
        return ConversationHandler.END
    
    word_id, word, translation, definition, example, phonetic = word_data
    
    # Получаем ВСЕ переводы этого слова из базы
    all_translations = db.get_all_translations_for_word(user_id, word)
    word_ids = db.get_word_ids_by_word(user_id, word)
    
    # Сохраняем данные для проверки ответа
    context.user_data["training"] = {
        "word_ids": word_ids,  # Все id записей этого слова
        "word": word,
        "translations": all_translations,  # Все возможные переводы
        "definition": definition,
        "example": example,
        "phonetic": phonetic,
        "correct_count": 0,
        "total_count": 0,
    }
    
    # Формируем текст с транскрипцией
    word_display = f"*{word}*"
    if phonetic:
        word_display += f" `{phonetic}`"
    
    await update.message.reply_text(
        f"🎯 *Тренировка*\n\n"
        f"Напиши перевод слова:\n\n"
        f"{word_display}\n\n"
        f"_Введи ответ на русском языке:_",
        parse_mode="Markdown",
        reply_markup=TRAINING_KEYBOARD
    )
    
    return WAITING_ANSWER


async def check_training_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка ответа пользователя в тренировке."""
    user_answer = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Проверка на команды управления
    if user_answer == "⏭ Пропустить":
        return await skip_word(update, context)
    elif user_answer == "🛑 Завершить":
        return await end_training(update, context)
    
    training_data = context.user_data.get("training")
    
    if not training_data:
        await update.message.reply_text("⚠️ Сессия тренировки истекла. Начни заново: /train")
        return ConversationHandler.END
    
    word = training_data["word"]
    translations = training_data["translations"]
    definition = training_data.get("definition", "")
    word_ids = training_data["word_ids"]
    
    # Проверяем ответ
    is_correct, correct_answer = check_answer(user_answer, translations)
    
    # Обновляем статистику
    training_data["total_count"] = training_data.get("total_count", 0) + 1
    
    if is_correct:
        training_data["correct_count"] = training_data.get("correct_count", 0) + 1
        # Обновляем статистику для всех записей этого слова
        for wid in word_ids:
            db.update_word_stats(wid, is_correct=True)
        
        result_text = f"✅ *Правильно!*\n\n*{word}*"
        if translations:
            result_text += f"\n🇷🇺 {translations[0]}"
        if definition:
            result_text += f"\n🇬🇧 _{definition}_"
    else:
        # Обновляем статистику для всех записей этого слова
        for wid in word_ids:
            db.update_word_stats(wid, is_correct=False)
        
        result_text = f"❌ *Неправильно*\n\n"
        result_text += f"Твой ответ: _{user_answer}_\n\n"
        result_text += f"*{word}*"
        if translations:
            result_text += f"\n🇷🇺 {translations[0]}"
        if definition:
            result_text += f"\n🇬🇧 _{definition}_"
    
    # Показываем результат и следующее слово
    await update.message.reply_text(result_text, parse_mode="Markdown")
    
    # Отправляем следующее слово
    return await send_next_training_word(update, context)


async def skip_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск слова."""
    training_data = context.user_data.get("training", {})
    word = training_data.get("word", "?")
    translations = training_data.get("translations", [])
    definition = training_data.get("definition", "")
    
    skip_text = f"⏭ *Пропущено*\n\n*{word}*"
    if translations:
        skip_text += f"\n🇷🇺 {translations[0]}"
    if definition:
        skip_text += f"\n🇬🇧 _{definition}_"
    
    await update.message.reply_text(skip_text, parse_mode="Markdown")
    
    return await send_next_training_word(update, context)


async def send_next_training_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка следующего слова для тренировки."""
    user_id = update.effective_user.id
    
    # Сохраняем счётчики
    old_training = context.user_data.get("training", {})
    correct_count = old_training.get("correct_count", 0)
    total_count = old_training.get("total_count", 0)
    
    # Получаем новое слово
    word_data = db.get_random_word(user_id)
    
    if not word_data:
        return await end_training(update, context)
    
    word_id, word, translation, definition, example, phonetic = word_data
    
    # Получаем ВСЕ переводы этого слова
    all_translations = db.get_all_translations_for_word(user_id, word)
    word_ids = db.get_word_ids_by_word(user_id, word)
    
    # Сохраняем данные
    context.user_data["training"] = {
        "word_ids": word_ids,
        "word": word,
        "translations": all_translations,
        "definition": definition,
        "example": example,
        "phonetic": phonetic,
        "correct_count": correct_count,
        "total_count": total_count,
    }
    
    # Формируем текст
    word_display = f"*{word}*"
    if phonetic:
        word_display += f" `{phonetic}`"
    
    stats_text = f"📊 {correct_count}/{total_count}" if total_count > 0 else ""
    
    await update.message.reply_text(
        f"🎯 *Тренировка* {stats_text}\n\n"
        f"Напиши перевод слова:\n\n"
        f"{word_display}",
        parse_mode="Markdown",
        reply_markup=TRAINING_KEYBOARD
    )
    
    return WAITING_ANSWER


async def end_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение тренировки."""
    from handlers.commands import MAIN_KEYBOARD
    
    user_id = update.effective_user.id
    training_data = context.user_data.get("training", {})
    correct_count = training_data.get("correct_count", 0)
    total_count = training_data.get("total_count", 0)
    
    if total_count > 0:
        accuracy = round(correct_count / total_count * 100)
        
        # Сохраняем результат тренировки в БД
        db.save_training_session(user_id, total_count, correct_count)
        
        if accuracy >= 80:
            emoji = "🏆"
            comment = "Отличный результат!"
        elif accuracy >= 60:
            emoji = "👍"
            comment = "Хорошо! Продолжай в том же духе!"
        elif accuracy >= 40:
            emoji = "📚"
            comment = "Есть над чем поработать."
        else:
            emoji = "💪"
            comment = "Не сдавайся! Повторение — мать учения."
        
        result_text = (
            f"🛑 *Тренировка завершена!*\n\n"
            f"{emoji} Результат: *{correct_count}/{total_count}* ({accuracy}%)\n\n"
            f"{comment}"
        )
    else:
        result_text = "🛑 *Тренировка завершена!*\n\nДо встречи!"
    
    # Очищаем данные тренировки
    context.user_data.pop("training", None)
    
    await update.message.reply_text(
        result_text,
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD
    )
    
    return ConversationHandler.END


async def cancel_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена тренировки."""
    return await end_training(update, context)


# Для обратной совместимости с callback-кнопками (если остались старые сообщения)
async def handle_training_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка старых callback-кнопок тренировки."""
    query = update.callback_query
    await query.answer("Начни новую тренировку: /train", show_alert=True)
