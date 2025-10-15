#!/usr/bin/env python3
"""
Улучшенный агент базы знаний с BM25 поиском
Версия 3.0 - правильная архитектура без костылей
Версия 3.1 - двуязычная поддержка (rus/eng)
"""

import json
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Literal
from collections import defaultdict
from functools import lru_cache

# Утилиты для работы с языками
try:
    from language_utils import LanguageDetector, LanguageRouter, Language
    LANGUAGE_UTILS_AVAILABLE = True
except ImportError:
    LANGUAGE_UTILS_AVAILABLE = False
    Language = Literal["rus", "eng"]
    print("⚠️  language_utils не найден. Двуязычность отключена.")

# BM25 для правильного поиска
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    print("⚠️  rank_bm25 не установлен. Установите: pip install rank-bm25")

# LLM для генерации ответов
try:
    from groq import Groq
    import os
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("⚠️  Groq не установлен.")


class TextNormalizer:
    """Нормализация текста для лучшего поиска"""
    
    def __init__(self):
        # Двунаправленный словарь переводов: RU ↔ EN
        # Это позволяет искать на любом языке
        self.translations = {
            # Страны (корень слова для русского → английский)
            'portugal': ['португал', 'portugal'],
            'greece': ['грец', 'греч', 'греческ', 'greece'],
            'turkey': ['турц', 'турец', 'турецк', 'turkey'],
            'grenada': ['гренад', 'grenada'],
            'malta': ['мальт', 'malta'],
            'cyprus': ['кипр', 'cyprus'],
            'spain': ['испан', 'spain'],
            'paraguay': ['парагва', 'paraguay'],
            'vanuatu': ['вануату', 'vanuatu'],
            'dominica': ['доминик', 'dominica'],
            'antigua': ['антигуа', 'antigua'],
            'barbuda': ['барбуд', 'barbuda'],
            'caribbean': ['карибск', 'caribbean'],
            'saint kitts': ['сент киттс', 'сент китс', 'saint kitts', 'st kitts'],
            'saint lucia': ['сент люси', 'сент лючи', 'saint lucia', 'st lucia'],
            'france': ['франц', 'france'],
            'germany': ['герман', 'germany', 'deutschland'],
            'italy': ['итал', 'italy'],
            'austria': ['австр', 'austria'],
            'hungary': ['венгр', 'hungary'],
            'bulgaria': ['болгар', 'bulgaria'],
            'serbia': ['серб', 'serbia'],
            'montenegro': ['черногор', 'montenegro'],
            'latvia': ['латв', 'latvia'],
            'slovenia': ['словен', 'slovenia'],
            'luxembourg': ['люксембург', 'luxembourg'],
            'canada': ['канад', 'canada'],
            'usa': ['сша', 'usa', 'америк'],
            'uk': ['великобритан', 'британ', 'uk', 'united kingdom'],
            'egypt': ['египт', 'egypt'],
            'nauru': ['науру', 'nauru'],
            'sao tome': ['сан том', 'sao tome'],
            
            # Программы иммиграции
            'citizenship': ['гражданств', 'citizenship', 'паспорт', 'passport'],
            'residence permit': ['внж', 'вид на жительств', 'residence permit', 'виз', 'visa'],
            'permanent residence': ['пмж', 'постоянн проживан', 'permanent residence'],
            'golden visa': ['золот виз', 'голден виз', 'golden visa'],
            'investment': ['инвестиц', 'investment'],
            'digital nomad': ['цифров кочевник', 'digital nomad'],
            'startup': ['стартап', 'startup'],
            'business': ['бизнес', 'business'],
            
            # Общие термины
            'cost': ['стоимост', 'цен', 'cost', 'price'],
            'requirements': ['требован', 'услов', 'requirements', 'conditions'],
            'timeline': ['срок', 'timeline'],
        }
        
        # Создаем паттерны для замены (старая логика, но теперь генерируется автоматически)
        self.replacements = {}
        for english_key, variants in self.translations.items():
            for variant in variants:
                # Добавляем паттерн с окончаниями
                pattern = variant.replace(' ', r'\s+') + r'\w*'
                self.replacements[pattern] = english_key.replace(' ', '_')
        
    def normalize(self, text: str) -> str:
        """Нормализовать текст"""
        text = text.lower()
        
        # Применяем замены
        for pattern, replacement in self.replacements.items():
            text = re.sub(pattern, replacement, text)
        
        # Убираем лишние символы
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Убираем двойные пробелы
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def tokenize(self, text: str) -> List[str]:
        """Разбить на токены"""
        normalized = self.normalize(text)
        tokens = normalized.split()
        # Фильтруем слишком короткие слова (стоп-слова)
        tokens = [t for t in tokens if len(t) > 2]
        return tokens


