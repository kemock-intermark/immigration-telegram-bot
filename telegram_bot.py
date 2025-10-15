#!/usr/bin/env python3
"""
Telegram-бот для работы с базой знаний по иммиграции
Использует существующий KnowledgeAgent из chat_agent.py
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Импортируем наш существующий агент
from chat_agent import KnowledgeAgent

# Импортируем логгер вопросов
from question_logger import get_logger

# Импортируем утилиты языка
try:
    from language_utils import LanguageDetector
    language_detector = LanguageDetector()
except ImportError:
    language_detector = None
    print("⚠️  language_utils не найден. Определение языка отключено.")

# Для Telegram бота нужна библиотека python-telegram-bot
try:
    from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
except ImportError:
    print("❌ Ошибка: Не установлена библиотека python-telegram-bot")
    print("\nУстановите её командой:")
    print("  pip install python-telegram-bot")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация агентов знаний (по одному для каждого языка)
KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

# Проверяем наличие language_utils
try:
    from language_utils import LanguageDetector
    LANGUAGE_UTILS_AVAILABLE = True
except ImportError:
    LANGUAGE_UTILS_AVAILABLE = False
    print("⚠️  language_utils недоступен, двуязычность отключена")

# Создаем агентов для каждого языка
if LANGUAGE_UTILS_AVAILABLE:
    agent_rus = KnowledgeAgent(str(KNOWLEDGE_DIR), lang="rus")
    agent_eng = KnowledgeAgent(str(KNOWLEDGE_DIR), lang="eng")
    language_detector = LanguageDetector()
    print("🌍 Созданы агенты для RUS и ENG")
else:
    # Fallback - один агент для всех
    agent_rus = KnowledgeAgent(str(KNOWLEDGE_DIR))
    agent_eng = None
    language_detector = None
    print("📚 Создан общий агент (legacy режим)")

# Инициализация логгера вопросов
question_logger = get_logger(str(KNOWLEDGE_DIR))

# Статистика использования
usage_stats = {
    'total_queries': 0,
    'users': set(),
    'started': datetime.now()
}

# Создаем клавиатуру с кнопками команд
def get_main_keyboard():
    """Возвращает основную клавиатуру с кнопками команд"""
    keyboard = [
        [KeyboardButton("❓ Справка"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("🔄 Перезапуск")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - приветствие"""
    user = update.effective_user
    usage_stats['users'].add(user.id)
    
    welcome_message = f"""👋 <b>Добро пожаловать, {user.first_name}!</b>

Я — интеллектуальный помощник по программам <b>иммиграции и получения гражданства</b> от компании Intermark Global.

━━━━━━━━━━━━━━━━━━━━━━

<b>🎯 Зачем я нужен?</b>

Помогаю быстро найти информацию о:
• <b>Гражданстве за инвестиции</b> (Карибы, Вануату, Турция, Египет)
• <b>Golden Visa</b> (Португалия, Греция, Испания, Мальта)
• <b>ВНЖ для предпринимателей</b> (Франция, UK, Канада)
• <b>ПМЖ и натурализации</b> в различных странах

━━━━━━━━━━━━━━━━━━━━━━

<b>📚 База знаний:</b>
✓ {len(agent_rus.documents) + len(agent_eng.documents) if agent_eng else len(agent_rus.documents)} актуальных документов
✓ 40+ стран и программ
✓ Точные цифры, сроки, требования
✓ Ссылки на источники

━━━━━━━━━━━━━━━━━━━━━━

<b>💬 Как работать со мной?</b>

Просто задайте вопрос на <b>русском или английском</b> — я найду ответ в базе знаний и предоставлю структурированную информацию с указанием источников.

<b>Примеры вопросов:</b>

🔹 <i>Какие карибские паспорта дают безвизовый въезд в Шенген?</i>
🔹 <i>Сколько стоит Golden Visa в Португалии?</i>
🔹 <i>Какие требования для гражданства Турции?</i>
🔹 <i>Malta citizenship by investment requirements</i>
🔹 <i>Как получить ВНЖ во Франции для бизнеса?</i>

━━━━━━━━━━━━━━━━━━━━━━

<b>📌 Полезные команды:</b>

/help — подробная справка
/stats — статистика базы знаний

━━━━━━━━━━━━━━━━━━━━━━

<b>Готов ответить на ваш первый вопрос!</b> 👇"""
    
    await update.message.reply_text(
        welcome_message, 
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help - справка"""
    help_message = """📖 <b>СПРАВКА ПО ИСПОЛЬЗОВАНИЮ</b>

━━━━━━━━━━━━━━━━━━━━━━

<b>🤖 Что я умею:</b>

✓ Отвечать на вопросы о программах иммиграции
✓ Предоставлять точные данные о стоимости и сроках
✓ Объяснять требования к заявителям
✓ Сравнивать различные программы
✓ Давать ссылки на источники (презентации Intermark)

━━━━━━━━━━━━━━━━━━━━━━

<b>⚡️ Как задавать вопросы:</b>

• Пишите на <b>русском или английском</b>
• Формулируйте конкретно: <i>"Сколько стоит гражданство Гренады?"</i>
• Можно спрашивать про несколько стран сразу
• Используйте ключевые слова: стоимость, требования, сроки

━━━━━━━━━━━━━━━━━━━━━━

<b>📌 Важные принципы:</b>

🔹 Использую <b>только проверенную информацию</b> из официальных материалов Intermark
🔹 Если информации нет в базе — <b>честно скажу "не знаю"</b>
🔹 Все ответы содержат <b>ссылки на источники</b>
🔹 Отвечаю <b>структурированно</b> с выделением ключевых данных

━━━━━━━━━━━━━━━━━━━━━━

<b>💡 Примеры хороших вопросов:</b>

<i>По странам:</i>
• Как получить гражданство Malta?
• Сколько стоит Golden Visa в Portugal?
• Требования для ВНЖ во Франции

<i>Сравнительные:</i>
• Какие карибские паспорта самые дешевые?
• Сравни Golden Visa Португалии и Греции

<i>Конкретные детали:</i>
• Сколько времени занимает процесс в Turkey?
• Можно ли включить детей в заявку на Grenada?

━━━━━━━━━━━━━━━━━━━━━━

<b>🔧 Доступные команды:</b>

/start — показать приветствие
/help — эта справка
/stats — статистика базы знаний

━━━━━━━━━━━━━━━━━━━━━━

<b>Готов помочь! Задайте ваш вопрос 👇</b>"""
    
    await update.message.reply_text(
        help_message, 
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats - статистика"""
    uptime = datetime.now() - usage_stats['started']
    
    # Формируем информацию о базе знаний
    if LANGUAGE_UTILS_AVAILABLE and agent_eng:
        docs_info = f"""• Документов (RUS): <b>{len(agent_rus.documents)}</b>
• Документов (ENG): <b>{len(agent_eng.documents)}</b>
• <b>Всего: {len(agent_rus.documents) + len(agent_eng.documents)}</b>"""
        version_info = f"<code>{agent_rus.kb_version or 'unknown'}</code>"
        multilang_status = "✓ активен (RUS/ENG)"
    else:
        docs_info = f"• Документов: <b>{len(agent_rus.documents)}</b>"
        version_info = f"<code>{agent_rus.kb_version or 'unknown'}</code>"
        multilang_status = "⚠️  недоступен"
    
    stats_message = f"""📊 <b>СТАТИСТИКА БОТА</b>

━━━━━━━━━━━━━━━━━━━━━━

<b>📚 База знаний:</b>

{docs_info}
• Стран и программ: <b>40+</b>
• Версия базы: {version_info}
• Последнее обновление: <i>2025-10-15</i>

━━━━━━━━━━━━━━━━━━━━━━

<b>👥 Использование:</b>

• Всего запросов: <b>{usage_stats['total_queries']}</b>
• Уникальных пользователей: <b>{len(usage_stats['users'])}</b>
• Время работы: <b>{uptime.days}д {uptime.seconds//3600}ч {(uptime.seconds//60)%60}м</b>

━━━━━━━━━━━━━━━━━━━━━━

<b>⚡️ Производительность:</b>

• Поиск BM25: <b>~0.1 сек</b>
• Генерация ответа: <b>~2 сек</b>
• Многоязычный поиск: <b>{multilang_status}</b>

━━━━━━━━━━━━━━━━━━━━━━

<b>Готов ответить на ваши вопросы!</b> 🔍"""
    
    await update.message.reply_text(
        stats_message, 
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка обычных сообщений (вопросов и нажатий на кнопки)"""
    user = update.effective_user
    text = update.message.text
    
    # Проверяем, не нажата ли кнопка команды
    if text == "❓ Справка":
        logger.info(f"Button pressed: Справка by {user.username or user.id}")
        await help_command(update, context)
        return
    elif text == "📊 Статистика":
        logger.info(f"Button pressed: Статистика by {user.username or user.id}")
        await stats_command(update, context)
        return
    elif text == "🔄 Перезапуск":
        logger.info(f"Button pressed: Перезапуск by {user.username or user.id}")
        await start_command(update, context)
        return
    
    # Если это не кнопка, обрабатываем как вопрос
    question = text
    
    # Определяем язык запроса
    detected_lang = None
    if language_detector:
        detected_lang = language_detector.detect_from_query(question)
        logger.info(f"Detected language: {detected_lang}")
    
    # Обновляем статистику
    usage_stats['total_queries'] += 1
    usage_stats['users'].add(user.id)
    
    logger.info(f"Question from {user.username or user.id}: {question}")
    
    # Показываем индикатор "печатает..."
    await update.message.chat.send_action("typing")
    
    try:
        # Выбираем правильный агент на основе языка запроса
        if LANGUAGE_UTILS_AVAILABLE and detected_lang:
            selected_agent = agent_rus if detected_lang == "rus" else agent_eng
            logger.info(f"Selected agent: {detected_lang.upper()}")
        else:
            # Fallback - используем русский агент
            selected_agent = agent_rus
        
        # Поиск в базе знаний
        results = selected_agent.search_documents(question, limit=5)
        
        # Проверяем, есть ли результаты
        if not results:
            answer = "❌ Не знаю — нет в материалах.\n\nПо вашему запросу не найдено информации в базе знаний."
        else:
            # Формирование ответа с обработкой rate limits
            answer = selected_agent.format_answer(question, results)
            
            # Если ответ содержит fallback (rate limit), отправляем уведомление
            if "сервис генерации ответов перегружен" in answer:
                # Отправляем уведомление о задержке
                delay_message = """⏳ <b>Сервис временно перегружен</b>

Генерирую ответ... это может занять 1-2 минуты.

<i>Пожалуйста, подождите</i> ⏰"""
                
                await update.message.reply_text(
                    delay_message, 
                    parse_mode='HTML',
                    reply_markup=get_main_keyboard()
                )
                
                # Продолжаем показывать "печатает"
                await update.message.chat.send_action("typing")
        
        # Логируем вопрос с информацией о результате и языке
        answer_found = len(results) > 0 and "не знаю — нет в материалах" not in answer.lower()
        question_logger.log_question(
            user_id=user.id,
            username=user.username,
            question=question,
            answer_found=answer_found,
            response_length=len(answer),
            lang=detected_lang  # Добавляем язык
        )
        
        # Telegram имеет лимит 4096 символов на сообщение
        # Разбиваем длинные ответы
        if len(answer) <= 4096:
            await update.message.reply_text(
                answer, 
                parse_mode='HTML',
                reply_markup=get_main_keyboard()
            )
        else:
            # Разбиваем на части
            parts = []
            current_part = ""
            
            for line in answer.split('\n'):
                if len(current_part) + len(line) + 1 <= 4000:
                    current_part += line + '\n'
                else:
                    parts.append(current_part)
                    current_part = line + '\n'
            
            if current_part:
                parts.append(current_part)
            
            # Отправляем части (клавиатура только на последней части)
            for i, part in enumerate(parts, 1):
                is_last_part = (i == len(parts))
                if i == 1:
                    await update.message.reply_text(
                        f"{part}\n\n<i>[Часть {i}/{len(parts)}]</i>",
                        parse_mode='HTML',
                        reply_markup=get_main_keyboard() if is_last_part else None
                    )
                else:
                    await update.message.reply_text(
                        f"{part}\n\n<i>[Часть {i}/{len(parts)}]</i>",
                        parse_mode='HTML',
                        reply_markup=get_main_keyboard() if is_last_part else None
                    )
        
        logger.info(f"Answer sent to {user.username or user.id}")
        
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        await update.message.reply_text(
            "😔 Извините, произошла ошибка при обработке вашего вопроса.\n"
            "Попробуйте переформулировать или задайте другой вопрос.",
            reply_markup=get_main_keyboard()
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Update {update} caused error {context.error}")


def main():
    """Запуск бота"""
    # Получаем токен из переменной окружения
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not TOKEN:
        print("❌ Ошибка: не найден TELEGRAM_BOT_TOKEN")
        print("\nУстановите токен бота:")
        print("  export TELEGRAM_BOT_TOKEN='ваш_токен_от_BotFather'")
        print("\nИли создайте файл .env:")
        print("  TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather")
        sys.exit(1)
    
    print("=" * 80)
    print("🤖 TELEGRAM-БОТ ДЛЯ БАЗЫ ЗНАНИЙ ПО ИММИГРАЦИИ")
    print("=" * 80)
    # Показываем статистику по агентам
    if LANGUAGE_UTILS_AVAILABLE and agent_eng:
        total_docs = len(agent_rus.documents) + len(agent_eng.documents)
        print(f"📚 База знаний загружена: {total_docs} документов")
        print(f"   🇷🇺 RUS: {len(agent_rus.documents)} документов")
        print(f"   🇬🇧 ENG: {len(agent_eng.documents)} документов")
        print(f"📦 Версия: {agent_rus.kb_version or 'unknown'}")
    else:
        print(f"📚 База знаний загружена: {len(agent_rus.documents)} документов")
        print(f"📦 Версия: {agent_rus.kb_version or 'unknown'}")
    print("🚀 Запуск бота...")
    print("=" * 80)
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Обработчик обычных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    print("✅ Бот запущен и готов к работе!")
    print("💬 Пользователи могут начать общение командой /start")
    print("\nДля остановки нажмите Ctrl+C")
    print("=" * 80)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

