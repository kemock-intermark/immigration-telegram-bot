#!/usr/bin/env python3
"""
Демонстрация работы чат-агента
Показывает примеры вопросов и ответов
"""

from pathlib import Path
import subprocess
import time

def ask_question(question: str):
    """Задать вопрос агенту и показать ответ"""
    print("=" * 80)
    print(f"❓ ВОПРОС: {question}")
    print("=" * 80)
    
    result = subprocess.run(
        ['python3', 'chat_agent.py', question],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    
    # Убираем загрузочные сообщения из вывода
    output = result.stdout
    lines = output.split('\n')
    answer_started = False
    answer_lines = []
    
    for line in lines:
        if 'Вопрос:' in line:
            answer_started = True
            continue
        if answer_started:
            answer_lines.append(line)
    
    print('\n'.join(answer_lines))
    print()
    time.sleep(0.5)

def main():
    print()
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║                    ДЕМОНСТРАЦИЯ ЧАТА-АГЕНТА                               ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    print()
    print("Примеры вопросов и ответов агента на основе базы знаний.")
    print()
    
    # Примеры вопросов
    questions = [
        "гражданство Malta",
        "Portugal residence permit",
        "citizenship investment Caribbean",
        "Golden Visa Greece",
        "Turkey citizenship investment",
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n┌─ ПРИМЕР {i}/{len(questions)} {'─' * (80 - len(f' ПРИМЕР {i}/{len(questions)} ') - 3)}┐")
        print()
        ask_question(question)
        print(f"└{'─' * 78}┘")
    
    print()
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║                       ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА                              ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    print()
    print("💡 Для интерактивного режима запустите напрямую в терминале:")
    print("   python3 chat_agent.py")
    print()
    print("💡 Для одиночного вопроса:")
    print("   python3 chat_agent.py \"ваш вопрос\"")
    print()
    print("📊 Просмотр неотвеченных вопросов:")
    print("   cat knowledge/_unanswered_log.md")
    print()

if __name__ == "__main__":
    main()


