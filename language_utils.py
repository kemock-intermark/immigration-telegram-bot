#!/usr/bin/env python3
"""
Утилиты для определения и работы с языками в двуязычной базе знаний
"""

import re
from typing import Literal, Optional
from pathlib import Path

Language = Literal["rus", "eng"]

class LanguageDetector:
    """Определение языка текста и маршрутизация по языковым артефактам"""
    
    @staticmethod
    def detect_from_text(text: str, threshold: float = 0.30) -> Language:
        """
        Определить язык по тексту
        
        Args:
            text: Текст для анализа
            threshold: Порог доли кириллицы для определения как rus (по умолчанию 30%)
        
        Returns:
            "rus" если доля кириллицы >= threshold, иначе "eng"
        """
        if not text:
            return "eng"
        
        # Считаем кириллические символы
        cyrillic_pattern = re.compile(r'[а-яА-ЯёЁ]')
        total_letters = len(re.findall(r'[a-zA-Zа-яА-ЯёЁ]', text))
        
        if total_letters == 0:
            return "eng"
        
        cyrillic_count = len(cyrillic_pattern.findall(text))
        cyrillic_ratio = cyrillic_count / total_letters
        
        return "rus" if cyrillic_ratio >= threshold else "eng"
    
    @staticmethod
    def detect_from_query(query: str) -> Language:
        """
        Определить язык запроса пользователя
        
        Правило: если есть хотя бы 1 кириллический символ → rus, иначе eng
        
        Args:
            query: Запрос пользователя
        
        Returns:
            "rus" или "eng"
        """
        cyrillic_pattern = re.compile(r'[а-яА-ЯёЁ]')
        return "rus" if cyrillic_pattern.search(query) else "eng"
    
    @staticmethod
    def get_source_language(source_path: Path) -> Language:
        """
        Определить язык исходного файла по его расположению
        
        Правила:
        - raw/rus/* → rus
        - raw/eng/* → eng
        - raw/* (legacy) → определяется по содержимому при обработке
        
        Args:
            source_path: Путь к файлу источника
        
        Returns:
            "rus" или "eng", или None для legacy файлов
        """
        parts = source_path.parts
        
        if 'raw' in parts:
            raw_index = parts.index('raw')
            if raw_index + 1 < len(parts):
                next_part = parts[raw_index + 1]
                if next_part == 'rus':
                    return "rus"
                elif next_part == 'eng':
                    return "eng"
        
        return None  # Legacy - требуется определение по содержимому


class LanguageRouter:
    """Маршрутизация к языковым артефактам"""
    
    def __init__(self, knowledge_dir: Path):
        self.knowledge_dir = Path(knowledge_dir)
    
    def get_docs_dir(self, lang: Language) -> Path:
        """Получить директорию документов для языка"""
        return self.knowledge_dir / lang
    
    def get_manifest_path(self, lang: Language) -> Path:
        """Получить путь к manifest для языка"""
        return self.knowledge_dir / f"manifest.{lang}.json"
    
    def get_index_path(self, lang: Language) -> Path:
        """Получить путь к 00_index для языка"""
        return self.knowledge_dir / f"00_index.{lang}.md"
    
    def get_kw_index_path(self, lang: Language) -> Path:
        """Получить путь к индексу ключевых слов для языка"""
        return self.knowledge_dir / f"kw_index.{lang}.jsonl"
    
    def get_emb_index_pattern(self, lang: Language) -> str:
        """Получить паттерн для эмбеддингов"""
        return str(self.knowledge_dir / f"emb_index.{lang}.*")
    
    def get_chunks_index_path(self, lang: Language) -> Path:
        """Получить путь к индексу чанков"""
        return self.knowledge_dir / f"chunks.{lang}.idx"
    
    def ensure_structure(self):
        """Создать структуру директорий для двуязычной системы"""
        # Создаем языковые директории для документов
        for lang in ["rus", "eng"]:
            (self.knowledge_dir / lang).mkdir(exist_ok=True)
        
        # Создаем директории источников
        raw_dir = self.knowledge_dir.parent / 'raw'
        (raw_dir / 'rus').mkdir(parents=True, exist_ok=True)
        (raw_dir / 'eng').mkdir(parents=True, exist_ok=True)
        
        print("✅ Двуязычная структура директорий создана")


def format_source_attribution(source_file: str, lang: Language, 
                              slides_start: int, slides_end: int) -> str:
    """
    Форматировать атрибуцию источника с учетом языка
    
    Args:
        source_file: Имя файла источника
        lang: Язык источника
        slides_start: Начальный слайд
        slides_end: Конечный слайд
    
    Returns:
        Форматированная строка атрибуции
    """
    # Определяем правильный путь
    if source_file.startswith('raw/'):
        # Уже содержит путь
        path = source_file
    else:
        # Добавляем язык в путь
        path = f"raw/{lang}/{source_file}"
    
    # Выбираем термин для страниц в зависимости от языка
    pages_term = "слайды" if lang == "rus" else "slides"
    
    return f"{path} → {pages_term} {slides_start}–{slides_end}"


if __name__ == "__main__":
    # Тесты
    detector = LanguageDetector()
    
    tests = [
        ("Какие программы карибских паспортов?", "rus"),
        ("Caribbean citizenship programs", "eng"),
        ("Portugal golden visa", "eng"),
        ("Сколько стоит Golden Visa?", "rus"),
        ("Malta citizenship requirements", "eng"),
        ("123456", "eng"),  # Нет букв
    ]
    
    print("🧪 Тестирование определения языка:\n")
    for query, expected in tests:
        detected = detector.detect_from_query(query)
        status = "✓" if detected == expected else "✗"
        print(f"{status} '{query}' → {detected} (ожидалось: {expected})")

