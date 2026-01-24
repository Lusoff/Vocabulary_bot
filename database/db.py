"""Работа с базой данных SQLite."""
import sqlite3
from datetime import datetime
from typing import Optional

from config import MAX_WORDS_PER_USER


class Database:
    """Класс для работы с базой данных слов."""

    def __init__(self, db_path: str = "vocabulary.db"):
        """Инициализация подключения к БД."""
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self._create_tables()

    def _create_tables(self):
        """Создание таблиц в базе данных."""
        # Таблица пользователей
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица слов
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                word TEXT NOT NULL,
                phonetic TEXT,
                translation TEXT NOT NULL,
                definition TEXT,
                example TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                times_shown INTEGER DEFAULT 0,
                times_correct INTEGER DEFAULT 0,
                last_reviewed TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Таблица сессий тренировок
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                total_questions INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                accuracy REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Добавляем колонку definition если её нет (для совместимости со старой БД)
        try:
            self.cursor.execute("ALTER TABLE words ADD COLUMN definition TEXT")
            self.connection.commit()
        except:
            pass  # Колонка уже существует

        self.connection.commit()

    def add_user(self, user_id: int, username: str, first_name: str):
        """Добавление нового пользователя."""
        self.cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
        """, (user_id, username, first_name))
        self.connection.commit()

    def add_word(self, user_id: int, word: str, translation: str, definition: str = None, example: str = None, phonetic: str = None) -> tuple[bool, str]:
        """
        Добавление нового слова.
        
        Returns:
            tuple[bool, str]: (успех, сообщение об ошибке или пустая строка)
        """
        try:
            # Проверяем лимит слов
            current_count = self.get_word_count(user_id)
            if current_count >= MAX_WORDS_PER_USER:
                return False, f"Достигнут лимит ({MAX_WORDS_PER_USER} слов). Удали старые слова."
            
            self.cursor.execute("""
                INSERT INTO words (user_id, word, translation, definition, example, phonetic)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, word, translation, definition, example, phonetic))
            self.connection.commit()
            return True, ""
        except Exception as e:
            print(f"Ошибка добавления слова: {e}")
            return False, str(e)

    def get_user_words(self, user_id: int, limit: int = None) -> list:
        """Получение всех слов пользователя."""
        query = """
            SELECT id, word, translation, definition, example, times_shown, times_correct, phonetic
            FROM words WHERE user_id = ?
            ORDER BY LOWER(word) ASC
        """
        if limit:
            query += f" LIMIT {limit}"

        self.cursor.execute(query, (user_id,))
        return self.cursor.fetchall()

    def get_word_count(self, user_id: int) -> int:
        """Получение количества слов пользователя."""
        self.cursor.execute("""
            SELECT COUNT(*) FROM words WHERE user_id = ?
        """, (user_id,))
        return self.cursor.fetchone()[0]

    def get_random_word(self, user_id: int) -> Optional[tuple]:
        """Получение случайного слова для тренировки."""
        self.cursor.execute("""
            SELECT id, word, translation, definition, example, phonetic
            FROM words WHERE user_id = ?
            ORDER BY RANDOM() LIMIT 1
        """, (user_id,))
        return self.cursor.fetchone()

    def get_words_for_review(self, user_id: int, limit: int = 10) -> list:
        """Получение слов для повторения (с наименьшим успехом)."""
        self.cursor.execute("""
            SELECT id, word, translation, definition, example, times_shown, times_correct
            FROM words WHERE user_id = ?
            ORDER BY 
                CASE WHEN times_shown = 0 THEN 0 
                ELSE CAST(times_correct AS FLOAT) / times_shown END ASC,
                last_reviewed ASC NULLS FIRST
            LIMIT ?
        """, (user_id, limit))
        return self.cursor.fetchall()

    def update_word_stats(self, word_id: int, is_correct: bool):
        """Обновление статистики слова после тренировки."""
        correct_increment = 1 if is_correct else 0
        self.cursor.execute("""
            UPDATE words
            SET times_shown = times_shown + 1,
                times_correct = times_correct + ?,
                last_reviewed = ?
            WHERE id = ?
        """, (correct_increment, datetime.now(), word_id))
        self.connection.commit()

    def get_all_translations_for_word(self, user_id: int, word: str) -> list[str]:
        """Получение всех переводов для данного слова пользователя."""
        self.cursor.execute("""
            SELECT translation FROM words 
            WHERE user_id = ? AND LOWER(word) = LOWER(?)
        """, (user_id, word))
        rows = self.cursor.fetchall()
        return [row[0] for row in rows]

    def get_word_ids_by_word(self, user_id: int, word: str) -> list[int]:
        """Получение всех id записей для данного слова."""
        self.cursor.execute("""
            SELECT id FROM words 
            WHERE user_id = ? AND LOWER(word) = LOWER(?)
        """, (user_id, word))
        rows = self.cursor.fetchall()
        return [row[0] for row in rows]

    def delete_word(self, word_id: int, user_id: int) -> bool:
        """Удаление слова."""
        self.cursor.execute("""
            DELETE FROM words WHERE id = ? AND user_id = ?
        """, (word_id, user_id))
        self.connection.commit()
        return self.cursor.rowcount > 0

    def get_word_ids_by_word(self, user_id: int, word: str) -> list[int]:
        """Получение всех id записей для слова (может быть несколько с разными переводами)."""
        self.cursor.execute("""
            SELECT id FROM words 
            WHERE user_id = ? AND LOWER(word) = LOWER(?)
        """, (user_id, word))
        return [row[0] for row in self.cursor.fetchall()]

    def save_training_session(self, user_id: int, total_questions: int, correct_answers: int):
        """Сохранение результата тренировки."""
        if total_questions == 0:
            return
        accuracy = round(correct_answers / total_questions * 100, 1)
        self.cursor.execute("""
            INSERT INTO training_sessions (user_id, total_questions, correct_answers, accuracy)
            VALUES (?, ?, ?, ?)
        """, (user_id, total_questions, correct_answers, accuracy))
        self.connection.commit()
    
    def get_last_training(self, user_id: int) -> Optional[dict]:
        """Получение результата последней тренировки."""
        self.cursor.execute("""
            SELECT total_questions, correct_answers, accuracy, created_at
            FROM training_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        row = self.cursor.fetchone()
        if row:
            return {
                "total_questions": row[0],
                "correct_answers": row[1],
                "accuracy": row[2],
                "date": row[3]
            }
        return None
    
    def get_user_stats(self, user_id: int) -> dict:
        """Получение статистики пользователя."""
        # Статистика по словам
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_words,
                SUM(times_shown) as total_reviews,
                SUM(times_correct) as total_correct
            FROM words WHERE user_id = ?
        """, (user_id,))
        row = self.cursor.fetchone()
        
        total_words = row[0] or 0
        total_reviews = row[1] or 0
        total_correct = row[2] or 0
        
        # Общая статистика по всем тренировкам
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_sessions,
                SUM(total_questions) as all_questions,
                SUM(correct_answers) as all_correct
            FROM training_sessions WHERE user_id = ?
        """, (user_id,))
        session_row = self.cursor.fetchone()
        
        total_sessions = session_row[0] or 0
        all_questions = session_row[1] or 0
        all_correct = session_row[2] or 0
        
        return {
            "total_words": total_words,
            "total_reviews": total_reviews,
            "total_correct": total_correct,
            "accuracy": round(total_correct / total_reviews * 100, 1) if total_reviews > 0 else 0,
            "total_sessions": total_sessions,
            "all_questions": all_questions,
            "all_correct": all_correct,
            "overall_accuracy": round(all_correct / all_questions * 100, 1) if all_questions > 0 else 0
        }

    def close(self):
        """Закрытие соединения с БД."""
        self.connection.close()
