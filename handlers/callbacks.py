"""Обработчики callback-кнопок."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import Database
from services import DictionaryService
from .training import handle_training_answer

db = Database()
dictionary = DictionaryService()


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главный обработчик всех callback-кнопок."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Callback'и тренировки
    training_callbacks = ["show_answer", "know", "dont_know", "skip", "next"]
    if data in training_callbacks:
        await handle_training_answer(update, context)
        return
    
    # Сохранение слова
    if data.startswith("save_word:"):
        await save_word_callback(update, context)
        return
    
    # Выбор значения для сохранения
    if data.startswith("save_meaning:"):
        await save_meaning_callback(update, context)
        return
    
    # Аудио произношение
    if data.startswith("audio:"):
        await audio_callback(update, context)
        return
    
    # Искать другое слово
    if data == "search_another":
        await query.edit_message_text(
            "🔍 Введи английское слово для поиска:"
        )
        return
    
    # Отмена
    if data == "cancel":
        await query.edit_message_text("❌ Отменено.")
        return
    
    await query.answer("Неизвестная команда")


async def save_word_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показываем выбор значений для сохранения."""
    query = update.callback_query
    user_id = query.from_user.id
    
    word_data = context.user_data.get("current_word")
    if not word_data:
        await query.edit_message_text("⚠️ Данные устарели. Найди слово заново.")
        return
    
    word = word_data["word"]
    phonetic = word_data.get("phonetic", "")
    parts = word_data["parts_of_speech"]
    
    # Собираем все значения
    meanings = []
    for pos in parts:
        for defn in pos.definitions[:3]:  # Максимум 3 значения на часть речи
            meanings.append({
                "pos": pos.part_of_speech,
                "definition": defn.definition,
                "example": defn.example,
                "translation_ru": defn.translation_ru,
            })
    
    if not meanings:
        await query.edit_message_text("⚠️ Не найдено значений для сохранения.")
        return
    
    # Сохраняем значения в контекст
    context.user_data["meanings_to_save"] = meanings
    
    # Формируем текст со всеми значениями и примерами
    header = f"📝 *{word}*"
    if phonetic:
        header += f" `{phonetic}`"
    header += "\n\nВыбери значение для сохранения:\n"
    
    text_lines = [header]
    for i, m in enumerate(meanings[:8]):
        pos_emoji = _get_pos_emoji(m["pos"])
        # Показываем русский перевод если есть
        if m.get("translation_ru"):
            text_lines.append(f"\n{i+1}. {pos_emoji} *{m['pos']}*")
            text_lines.append(f"   🇷🇺 *{m['translation_ru']}*")
            text_lines.append(f"   🇬🇧 {m['definition'][:100]}")
        else:
            text_lines.append(f"\n{i+1}. {pos_emoji} *{m['pos']}*: {m['definition'][:100]}")
        if m.get("example"):
            text_lines.append(f"   💬 _{m['example'][:80]}_")
    
    # Создаём кнопки для выбора
    keyboard = []
    for i, m in enumerate(meanings[:8]):  # Максимум 8 кнопок
        pos_emoji = _get_pos_emoji(m["pos"])
        # В кнопке показываем русский перевод если есть
        if m.get("translation_ru"):
            btn_text = m["translation_ru"][:35]
        else:
            btn_text = m["definition"][:35]
        if len(btn_text) >= 35:
            btn_text += "..."
        keyboard.append([
            InlineKeyboardButton(
                f"{i+1}. {pos_emoji} {btn_text}", 
                callback_data=f"save_meaning:{i}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("💾 Сохранить все", callback_data="save_meaning:all")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    
    await query.edit_message_text(
        "\n".join(text_lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def save_meaning_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение выбранного значения."""
    query = update.callback_query
    user_id = query.from_user.id
    
    word_data = context.user_data.get("current_word")
    meanings = context.user_data.get("meanings_to_save")
    
    if not word_data or not meanings:
        await query.edit_message_text("⚠️ Данные устарели. Найди слово заново.")
        return
    
    word = word_data["word"]
    phonetic = word_data.get("phonetic", "")
    
    # Какое значение сохранять
    choice = query.data.split(":")[1]
    
    saved_count = 0
    
    if choice == "all":
        # Сохраняем все значения
        for m in meanings:
            # Русский перевод имеет приоритет
            if m.get("translation_ru"):
                translation = f"({m['pos']}) {m['translation_ru']}"
            else:
                translation = f"({m['pos']}) {m['definition']}"
            example = m.get("example")
            if db.add_word(user_id, word, translation, example, phonetic):
                saved_count += 1
    else:
        # Сохраняем одно значение
        idx = int(choice)
        if idx < len(meanings):
            m = meanings[idx]
            # Русский перевод имеет приоритет
            if m.get("translation_ru"):
                translation = f"({m['pos']}) {m['translation_ru']}"
            else:
                translation = f"({m['pos']}) {m['definition']}"
            example = m.get("example")
            if db.add_word(user_id, word, translation, example, phonetic):
                saved_count += 1
    
    if saved_count > 0:
        total = db.get_word_count(user_id)
        await query.edit_message_text(
            f"✅ Сохранено значений: {saved_count}\n\n"
            f"*{word}* добавлено в твой словарь!\n\n"
            f"📚 Всего слов: {total}\n\n"
            f"Отправь ещё слово для поиска или начни /train тренировку!",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка сохранения. Попробуй ещё раз."
        )


async def audio_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка аудио произношения."""
    query = update.callback_query
    
    word_data = context.user_data.get("current_word")
    if not word_data or not word_data.get("phonetic_audio"):
        await query.answer("Аудио недоступно", show_alert=True)
        return
    
    audio_url = word_data["phonetic_audio"]
    
    try:
        await query.message.reply_voice(
            voice=audio_url,
            caption=f"🔊 {word_data['word']}"
        )
        await query.answer("🔊 Аудио отправлено")
    except Exception as e:
        print(f"Audio error: {e}")
        await query.answer("Не удалось загрузить аудио", show_alert=True)


def _get_pos_emoji(pos: str) -> str:
    """Эмодзи для части речи."""
    emojis = {
        "noun": "📦",
        "verb": "⚡",
        "adjective": "🎨",
        "adverb": "💨",
        "pronoun": "👤",
        "preposition": "📍",
        "conjunction": "🔗",
        "interjection": "❗",
    }
    return emojis.get(pos.lower(), "📌")
