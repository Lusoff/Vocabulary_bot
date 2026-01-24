#!/bin/bash
# Скрипт для быстрого деплоя Vocabulary Bot на VPS

echo "🚀 Начинаем деплой Vocabulary Bot..."

# Переход в домашнюю директорию
cd /root

# Клонирование репозитория (если еще не клонирован)
if [ ! -d "Vocabulary_bot" ]; then
    echo "📦 Клонирование репозитория..."
    git clone https://github.com/Lusoff/Vocabulary_bot.git
    cd Vocabulary_bot
else
    echo "📦 Обновление репозитория..."
    cd Vocabulary_bot
    git pull origin main
fi

# Проверка наличия .env файла
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден!"
    echo "Создайте файл .env с содержимым:"
    echo ""
    echo "BOT_TOKEN=your_telegram_bot_token"
    echo "YANDEX_DICT_API_KEY=your_yandex_api_key"
    echo ""
    echo "После создания .env запустите скрипт снова."
    exit 1
fi

# Остановка старого контейнера (если есть)
echo "🛑 Остановка старого контейнера..."
docker-compose down 2>/dev/null || true

# Сборка и запуск
echo "🔨 Сборка Docker образа..."
docker-compose build

echo "▶️  Запуск бота..."
docker-compose up -d

# Проверка статуса
echo ""
echo "✅ Деплой завершен!"
echo ""
echo "📊 Статус контейнера:"
docker-compose ps

echo ""
echo "📝 Логи бота (Ctrl+C для выхода):"
docker-compose logs -f
