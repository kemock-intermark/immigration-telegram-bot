# ☁️ Развертывание Telegram-бота в облаке (БЕСПЛАТНО 24/7)

Пошаговая инструкция по запуску бота на бесплатных облачных платформах.

---

## 🎯 Рекомендуемая платформа: **Render.com**

**Почему Render:**
- ✅ **Полностью бесплатно** (не требует кредитной карты)
- ✅ Работает **24/7** без остановок
- ✅ Автоматический деплой из GitHub
- ✅ Простая настройка (10 минут)
- ✅ 750 часов в месяц бесплатно (хватает на 24/7)

---

## 📋 ЧТО ПОНАДОБИТСЯ:

1. ✅ Аккаунт на GitHub (бесплатно)
2. ✅ Аккаунт на Render.com (бесплатно, без карты)
3. ✅ Токен Telegram-бота от @BotFather
4. ⏱️ 10-15 минут времени

---

# 🚀 ПОШАГОВАЯ ИНСТРУКЦИЯ

## ШАГ 1: Создание Telegram-бота (2 минуты)

1. **Откройте Telegram** и найдите **@BotFather**
2. **Отправьте:** `/newbot`
3. **Введите имя:** `Immigration Knowledge Bot`
4. **Введите username:** `intermark_immigration_bot` (или другой свободный)
5. **СОХРАНИТЕ ТОКЕН!** Выглядит так: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

✅ **Готово!** Бот создан.

---

## ШАГ 2: Регистрация на GitHub (если нет аккаунта)

1. Перейдите на **github.com**
2. Нажмите **Sign up**
3. Создайте аккаунт (бесплатно)

---

## ШАГ 3: Создание репозитория на GitHub (3 минуты)

### Вариант A: Через веб-интерфейс GitHub

1. Войдите на **github.com**
2. Нажмите **New repository** (зелёная кнопка)
3. **Название:** `immigration-telegram-bot`
4. Выберите **Public** (для бесплатного деплоя)
5. Поставьте галочку **Add a README file**
6. Нажмите **Create repository**

### Вариант B: Через командную строку (если знакомы с Git)

```bash
cd "/Users/kemock/Intermark Global/Agent/Immigration-date base"

# Инициализация Git
git init

# Добавление файлов
git add telegram_bot.py chat_agent.py knowledge/
git add requirements.txt

# Коммит
git commit -m "Initial commit: Telegram bot for immigration knowledge base"

# Создайте репозиторий на GitHub через веб-интерфейс, затем:
git remote add origin https://github.com/ваш-username/immigration-telegram-bot.git
git branch -M main
git push -u origin main
```

---

## ШАГ 4: Подготовка файлов для деплоя

### 4.1. Создайте файл `requirements.txt`

Этот файл содержит список зависимостей Python:

```
PyPDF2==3.0.1
python-telegram-bot==20.7
```

### 4.2. Создайте файл `render.yaml` (опционально)

Это конфигурация для Render:

```yaml
services:
  - type: web
    name: immigration-telegram-bot
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python telegram_bot.py
    envVars:
      - key: TELEGRAM_BOT_TOKEN
        sync: false
```

### 4.3. Убедитесь, что все файлы в репозитории:

```
immigration-telegram-bot/
├── telegram_bot.py          ✅
├── chat_agent.py            ✅
├── requirements.txt         ✅
├── render.yaml              ✅ (опционально)
├── knowledge/               ✅
│   ├── 00_index.md
│   ├── manifest.json
│   └── [все .md файлы]
└── raw/                     ❌ НЕ НУЖНА (PDF не загружаем)
```

**⚠️ ВАЖНО:** Папку `raw/` с PDF НЕ загружайте на GitHub (слишком большая). База знаний уже в `knowledge/`.

---

## ШАГ 5: Загрузка на GitHub (если ещё не загрузили)

### Через веб-интерфейс (проще):

1. Откройте ваш репозиторий на GitHub
2. Нажмите **Add file** → **Upload files**
3. Перетащите файлы:
   - `telegram_bot.py`
   - `chat_agent.py`
   - `requirements.txt`
   - Папку `knowledge/` (целиком)
4. Напишите комментарий: `Add bot files`
5. Нажмите **Commit changes**

### Через командную строку:

```bash
git add .
git commit -m "Add all bot files"
git push
```

---

## ШАГ 6: Регистрация на Render.com (1 минута)

1. Перейдите на **render.com**
2. Нажмите **Get Started**
3. Войдите через GitHub (Sign in with GitHub)
4. Разрешите доступ Render к вашим репозиториям

---

## ШАГ 7: Деплой на Render.com (5 минут)

### 7.1. Создание нового сервиса

1. На **Dashboard** Render нажмите **New +**
2. Выберите **Background Worker** (для ботов)
3. Нажмите **Build and deploy from a Git repository**
4. Нажмите **Connect** рядом с вашим репозиторием `immigration-telegram-bot`

### 7.2. Настройка сервиса

**Name:** `immigration-bot`

**Region:** `Oregon (US West)` (или ближайший к вам)

**Branch:** `main`

