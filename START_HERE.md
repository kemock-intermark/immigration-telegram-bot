# 🚀 БЫСТРЫЙ СТАРТ

Система готова к использованию! Вот как начать работу.

---

## ✅ Статус системы

- ✅ База знаний создана (50 документов, 43 страны)
- ✅ Все скрипты готовы
- ✅ Оптимизация включена (↓ 30-40% времени)
- ✅ Логирование неотвеченных вопросов работает

---

## 💬 Использование чат-агента

### Вариант 1: Быстрый вопрос (рекомендуется)

```bash
python3 chat_agent.py "ваш вопрос"
```

**Примеры:**

```bash
# На русском
python3 chat_agent.py "гражданство Malta"
python3 chat_agent.py "ВНЖ в Португалии"
python3 chat_agent.py "стоимость citizenship Греция"

# На английском
python3 chat_agent.py "Portugal residence permit"
python3 chat_agent.py "Golden Visa requirements"
python3 chat_agent.py "Caribbean citizenship programs"
```

### Вариант 2: Интерактивный режим

**Запуск напрямую в терминале:**

```bash
python3 chat_agent.py
```

Затем вводите вопросы интерактивно. Команды:
- `/помощь` — справка
- `/статистика` — статистика базы
- `/выход` — завершить

**⚠️ Важно:** Интерактивный режим работает только при запуске напрямую в вашем терминале, не через IDE или скрипты.

### Вариант 3: Демонстрация

```bash
python3 demo_chat.py
```

Показывает примеры вопросов и ответов.

---

## 🔧 Основные команды

### Работа с базой знаний

```bash
# Создать базу с нуля (первый раз или полная пересборка)
python3 build_knowledge.py

# Обновить базу (после изменения PDF в raw/)
python3 update_knowledge.py

# Статистика
python3 stats_knowledge.py

# Поиск
python3 search_knowledge.py --country "Portugal"
```

### Работа с чатом

```bash
# Одиночный вопрос
python3 chat_agent.py "ваш вопрос"

# Демонстрация
python3 demo_chat.py

# Интерактивный режим (в терминале)
python3 chat_agent.py
```

---

## 📊 Просмотр результатов

```bash
# Индекс всех документов
cat knowledge/00_index.md

# Логи
cat knowledge/build_log.md
cat knowledge/update_log.md

# Неотвеченные вопросы
cat knowledge/_unanswered_log.md

# Manifest (метаданные)
cat knowledge/manifest.json
```

---

## 📖 Документация

| Файл | Описание |
|------|----------|
| `COMMANDS.txt` | Краткая шпаргалка всех команд |
| `USAGE.md` | Руководство пользователя с примерами |
| `CHAT_GUIDE.md` | Подробное руководство по чату |
| `PERFORMANCE.md` | Информация об оптимизации |
| `UNANSWERED_LOG_GUIDE.md` | Работа с логом неотвеченных вопросов |
| `README.md` | Полная документация проекта |

**Быстрая справка:**
```bash
cat COMMANDS.txt
```

---

## 🎯 Типичные сценарии

### Сценарий 1: Задать вопрос агенту

```bash
python3 chat_agent.py "какие программы гражданства в Malta?"
```

### Сценарий 2: Найти информацию о стране

```bash
python3 search_knowledge.py --country "Portugal"
python3 stats_knowledge.py --country "Portugal"
```

### Сценарий 3: Добавили новые PDF

```bash
# 1. Скопировать новые PDF в raw/
# 2. Обновить базу
python3 update_knowledge.py

# 3. Проверить что обновилось
cat knowledge/update_log.md
```

### Сценарий 4: Анализ пробелов

```bash
# Посмотреть что не нашлось в базе
cat knowledge/_unanswered_log.md

# Определить какие материалы добавить
```

---

## ⚡ Производительность

**Текущие показатели (v1.2 — оптимизированная):**
- Создание базы: ~8 секунд (50 PDF)
- Обновление: ~0.1 секунды (без изменений)
- Поиск: ~0.07 секунды
- Поиск с кэшем: ~0.05 секунды

---

## 🆘 Помощь

### Проблемы?

```bash
# Проверить что всё установлено
python3 --version  # Должно быть 3.7+
pip list | grep PyPDF2

# Переустановить зависимости
pip install PyPDF2

# Пересоздать базу
python3 build_knowledge.py
```

### Вопросы по использованию?

Смотрите документацию:
- `USAGE.md` — примеры использования
- `CHAT_GUIDE.md` — руководство по чату
- `README.md` — полная документация

---

## 🎉 Готово!

Система полностью настроена и готова к работе.

**Начните с:**
```bash
python3 chat_agent.py "Malta citizenship"
```

или

```bash
python3 demo_chat.py  # Посмотреть примеры
```

---

*Версия: 1.2.0*  
*Дата: 2025-10-14*  
*Статус: ✅ Production Ready*


