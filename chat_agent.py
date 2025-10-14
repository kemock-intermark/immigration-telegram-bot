#!/usr/bin/env python3
"""
Интерактивный чат-агент для работы с базой знаний
Отвечает на вопросы используя только материалы из knowledge/
"""

import sys
import re
import hashlib
import json
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from datetime import datetime
from functools import lru_cache

# LLM для генерации ответов
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("⚠️  Groq не установлен. Ответы будут без LLM обработки.")


class KnowledgeAgent:
    def __init__(self, knowledge_dir: str):
        self.knowledge_dir = Path(knowledge_dir)
        self.documents = []
        self.conversation_history = []
        self.unanswered_log_path = self.knowledge_dir / "_unanswered_log.md"
        self.search_cache = {}  # Простой кэш для результатов поиска
        self.kb_version = None
        
        # Инициализация Groq клиента
        self.groq_client = None
        if GROQ_AVAILABLE:
            groq_api_key = os.getenv('GROQ_API_KEY')
            if groq_api_key:
                try:
                    self.groq_client = Groq(api_key=groq_api_key)
                except Exception as e:
                    print(f"⚠️  Не удалось инициализировать Groq: {e}")
        
        self.load_knowledge_base()
        
    def extract_metadata_and_content(self, md_path: Path) -> Dict:
        """Извлечь метаданные и содержимое из Markdown файла"""
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Ищем YAML frontmatter и тело документа
            match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
            if not match:
                return {}
            
            yaml_content = match.group(1)
            body_content = match.group(2)
            
            # Парсим метаданные
            metadata = {
                'body': body_content,
                'file_path': md_path,
                'file_name': md_path.name
            }
            
            # Простой парсинг YAML
            lines = yaml_content.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i]
                if ':' in line and not line.strip().startswith('-'):
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    
                    # Специальная обработка source_files
                    if key == 'source_files' and i + 1 < len(lines):
                        # Ищем path в следующих строках
                        j = i + 1
                        while j < len(lines) and (lines[j].startswith(' ') or lines[j].startswith('\t')):
                            subline = lines[j].strip()
                            if subline.startswith('- path:'):
                                path_match = re.search(r'path:\s*["\']?([^"\']+)["\']?', subline)
                                if path_match:
                                    full_path = path_match.group(1)
                                    metadata['source_file'] = full_path.replace('raw/', '')
                            elif subline.startswith('slides:'):
                                slides_match = re.search(r'slides:\s*\[(\d+)-(\d+)\]', subline)
                                if slides_match:
                                    metadata['slides_start'] = slides_match.group(1)
                                    metadata['slides_end'] = slides_match.group(2)
                            j += 1
                    else:
                        metadata[key] = value
                i += 1
            
            # Если не нашли в метаданных, ищем в теле документа
            if 'source_file' not in metadata:
                source_match = re.search(r'raw/([^\s→\]]+\.pdf)', body_content)
                if source_match:
                    metadata['source_file'] = source_match.group(1)
            
            if 'slides_start' not in metadata:
                slides_match = re.search(r'слайды?\s+(\d+)[-–](\d+)', body_content)
                if slides_match:
                    metadata['slides_start'] = slides_match.group(1)
                    metadata['slides_end'] = slides_match.group(2)
            
            return metadata
            
        except Exception as e:
            print(f"⚠️  Ошибка чтения {md_path.name}: {e}")
            return {}
    
    def load_knowledge_base(self):
        """Загрузить всю базу знаний в память"""
        print("📚 Загрузка базы знаний...")
        
        # Загружаем версию из manifest если есть
        manifest_path = self.knowledge_dir / 'manifest.json'
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                    self.kb_version = manifest.get('version', 'unknown')
                    print(f"📦 Версия базы: {self.kb_version}")
            except:
                self.kb_version = 'unknown'
        
        for md_file in self.knowledge_dir.rglob("*.md"):
            if md_file.name in ['00_index.md', 'build_log.md', 'update_log.md', '_unanswered_log.md']:
                continue
            
            doc = self.extract_metadata_and_content(md_file)
            if doc and 'body' in doc:
                self.documents.append(doc)
        
        print(f"✅ Загружено {len(self.documents)} документов\n")
    
    def normalize_query(self, query: str) -> List[str]:
        """Нормализовать запрос, добавить синонимы"""
        query_lower = query.lower()
        
        # Словарь синонимов
        synonyms = {
            'гражданство': ['citizenship', 'гражданство', 'паспорт'],
            'citizenship': ['citizenship', 'гражданство', 'паспорт'],
            'вид на жительство': ['residence permit', 'вид на жительство', 'внж', 'residence', 'golden visa'],
            'residence': ['residence permit', 'вид на жительство', 'внж', 'residence', 'golden visa'],
            'внж': ['residence permit', 'вид на жительство', 'внж', 'residence', 'golden visa'],
            'golden visa': ['golden visa', 'золотая виза', 'residence permit', 'вид на жительство', 'внж'],
            'золотая виза': ['golden visa', 'золотая виза', 'residence permit', 'вид на жительство', 'внж'],
            'постоянное проживание': ['permanent residence', 'постоянное проживание', 'пмж', 'permanent'],
            'permanent': ['permanent residence', 'постоянное проживание', 'пмж', 'permanent'],
            'пмж': ['permanent residence', 'постоянное проживание', 'пмж', 'permanent'],
            'инвестиции': ['investment', 'инвестиции', 'invest'],
            'investment': ['investment', 'инвестиции', 'invest'],
            'получить': ['получить', 'requirements', 'process', 'procedure', 'как получить'],
            'требования': ['requirements', 'требования', 'conditions', 'условия'],
            'стоимость': ['cost', 'price', 'стоимость', 'цена'],
            'portugal': ['portugal', 'португалия'],
            'португалия': ['portugal', 'португалия'],
            'malta': ['malta', 'мальта'],
            'мальта': ['malta', 'мальта'],
            'greece': ['greece', 'греция'],
            'греция': ['greece', 'греция'],
            'turkey': ['turkey', 'турция'],
            'турция': ['turkey', 'турция'],
            'caribbean': ['caribbean', 'карибы', 'карибские острова'],
            'карибы': ['caribbean', 'карибы', 'карибские острова'],
        }
        
        # Извлекаем ключевые слова
        keywords = [query_lower]
        
        for key, values in synonyms.items():
            if key in query_lower:
                keywords.extend(values)
        
        return list(set(keywords))
    
    def search_documents(self, query: str, limit: int = 5) -> List[Tuple[Dict, float]]:
        """Поиск релевантных документов по запросу (с кэшированием)"""
        # Создаём ключ кэша
        cache_key = f"{query.lower().strip()}_{self.kb_version}_{limit}"
        
        # Проверяем кэш
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Получаем варианты запроса с синонимами
        query_variants = self.normalize_query(query)
        
        # Список стран для приоритизации (с учетом разных падежей)
        countries = {
            'portugal': ['portugal', 'португал'],  # португалия, португалии, португалию
            'malta': ['malta', 'мальт'],  # мальта, мальты, мальте
            'greece': ['greece', 'греци'],  # греция, греции, грецию
            'turkey': ['turkey', 'турци'],  # турция, турции, турцию
            'grenada': ['grenada', 'гренад'],  # гренада, гренады, гренаде
            'vanuatu': ['vanuatu', 'вануату'],  # не склоняется
            'antigua': ['antigua', 'антигуа'],  # не склоняется
            'dominica': ['dominica', 'доминик'],  # доминика, доминики
            'st lucia': ['st lucia', 'сент-люси', 'сент люси'],
            'st kitts': ['st kitts', 'сент-китс', 'сент китс'],
            'caribbean': ['caribbean', 'кариб'],  # карибы, карибских
            'cyprus': ['cyprus', 'кипр'],  # кипр, кипра
            'spain': ['spain', 'испани'],  # испания, испании
            'paraguay': ['paraguay', 'парагва'],  # парагвай, парагвая
            'sao tome': ['sao tome', 'сан-томе', 'сан томе']
        }
        
        # Проверяем есть ли название страны в запросе
        country_in_query = None
        for country_key, country_variants in countries.items():
            for variant in country_variants:
                if variant in query_lower:
                    country_in_query = country_key
                    break
            if country_in_query:
                break
        
        results = []
        
        for doc in self.documents:
            body_lower = doc.get('body', '').lower()
            title_lower = doc.get('title', '').lower()
            category_lower = doc.get('category', '').lower()
            subcategory = doc.get('subcategory', '').lower()
            
            # Вычисляем релевантность
            score = 0
            
            # КРИТИЧЕСКИ ВАЖНО: Если в запросе есть страна - даём огромный буст документам этой страны
            if country_in_query:
                if country_in_query in category_lower or country_in_query in title_lower:
                    score += 500  # Огромный приоритет!
            
            # Точное совпадение фразы - высокий приоритет
            for variant in query_variants:
                if variant in body_lower:
                    score += 80
                if variant in title_lower:
                    score += 100
                if variant in category_lower:
                    score += 60
                if variant in subcategory:
                    score += 40
            
            # Совпадение по словам
            body_words = set(body_lower.split())
            matching_words = query_words & body_words
            score += len(matching_words) * 15
            
            if score > 0:
                results.append((doc, score))
        
        # Сортируем по релевантности
        results.sort(key=lambda x: x[1], reverse=True)
        final_results = results[:limit]
        
        # Сохраняем в кэш (ограничиваем размер кэша)
        if len(self.search_cache) < 100:  # Максимум 100 закэшированных запросов
            self.search_cache[cache_key] = final_results
        
        return final_results
    
    def extract_relevant_content(self, doc: Dict, query: str, context_size: int = 1000) -> List[str]:
        """Извлечь релевантные фрагменты из документа"""
        body = doc.get('body', '')
        title = doc.get('title', '')
        summary = doc.get('summary', '')
        
        excerpts = []
        
        # Для топовых документов берём весь контент (или большую часть)
        # Это даст LLM достаточно информации для полного ответа
        
        # Всегда включаем заголовок
        if title:
            header = f"# {title}\n\n"
            if summary:
                header += f"**Краткое описание:** {summary}\n\n"
            excerpts.append(header)
        
        # Берём весь body документа, разбивая на части по 2000 символов
        # Это даст LLM полный контекст
        if body:
            # Разбиваем на части по слайдам
            slides = body.split('--- Слайд')
            
            # Берём первые 10 слайдов (обычно там основная информация)
            relevant_slides = []
            for i, slide in enumerate(slides[:15]):  # Увеличено до 15 слайдов
                if slide.strip():
                    if i > 0:
                        relevant_slides.append('--- Слайд' + slide)
                    else:
                        relevant_slides.append(slide)
            
            if relevant_slides:
                body_excerpt = '\n'.join(relevant_slides)
                # Обрезаем если слишком длинно (макс 6000 символов)
                if len(body_excerpt) > 6000:
                    body_excerpt = body_excerpt[:6000] + "\n\n[...документ продолжается...]"
                excerpts.append(body_excerpt)
            
            else:
                # Fallback: просто берём начало документа
                excerpts.append(body[:3000])
        
        return excerpts if excerpts else [summary or title or "Нет содержимого"]
    
    def get_knowledge_base_version(self) -> str:
        """Получить версию базы знаний из индекса"""
        try:
            index_path = self.knowledge_dir / "00_index.md"
            if index_path.exists():
                with open(index_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    match = re.search(r'version:\s*["\']?([^"\'\n]+)["\']?', content)
                    if match:
                        return match.group(1)
            return "unknown"
        except:
            return "unknown"
    
    def extract_keywords(self, text: str, max_keywords: int = 7) -> List[str]:
        """Извлечь ключевые слова из текста"""
        # Удаляем стоп-слова и короткие слова
        stop_words = {
            'в', 'на', 'и', 'для', 'как', 'что', 'это', 'с', 'по', 'о', 'из', 'у',
            'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are'
        }
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]
        
        # Берём уникальные слова с приоритетом по порядку появления
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords[:max_keywords]
    
    def clean_personal_data(self, text: str) -> str:
        """Очистить текст от персональных данных"""
        # Удаляем email
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        # Удаляем телефоны
        text = re.sub(r'\+?\d[\d\-\(\) ]{7,}\d', '[PHONE]', text)
        
        # Удаляем потенциальные имена (заглавные буквы)
        # text = re.sub(r'\b[A-ZА-Я][a-zа-я]+\s+[A-ZА-Я][a-zа-я]+\b', '[NAME]', text)
        
        return text
    
    def hash_question(self, question: str) -> str:
        """Создать хеш вопроса для проверки дубликатов"""
        # Нормализация: нижний регистр, без пунктуации
        normalized = re.sub(r'[^\w\s]', '', question.lower())
        normalized = ' '.join(normalized.split())  # Убрать лишние пробелы
        
        hash_obj = hashlib.sha256(normalized.encode('utf-8'))
        return hash_obj.hexdigest()[:8]
    
    def log_unanswered_question(self, question: str):
        """Логировать неотвеченный вопрос"""
        try:
            # Получаем метаданные
            current_date = datetime.now().strftime("%Y-%m-%d")
            current_month = datetime.now().strftime("%Y-%m")
            kb_version = self.get_knowledge_base_version()
            question_hash = self.hash_question(question)
            
            # Извлекаем ключевые слова
            keywords = self.extract_keywords(question)
            keywords_str = '; '.join(keywords)
            
            # Определяем тему (первые 2-3 ключевых слова)
            topic = ' '.join(keywords[:3]) if keywords else 'Общий вопрос'
            
            # Получаем контекст (последние 2 реплики)
            context = ""
            if len(self.conversation_history) >= 2:
                recent = self.conversation_history[-2:]
                context_parts = []
                for q, _ in recent:
                    cleaned = self.clean_personal_data(q)
                    context_parts.append(cleaned[:50])
                context = " → ".join(context_parts)
            else:
                context = "Нет предыдущего контекста"
            
            # Проверяем дубликаты
            if self.unanswered_log_path.exists():
                with open(self.unanswered_log_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Ищем этот же хеш в текущем месяце с той же версией
                    month_section = re.search(
                        rf'## {re.escape(current_month)}.*?(?=## \d{{4}}-\d{{2}}|$)',
                        content,
                        re.DOTALL
                    )
                    
                    if month_section:
                        month_text = month_section.group(0)
                        if question_hash in month_text and kb_version in month_text:
                            # Дубликат найден, не логируем
                            return
            
            # Формируем новую запись
            new_entry = f"| {current_date} | {topic} | {question} | [{keywords_str}] | {context} | {kb_version} | {question_hash} |"
            
            # Читаем существующий файл или создаём новый
            if self.unanswered_log_path.exists():
                with open(self.unanswered_log_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                content = "# Вопросы без ответов\n\n"
            
            # Проверяем, есть ли секция для текущего месяца
            month_header = f"## {current_month}"
            if month_header not in content:
                # Добавляем новую секцию месяца
                table_header = "| Дата | Тема | Вопрос | Ключевые слова | Контекст | Версия базы | Хеш вопроса |\n"
                table_separator = "|------|------|--------|----------------|-----------|--------------|-------------|\n"
                
                new_section = f"\n{month_header}\n\n{table_header}{table_separator}{new_entry}\n"
                content += new_section
            else:
                # Добавляем в существующую секцию
                # Находим позицию после заголовка таблицы текущего месяца
                pattern = rf'(## {re.escape(current_month)}.*?\|---.*?\|\n)(.*?)(?=\n## |\Z)'
                
                def add_entry(match):
                    header = match.group(1)
                    entries = match.group(2)
                    return header + entries.rstrip() + '\n' + new_entry + '\n'
                
                content = re.sub(pattern, add_entry, content, flags=re.DOTALL)
            
            # Проверяем размер файла
            line_count = content.count('\n')
            if line_count > 500:
                # Архивирование (упрощённая версия)
                archive_dir = self.knowledge_dir / "_unanswered_archive"
                archive_dir.mkdir(exist_ok=True)
                
                current_year = datetime.now().year
                archive_file = archive_dir / f"{current_year - 1}.md"
                
                # Переносим старые записи (всё кроме текущего года)
                current_year_pattern = rf'## {current_year}-\d{{2}}'
                current_year_sections = re.findall(
                    current_year_pattern + r'.*?(?=## \d{4}-\d{2}|$)',
                    content,
                    re.DOTALL
                )
                
                if current_year_sections:
                    # Оставляем только текущий год
                    content = "# Вопросы без ответов\n\n" + '\n'.join(current_year_sections)
            
            # Записываем обновлённый файл
            with open(self.unanswered_log_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
        except Exception as e:
            # Бесшумно игнорируем ошибки логирования
            pass
    
    def generate_llm_answer(self, query: str, context: str, sources: List[str]) -> str:
        """Генерировать ответ с помощью LLM на основе найденного контекста"""
        if not self.groq_client:
            return None  # Fallback к обычному формату
        
        try:
            system_prompt = """Ты - консультант по программам иммиграции и получения гражданства.

ВАЖНЫЕ ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе предоставленного контекста
2. Если информации нет в контексте - честно скажи "нет в материалах"
3. Всегда указывай конкретные цифры, суммы, сроки из материалов
4. Форматируй ответ структурированно с заголовками и списками
5. Отвечай на том же языке, что и вопрос (русский или английский)
6. Не придумывай информацию - только факты из контекста

Твоя задача - дать понятный, структурированный ответ на вопрос пользователя."""

            user_prompt = f"""ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{query}

КОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ:
{context}

Дай развёрнутый структурированный ответ на вопрос на основе этого контекста. Если информации недостаточно - скажи об этом."""

            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Актуальная бесплатная модель Groq
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Низкая температура для точности
                max_tokens=1500,
            )
            
            llm_answer = response.choices[0].message.content
            
            # Добавляем источники в конец
            final_answer = llm_answer + "\n\n---\n\n**Источники:**\n"
            for source in sources:
                final_answer += f"- {source}\n"
            
            return final_answer
            
        except Exception as e:
            print(f"⚠️  Ошибка LLM: {e}")
            return None  # Fallback к обычному формату
    
    def format_answer(self, query: str, results: List[Tuple[Dict, float]]) -> str:
        """Форматировать ответ на основе найденных документов"""
        if not results:
            # Логируем неотвеченный вопрос
            self.log_unanswered_question(query)
            return "❌ Не знаю — нет в материалах.\n\nПо вашему запросу не найдено информации в базе знаний."
        
        answer_parts = []
        sources = []
        
        # Собираем информацию из документов
        seen_excerpts = set()
        
        for doc, score in results[:3]:  # Берём топ-3 документа
            title = doc.get('title', 'Без названия')
            category = doc.get('category', '')
            
            # Извлекаем релевантные фрагменты
            excerpts = self.extract_relevant_content(doc, query)
            
            for excerpt in excerpts:
                # Избегаем дубликатов
                excerpt_normalized = excerpt.lower().strip()
                if excerpt_normalized not in seen_excerpts:
                    seen_excerpts.add(excerpt_normalized)
                    answer_parts.append(excerpt)
            
            # Добавляем источник
            source_file = doc.get('source_file', 'Unknown')
            slides_start = doc.get('slides_start', '?')
            slides_end = doc.get('slides_end', '?')
            
            source_line = f"raw/{source_file} → слайды {slides_start}–{slides_end}"
            if source_line not in sources:
                sources.append(source_line)
        
        # Пробуем сгенерировать ответ с помощью LLM
        if self.groq_client and answer_parts:
            context = "\n\n---\n\n".join(answer_parts[:5])  # Топ-5 фрагментов как контекст
            llm_answer = self.generate_llm_answer(query, context, sources)
            if llm_answer:
                return "\n\n## Ответ\n\n" + llm_answer
        
        # Fallback: обычный формат без LLM
        answer = "\n\n## Ответ\n\n"
        
        if answer_parts:
            # Объединяем фрагменты
            for i, part in enumerate(answer_parts[:3], 1):  # Максимум 3 фрагмента
                if i > 1:
                    answer += "\n\n"
                answer += part
        else:
            answer += "Информация найдена, но не удалось извлечь релевантные фрагменты."
        
        # Добавляем источники
        answer += "\n\n---\n\n**Источники:**\n"
        for source in sources:
            answer += f"- {source}\n"
        
        # Если использовано несколько документов
        if len(results) > 1:
            answer += "\n*Примечание: информация из нескольких источников.*"
        
        return answer
    
    def ask(self, question: str) -> str:
        """Задать вопрос агенту"""
        if not question.strip():
            return "❓ Пожалуйста, задайте вопрос."
        
        # Поиск релевантных документов
        results = self.search_documents(question)
        
        # Формирование ответа
        answer = self.format_answer(question, results)
        
        # Сохраняем в историю диалога
        self.conversation_history.append((question, answer))
        
        # Ограничиваем размер истории
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
        
        return answer
    
    def interactive_mode(self):
        """Интерактивный режим чата"""
        print("╔════════════════════════════════════════════════════════════════╗")
        print("║           ЧАТ-АГЕНТ — БАЗА ЗНАНИЙ INTERMARK GLOBAL            ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print()
        print("Задавайте вопросы об иммиграционных программах.")
        print("Агент использует только материалы из базы знаний.")
        print()
        print("Команды:")
        print("  /помощь   — показать справку")
        print("  /статистика — статистика базы знаний")
        print("  /выход    — завершить работу")
        print()
        print("─" * 64)
        print()
        
        while True:
            try:
                question = input("❓ Вопрос: ").strip()
                
                if not question:
                    continue
                
                # Обработка команд
                if question.lower() in ['/выход', '/exit', '/quit', 'выход', 'exit']:
                    print("\n👋 До свидания!")
                    break
                
                if question.lower() in ['/помощь', '/help', 'помощь']:
                    self.show_help()
                    continue
                
                if question.lower() in ['/статистика', '/stats', 'статистика']:
                    self.show_stats()
                    continue
                
                # Получаем ответ
                print()
                answer = self.ask(question)
                print(answer)
                print()
                print("─" * 64)
                print()
                
            except KeyboardInterrupt:
                print("\n\n👋 До свидания!")
                break
            except Exception as e:
                print(f"\n⚠️  Ошибка: {e}\n")
    
    def show_help(self):
        """Показать справку"""
        print()
        print("═" * 64)
        print("СПРАВКА — ЧАТ-АГЕНТ")
        print("═" * 64)
        print()
        print("Агент отвечает на вопросы о:")
        print("  • Программах гражданства")
        print("  • Видах на жительство")
        print("  • Постоянном проживании")
        print("  • Инвестиционных возможностях")
        print("  • Требованиях и условиях программ")
        print()
        print("Примеры вопросов:")
        print("  • Какие программы гражданства есть в Португалии?")
        print("  • Требования для получения вида на жительство в Мальте?")
        print("  • Сколько стоит citizenship by investment в странах Карибского бассейна?")
        print("  • Что такое Golden Visa?")
        print()
        print("Принципы работы:")
        print("  ✓ Только достоверные данные из базы знаний")
        print("  ✓ Ссылки на источники в каждом ответе")
        print("  ✓ Если данных нет — сообщаем прямо")
        print("  ✓ Без фантазий и предположений")
        print()
        print("═" * 64)
        print()
    
    def show_stats(self):
        """Показать статистику базы знаний"""
        print()
        print("═" * 64)
        print("СТАТИСТИКА БАЗЫ ЗНАНИЙ")
        print("═" * 64)
        print()
        print(f"📚 Всего документов: {len(self.documents)}")
        
        # Категории
        categories = set(doc.get('category', 'Unknown') for doc in self.documents)
        print(f"🌍 Категорий (стран): {len(categories)}")
        
        # Типы программ
        subcategories = defaultdict(int)
        for doc in self.documents:
            subcat = doc.get('subcategory', 'unknown')
            subcategories[subcat] += 1
        
        print()
        print("📋 Распределение по типам:")
        type_names = {
            'citizenship': 'Гражданство',
            'residence-permit': 'Вид на жительство',
            'permanent-residence': 'Постоянное проживание',
            'passport': 'Паспорт',
            'golden-visa': 'Золотая виза',
            'general': 'Общая информация'
        }
        
        for subcat, count in sorted(subcategories.items(), key=lambda x: x[1], reverse=True):
            name = type_names.get(subcat, subcat)
            print(f"  • {name}: {count}")
        
        print()
        print("═" * 64)
        print()


def main():
    base_dir = Path(__file__).parent
    knowledge_dir = base_dir / "knowledge"
    
    if not knowledge_dir.exists():
        print("❌ Папка knowledge/ не найдена.")
        print("   Запустите сначала: python3 build_knowledge.py")
        sys.exit(1)
    
    # Проверяем наличие документов
    md_files = list(knowledge_dir.rglob("*.md"))
    doc_files = [f for f in md_files if f.name not in ['00_index.md', 'build_log.md', 'update_log.md']]
    
    if not doc_files:
        print("❌ База знаний пуста.")
        print("   Запустите: python3 build_knowledge.py")
        sys.exit(1)
    
    # Запускаем агента
    agent = KnowledgeAgent(knowledge_dir)
    
    # Режим работы
    if len(sys.argv) > 1:
        # Командная строка - один вопрос
        question = ' '.join(sys.argv[1:])
        print(f"❓ Вопрос: {question}\n")
        answer = agent.ask(question)
        print(answer)
    else:
        # Интерактивный режим
        agent.interactive_mode()


if __name__ == "__main__":
    main()

