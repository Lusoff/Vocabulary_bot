# 🚀 Деплой Vocabulary Bot на VPS

## Автоматический деплой (рекомендуется)

Выполните эту команду на вашем VPS:

```bash
cd /root && \
git clone https://github.com/Lusoff/Vocabulary_bot.git && \
cd Vocabulary_bot && \
nano .env
# Добавьте ваши токены (см. шаг 3) и сохраните
# Затем запустите:
# docker-compose up -d --build
```

## Пошаговая инструкция

### 1. Установка Docker (если еще не установлен)

```bash
# Обновление пакетов
apt update && apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Установка Docker Compose
apt install docker-compose -y

# Проверка установки
docker --version
docker-compose --version
```

### 2. Клонирование репозитория

```bash
cd /root
git clone https://github.com/Lusoff/Vocabulary_bot.git
cd Vocabulary_bot
```

### 3. Настройка переменных окружения

Создайте файл `.env`:

```bash
nano .env
```

Вставьте следующее содержимое (замените значения на ваши реальные токены):

```
BOT_TOKEN=your_telegram_bot_token_here
YANDEX_DICT_API_KEY=your_yandex_dictionary_api_key_here
```

Сохраните файл (Ctrl+O, Enter, Ctrl+X).

### 4. Запуск бота

```bash
# Сборка и запуск в фоновом режиме
docker-compose up -d --build
```

## Управление ботом

### Просмотр логов

```bash
# Все логи
docker-compose logs -f

# Последние 100 строк
docker-compose logs --tail=100
```

### Перезапуск бота

```bash
docker-compose restart
```

### Остановка бота

```bash
docker-compose down
```

### Обновление бота

```bash
# Остановить контейнер
docker-compose down

# Получить обновления
git pull origin main

# Пересобрать и запустить
docker-compose up -d --build
```

### Статус контейнера

```bash
docker-compose ps
```

### Полная очистка и перезапуск

```bash
# Остановить и удалить контейнер
docker-compose down

# Удалить старые образы
docker system prune -a

# Пересобрать и запустить
docker-compose up -d --build
```

## Автозапуск при перезагрузке сервера

Бот автоматически запустится при перезагрузке сервера благодаря параметру `restart: unless-stopped` в `docker-compose.yml`.

## Резервное копирование базы данных

База данных хранится в `./data/vocabulary.db`. Для создания бэкапа:

```bash
# Создать бэкап
cp data/vocabulary.db data/vocabulary_backup_$(date +%Y%m%d).db

# Или скачать на локальный компьютер
scp root@147.45.145.24:/root/Vocabulary_bot/data/vocabulary.db ./vocabulary_backup.db
```

## Проверка работы

После запуска бота, отправьте `/start` в Telegram, чтобы убедиться, что бот работает.

## Мониторинг ресурсов

```bash
# Использование ресурсов контейнером
docker stats vocabulary_bot
```

## Troubleshooting

### Бот не запускается

```bash
# Проверить логи
docker-compose logs

# Проверить, что .env файл создан
cat .env

# Проверить статус контейнера
docker-compose ps
```

### Порт уже занят

```bash
# Найти процесс, использующий порт
netstat -tulpn | grep LISTEN

# Остановить конфликтующий процесс
kill -9 <PID>
```

### Недостаточно места на диске

```bash
# Очистить неиспользуемые Docker образы
docker system prune -a

# Проверить место на диске
df -h
```
