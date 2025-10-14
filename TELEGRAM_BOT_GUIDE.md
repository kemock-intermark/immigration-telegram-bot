# 🤖 Руководство по запуску Telegram-бота

Ваш чат-агент теперь доступен через Telegram! 🎉

---

## 📋 Что вам понадобится

1. **Python 3.7+** (уже есть ✅)
2. **База знаний** (уже создана ✅)
3. **Библиотека для Telegram** (нужно установить)
4. **Токен от BotFather** (создадим за 2 минуты)

---

## 🚀 БЫСТРЫЙ СТАРТ (5 минут)

### Шаг 1: Установка библиотеки

```bash
pip install python-telegram-bot
```

или

```bash
pip3 install python-telegram-bot
```

---

### Шаг 2: Создание бота в Telegram

1. **Откройте Telegram** и найдите **@BotFather**
2. **Отправьте команду:** `/newbot`
3. **BotFather спросит имя бота:**
   ```
   Например: Immigration Knowledge Bot
   ```
4. **BotFather спросит username бота:**
   ```
   Например: intermark_immigration_bot
   (должен заканчиваться на _bot или Bot)
   ```
5. **BotFather даст вам токен:**
   ```
   1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```
   **⚠️ СОХРАНИТЕ ЭТОТ ТОКЕН! Он понадобится.**

---

### Шаг 3: Настройка токена

#### Вариант A: Переменная окружения (рекомендуется)

**macOS/Linux:**
```bash
export TELEGRAM_BOT_TOKEN='ваш_токен_от_BotFather'
```

**Windows:**
```cmd
set TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
```

#### Вариант B: Файл .env

Создайте файл `.env` в корне проекта:
```bash
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
```

---

### Шаг 4: Запуск бота

```bash
python3 telegram_bot.py
```

Вы увидите:
```
================================================================================
🤖 TELEGRAM-БОТ ДЛЯ БАЗЫ ЗНАНИЙ ПО ИММИГРАЦИИ
================================================================================
📚 База знаний загружена: 50 документов
📦 Версия: build_2025-10-14_17-38
🚀 Запуск бота...
================================================================================
✅ Бот запущен и готов к работе!
💬 Пользователи могут начать общение командой /start

Для остановки нажмите Ctrl+C
================================================================================
```

---

### Шаг 5: Тестирование

1. **Откройте Telegram**
2. **Найдите своего бота** (по username, который создали)
3. **Нажмите START** или отправьте `/start`
4. **Задайте вопрос**, например:
   ```
   Malta citizenship requirements
   ```

**Готово!** 🎉

---

## 💬 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и инструкции |
| `/help` | Справка по использованию |
| `/stats` | Статистика базы знаний |

**Все остальные сообщения** воспринимаются как вопросы к базе знаний.

---

## 📱 Примеры использования

### Пример 1: Вопрос о гражданстве
```
👤 Пользователь: Malta citizenship cost

🤖 Бот: [детальный ответ с ценами и источниками]
```

### Пример 2: Вопрос на русском
```
👤 Пользователь: Сколько стоит Golden Visa в Греции?

🤖 Бот: [ответ с тремя вариантами 250K/400K/800K EUR]
```

### Пример 3: Неизвестная информация
```
👤 Пользователь: Антарктида программа гражданства

🤖 Бот: ❌ Не знаю — нет в материалах.
         По вашему запросу не найдено информации в базе знаний.
```

---

## 🔧 Настройка (опционально)

### Изменение лимита результатов поиска

В файле `telegram_bot.py` найдите строку:
```python
results = agent.search_documents(question, limit=5)
```

Измените `limit=5` на нужное вам значение (например, `limit=3` или `limit=10`).

---

### Добавление дополнительных команд

Добавьте новую функцию в `telegram_bot.py`:

```python
async def my_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ваша команда"""
    await update.message.reply_text("Ваш ответ")

# В main() добавьте:
application.add_handler(CommandHandler("mycommand", my_command))
```

---

## 🌐 Запуск на сервере (для постоянной работы)

### Вариант 1: Screen (простой)

```bash
screen -S telegram_bot
python3 telegram_bot.py
# Нажмите Ctrl+A, затем D для отключения
# Для возврата: screen -r telegram_bot
```

### Вариант 2: tmux

```bash
tmux new -s telegram_bot
python3 telegram_bot.py
# Нажмите Ctrl+B, затем D для отключения
# Для возврата: tmux attach -t telegram_bot
```

### Вариант 3: nohup

```bash
nohup python3 telegram_bot.py > telegram_bot.log 2>&1 &
```

