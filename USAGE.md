# Руководство по использованию базы знаний

Быстрый старт и примеры использования всех доступных инструментов.

---

## 🚀 Быстрый старт

### 1. Первичное создание базы знаний

```bash
python3 build_knowledge.py
```

**Результат:**
- Создаётся папка `knowledge/` с 50 документами
- Генерируется индекс `00_index.md`
- Создаётся лог сборки `build_log.md`

**Время выполнения:** ~13 секунд

---

### 2. Обновление базы знаний

После изменения PDF файлов в папке `raw/`:

```bash
python3 update_knowledge.py
```

**Результат:**
- Обновляются только изменённые файлы (по хешу)
- Неизменённые файлы пропускаются
- Создаётся лог обновления `update_log.md`

**Время выполнения:** 
- Без изменений: ~0.2 секунды
- С изменениями: зависит от количества обновлённых файлов

---

## 🔍 Поиск в базе знаний

### Интерактивный режим

```bash
python3 search_knowledge.py
```

Выберите тип поиска и введите запрос.

### Поиск по стране

```bash
python3 search_knowledge.py --country "Portugal"
```

**Пример вывода:**
```
✅ Найдено результатов: 8

1. Portugal: Вид на жительство
   📁 Portugal/portugal-residence-permit.md
   📝 Категория: Portugal
   📌 Тип: residence-permit
```

### Поиск по типу программы

```bash
# Гражданство
python3 search_knowledge.py --type "citizenship"

# Вид на жительство
python3 search_knowledge.py --type "residence"

# Постоянное проживание
python3 search_knowledge.py --type "permanent"
```

### Полнотекстовый поиск

```bash
python3 search_knowledge.py --search "investment"
```

Найдёт все документы, содержащие слово "investment" с контекстом.

---

## 📊 Статистика

### Общая статистика

```bash
python3 stats_knowledge.py
```

**Показывает:**
- Общее количество документов
- Распределение по типам программ
- ТОП-10 стран по количеству документов
- Объём базы знаний (символы, слова)
- Количество исходных PDF файлов

**Пример вывода:**
```
📊 СТАТИСТИКА БАЗЫ ЗНАНИЙ
📚 Всего документов: 50
🌍 Категорий (стран): 43

📋 РАСПРЕДЕЛЕНИЕ ПО ТИПАМ ПРОГРАММ:
  • Вид на жительство: 24 документов
  • Гражданство: 15 документов
  • Постоянное проживание: 7 документов
  • Общая информация: 3 документов
  • Паспорт: 1 документов

📏 ОБЪЁМ БАЗЫ ЗНАНИЙ:
  • Всего символов: 441,141
  • Всего слов: 66,299
  • Среднее слов на документ: 1,325
```

### Список всех стран

```bash
python3 stats_knowledge.py --list
```

Выводит полный список стран/регионов с количеством документов.

### Статистика по конкретной стране

```bash
python3 stats_knowledge.py --country "Malta"
```

Показывает детальную информацию по всем документам конкретной страны.

---

## 📁 Структура файлов

```
Immigration-date base/
├── raw/                          # Исходные PDF (50 файлов)
│   ├── Intermark. Portugal RP. Arish Capital Partners ENG.pdf
│   ├── Intermark. Malta Citizenship ENG.pdf
│   └── ...
│
├── knowledge/                    # База знаний (автоматически)
│   ├── 00_index.md              # Главный индекс
│   ├── build_log.md             # Лог сборки
│   ├── update_log.md            # Лог обновления
│   ├── Portugal/
│   │   ├── portugal-residence-permit.md
│   │   ├── portugal-residence-permit_v2.md
│   │   └── ...
│   ├── Malta/
│   │   └── malta-citizenship.md
│   └── [41 другая категория]
│
├── build_knowledge.py           # Создание базы с нуля
├── update_knowledge.py          # Инкрементальное обновление
├── search_knowledge.py          # Поиск
├── stats_knowledge.py           # Статистика
├── README.md                    # Полная документация
└── USAGE.md                     # Это руководство
```

---

## 🎯 Типичные сценарии использования

### Сценарий 1: Первый запуск

