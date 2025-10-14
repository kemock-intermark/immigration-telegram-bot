#!/usr/bin/env python3
"""
Telegram-бот для работы с базой знаний по иммиграции (версия для Glitch.com)
Включает встроенный веб-сервер для keep-alive
"""

import os
import sys
import logging
import threading
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# Импортируем наш существующий агент
from chat_agent import KnowledgeAgent

# Для Telegram бота
try:
    from telegram import Update
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

# Инициализация агента знаний
KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
agent = KnowledgeAgent(str(KNOWLEDGE_DIR))

# Статистика использования
usage_stats = {
    'total_queries': 0,
    'users': set(),
    'started': datetime.now()
}


# Keep-alive веб-сервер
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Immigration Bot Status</title>
            <meta charset="utf-8">
        </head>
        <body>
            <h1>🤖 Immigration Telegram Bot</h1>
            <p><strong>Status:</strong> ✅ Running</p>
            <p><strong>Total queries:</strong> {usage_stats['total_queries']}</p>
            <p><strong>Users:</strong> {len(usage_stats['users'])}</p>
            <p><strong>Uptime:</strong> {datetime.now() - usage_stats['started']}</p>
            <p><strong>Documents:</strong> {len(agent.documents)}</p>
            <hr>
            <p><small>This endpoint keeps the bot alive on Glitch.com</small></p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        # Отключаем логи HTTP запросов
        pass


def run_keep_alive_server():
    """Запустить keep-alive веб-сервер"""
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), KeepAliveHandler)
    logger.info(f"Keep-alive server started on port {port}")
    server.serve_forever()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - приветствие"""
    user = update.effective_user
    usage_stats['users'].add(user.id)
    
    welcome_message = f"""
👋 Здравствуйте, {user.first_name}!

Я — бот-консультант по программам иммиграции и получения гражданства.

📚 **Моя база знаний:**
• {len(agent.documents)} документов
• 43 страны
• Информация о гражданстве, ВНЖ, Golden Visa

💬 **Как со мной работать:**
Просто задавайте вопросы на русском или английском языке.

**Примеры вопросов:**
• Malta citizenship requirements
• Сколько стоит Golden Visa в Греции?
• Какие программы есть в Caribbean?
• Portugal residence permit

📌 **Команды:**
/start - это сообщение
/help - справка
/stats - статистика базы знаний

⚠️ **Примечание:** Бот размещён на бесплатном хостинге. Первый ответ может занять 10-15 секунд (пробуждение).

Задайте свой первый вопрос! 👇
"""
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help - справка"""
    help_message = """
📖 **СПРАВКА**

**Что я умею:**
• Отвечать на вопросы о программах иммиграции
• Предоставлять информацию о требованиях и стоимости
• Давать ссылки на источники (презентации Intermark)

**Важно:**
✅ Я использую только проверенную информацию из презентаций
✅ Если информации нет в базе, я честно скажу "не знаю"
✅ Все ответы содержат ссылки на источники

**Примеры вопросов:**
• Как получить гражданство Malta?
• Golden Visa Greece требования
• Сколько стоит ВНЖ в Portugal?
• Программы citizenship в Caribbean
• Turkey residence permit process

**Команды:**
/start - перезапуск
/help - эта справка
/stats - статистика

Просто пишите мне вопросы! 💬
"""
    await update.message.reply_text(help_message)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats - статистика"""
    uptime = datetime.now() - usage_stats['started']
    
    stats_message = f"""
📊 **СТАТИСТИКА**

**База знаний:**
• Документов: {len(agent.documents)}
• Стран: 43
• Версия: {agent.kb_version or 'unknown'}

**Использование бота:**
• Всего запросов: {usage_stats['total_queries']}
• Уникальных пользователей: {len(usage_stats['users'])}
• Работает: {uptime.days}д {uptime.seconds//3600}ч {(uptime.seconds//60)%60}м

**Производительность:**
• Поиск: ~0.07 сек
• Кэширование: активно

**Хостинг:** Glitch.com (бесплатный)
⚠️ Может "засыпать" при простое

🔍 Задайте вопрос!
"""
    await update.message.reply_text(stats_message)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка обычных сообщений (вопросов)"""
    user = update.effective_user
    question = update.message.text
    
    # Обновляем статистику
    usage_stats['total_queries'] += 1
    usage_stats['users'].add(user.id)
    
    logger.info(f"Question from {user.username or user.id}: {question}")
    
    # Показываем индикатор "печатает..."
    await update.message.chat.send_action("typing")
    
    try:
        # Поиск в базе знаний
        results = agent.search_documents(question, limit=5)
        
        # Формирование ответа
        answer = agent.format_answer(question, results)
        
        # Telegram имеет лимит 4096 символов на сообщение
        if len(answer) <= 4096:
            await update.message.reply_text(answer, parse_mode='Markdown')
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
            
            # Отправляем части
            for i, part in enumerate(parts, 1):
                await update.message.reply_text(
                    f"{part}\n\n_[Часть {i}/{len(parts)}]_",
                    parse_mode='Markdown'
                )
        
        logger.info(f"Answer sent to {user.username or user.id}")
        
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        await update.message.reply_text(
            "😔 Извините, произошла ошибка при обработке вашего вопроса.\n"
            "Попробуйте переформулировать или задайте другой вопрос."
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
        print("\nДобавьте токен в файл .env на Glitch:")
        print("  TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather")
        sys.exit(1)
    
    print("=" * 80)
    print("🤖 TELEGRAM-БОТ ДЛЯ БАЗЫ ЗНАНИЙ ПО ИММИГРАЦИИ (Glitch Edition)")
    print("=" * 80)
    print(f"📚 База знаний загружена: {len(agent.documents)} документов")
    print(f"📦 Версия: {agent.kb_version or 'unknown'}")
    print("🌐 Запуск keep-alive сервера...")
    
    # Запускаем keep-alive сервер в отдельном потоке
    keep_alive_thread = threading.Thread(target=run_keep_alive_server, daemon=True)
    keep_alive_thread.start()
    
    print("🚀 Запуск Telegram бота...")
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
    print("🌐 Keep-alive endpoint: http://ваш-проект.glitch.me")
    print("\nДля остановки нажмите Ctrl+C")
    print("=" * 80)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