### Вариант 4: systemd service (продакшн)

Создайте файл `/etc/systemd/system/telegram-bot.service`:

```ini
[Unit]
Description=Immigration Knowledge Telegram Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/Immigration-date base
Environment="TELEGRAM_BOT_TOKEN=ваш_токен"
ExecStart=/usr/bin/python3 /path/to/Immigration-date base/telegram_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Запуск:
```bash
sudo systemctl daemon-reload
sudo systemctl start telegram-bot
sudo systemctl enable telegram-bot
```

---

## 📊 Мониторинг

### Просмотр логов

Бот выводит логи в консоль:
```
2025-10-14 18:00:00 - __main__ - INFO - Question from user123: Malta citizenship
2025-10-14 18:00:01 - __main__ - INFO - Answer sent to user123
```

### Статистика использования

Пользователи могут запросить статистику командой `/stats`:
```
📊 СТАТИСТИКА

База знаний:
• Документов: 50
• Стран: 43
• Версия: build_2025-10-14_17-38

Использование бота:
• Всего запросов: 127
• Уникальных пользователей: 15
• Работает: 2д 5ч 32м
```

---

## ⚙️ Расширенные настройки

### Ограничение доступа (whitelist)

Добавьте в `telegram_bot.py`:

```python
ALLOWED_USERS = [123456789, 987654321]  # Telegram User IDs

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in ALLOWED_USERS:
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return
    
    # ... остальной код
```

### Уведомления администратору

```python
ADMIN_ID = 123456789  # Ваш Telegram ID

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... обработка вопроса
    
    # Уведомление админу
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"Новый вопрос от {user.username}: {question}"
    )
```

---

## 🐛 Решение проблем

### Ошибка: "No module named 'telegram'"

**Решение:**
```bash
pip install python-telegram-bot
```

### Ошибка: "не найден TELEGRAM_BOT_TOKEN"

**Решение:**
```bash
export TELEGRAM_BOT_TOKEN='ваш_токен'
python3 telegram_bot.py
```

### Бот не отвечает

1. Проверьте, что бот запущен (`python3 telegram_bot.py`)
2. Проверьте токен (правильный ли)
3. Проверьте интернет-соединение
4. Посмотрите логи на наличие ошибок

### Бот отвечает медленно

1. Проверьте загрузку сервера
2. Убедитесь, что база знаний загружена (`agent.documents`)
3. Проверьте сетевое соединение

---

## 🔐 Безопасность

**⚠️ ВАЖНО:**

1. **Никогда не публикуйте токен бота в открытом доступе!**
2. Если токен утек — создайте нового бота через @BotFather
3. Используйте переменные окружения или `.env` файлы
4. Добавьте `.env` в `.gitignore`

---

## 📈 Метрики и аналитика

Бот автоматически собирает:
- Количество запросов
- Уникальных пользователей
- Время работы

Для расширенной аналитики можно интегрировать:
- Google Analytics
- Mixpanel
- Amplitude

---

## 🎯 Возможности улучшения

### Уже реализовано:
- ✅ Базовые команды (/start, /help, /stats)
- ✅ Обработка вопросов
- ✅ Разбиение длинных ответов
- ✅ Статистика использования
- ✅ Логирование

### Можно добавить:
- ⭐ Inline кнопки (выбор категории)
- ⭐ История вопросов пользователя
- ⭐ Экспорт ответов в PDF
- ⭐ Мультиязычность
- ⭐ Голосовые сообщения (распознавание)
- ⭐ Административная панель

---

## 📞 Поддержка

**Проблемы с ботом?**
1. Проверьте логи
2. Перезапустите бота
3. Обновите библиотеку: `pip install -U python-telegram-bot`

**Технические вопросы:**
- Документация python-telegram-bot: https://docs.python-telegram-bot.org
- GitHub: https://github.com/python-telegram-bot/python-telegram-bot

---

## ✅ Чеклист запуска

- [ ] Python 3.7+ установлен
- [ ] База знаний создана (`knowledge/`)
- [ ] Установлена библиотека `python-telegram-bot`
- [ ] Создан бот через @BotFather
- [ ] Получен токен
- [ ] Токен добавлен в переменные окружения
- [ ] Бот запущен (`python3 telegram_bot.py`)
- [ ] Бот отвечает на `/start`
- [ ] Бот корректно обрабатывает вопросы

---

**🎉 Поздравляем! Ваш Telegram-бот готов к работе!**

*Версия руководства: 1.0*  
*Дата: 2025-10-14*