**Runtime:** `Python 3`

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
python telegram_bot.py
```

### 7.3. Добавление переменных окружения

В разделе **Environment Variables** нажмите **Add Environment Variable**:

**Key:** `TELEGRAM_BOT_TOKEN`  
**Value:** `ваш_токен_от_BotFather` (вставьте токен из Шага 1)

### 7.4. Выбор плана

**Instance Type:** `Free` (выберите бесплатный план)

**Нажмите:** `Create Background Worker`

---

## ШАГ 8: Ожидание деплоя (2-3 минуты)

Render начнёт:
1. ✅ Клонировать ваш репозиторий
2. ✅ Устанавливать зависимости
3. ✅ Загружать базу знаний
4. ✅ Запускать бота

**В логах вы увидите:**
```
📚 Загрузка базы знаний...
📦 Версия базы: build_2025-10-14_17-38
✅ Загружено 50 документов
🚀 Запуск бота...
✅ Бот запущен и готов к работе!
```

---

## ШАГ 9: Тестирование (30 секунд)

1. **Откройте Telegram**
2. **Найдите вашего бота** (по username из Шага 1)
3. **Нажмите START**
4. **Задайте вопрос:**
   ```
   Malta citizenship requirements
   ```

**🎉 Если бот ответил — всё работает!**

---

## ✅ ГОТОВО!

Ваш бот теперь работает **24/7 бесплатно** в облаке Render.com!

---

# 📊 Мониторинг и управление

## Просмотр логов

На Render.com:
1. Откройте ваш сервис
2. Перейдите на вкладку **Logs**
3. Видите все запросы в реальном времени

## Перезапуск бота

1. На странице сервиса нажмите **Manual Deploy**
2. Выберите **Clear build cache & deploy**

## Обновление кода

1. Внесите изменения в код локально
2. Загрузите на GitHub:
   ```bash
   git add .
   git commit -m "Update bot"
   git push
   ```
3. Render автоматически задеплоит новую версию!

---

# 🔧 Альтернативные платформы

Если Render не подходит, вот альтернативы:

## 1. **Railway.app**

**Плюсы:**
- Бесплатный план: $5 кредитов/месяц
- Очень простой интерфейс
- Автодеплой из GitHub

**Минусы:**
- Требует карту (не списывают деньги)
- Кредиты могут закончиться

**Инструкция:** Почти идентична Render

---

## 2. **Fly.io**

**Плюсы:**
- Бесплатный план
- Быстрые серверы
- Глобальная сеть

**Минусы:**
- Чуть сложнее настройка
- Требует CLI

---

## 3. **Heroku** (НЕ РЕКОМЕНДУЮ)

**Почему:**
- ❌ Убрали бесплатный план в 2022
- ❌ Теперь платный от $5/месяц

---

# ⚠️ Ограничения бесплатного плана Render

1. **Засыпание:** Сервис может "заснуть" после 15 минут неактивности
   - **Решение:** Первый ответ может быть медленным (~30 сек), дальше работает быстро

2. **750 часов/месяц:** Хватает на 24/7
   - **Решение:** Не нужно ничего делать, хватает

3. **Публичный репозиторий:** Код на GitHub должен быть public
   - **Решение:** Если нужен private — используйте Railway (требует карту)

---

# 🎁 Бонус: Мониторинг "засыпания"

Чтобы бот не засыпал, можно настроить пинг каждые 10 минут:

## Вариант 1: UptimeRobot (бесплатно)

1. Регистрируйтесь на **uptimerobot.com**
2. Добавьте ваш Render URL
3. Проверка каждые 5 минут
4. Бот всегда "проснут"

## Вариант 2: Встроенный keep-alive

Добавьте в `telegram_bot.py`:

```python
import threading
import time

def keep_alive():
    while True:
        time.sleep(600)  # Каждые 10 минут
        print("Keep-alive ping")

# В main():
threading.Thread(target=keep_alive, daemon=True).start()
```

---

# 💡 Советы

## Безопасность

✅ Никогда не публикуйте токен бота в коде!  
✅ Используйте Environment Variables  
✅ Если токен утек — пересоздайте бота через @BotFather  

## Производительность

✅ База знаний загружается один раз при старте  
✅ Кэширование поиска работает  
✅ Первый запрос может быть медленным (пробуждение)  

## Обновление базы знаний

1. Обновите `knowledge/` локально
2. Загрузите на GitHub
3. Render автоматически обновит бота

---

# 🆘 Решение проблем

## Бот не запускается

**Проверьте логи на Render:**
1. Вкладка **Logs**
2. Ищите ошибки красным цветом

**Частые проблемы:**
- ❌ Неверный токен → проверьте Environment Variable
- ❌ Нет файла `requirements.txt` → добавьте в репозиторий
- ❌ Нет папки `knowledge/` → загрузите на GitHub

## Бот не отвечает

1. Проверьте статус на Render (Running?)
2. Проверьте логи (есть ли ошибки?)
3. Перезапустите сервис (Manual Deploy)

## "Module not found"

Проверьте `requirements.txt`:
```
PyPDF2==3.0.1
python-telegram-bot==20.7
```

---

# 📞 Поддержка

**Документация Render:** docs.render.com  
**Telegram Bot API:** core.telegram.org/bots  

---

**🎉 Поздравляем! Ваш бот работает в облаке 24/7 бесплатно!**

*Версия: 1.0*  
*Дата: 2025-10-14*

