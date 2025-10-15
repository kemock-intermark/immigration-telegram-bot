#!/usr/bin/env python3
"""
Мультипровайдерная система LLM с автоматическим переключением
Поддерживает Groq, OpenAI, Anthropic, Ollama
"""

import os
import time
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class LLMResponse:
    """Стандартизированный ответ от LLM"""
    content: str
    provider: str
    model: str
    tokens_used: Optional[int] = None
    error: Optional[str] = None

class BaseLLMProvider:
    """Базовый класс для LLM провайдеров"""
    
    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model
        self.is_available = True
        self.last_error = None
    
    def is_configured(self) -> bool:
        """Проверить, настроен ли провайдер"""
        raise NotImplementedError
    
    def generate_response(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Генерировать ответ"""
        raise NotImplementedError
    
    def handle_error(self, error: Exception) -> None:
        """Обработать ошибку"""
        self.last_error = str(error)
        if "rate limit" in str(error).lower() or "429" in str(error):
            self.is_available = False
            print(f"⚠️  {self.name} временно недоступен: {error}")

class GroqProvider(BaseLLMProvider):
    """Groq LLM провайдер"""
    
    def __init__(self):
        super().__init__("Groq", "llama-3.3-70b-versatile")
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Инициализировать Groq клиент"""
        try:
            from groq import Groq
            api_key = os.getenv("GROQ_API_KEY")
            if api_key:
                self.client = Groq(api_key=api_key)
            else:
                self.client = None
        except ImportError:
            self.client = None
    
    def is_configured(self) -> bool:
        return self.client is not None and os.getenv("GROQ_API_KEY") is not None
    
    def generate_response(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        if not self.is_configured():
            return LLMResponse("", self.name, self.model, error="Не настроен")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if hasattr(response, 'usage') else None
            
            return LLMResponse(content, self.name, self.model, tokens)
            
        except Exception as e:
            self.handle_error(e)
            return LLMResponse("", self.name, self.model, error=str(e))

class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM провайдер"""
    
    def __init__(self):
        super().__init__("OpenAI", "gpt-3.5-turbo")
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Инициализировать OpenAI клиент"""
        try:
            import openai
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.client = openai.OpenAI(api_key=api_key)
            else:
                self.client = None
        except ImportError:
            self.client = None
    
    def is_configured(self) -> bool:
        return self.client is not None and os.getenv("OPENAI_API_KEY") is not None
    
    def generate_response(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        if not self.is_configured():
            return LLMResponse("", self.name, self.model, error="Не настроен")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if hasattr(response, 'usage') else None
            
            return LLMResponse(content, self.name, self.model, tokens)
            
        except Exception as e:
            self.handle_error(e)
            return LLMResponse("", self.name, self.model, error=str(e))

class OllamaProvider(BaseLLMProvider):
    """Ollama локальный провайдер"""
    
    def __init__(self):
        super().__init__("Ollama", "llama3.1:8b")
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    def is_configured(self) -> bool:
        """Проверить доступность Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def generate_response(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        if not self.is_configured():
            return LLMResponse("", self.name, self.model, error="Ollama недоступен")
        
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 1500
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("message", {}).get("content", "")
                tokens = data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                
                return LLMResponse(content, self.name, self.model, tokens)
            else:
                raise Exception(f"Ollama error: {response.status_code}")
                
        except Exception as e:
            self.handle_error(e)
            return LLMResponse("", self.name, self.model, error=str(e))

class MultiLLMProvider:
    """Мультипровайдерная система с автоматическим переключением"""
    
    def __init__(self):
        self.providers = [
            GroqProvider(),
            OpenAIProvider(),
            OllamaProvider(),
        ]
        self.current_provider_index = 0
        self.retry_counts = {provider.name: 0 for provider in self.providers}
        self.max_retries_per_provider = 2
        self.last_reset_time = {provider.name: 0 for provider in self.providers}
        self.reset_interval = 3600  # 1 час в секундах
    
    def _should_reset_provider(self, provider_name: str) -> bool:
        """Проверить, нужно ли сбросить статус провайдера"""
        import time
        current_time = time.time()
        last_reset = self.last_reset_time.get(provider_name, 0)
        return (current_time - last_reset) > self.reset_interval
    
    def _auto_reset_providers(self):
        """Автоматически сбросить статус провайдеров через определенное время"""
        import time
        current_time = time.time()
        
        for provider in self.providers:
            if not provider.is_available and self._should_reset_provider(provider.name):
                # Проверяем, действительно ли провайдер недоступен
                try:
                    # Простой тест доступности
                    if provider.name == "Groq" and provider.is_configured():
                        # Для Groq делаем простой запрос
                        test_response = provider.generate_response(
                            "Test", "Say 'test'", max_retries=1
                        )
                        if not test_response.error or "rate limit" not in test_response.error.lower():
                            provider.is_available = True
                            self.retry_counts[provider.name] = 0
                            provider.last_error = None
                            self.last_reset_time[provider.name] = current_time
                            print(f"🔄 {provider.name} автоматически восстановлен")
                    
                except Exception as e:
                    # Если тест не прошел, оставляем как есть
                    pass

    def get_available_providers(self) -> list:
        """Получить список доступных провайдеров"""
        # Автоматически сбрасываем провайдеров если прошло достаточно времени
        self._auto_reset_providers()
        
        available = []
        for provider in self.providers:
            if provider.is_configured() and provider.is_available:
                available.append(provider)
        return available
    
    def generate_response(self, system_prompt: str, user_prompt: str, max_retries: int = 3) -> LLMResponse:
        """Генерировать ответ с автоматическим переключением между провайдерами"""
        
        available_providers = self.get_available_providers()
        
        if not available_providers:
            return LLMResponse(
                "", 
                "None", 
                "None", 
                error="Все LLM провайдеры недоступны"
            )
        
        for attempt in range(max_retries):
            # Выбираем провайдера (начинаем с текущего, потом перебираем)
            for i in range(len(available_providers)):
                provider_index = (self.current_provider_index + i) % len(available_providers)
                provider = available_providers[provider_index]
                
                # Пропускаем провайдеров, которые исчерпали попытки
                if self.retry_counts[provider.name] >= self.max_retries_per_provider:
                    continue
                
                print(f"🔄 Попытка {attempt + 1}/{max_retries} с {provider.name}...")
                
                response = provider.generate_response(system_prompt, user_prompt)
                
                if response.error:
                    print(f"⚠️  {provider.name} ошибка: {response.error}")
                    self.retry_counts[provider.name] += 1
                    
                    # Если rate limit, временно отключаем провайдера
                    if "rate limit" in response.error.lower() or "429" in response.error:
                        provider.is_available = False
                        print(f"🚫 {provider.name} временно отключен из-за rate limit")
                    
                    continue
                
                # Успешный ответ
                print(f"✅ Ответ получен от {provider.name}")
                self.current_provider_index = provider_index
                self.retry_counts[provider.name] = 0  # Сбрасываем счетчик при успехе
                
                return response
            
            # Если все провайдеры недоступны, ждем перед следующей попыткой
            if attempt < max_retries - 1:
                delay = 2 ** attempt  # Exponential backoff
                print(f"⏳ Ожидание {delay} сек перед следующей попыткой...")
                time.sleep(delay)
        
        # Все попытки исчерпаны
        return LLMResponse(
            "", 
            "None", 
            "None", 
            error="Все попытки исчерпаны. Все LLM провайдеры недоступны."
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус всех провайдеров"""
        status = {}
        for provider in self.providers:
            status[provider.name] = {
                "configured": provider.is_configured(),
                "available": provider.is_available,
                "retry_count": self.retry_counts[provider.name],
                "last_error": provider.last_error
            }
        return status
    
    def reset_provider(self, provider_name: str) -> None:
        """Сбросить статус провайдера (для ручного восстановления)"""
        for provider in self.providers:
            if provider.name == provider_name:
                provider.is_available = True
                self.retry_counts[provider.name] = 0
                provider.last_error = None
                print(f"🔄 {provider_name} сброшен и готов к использованию")

# Глобальный экземпляр мультипровайдера
multi_llm = MultiLLMProvider()

def get_llm_response(system_prompt: str, user_prompt: str) -> Optional[str]:
    """Удобная функция для получения ответа от LLM"""
    response = multi_llm.generate_response(system_prompt, user_prompt)
    
    if response.error:
        print(f"❌ LLM ошибка: {response.error}")
        return None
    
    return response.content

def get_llm_status() -> Dict[str, Any]:
    """Получить статус всех LLM провайдеров"""
    return multi_llm.get_status()
