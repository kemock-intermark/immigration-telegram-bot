#!/usr/bin/env python3
"""
Тестовый скрипт для проверки двуязычной системы
"""

import sys
from pathlib import Path
from language_utils import LanguageDetector, LanguageRouter
from chat_agent import KnowledgeAgent

def test_language_detection():
    """Тест определения языка"""
    print("\n" + "="*60)
    print("ТЕСТ 1: Определение языка запросов")
    print("="*60)
    
    detector = LanguageDetector()
    
    test_cases = [
        ("Какие программы карибских паспортов существуют?", "rus"),
        ("Caribbean citizenship programs", "eng"),
        ("Сколько стоит португальский ВНЖ?", "rus"),
        ("Portugal golden visa cost", "eng"),
        ("Турецкое гражданство за инвестиции", "rus"),
        ("Malta citizenship requirements", "eng"),
    ]
    
    passed = 0
    for query, expected in test_cases:
        detected = detector.detect_from_query(query)
        status = "✅" if detected == expected else "❌"
        if detected == expected:
            passed += 1
        print(f"{status} '{query}' → {detected} (ожидалось: {expected})")
    
    print(f"\n📊 Результат: {passed}/{len(test_cases)} тестов пройдено")
    return passed == len(test_cases)


def test_routing():
    """Тест маршрутизации к артефактам"""
    print("\n" + "="*60)
    print("ТЕСТ 2: Маршрутизация к языковым артефактам")
    print("="*60)
    
    knowledge_dir = Path("knowledge")
    router = LanguageRouter(knowledge_dir)
    
    # Проверяем пути
    rus_paths = {
        "docs": router.get_docs_dir("rus"),
        "manifest": router.get_manifest_path("rus")
    }
    
    eng_paths = {
        "docs": router.get_docs_dir("eng"),
        "manifest": router.get_manifest_path("eng")
    }
    
    print("\n🇷🇺 Русские пути:")
    for name, path in rus_paths.items():
        exists = "✅ существует" if path.exists() else "⚠️  не найден"
        print(f"  {name}: {path} {exists}")
    
    print("\n🇬🇧 Английские пути:")
    for name, path in eng_paths.items():
        exists = "✅ существует" if path.exists() else "⚠️  не найден"
        print(f"  {name}: {path} {exists}")
    
    return True


def test_agent_initialization():
    """Тест создания агентов"""
    print("\n" + "="*60)
    print("ТЕСТ 3: Инициализация агентов")
    print("="*60)
    
    knowledge_dir = "knowledge"
    
    try:
        print("\n📚 Создание русского агента...")
        agent_rus = KnowledgeAgent(knowledge_dir, lang="rus")
        print(f"  ✅ Загружено {len(agent_rus.documents)} русских документов")
        print(f"  📦 Версия: {agent_rus.kb_version}")
        
        print("\n📚 Создание английского агента...")
        agent_eng = KnowledgeAgent(knowledge_dir, lang="eng")
        print(f"  ✅ Загружено {len(agent_eng.documents)} английских документов")
        print(f"  📦 Версия: {agent_eng.kb_version}")
        
        print("\n📚 Создание универсального агента (оба языка)...")
        agent_all = KnowledgeAgent(knowledge_dir, lang=None)
        print(f"  ✅ Загружено {len(agent_all.documents)} документов (всего)")
        
        return True
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search():
    """Тест поиска документов"""
    print("\n" + "="*60)
    print("ТЕСТ 4: Поиск документов по языкам")
    print("="*60)
    
    knowledge_dir = "knowledge"
    
    try:
        # Создаем агентов
        agent_rus = KnowledgeAgent(knowledge_dir, lang="rus")
        agent_eng = KnowledgeAgent(knowledge_dir, lang="eng")
        
        test_queries = [
            ("rus", agent_rus, "Какие программы карибских паспортов существуют?"),
            ("eng", agent_eng, "Caribbean citizenship programs"),
            ("rus", agent_rus, "Португальский золотой виз"),
            ("eng", agent_eng, "Portugal golden visa"),
        ]
        
        for lang, agent, query in test_queries:
            print(f"\n🔍 [{lang.upper()}] '{query}'")
            results = agent.search_documents(query, limit=3)
            
            if results:
                print(f"  ✅ Найдено {len(results)} документов:")
                for i, (doc, score) in enumerate(results[:3], 1):
                    doc_lang = doc.get('lang', '?')
                    print(f"    {i}. [{doc_lang.upper()}] {doc['title']} (score: {score:.2f})")
            else:
                print(f"  ⚠️  Документы не найдены")
        
        return True
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_answer_generation():
    """Тест генерации ответов"""
    print("\n" + "="*60)
    print("ТЕСТ 5: Генерация ответов через LLM")
    print("="*60)
    
    knowledge_dir = "knowledge"
    
    try:
        # Проверяем наличие GROQ_API_KEY
        import os
        if not os.getenv("GROQ_API_KEY"):
            print("  ⚠️  GROQ_API_KEY не установлен, пропуск теста LLM")
            return True
        
        # Создаем агента
        agent_rus = KnowledgeAgent(knowledge_dir, lang="rus")
        
        query = "Какие есть программы карибских паспортов?"
        print(f"\n🔍 Вопрос: {query}")
        
        answer = agent_rus.ask(query)
        print(f"\n💬 Ответ (первые 300 символов):\n{answer[:300]}...")
        
        return True
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Запуск всех тестов"""
    print("\n" + "="*60)
    print("🧪 ТЕСТИРОВАНИЕ ДВУЯЗЫЧНОЙ СИСТЕМЫ")
    print("="*60)
    
    tests = [
        ("Определение языка", test_language_detection),
        ("Маршрутизация", test_routing),
        ("Инициализация агентов", test_agent_initialization),
        ("Поиск документов", test_search),
        ("Генерация ответов", test_answer_generation),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Тест '{name}' завершился с ошибкой: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Итоговый отчет
    print("\n" + "="*60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("="*60)
    
    for name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print("\n" + "="*60)
    print(f"Тестов пройдено: {passed}/{total}")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