class KnowledgeAgentV3:
    """Улучшенный агент с BM25 поиском и двуязычной поддержкой"""
    
    def __init__(self, knowledge_dir: str, lang: Optional[Language] = None, auto_detect_lang: bool = True):
        """
        Инициализация агента
        
        Args:
            knowledge_dir: Путь к директории knowledge/
            lang: Язык для загрузки ("rus" или "eng"). Если None - загружаются оба
            auto_detect_lang: Автоматически определять язык запросов (по умолчанию True)
        """
        self.knowledge_dir = Path(knowledge_dir)
        self.documents = []
        self.normalizer = TextNormalizer()
        self.bm25 = None
        self.tokenized_corpus = []
        self.kb_version = None
        self.lang = lang  # Текущий язык (или None для обоих)
        self.auto_detect_lang = auto_detect_lang
        
        # Инициализация языковых утилит
        if LANGUAGE_UTILS_AVAILABLE:
            self.language_detector = LanguageDetector()
            self.language_router = LanguageRouter(self.knowledge_dir)
        else:
            self.language_detector = None
            self.language_router = None
        
        # LLM клиент
        self.groq_client = None
        if GROQ_AVAILABLE:
            groq_api_key = os.getenv('GROQ_API_KEY')
            if groq_api_key:
                try:
                    self.groq_client = Groq(api_key=groq_api_key)
                except Exception as e:
                    print(f"⚠️  Не удалось инициализировать Groq: {e}")
        
        self.load_knowledge_base()
    
    def load_knowledge_base(self):
        """Загрузить базу знаний с учетом языка"""
        lang_label = f" ({self.lang.upper()})" if self.lang else ""
        print(f"📚 Загрузка базы знаний{lang_label}...")
        
        # Загружаем версию из manifest (с учетом языка)
        self._load_manifest()
        
        # Определяем директории для сканирования
        search_dirs = self._get_search_directories()
        
        # Загружаем все .md файлы
        md_files = []
        for search_dir in search_dirs:
            for md_file in search_dir.rglob("*.md"):
                if not md_file.name.startswith(('00_', '_')):
                    md_files.append(md_file)
        
        # Загружаем документы
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                doc = self.extract_metadata_and_content(content, md_file)
                if doc:
                    # Фильтрация по языку (если задан)
                    if self.lang is None or doc.get('lang') == self.lang:
                        self.documents.append(doc)
            except Exception as e:
                print(f"⚠️  Ошибка загрузки {md_file.name}: {e}")
        
        print(f"✅ Загружено {len(self.documents)} документов{lang_label}")
        
        # Строим BM25 индекс
        if BM25_AVAILABLE and self.documents:
            print("🔍 Построение BM25 индекса...")
            self.build_bm25_index()
            print("✅ BM25 индекс готов")
    
    def _load_manifest(self):
        """Загрузить manifest с учетом языка"""
        if self.lang and self.language_router:
            # Язык задан - загружаем языковой manifest
            manifest_path = self.language_router.get_manifest_path(self.lang)
        else:
            # Язык не задан - загружаем общий manifest (legacy)
            manifest_path = self.knowledge_dir / 'manifest.json'
        
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                    self.kb_version = manifest.get('version', 'unknown')
                    print(f"📦 Версия базы: {self.kb_version}")
            except Exception as e:
                print(f"⚠️  Ошибка загрузки manifest: {e}")
                self.kb_version = 'unknown'
        else:
            self.kb_version = 'unknown'
    
    def _get_search_directories(self) -> List[Path]:
        """Определить директории для поиска документов"""
        if self.lang and self.language_router:
            # Язык задан - загружаем только из языковой директории
            lang_dir = self.language_router.get_docs_dir(self.lang)
            if lang_dir.exists():
                return [lang_dir]
            else:
                print(f"⚠️  Языковая директория {lang_dir} не найдена")
                return []
        else:
            # Язык не задан - загружаем из корня (legacy) и из обеих языковых папок (если есть)
            dirs = [self.knowledge_dir]
            if self.language_router:
                for lang in ["rus", "eng"]:
                    lang_dir = self.language_router.get_docs_dir(lang)
                    if lang_dir.exists():
                        dirs.append(lang_dir)
            return dirs
    
    def extract_metadata_and_content(self, content: str, file_path: Path) -> Optional[Dict]:
        """Извлечь метаданные и контент"""
        try:
            # Разделяем метаданные и тело
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    metadata_str = parts[1]
                    body = parts[2].strip()
                else:
                    return None
            else:
                return None
            
            # Парсим метаданные
            doc = {'body': body, 'file_path': str(file_path)}
            
            for line in metadata_str.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    if key in ['title', 'summary', 'category', 'subcategory', 'lang']:
                        doc[key] = value
            
            # Извлекаем tags (могут содержать и русские, и английские термины)
            tags_match = re.search(r'tags:\s*\[(.*?)\]', metadata_str)
            if tags_match:
                tags_str = tags_match.group(1)
                # Парсим список тегов
                tags = [t.strip().strip('"').strip("'") for t in tags_str.split(',')]
                doc['tags'] = tags
            
            # Извлекаем source файлы
            source_match = re.search(r'- path:\s*"([^"]+)"', metadata_str)
            if source_match:
                doc['source_file'] = source_match.group(1).replace('raw/', '')
            
            # Извлекаем слайды
            slides_match = re.search(r'slides:\s*\[(\d+)-(\d+)\]', metadata_str)
            if slides_match:
                doc['slides_start'] = slides_match.group(1)
                doc['slides_end'] = slides_match.group(2)
            
            return doc
            
        except Exception as e:
            print(f"⚠️  Ошибка парсинга {file_path.name}: {e}")
            return None
    
    def _get_multilingual_terms(self, title: str, category: str, subcategory: str) -> List[str]:
        """Получить многоязычные синонимы для терминов документа"""
        terms = []
        
        # Собираем все слова из title, category, subcategory
        all_text = f"{title} {category} {subcategory}".lower()
        words = re.findall(r'\w+', all_text)
        
        # Для каждого слова ищем переводы в словаре
        for word in words:
            if len(word) < 3:  # Игнорируем короткие слова
                continue
            
            # Ищем совпадения в словаре переводов
            for english_key, variants in self.normalizer.translations.items():
                # Проверяем, совпадает ли слово с каким-то вариантом
                for variant in variants:
                    variant_clean = variant.replace(' ', '').lower()
                    if word.startswith(variant_clean[:min(5, len(variant_clean))]):
                        # Добавляем все варианты этого термина
                        terms.extend(variants)
                        break
        
        return list(set(terms))  # Убираем дубликаты
    
    def build_bm25_index(self):
        """Построить BM25 индекс"""
        if not BM25_AVAILABLE:
            print("❌ BM25 недоступен")
            return
        
        # Токенизируем все документы
        self.tokenized_corpus = []
        for doc in self.documents:
            # ВАЖНО: Повторяем title и category 3 раза для увеличения их веса
            # Это стандартная техника для boosting важных полей
            title = doc.get('title', '')
            category = doc.get('category', '')
            subcategory = doc.get('subcategory', '')
            tags = doc.get('tags', [])
            
            # Добавляем многоязычные синонимы для title и category
            # Это позволяет искать на русском и английском
            multilingual_terms = self._get_multilingual_terms(title, category, subcategory)
            
            text_parts = [
                title, title, title,  # 3x boost для title
                category, category,   # 2x boost для category
                subcategory,
                ' '.join(tags),       # Добавляем tags (содержат оба языка)
                ' '.join(multilingual_terms),  # Добавляем синонимы/переводы
                doc.get('summary', ''),
                doc.get('body', '')[:5000]  # Первые 5000 символов тела
            ]
            
            full_text = ' '.join(text_parts)
            tokens = self.normalizer.tokenize(full_text)
            self.tokenized_corpus.append(tokens)
        
        # Создаём BM25 индекс
        self.bm25 = BM25Okapi(self.tokenized_corpus)
    
    def search_documents(self, query: str, limit: int = 5) -> List[Tuple[Dict, float]]:
        """Поиск документов с BM25"""
        if not BM25_AVAILABLE or not self.bm25:
            print("❌ BM25 недоступен, используем fallback")
            return self._fallback_search(query, limit)
        
        # Токенизируем запрос
        query_tokens = self.normalizer.tokenize(query)
        query_normalized = ' '.join(query_tokens)
        
        # BM25 скоринг
        scores = self.bm25.get_scores(query_tokens)
        
        # Собираем результаты с пост-обработкой
        results = []
        for idx, score in enumerate(scores):
            if score > 0:
                doc = self.documents[idx]
                final_score = float(score)
                
                # БОНУС: точное совпадение важных терминов в title/category
                title = doc.get('title', '')
                category = doc.get('category', '')
                
                # Нормализуем и токенизируем вместе (важно для комбинаций типа "страна + программа")
                combined_text = f"{category} {title}"
                combined_tokens = self.normalizer.tokenize(combined_text)
                
                # Считаем сколько токенов из запроса есть в документе
                significant_tokens = [t for t in query_tokens if len(t) > 3]
                matches = sum(1 for token in significant_tokens if token in combined_tokens)
                
                # Усиленный буст если совпали ВСЕ или большинство значимых токенов
                if len(significant_tokens) > 0:
                    match_ratio = matches / len(significant_tokens)
                    
                    if match_ratio >= 0.8:  # 80%+ токенов совпало
                        final_score *= 3.0  # Сильный буст
                    elif match_ratio >= 0.5:  # 50%+ токенов совпало
                        final_score *= 2.0  # Средний буст
                    elif match_ratio > 0:  # Хоть что-то совпало
                        final_score *= (1 + match_ratio * 0.5)  # Небольшой буст
                
                results.append((doc, final_score))
        
        # Сортируем по релевантности
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:limit]
    
    def _fallback_search(self, query: str, limit: int = 5) -> List[Tuple[Dict, float]]:
        """Простой fallback поиск если BM25 недоступен"""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        results = []
        for doc in self.documents:
            body_lower = doc.get('body', '').lower()
            title_lower = doc.get('title', '').lower()
            
            score = 0
            for word in query_words:
                if len(word) > 2:
                    if word in title_lower:
                        score += 10
                    if word in body_lower:
                        score += 1
            
            if score > 0:
                results.append((doc, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    def extract_relevant_content(self, doc: Dict, query: str, context_size: int = 6000) -> str:
        """Извлечь релевантный контент из документа"""
        body = doc.get('body', '')
        title = doc.get('title', '')
        summary = doc.get('summary', '')
        
        # Формируем контекст
        context = f"# {title}\n\n"
        if summary:
            context += f"**Краткое описание:** {summary}\n\n"
        
        # Добавляем начало документа (первые слайды)
        if body:
            slides = body.split('--- Слайд')
            relevant_slides = []
            for i, slide in enumerate(slides[:15]):
                if slide.strip():
                    if i > 0:
                        relevant_slides.append('--- Слайд' + slide)
                    else:
                        relevant_slides.append(slide)
            
            body_excerpt = '\n'.join(relevant_slides)
            if len(body_excerpt) > context_size:
                body_excerpt = body_excerpt[:context_size] + "\n\n[...документ продолжается...]"
            
            context += body_excerpt
        
        return context
    
    def generate_llm_answer(self, query: str, context: str, sources: List[str]) -> Optional[str]:
        """Генерировать ответ с помощью LLM с обработкой rate limits"""
        if not self.groq_client:
            return None
        
        import time
        import requests
        
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                system_prompt = """Ты - опытный консультант по программам иммиграции и получения гражданства.

СТИЛЬ ОБЩЕНИЯ:
- Отвечай как живой человек, без формальных "Введение" и "Заключение"
- Сразу переходи к сути вопроса
- Будь конкретным и информативным
- Используй естественный разговорный язык

ФОРМАТИРОВАНИЕ (ОБЯЗАТЕЛЬНО):
- Используй HTML для красивой структуры (это для Telegram)
- <b>Жирный текст</b> для важных терминов, названий программ, стран
- <i>Курсив</i> для пояснений и примечаний
- Списки с маркерами (•) или номерами для перечислений
- Разбивай длинные абзацы на короткие (2-3 предложения макс)
- Суммы и сроки выделяй жирным: <b>$250,000</b>, <b>3-4 месяца</b>
- Используй \n\n для разделения абзацев (двойной перенос строки)
- Эмодзи используй умеренно, только для важных пунктов (✓, •, 💰, 📅, 🌍)
- НЕ используй <h1>, <h2>, <h3> - только <b> для заголовков
- Используй символы для подзаголовков: 🔹 <b>Заголовок</b>

ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе предоставленного контекста
2. Если информации нет - скажи "К сожалению, такой информации нет в наших материалах"
3. Всегда указывай конкретные цифры, суммы, сроки
4. Структурируй ответ логично и красиво
5. Отвечай на том же языке, что и вопрос
6. НЕ придумывай - только факты из контекста"""

                user_prompt = f"""Вопрос клиента:
{query}

Доступная информация:
{context}

Ответь на вопрос клиента красиво и структурированно. Используй HTML-форматирование: <b>жирный текст</b>, <i>курсив</i>, списки с маркерами. Разбивай текст на короткие абзацы (используй \\n\\n для разделения)."""

                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1500,
                )
                
                llm_answer = response.choices[0].message.content
                
                final_answer = llm_answer + "\n\n---\n\n**Источники:**\n"
                for source in sources:
                    final_answer += f"- {source}\n"
                
                return final_answer
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    # Rate limit exceeded
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"⚠️  Rate limit exceeded (429). Попытка {attempt + 1}/{max_retries}, ожидание {delay} сек...")
                    
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        continue
                    else:
                        # Все попытки исчерпаны, возвращаем fallback ответ
                        print(f"❌ Все попытки исчерпаны. Возвращаем fallback ответ.")
                        return self._generate_fallback_answer(query, context, sources)
                else:
                    print(f"⚠️  HTTP ошибка LLM: {e}")
                    return None
                    
            except Exception as e:
                print(f"⚠️  Ошибка LLM: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"🔄 Повторная попытка через {delay} сек...")
                    time.sleep(delay)
                else:
                    return None
        
        return None
    
    def _generate_fallback_answer(self, query: str, context: str, sources: List[str]) -> str:
        """Генерировать fallback ответ когда LLM недоступен"""
        # Простой fallback ответ на основе найденных документов
        fallback = f"""<b>📚 Информация найдена в базе знаний</b>

К сожалению, в данный момент сервис генерации ответов перегружен. 
Но я нашел релевантную информацию по вашему запросу:

<b>🔍 Найденные материалы:</b>
"""
        
        # Извлекаем заголовки из контекста
        lines = context.split('\n')
        titles = []
        for line in lines:
            if line.startswith('# ') and len(line) > 3:
                titles.append(line[2:].strip())
        
        if titles:
            for title in titles[:5]:  # Показываем до 5 заголовков
                fallback += f"• {title}\n"
        else:
            fallback += "• Документы найдены в базе знаний\n"
        
        fallback += f"""

<b>⏳ Попробуйте повторить запрос через 1-2 минуты</b> - сервис восстановится автоматически.

<b>📋 Источники:</b>
"""
        
        for source in sources[:3]:  # Показываем до 3 источников
            fallback += f"• {source}\n"
        
        return fallback
    
    def format_answer(self, query: str, results: List[Tuple[Dict, float]]) -> str:
        """Форматировать ответ"""
        if not results:
            return "❌ Не знаю — нет в материалах.\n\nПо вашему запросу не найдено информации в базе знаний."
        
        # Собираем контекст и источники
        contexts = []
        sources = []
        
        for doc, score in results[:3]:
            context = self.extract_relevant_content(doc, query)
            contexts.append(context)
            
            source_file = doc.get('source_file', 'Unknown')
            slides_start = doc.get('slides_start', '?')
            slides_end = doc.get('slides_end', '?')
            source_line = f"raw/{source_file} → слайды {slides_start}–{slides_end}"
            if source_line not in sources:
                sources.append(source_line)
        
        # Генерируем ответ через LLM
        if self.groq_client and contexts:
            full_context = "\n\n---\n\n".join(contexts)
            llm_answer = self.generate_llm_answer(query, full_context, sources)
            if llm_answer:
                return llm_answer
        
        # Fallback если LLM недоступен
        answer = contexts[0]
        answer += "\n\n---\n\n**Источники:**\n"
        for source in sources:
            answer += f"- {source}\n"
        
        return answer
    
    def ask(self, question: str, lang: Optional[Language] = None) -> str:
        """
        Задать вопрос с автоопределением языка
        
        Args:
            question: Вопрос пользователя
            lang: Принудительное указание языка (опционально)
        
        Returns:
            Ответ на вопрос
        """
        # Определяем язык запроса
        detected_lang = None
        if self.auto_detect_lang and self.language_detector and not lang:
            detected_lang = self.language_detector.detect_from_query(question)
            
            # Если агент инициализирован с конкретным языком и он отличается - предупреждаем
            if self.lang and detected_lang != self.lang:
                print(f"⚠️  Обнаружен запрос на {detected_lang}, но агент работает с {self.lang}")
                # Используем язык агента
                detected_lang = self.lang
        else:
            # Используем переданный lang или язык агента
            detected_lang = lang or self.lang
        
        # Поиск документов
        results = self.search_documents(question, limit=5)
        
        # Форматирование ответа
        answer = self.format_answer(question, results)
        
        return answer
    
    def set_language(self, lang: Optional[Language]):
        """
        Переключить язык агента (перезагружает базу знаний)
        
        Args:
            lang: Новый язык ("rus", "eng" или None для обоих)
        """
        if lang not in [None, "rus", "eng"]:
            raise ValueError(f"Неподдерживаемый язык: {lang}. Используйте 'rus', 'eng' или None")
        
        self.lang = lang
        self.documents = []
        self.tokenized_corpus = []
        self.bm25 = None
        
        # Перезагружаем базу знаний с новым языком
        self.load_knowledge_base()
        
        lang_label = f"{lang.upper()}" if lang else "все языки"
        print(f"🌍 Язык переключен на: {lang_label}")


# Для совместимости
KnowledgeAgent = KnowledgeAgentV3

