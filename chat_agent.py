#!/usr/bin/env python3
"""
Улучшенный агент базы знаний с BM25 поиском
Версия 3.0 - правильная архитектура без костылей
"""

import json
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from functools import lru_cache

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
        # Словарь для приведения к нормальной форме (лемматизация lite)
        self.replacements = {
            # Падежи стран (окончания)
            r'португали\w+': 'portugal',
            r'греци\w+': 'greece',
            r'турци\w+': 'turkey',
            r'гренад\w+': 'grenada',
            r'мальт\w+': 'malta',
            r'кипр\w*': 'cyprus',
            r'испани\w+': 'spain',
            r'парагва\w+': 'paraguay',
            r'вануату': 'vanuatu',
            r'доминик\w+': 'dominica',
            r'антигуа': 'antigua',
            r'барбуд\w+': 'barbuda',
            r'карибск\w+': 'caribbean',
            r'сент[\s\-]киттс': 'saint kitts',
            r'сент[\s\-]китс': 'saint kitts',
            r'сент[\s\-]люси\w+': 'saint lucia',
            r'сент[\s\-]лючи\w+': 'saint lucia',
            
            # Программы иммиграции
            r'гражданств\w+': 'citizenship',
            r'паспорт\w*': 'passport',
            r'виз\w+': 'visa',
            r'внж': 'residence_permit',
            r'вид\s+на\s+жительств\w*': 'residence_permit',
            r'постоянн\w+\s+проживан\w+': 'permanent_residence',
            r'пмж': 'permanent_residence',
            r'инвестиц\w+': 'investment',
            r'голден\w*': 'golden',
            r'золот\w+': 'golden',
            
            # Глаголы
            r'получ\w+': 'get',
            r'оформ\w+': 'apply',
            r'требован\w+': 'requirements',
            r'услов\w+': 'conditions',
            r'стоимост\w+': 'cost',
            r'цен\w+': 'price',
            r'срок\w*': 'timeline',
        }
        
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
    """Улучшенный агент с BM25 поиском"""
    
    def __init__(self, knowledge_dir: str):
        self.knowledge_dir = Path(knowledge_dir)
        self.documents = []
        self.normalizer = TextNormalizer()
        self.bm25 = None
        self.tokenized_corpus = []
        self.kb_version = None
        
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
        """Загрузить базу знаний"""
        print("📚 Загрузка базы знаний...")
        
        # Загружаем версию из manifest если есть
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
        
        # Загружаем все .md файлы кроме служебных
        md_files = []
        for md_file in self.knowledge_dir.rglob("*.md"):
            if not md_file.name.startswith(('00_', '_')):
                md_files.append(md_file)
        
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                doc = self.extract_metadata_and_content(content, md_file)
                if doc:
                    self.documents.append(doc)
            except Exception as e:
                print(f"⚠️  Ошибка загрузки {md_file.name}: {e}")
        
        print(f"✅ Загружено {len(self.documents)} документов")
        
        # Строим BM25 индекс
        if BM25_AVAILABLE and self.documents:
            print("🔍 Построение BM25 индекса...")
            self.build_bm25_index()
            print("✅ BM25 индекс готов")
    
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
                    
                    if key in ['title', 'summary', 'category', 'subcategory']:
                        doc[key] = value
            
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
            
            text_parts = [
                title, title, title,  # 3x boost для title
                category, category,   # 2x boost для category
                subcategory,
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
                title_normalized = self.normalizer.normalize(doc.get('title', ''))
                category_normalized = self.normalizer.normalize(doc.get('category', ''))
                
                # Проверяем ключевые термины в запросе
                for token in query_tokens:
                    if len(token) > 3:  # Только значимые слова
                        if token in title_normalized.split():
                            final_score *= 1.5  # 50% буст за совпадение в title
                        elif token in category_normalized.split():
                            final_score *= 1.2  # 20% буст за совпадение в category
                
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
        """Генерировать ответ с помощью LLM"""
        if not self.groq_client:
            return None
        
        try:
            system_prompt = """Ты - консультант по программам иммиграции и получения гражданства.
ВАЖНЫЕ ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе предоставленного контекста
2. Если информации нет в контексте - честно скажи "нет в материалах"
3. Всегда указывай конкретные цифры, суммы, сроки из материалов
4. Форматируй ответ структурированно с заголовками и списками
5. Отвечай на том же языке, что и вопрос (русский или английский)
6. Не придумывай информацию - только факты из контекста"""

            user_prompt = f"""ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{query}

КОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ:
{context}

Дай развёрнутый структурированный ответ на вопрос на основе этого контекста. Если информации недостаточно - скажи об этом."""

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
            
        except Exception as e:
            print(f"⚠️  Ошибка LLM: {e}")
            return None
    
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
                return "\n\n## Ответ\n\n" + llm_answer
        
        # Fallback если LLM недоступен
        answer = "\n\n## Ответ\n\n" + contexts[0]
        answer += "\n\n---\n\n**Источники:**\n"
        for source in sources:
            answer += f"- {source}\n"
        
        return answer
    
    def ask(self, question: str) -> str:
        """Задать вопрос"""
        results = self.search_documents(question, limit=5)
        answer = self.format_answer(question, results)
        return answer


# Для совместимости
KnowledgeAgent = KnowledgeAgentV3