```bash
# 1. Создать базу знаний
python3 build_knowledge.py

# 2. Посмотреть статистику
python3 stats_knowledge.py

# 3. Посмотреть список всех стран
python3 stats_knowledge.py --list

# 4. Открыть индексный файл
open knowledge/00_index.md
```

### Сценарий 2: Обновление после изменения PDF

```bash
# 1. Скопировать новые/обновлённые PDF в raw/

# 2. Запустить обновление
python3 update_knowledge.py

# 3. Проверить лог обновления
cat knowledge/update_log.md
```

### Сценарий 3: Поиск информации по стране

```bash
# 1. Найти все документы по Португалии
python3 search_knowledge.py --country "Portugal"

# 2. Посмотреть детальную статистику
python3 stats_knowledge.py --country "Portugal"

# 3. Открыть конкретный документ
open "knowledge/Portugal/portugal-residence-permit.md"
```

### Сценарий 4: Анализ по типу программы

```bash
# 1. Найти все программы гражданства
python3 search_knowledge.py --type "citizenship"

# 2. Посмотреть общую статистику
python3 stats_knowledge.py
```

### Сценарий 5: Поиск по ключевым словам

```bash
# Найти все упоминания инвестиций
python3 search_knowledge.py --search "investment"

# Найти информацию о стартапах
python3 search_knowledge.py --search "startup"

# Найти Golden Visa программы
python3 search_knowledge.py --search "golden visa"
```

---

## 🔧 Дополнительные команды

### Просмотр индекса

```bash
# Открыть в браузере (macOS)
open knowledge/00_index.md

# Просмотреть в терминале
cat knowledge/00_index.md

# Первые 50 строк
head -50 knowledge/00_index.md
```

### Просмотр логов

```bash
# Лог сборки
cat knowledge/build_log.md

# Лог обновления
cat knowledge/update_log.md

# Последние 20 строк лога обновления
tail -20 knowledge/update_log.md
```

### Поиск grep

```bash
# Найти все упоминания конкретной страны
grep -r "Malta" knowledge/

# Найти документы с определённым тегом
grep -r "инвестиции" knowledge/

# Поиск с номерами строк
grep -rn "citizenship" knowledge/
```

---

## 💡 Полезные советы

### 1. Проверка целостности базы

```bash
# Подсчитать количество документов
find knowledge -name "*.md" -not -name "00_index.md" -not -name "*_log.md" | wc -l

# Должно быть 50 документов
```

### 2. Резервное копирование

```bash
# Создать архив базы знаний
tar -czf knowledge_backup_$(date +%Y%m%d).tar.gz knowledge/

# Восстановить из архива
tar -xzf knowledge_backup_20251014.tar.gz
```

### 3. Сравнение версий

```bash
# Посмотреть различия в индексе
diff knowledge/00_index.md knowledge_backup/00_index.md
```

### 4. Экспорт в другие форматы

```bash
# Конвертация MD в HTML (требует pandoc)
pandoc knowledge/Portugal/portugal-residence-permit.md -o portugal.html

# Конвертация в PDF (требует pandoc + LaTeX)
pandoc knowledge/Portugal/portugal-residence-permit.md -o portugal.pdf
```

---

## ❓ Решение проблем

### Проблема: PyPDF2 не установлен

**Решение:**
```bash
pip install PyPDF2
```

### Проблема: Папка knowledge/ не найдена

**Решение:**
```bash
# Создать базу с нуля
python3 build_knowledge.py
```

### Проблема: Скрипт не запускается

**Решение:**
```bash
# Убедитесь, что используете Python 3
python3 --version

# Должно быть Python 3.7 или выше
```

### Проблема: Не находит документы по поиску

**Решение:**
```bash
# Проверьте наличие документов
ls -R knowledge/

# Пересоздайте базу
python3 build_knowledge.py
```

---

## 📚 Дополнительная информация

Полную документацию смотрите в файле `README.md`.

**Основные принципы работы:**
1. ✅ Точность — только данные из презентаций
2. ✅ Прозрачность — полное логирование
3. ✅ Версионирование — контроль изменений через хеши
4. ✅ Эффективность — обновление только изменённых файлов

**Поддержка:** 
- Документация: `README.md`
- Примеры: `USAGE.md` (этот файл)
- Логи: `knowledge/build_log.md`, `knowledge/update_log.md`

---

*Последнее обновление: 2025-10-14*

