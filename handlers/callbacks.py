"""Обработчики callback-кнопок."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import Database
from services import DictionaryService
from middleware.security import protected
from .training import handle_training_answer

db = Database()
dictionary = DictionaryService()


@protected
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
    
    # Пагинация "Мои слова"
    if data.startswith("words_page:"):
        await words_page_callback(update, context)
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
        # Получаем переводы для этой части речи
        translations = pos.translations_ru if hasattr(pos, 'translations_ru') else []
        translation_str = ", ".join(translations) if translations else ""
        
        for defn in pos.definitions[:3]:  # Максимум 3 значения на часть речи
            meanings.append({
                "pos": pos.part_of_speech,
                "definition": defn.definition,
                "example": defn.example,
                "translation_ru": translation_str,  # Общий перевод для части речи
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
        # Показываем определение на английском + перевод если есть
        text_lines.append(f"\n{i+1}. {pos_emoji} *{m['pos']}*")
        text_lines.append(f"   🇬🇧 {m['definition'][:100]}")
        if m.get("translation_ru"):
            text_lines.append(f"   🇷🇺 _{m['translation_ru'][:80]}_")
        if m.get("example"):
            text_lines.append(f"   💬 _{m['example'][:80]}_")
    
    # Создаём кнопки для выбора — показываем английское определение (уникальное)
    keyboard = []
    for i, m in enumerate(meanings[:8]):  # Максимум 8 кнопок
        pos_emoji = _get_pos_emoji(m["pos"])
        # В кнопке показываем английское определение (оно уникальное для каждого значения)
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
    limit_error = ""
    
    if choice == "all":
        # Сохраняем все значения
        for m in meanings:
            # Русский перевод
            translation = f"({m['pos']}) {m['translation_ru']}" if m.get("translation_ru") else f"({m['pos']})"
            # Английское определение
            definition = m.get("definition", "")
            example = m.get("example")
            success, error = db.add_word(user_id, word, translation, definition, example, phonetic)
            if success:
                saved_count += 1
            elif error:
                limit_error = error
                break
    else:
        # Сохраняем одно значение
        idx = int(choice)
        if idx < len(meanings):
            m = meanings[idx]
            # Русский перевод
            translation = f"({m['pos']}) {m['translation_ru']}" if m.get("translation_ru") else f"({m['pos']})"
            # Английское определение
            definition = m.get("definition", "")
            example = m.get("example")
            success, error = db.add_word(user_id, word, translation, definition, example, phonetic)
            if success:
                saved_count += 1
            elif error:
                limit_error = error
    
    if limit_error:
        await query.edit_message_text(
            f"⚠️ {limit_error}\n\n"
            f"Сохранено: {saved_count} значений (до лимита).",
            parse_mode="Markdown"
        )
    elif saved_count > 0:
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


async def words_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пагинация списка слов."""
    query = update.callback_query
    user_id = query.from_user.id
    
    page = int(query.data.split(":")[1])
    words = db.get_user_words(user_id)
    
    # Пагинация: 5 слов на страницу
    PAGE_SIZE = 5
    total = len(words)
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    
    page_words = words[start:end]
    
    text = f"📚 *Твои слова* ({start + 1}-{end} из {total}):\n\n"
    for i, row in enumerate(page_words, start + 1):
        word_id, word, translation, definition, example, shown, correct, phonetic = row
        accuracy = f" ({correct}/{shown})" if shown > 0 else ""
        phonetic_str = f" `{phonetic}`" if phonetic else ""
        
        text += f"{i}. *{word}*{phonetic_str}{accuracy}\n"
        
        # Показываем русский перевод
        if translation:
            short_translation = translation[:80] + "..." if len(translation) > 80 else translation
            text += f"    🇷🇺 _{short_translation}_\n"
        
        # Показываем английское определение
        if definition:
            short_definition = definition[:80] + "..." if len(definition) > 80 else definition
            text += f"    🇬🇧 _{short_definition}_\n"
        
        text += "\n"
    
    # Кнопки пагинации
    keyboard = []
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"words_page:{page - 1}"))
    
    if end < total:
        nav_buttons.append(InlineKeyboardButton("Ещё ➡️", callback_data=f"words_page:{page + 1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
