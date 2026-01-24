"""Работа с базой данных SQLite."""
import sqlite3
from datetime import datetime
from typing import Optional


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
                example TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                times_shown INTEGER DEFAULT 0,
                times_correct INTEGER DEFAULT 0,
                last_reviewed TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        self.connection.commit()

    def add_user(self, user_id: int, username: str, first_name: str):
        """Добавление нового пользователя."""
        self.cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
        """, (user_id, username, first_name))
        self.connection.commit()

    def add_word(self, user_id: int, word: str, translation: str, example: str = None, phonetic: str = None) -> bool:
        """Добавление нового слова."""
        try:
            self.cursor.execute("""
                INSERT INTO words (user_id, word, translation, example, phonetic)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, word, translation, example, phonetic))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Ошибка добавления слова: {e}")
            return False

    def get_user_words(self, user_id: int, limit: int = None) -> list:
        """Получение всех слов пользователя."""
        query = """
            SELECT id, word, translation, example, times_shown, times_correct, phonetic
            FROM words WHERE user_id = ?
            ORDER BY created_at DESC
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
            SELECT id, word, translation, example, phonetic
            FROM words WHERE user_id = ?
            ORDER BY RANDOM() LIMIT 1
        """, (user_id,))
        return self.cursor.fetchone()

    def get_words_for_review(self, user_id: int, limit: int = 10) -> list:
        """Получение слов для повторения (с наименьшим успехом)."""
        self.cursor.execute("""
            SELECT id, word, translation, example, times_shown, times_correct
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

    def delete_word(self, word_id: int, user_id: int) -> bool:
        """Удаление слова."""
        self.cursor.execute("""
            DELETE FROM words WHERE id = ? AND user_id = ?
        """, (word_id, user_id))
        self.connection.commit()
        return self.cursor.rowcount > 0

    def get_user_stats(self, user_id: int) -> dict:
        """Получение статистики пользователя."""
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
        
        return {
            "total_words": total_words,
            "total_reviews": total_reviews,
            "total_correct": total_correct,
            "accuracy": round(total_correct / total_reviews * 100, 1) if total_reviews > 0 else 0
        }

    def close(self):
        """Закрытие соединения с БД."""
        self.connection.close()
