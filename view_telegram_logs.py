#!/usr/bin/env python3
"""
Просмотр и анализ логов вопросов из Telegram
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict


def load_logs(log_file: Path):
    """Загрузить все логи"""
    if not log_file.exists():
        print(f"❌ Файл логов не найден: {log_file}")
        return []
    
    logs = []
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                logs.append(json.loads(line))
            except:
                continue
    
    return logs


def show_summary(logs):
    """Показать сводку"""
    if not logs:
        print("📊 Логов пока нет")
        return
    
    total = len(logs)
    answered = sum(1 for log in logs if log.get('answer_found'))
    not_answered = total - answered
    
    users = Counter(log.get('username') for log in logs)
    dates = Counter(log.get('date') for log in logs)
    
    print("=" * 80)
    print("📊 СВОДКА ПО ВОПРОСАМ ИЗ TELEGRAM")
    print("=" * 80)
    print(f"\n📈 Всего вопросов: {total}")
    print(f"✅ С ответом: {answered} ({answered/total*100:.1f}%)")
    print(f"❌ Без ответа: {not_answered} ({not_answered/total*100:.1f}%)")
    print(f"\n👥 Уникальных пользователей: {len(users)}")
    
    print(f"\n📅 По датам:")
    for date, count in sorted(dates.items(), reverse=True)[:7]:
        print(f"   {date}: {count} вопросов")
    
    print(f"\n🔝 Топ-5 активных пользователей:")
    for username, count in users.most_common(5):
        print(f"   @{username}: {count} вопросов")


def show_recent(logs, limit=20):
    """Показать последние вопросы"""
    print("\n" + "=" * 80)
    print(f"📝 ПОСЛЕДНИЕ {min(limit, len(logs))} ВОПРОСОВ")
    print("=" * 80)
    
    for log in logs[-limit:]:
        status = "✅" if log.get('answer_found') else "❌"
        timestamp = log.get('time', '')
        username = log.get('username', 'anonymous')
        question = log.get('question', '')
        
        print(f"\n{status} [{timestamp}] @{username}")
        print(f"   {question}")


def show_unanswered(logs):
    """Показать неотвеченные вопросы"""
    unanswered = [log for log in logs if not log.get('answer_found')]
    
    if not unanswered:
        print("\n✅ Все вопросы получили ответ!")
        return
    
    print("\n" + "=" * 80)
    print(f"❌ НЕОТВЕЧЕННЫЕ ВОПРОСЫ ({len(unanswered)})")
    print("=" * 80)
    
    # Группируем похожие вопросы
    questions = [log.get('question', '').lower() for log in unanswered]
    question_counts = Counter(questions)
    
    for question, count in question_counts.most_common(20):
        print(f"\n[{count}x] {question}")


def show_popular_topics(logs):
    """Показать популярные темы"""
    print("\n" + "=" * 80)
    print("🔥 ПОПУЛЯРНЫЕ ТЕМЫ")
    print("=" * 80)
    
    # Извлекаем ключевые слова из вопросов
    keywords = []
    for log in logs:
        question = log.get('question', '').lower()
        # Простое извлечение слов (можно улучшить)
        words = question.split()
        keywords.extend([w for w in words if len(w) > 3])
    
    keyword_counts = Counter(keywords)
    
    print("\n🔑 Топ-20 ключевых слов:")
    for keyword, count in keyword_counts.most_common(20):
        print(f"   {keyword}: {count}")


def export_to_csv(logs, output_file: str):
    """Экспортировать в CSV"""
    import csv
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'timestamp', 'date', 'time', 'user_id', 'username',
            'question', 'answer_found', 'response_length'
        ])
        writer.writeheader()
        writer.writerows(logs)
    
    print(f"\n✅ Экспортировано в {output_file}")


def main():
    log_file = Path(__file__).parent / "knowledge" / "telegram_questions.jsonl"
    
    print("\n╔════════════════════════════════════════════════════════════════════════════╗")
    print("║              📊 АНАЛИЗ ВОПРОСОВ ИЗ TELEGRAM                               ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    
    logs = load_logs(log_file)
    
    if not logs:
        print("\n⚠️  Логов пока нет. Задайте несколько вопросов боту в Telegram!")
        return
    
    # Показываем разные отчёты
    show_summary(logs)
    show_recent(logs, limit=10)
    show_unanswered(logs)
    show_popular_topics(logs)
    
    # Предлагаем экспорт
    print("\n" + "=" * 80)
    print("\n💾 Для экспорта в CSV:")
    print(f"   python {Path(__file__).name} export")
    
    if len(sys.argv) > 1 and sys.argv[1] == 'export':
        export_to_csv(logs, "telegram_questions.csv")


if __name__ == "__main__":
    main()

