#!/usr/bin/env python3
"""
Тестовый скрипт для проверки статуса Groq API
"""

import os
import sys

def test_groq():
    """Тестируем Groq API"""
    print("🧪 Тестирование Groq API...")
    
    # Проверяем наличие API ключа
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        print("❌ GROQ_API_KEY не найден в переменных окружения")
        return False
    
    print(f"✅ API ключ найден: {api_key[:10]}...")
    
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        
        # Простой тест запроса
        print("🔄 Отправляем тестовый запрос...")
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Say 'Hello, test successful!'"}],
            max_tokens=20,
            temperature=0.1
        )
        
        result = response.choices[0].message.content
        print(f"✅ Успешный ответ: {result}")
        
        # Проверяем лимиты
        if hasattr(response, 'usage'):
            usage = response.usage
            print(f"📊 Токены использованы: {usage.total_tokens}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка Groq: {e}")
        
        # Анализируем тип ошибки
        error_str = str(e).lower()
        if "rate limit" in error_str or "429" in error_str:
            print("🚫 Rate limit - нужно подождать")
        elif "unauthorized" in error_str or "401" in error_str:
            print("🔑 Проблема с API ключом")
        elif "model" in error_str:
            print("🤖 Проблема с моделью")
        else:
            print("❓ Неизвестная ошибка")
        
        return False

def test_multi_provider():
    """Тестируем мультипровайдерную систему"""
    print("\n🤖 Тестирование мультипровайдерной системы...")
    
    try:
        from llm_providers import multi_llm, get_llm_status
        
        # Получаем статус
        status = get_llm_status()
        print("📊 Статус провайдеров:")
        for name, info in status.items():
            configured = "✅" if info['configured'] else "❌"
            available = "🟢" if info['available'] else "🔴"
            print(f"  {name}: {configured} {available}")
        
        # Тестируем генерацию ответа
        available_providers = multi_llm.get_available_providers()
        print(f"\n🔍 Доступно провайдеров: {len(available_providers)}")
        
        if len(available_providers) > 0:
            print("🔄 Тестируем генерацию ответа...")
            response = multi_llm.generate_response(
                "You are a helpful assistant.",
                "Say 'Multi-provider test successful!'",
                max_retries=1
            )
            
            if response.error:
                print(f"❌ Ошибка мультипровайдера: {response.error}")
            else:
                print(f"✅ Успешный ответ от {response.provider}: {response.content[:50]}...")
        else:
            print("⚠️ Нет доступных провайдеров")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка мультипровайдера: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 ДИАГНОСТИКА LLM СИСТЕМЫ")
    print("=" * 60)
    
    # Тест Groq
    groq_ok = test_groq()
    
    # Тест мультипровайдера
    multi_ok = test_multi_provider()
    
    print("\n" + "=" * 60)
    print("📋 ИТОГИ:")
    print(f"Groq API: {'✅ OK' if groq_ok else '❌ FAIL'}")
    print(f"Мультипровайдер: {'✅ OK' if multi_ok else '❌ FAIL'}")
    
    if groq_ok and multi_ok:
        print("🎉 Все системы работают!")
        sys.exit(0)
    else:
        print("⚠️ Есть проблемы, требуют внимания")
        sys.exit(1)
