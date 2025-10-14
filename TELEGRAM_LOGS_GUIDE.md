# 📊 Логирование вопросов из Telegram

Все вопросы из Telegram **автоматически сохраняются** в файл и **синхронизируются через Git**.

---

## 🎯 Что логируется

Для каждого вопроса записывается:
- 📅 **Дата и время** (точное)
- 👤 **User ID и username** пользователя Telegram
- ❓ **Полный текст вопроса**
- ✅/❌ **Найден ли ответ** (yes/no)
- 📏 **Длина ответа** (в символах)

---

## 📁 Где хранятся логи

**Файл:** `knowledge/telegram_questions.jsonl`

**Формат:** JSON Lines (каждая строка = отдельный JSON объект)

**Пример записи:**
```json
{
  "timestamp": "2025-10-14T22:45:30.123456",
  "user_id": 123456789,
  "username": "john_doe",
  "question": "Как получить Golden Visa в Греции?",
  "answer_found": true,
  "response_length": 1842,
  "date": "2025-10-14",
  "time": "22:45:30"
}
```

---

## 🔄 Автоматическая синхронизация с Git

Логи **автоматически** загружаются на GitHub:

### Когда происходит синхронизация:
1. Каждые **10 вопросов**, ИЛИ
2. Каждый **1 час** (если есть новые вопросы)

### Что происходит:
```bash
git add knowledge/telegram_questions.jsonl
git commit -m "📊 Auto-sync: Telegram questions log"
git push
```

**Синхронизация не блокирует бота** - происходит в фоновом режиме.

---

## 📊 Просмотр логов

### Вариант 1: Через скрипт (рекомендуется)

```bash
python3 view_telegram_logs.py
```

**Покажет:**
- ✅ Сводку (всего вопросов, с ответом, без ответа)
- 👥 Топ пользователей
- 📅 Статистику по датам
- 📝 Последние 10 вопросов
- ❌ Неотвеченные вопросы
- 🔥 Популярные темы

### Вариант 2: Экспорт в CSV

```bash
python3 view_telegram_logs.py export
```

Создаст файл `telegram_questions.csv` для анализа в Excel/Google Sheets.

### Вариант 3: Напрямую (JSON)

```bash
cat knowledge/telegram_questions.jsonl | jq '.'
```

или

```bash
tail -20 knowledge/telegram_questions.jsonl
```

---

## 🔍 Примеры анализа

### Сколько всего вопросов:
```bash
wc -l knowledge/telegram_questions.jsonl
```

### Последние 5 вопросов:
```bash
tail -5 knowledge/telegram_questions.jsonl | jq '.question'
```

### Неотвеченные вопросы:
```bash
grep '"answer_found": false' knowledge/telegram_questions.jsonl | jq '.question'
```

### Топ пользователей:
```bash
jq -r '.username' knowledge/telegram_questions.jsonl | sort | uniq -c | sort -rn
```

---

## 📥 Получение логов с GitHub

Логи автоматически пушатся на GitHub, поэтому вы можете:

### На другом компьютере:
```bash
git pull
cat knowledge/telegram_questions.jsonl
```

### Через веб-интерфейс GitHub:
1. Откройте репозиторий на github.com
2. Перейдите в `knowledge/telegram_questions.jsonl`
3. Нажмите `Raw` для скачивания

### Через API GitHub:
```bash
curl https://raw.githubusercontent.com/kemock-intermark/immigration-telegram-bot/main/knowledge/telegram_questions.jsonl
```

---

## 🔒 Безопасность и приватность

### Что НЕ логируется:
- ❌ Полное имя пользователя
- ❌ Email/телефон
- ❌ Содержимое ответов (только длина)
- ❌ IP адреса

### Что логируется:
- ✅ Telegram user_id (число)
- ✅ Telegram username (публичное имя)
- ✅ Вопросы (текст)

### Если нужна дополнительная приватность:

Можно хэшировать user_id в `question_logger.py`:
```python
import hashlib
user_id_hash = hashlib.sha256(str(user_id).encode()).hexdigest()[:16]
```

---

## 📈 Использование логов

### Анализ популярных тем
Помогает понять:
- О чём чаще всего спрашивают клиенты
- Какие страны/программы популярнее
- Какие вопросы повторяются

### Улучшение базы знаний
Неотвеченные вопросы показывают:
- Каких материалов не хватает
- Какие презентации нужно добавить
- Какие темы расширить

### Метрики эффективности
- % вопросов с ответом
- Активность пользователей
- Динамика роста запросов

---

## ⚙️ Настройка

### Изменить частоту синхронизации

В файле `question_logger.py`:

```python
self.sync_threshold = 10      # Каждые N вопросов
self.sync_interval = 3600     # Каждые N секунд (3600 = 1 час)
```

### Отключить автосинхронизацию

Установите очень большие значения:
```python
self.sync_threshold = 999999
self.sync_interval = 999999
```

Тогда синхронизация будет только вручную:
```bash
git add knowledge/telegram_questions.jsonl
git commit -m "Manual sync"
git push
```

---

## 🆘 Решение проблем

### Логи не создаются
Проверьте:
```bash
ls -la knowledge/telegram_questions.jsonl
```

Если файла нет - задайте вопрос боту в Telegram.

### Синхронизация не работает
Проверьте логи на Render:
```
🔄 Синхронизация логов с Git...
✅ Логи синхронизированы с Git
```

Если нет - проверьте права Git на Render.

### Слишком большой файл
Если файл > 10MB, можно архивировать старые логи:
```bash
# Архивировать логи старше месяца
grep '"date": "2025-09-' knowledge/telegram_questions.jsonl > archive_2025-09.jsonl
grep -v '"date": "2025-09-' knowledge/telegram_questions.jsonl > temp.jsonl
mv temp.jsonl knowledge/telegram_questions.jsonl
```

---

## 📊 Пример отчёта

```bash
$ python3 view_telegram_logs.py

================================================================================
📊 СВОДКА ПО ВОПРОСАМ ИЗ TELEGRAM
================================================================================

📈 Всего вопросов: 127
✅ С ответом: 114 (89.8%)
❌ Без ответа: 13 (10.2%)

👥 Уникальных пользователей: 15

📅 По датам:
   2025-10-14: 45 вопросов
   2025-10-13: 38 вопросов
   2025-10-12: 28 вопросов

🔝 Топ-5 активных пользователей:
   @john_doe: 23 вопроса
   @anna_smith: 18 вопросов
   @michael_k: 15 вопросов
```

---

## 🎁 Бонус: Telegram уведомления

Можно настроить уведомления о неотвеченных вопросах в отдельный Telegram канал.

В `question_logger.py` добавьте:
```python
if not answer_found:
    # Отправить в канал мониторинга
    send_to_monitoring_channel(question, username)
```

---

**✅ Готово! Все вопросы логируются и синхронизируются автоматически!**

*Версия: 1.0*  
*Дата: 2025-10-14*

