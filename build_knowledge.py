#!/usr/bin/env python3
"""
Скрипт для создания базы знаний из PDF презентаций
Извлекает текст, структурирует по темам и сохраняет в формате Markdown
Версия 2.0 - с поддержкой двуязычности (rus/eng)
"""

import os
import sys
import hashlib
import re
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Literal
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil

try:
    import PyPDF2
except ImportError:
    print("Установка необходимых библиотек...")
    os.system(f"{sys.executable} -m pip install PyPDF2 --quiet")
    import PyPDF2

# Утилиты для работы с языками
try:
    from language_utils import LanguageDetector, LanguageRouter, Language
    LANGUAGE_UTILS_AVAILABLE = True
except ImportError:
    LANGUAGE_UTILS_AVAILABLE = False
    Language = Literal["rus", "eng"]
    print("⚠️  language_utils не найден. Двуязычность отключена.")

# Настройки производительности
MAX_WORKERS = min(os.cpu_count() - 1 if os.cpu_count() else 1, 6)
BATCH_SIZE = 4


class KnowledgeBaseBuilder:
    def __init__(self, raw_dir: str, knowledge_dir: str, bilingual: bool = True):
        """
        Инициализация builder
        
        Args:
            raw_dir: Директория с исходными PDF файлами
            knowledge_dir: Директория для сохранения базы знаний
            bilingual: Включить двуязычную обработку (rus/eng отдельно)
        """
        self.raw_dir = Path(raw_dir)
        self.knowledge_dir = Path(knowledge_dir)
        self.build_date = datetime.now().strftime("%Y-%m-%d")
        self.bilingual = bilingual and LANGUAGE_UTILS_AVAILABLE
        self.documents = []
        self.build_log = []
        
        # Двуязычные артефакты
        self.documents_by_lang = {'rus': [], 'eng': []} if self.bilingual else None
        
        # Утилиты языка
        if self.bilingual:
            self.language_detector = LanguageDetector()
            self.language_router = LanguageRouter(self.knowledge_dir)
            self.log("🌍 Двуязычный режим активирован (RUS/ENG)")
        else:
            self.language_detector = None
            self.language_router = None
            self.log("📚 Обычный режим (legacy)")
        
    def log(self, message: str):
        """Добавить запись в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.build_log.append(log_entry)
        print(log_entry)
    
    def calculate_checksum(self, file_path: Path) -> Tuple[str, int, float]:
        """Вычислить SHA256 хеш файла + размер + mtime"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        stat = file_path.stat()
        return sha256.hexdigest()[:16], stat.st_size, stat.st_mtime
    
    def extract_text_from_pdf(self, pdf_path: Path) -> Tuple[str, int]:
        """Извлечь весь текст из PDF файла"""
        text_content = []
        page_count = 0
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                page_count = len(pdf_reader.pages)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    page_text = page.extract_text()
                    if page_text.strip():
                        # Добавляем маркер страницы
                        text_content.append(f"--- Слайд {page_num} ---")
                        text_content.append(page_text.strip())
                        text_content.append("")
                        
        except Exception as e:
            self.log(f"⚠️  Ошибка при чтении {pdf_path.name}: {e}")
            return "", 0
        
        return "\n".join(text_content), page_count
    
    def detect_document_language(self, pdf_path: Path, content: str) -> Language:
        """
        Определить язык документа
        
        Правила:
        1. Если файл в raw/rus/ → rus
        2. Если файл в raw/eng/ → eng
        3. Если legacy (raw/*.pdf) → определяем по содержимому
        
        Args:
            pdf_path: Путь к PDF файлу
            content: Извлеченный текст
        
        Returns:
            "rus" или "eng"
        """
        if not self.bilingual or not self.language_detector:
            return "rus"  # Default для legacy режима
        
        # Проверяем путь к файлу
        source_lang = self.language_detector.get_source_language(pdf_path)
        if source_lang:
            return source_lang
        
        # Legacy файл - определяем по содержимому
        detected = self.language_detector.detect_from_text(content, threshold=0.30)
        self.log(f"  📝 Legacy файл {pdf_path.name} → определен как {detected.upper()}")
        return detected
    
    def categorize_file(self, filename: str, content: str, lang: Optional[Language] = None) -> Dict[str, any]:
        """Определить категорию и метаданные по имени файла и содержимому"""
        filename_lower = filename.lower()
        
        # Извлекаем страну/регион из имени файла
        # Формат: "Intermark. <Country/Region> <Program Type> ENG.pdf"
        match = re.match(r'Intermark\.\s+(.+?)\s+(Residence|Citizenship|Passport|visa|RP|PR|Permit)', 
                        filename, re.IGNORECASE)
        
        if match:
            country = match.group(1).strip()
        else:
            # Попытка извлечь страну из начала имени
            parts = filename.replace("Intermark.", "").replace("ENG.pdf", "").strip().split(".")
            country = parts[0].strip() if parts else "Общее"
        
        # Определяем тип программы
        if any(word in filename_lower for word in ['citizenship', 'гражданство']):
            program_type = 'Гражданство'
            subcategory = 'citizenship'
        elif any(word in filename_lower for word in ['permanent residence', 'pr']):
            program_type = 'Постоянное проживание'
            subcategory = 'permanent-residence'
        elif any(word in filename_lower for word in ['residence permit', 'rp', 'visa']):
            program_type = 'Вид на жительство'
            subcategory = 'residence-permit'
        elif 'passport' in filename_lower:
            program_type = 'Паспорт'
            subcategory = 'passport'
        elif 'golden visa' in filename_lower:
            program_type = 'Золотая виза'
            subcategory = 'golden-visa'
        else:
            program_type = 'Общая информация'
            subcategory = 'general'
        
        # Генерируем краткое описание из первых строк контента
        lines = [l.strip() for l in content.split('\n') if l.strip() and not l.startswith('---')]
        summary = ' '.join(lines[:3])[:200] if lines else "Информация об иммиграционной программе"
        
        # Определяем теги
        tags = [country, program_type]
        if 'investment' in filename_lower or 'invest' in content.lower()[:500]:
            tags.append('инвестиции')
        if 'startup' in filename_lower:
            tags.append('стартап')
        if 'digital nomad' in filename_lower:
            tags.append('digital-nomad')
        if 'financial independence' in filename_lower:
            tags.append('финансовая-независимость')
        
        result = {
            'country': country,
            'program_type': program_type,
            'subcategory': subcategory,
            'summary': summary,
            'tags': tags
        }
        
        # Добавляем язык если передан
        if lang:
            result['lang'] = lang
        
        return result
    
    def _get_source_path(self, pdf_file: Path, lang: Optional[Language] = None) -> str:
        """
        Получить корректный путь к источнику с учетом языка
        
        Args:
            pdf_file: Path объект к PDF файлу
            lang: Язык документа
        
        Returns:
            Путь вида "raw/{lang}/file.pdf" или "raw/file.pdf"
        """
        # Проверяем, находится ли файл уже в языковой папке
        parts = pdf_file.parts
        if 'rus' in parts or 'eng' in parts:
            # Файл уже в языковой папке, возвращаем относительный путь от корня проекта
            raw_index = parts.index('raw')
            return '/'.join(parts[raw_index:])
        
        # Legacy файл - формируем путь с учетом определенного языка
        if lang and self.bilingual:
            return f"raw/{lang}/{pdf_file.name}"
        else:
            return f"raw/{pdf_file.name}"
    
    def create_markdown_document(self, pdf_file: Path, text: str, page_count: int, 
                                 metadata: Dict) -> str:
        """Создать Markdown документ по шаблону"""
        checksum = self.calculate_checksum(pdf_file)
        
        # Формируем имя файла для markdown
        safe_name = re.sub(r'[^\w\s-]', '', metadata['country'])
        safe_name = re.sub(r'[-\s]+', '-', safe_name).strip('-').lower()
        md_filename = f"{safe_name}-{metadata['subcategory']}.md"
        
        # Формируем путь к источнику с учетом языка
        source_path = self._get_source_path(pdf_file, metadata.get('lang'))
        
        # Формируем поле lang для YAML (если есть)
        lang_field = f'lang: "{metadata["lang"]}"\n' if 'lang' in metadata else ''
        
        # Создаем метаданные
        doc = f"""---
title: "{metadata['country']}: {metadata['program_type']}"
summary: "{metadata['summary']}"
category: "{metadata['country']}"
subcategory: "{metadata['subcategory']}"
{lang_field}tags: {metadata['tags']}
source_files:
  - path: "{source_path}"
    slides: [1-{page_count}]
extraction_date: "{self.build_date}"
version: "{checksum}"
checksum_sources: "{checksum}"
doc_type: "knowledge"
related: []
---

# {metadata['country']}: {metadata['program_type']}

## Содержание презентации

{text}

---

### Источники
[^src1]: raw/{pdf_file.name} → слайды 1–{page_count}
"""
        
        return md_filename, doc
    
    def clean_knowledge_dir(self):
        """Очистить папку knowledge если существует"""
        if self.knowledge_dir.exists():
            self.log(f"🗑️  Очистка папки {self.knowledge_dir}")
            shutil.rmtree(self.knowledge_dir)
        
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.log(f"✅ Создана папка {self.knowledge_dir}")
    
    def process_single_file(self, pdf_file: Path, file_index: int, total_files: int) -> Tuple[Dict, str]:
        """Обработать один PDF файл (для параллельного выполнения)"""
        try:
            # Извлекаем текст
            text, page_count = self.extract_text_from_pdf(pdf_file)
            
            if not text:
                return None, f"⚠️  Пропуск {pdf_file.name}: не удалось извлечь текст"
            
            # Определяем язык документа
            doc_lang = self.detect_document_language(pdf_file, text)
            
            # Определяем категорию (с языком)
            metadata = self.categorize_file(pdf_file.name, text, lang=doc_lang)
            
            # Создаем markdown документ
            md_filename, md_content = self.create_markdown_document(
                pdf_file, text, page_count, metadata
            )
            
            # Определяем базовую директорию (с учетом языка)
            if self.bilingual and self.language_router:
                base_dir = self.language_router.get_docs_dir(doc_lang)
            else:
                base_dir = self.knowledge_dir
            
            # Создаем папку для страны
            country_dir = base_dir / metadata['country']
            country_dir.mkdir(exist_ok=True, parents=True)
            
            # Сохраняем файл с проверкой на дубликаты
            md_path = country_dir / md_filename
            version = 2
            while md_path.exists():
                base_name = md_filename.replace('.md', '')
                md_filename = f"{base_name}_v{version}.md"
                md_path = country_dir / md_filename
                version += 1
            
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            # Формируем путь к документу (относительно knowledge/)
            if self.bilingual and self.language_router:
                # Путь включает языковую папку: rus/Country/file.md
                doc_path = f"{doc_lang}/{metadata['country']}/{md_filename}"
            else:
                # Legacy путь: Country/file.md
                doc_path = f"{metadata['country']}/{md_filename}"
            
            # Готовим информацию о документе
            doc_info = {
                'country': metadata['country'],
                'title': f"{metadata['country']}: {metadata['program_type']}",
                'path': doc_path,
                'summary': metadata['summary'],
                'subcategory': metadata['subcategory'],
                'tags': metadata['tags'],
                'source_file': str(pdf_file.name),
                'checksum': self.calculate_checksum(pdf_file)[0],
                'lang': doc_lang if self.bilingual else None
            }
            
            return doc_info, f"✅ ({doc_lang.upper()}) Создан: {doc_path}"
            
        except Exception as e:
            return None, f"❌ Ошибка при обработке {pdf_file.name}: {e}"
    
    def process_all_files(self):
        """Обработать все PDF файлы в папке raw (с параллелизмом)"""
        # Собираем файлы из всех источников
        pdf_files = []
        
        # Legacy файлы в корне raw/
        pdf_files.extend(list(self.raw_dir.glob("*.pdf")))
        
        # Файлы в языковых папках (если двуязычный режим)
        if self.bilingual:
            rus_dir = self.raw_dir / 'rus'
            eng_dir = self.raw_dir / 'eng'
            
            if rus_dir.exists():
                pdf_files.extend(list(rus_dir.glob("*.pdf")))
            
            if eng_dir.exists():
                pdf_files.extend(list(eng_dir.glob("*.pdf")))
        
        pdf_files = sorted(pdf_files)
        
        if not pdf_files:
            self.log("❌ Не найдено PDF файлов в папке raw/")
            return
        
        self.log(f"📚 Найдено {len(pdf_files)} PDF файлов для обработки")
        self.log(f"⚡ Используется {min(MAX_WORKERS, len(pdf_files))} потоков")
        
        # Группировка по странам
        countries = {}
        manifest_sources = []
        
        # Параллельная обработка файлов
        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(pdf_files))) as executor:
            futures = {}
            for i, pdf_file in enumerate(pdf_files):
                future = executor.submit(self.process_single_file, pdf_file, i + 1, len(pdf_files))
                futures[future] = pdf_file
            
            # Собираем результаты по мере готовности
            completed = 0
            for future in as_completed(futures):
                pdf_file = futures[future]
                completed += 1
                
                try:
                    doc_info, log_message = future.result()
                    
                    if doc_info:
                        self.documents.append(doc_info)
                        
                        # Добавляем в языковую коллекцию (если двуязычный режим)
                        if self.bilingual and doc_info.get('lang'):
                            doc_lang = doc_info['lang']
                            self.documents_by_lang[doc_lang].append(doc_info)
                        
                        # Группируем по странам
                        country = doc_info['country']
                        if country not in countries:
                            countries[country] = []
                        countries[country].append(doc_info)
                        
                        # Добавляем в manifest
                        checksum, size, mtime = self.calculate_checksum(pdf_file)
                        manifest_sources.append({
                            'path': f"raw/{pdf_file.name}",
                            'sha256': checksum,
                            'size': size,
                            'mtime': mtime
                        })
                    
                    # Логируем каждые 10 файлов или последний
                    if completed % 10 == 0 or completed == len(pdf_files):
                        self.log(f"📄 [{completed}/{len(pdf_files)}] {log_message}")
                    
                except Exception as e:
                    self.log(f"❌ Ошибка обработки {pdf_file.name}: {e}")
        
        # Сохраняем manifest
        self.save_manifest(manifest_sources)
        
        return countries
    
    def create_index(self, countries: Dict):
        """Создать индексный файл 00_index.md"""
        self.log("📑 Создание индексного файла...")
        
        index_content = f"""---
title: "База знаний — Иммиграционные программы"
type: "index"
created: "{self.build_date}"
total_documents: {len(self.documents)}
total_categories: {len(countries)}
version: "{hashlib.md5(str(self.documents).encode()).hexdigest()[:8]}"
---

# База знаний — Иммиграционные программы

Полная база данных иммиграционных программ Intermark Global.

**Обновлено:** {self.build_date}  
**Всего документов:** {len(self.documents)}  
**Категорий (стран/регионов):** {len(countries)}

---

## Категории по странам

"""
        
        # Сортируем страны по алфавиту
        for country in sorted(countries.keys()):
            docs = countries[country]
            index_content += f"\n### {country}\n\n"
            
            for doc in sorted(docs, key=lambda x: x['subcategory']):
                index_content += f"- [{doc['title']}]({doc['path']})\n"
                index_content += f"  - *{doc['summary'][:100]}...*\n"
        
        index_content += f"""

---

## Статистика

- Обработано файлов: {len(self.documents)}
- Категорий: {len(countries)}
- Дата создания: {self.build_date}

---

*Сгенерировано автоматически из презентаций Intermark Global*
"""
        
        index_path = self.knowledge_dir / "00_index.md"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        self.log(f"✅ Создан индексный файл: 00_index.md")
    
    def save_manifest(self, sources: List[Dict]):
        """Сохранить manifest.json (и языковые манифесты если двуязычный режим)"""
        try:
            version = f"build_{self.build_date}_{datetime.now().strftime('%H-%M')}"
            
            # Общий manifest (legacy совместимость)
            manifest = {
                'version': version,
                'created': datetime.now().isoformat(),
                'sources': sources,
                'total_documents': len(self.documents),
                'total_sources': len(sources)
            }
            
            manifest_path = self.knowledge_dir / 'manifest.json'
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            self.log(f"✅ Создан manifest: {len(sources)} источников")
            
            # Языковые манифесты (если двуязычный режим)
            if self.bilingual and self.documents_by_lang and self.language_router:
                for lang in ['rus', 'eng']:
                    lang_docs = self.documents_by_lang[lang]
                    
                    # Фильтруем источники по языку
                    lang_sources = [
                        s for s in sources 
                        if any(doc['source_file'] == Path(s['path']).name and doc.get('lang') == lang 
                               for doc in lang_docs)
                    ]
                    
                    lang_manifest = {
                        'version': version,
                        'created': datetime.now().isoformat(),
                        'language': lang,
                        'sources': lang_sources,
                        'total_documents': len(lang_docs),
                        'total_sources': len(lang_sources)
                    }
                    
                    lang_manifest_path = self.language_router.get_manifest_path(lang)
                    with open(lang_manifest_path, 'w', encoding='utf-8') as f:
                        json.dump(lang_manifest, f, indent=2, ensure_ascii=False)
                    
                    self.log(f"✅ Создан manifest.{lang}.json: {len(lang_docs)} документов")
            
        except Exception as e:
            self.log(f"⚠️  Ошибка создания manifest: {e}")
    
    def create_build_log(self):
        """Создать лог сборки"""
        self.log("📋 Создание лога сборки...")
        
        # Формируем статистику по языкам
        lang_stats = ""
        if self.bilingual and self.documents_by_lang:
            lang_stats = "\n### Языковая статистика\n\n"
            for lang in ['rus', 'eng']:
                count = len(self.documents_by_lang[lang])
                lang_stats += f"- **{lang.upper()}:** {count} документов\n"
        
        log_content = f"""# Лог сборки базы знаний

**Дата:** {self.build_date}  
**Время начала:** {self.build_log[0].split(']')[0].strip('[')}  
**Время окончания:** {self.build_log[-1].split(']')[0].strip('[')}

## Результаты

- **Обработано файлов:** {len(self.documents)}
- **Создано документов:** {len(self.documents)}
- **Категорий:** {len(set(doc['country'] for doc in self.documents))}
{lang_stats}
## Подробный лог

"""
        
        for entry in self.build_log:
            log_content += f"{entry}\n"
        
        log_path = self.knowledge_dir / "build_log.md"
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        self.log(f"✅ Создан лог сборки: build_log.md")
    
    def build(self):
        """Главный метод сборки базы знаний"""
        self.log("🚀 Начало создания базы знаний")
        self.log(f"📂 Исходная папка: {self.raw_dir}")
        self.log(f"📂 Целевая папка: {self.knowledge_dir}")
        
        # Шаг 0: Создание структуры директорий (если двуязычный режим)
        if self.bilingual and self.language_router:
            self.language_router.ensure_structure()
            self.log("✅ Двуязычная структура директорий готова")
        
        # Шаг 1: Очистка (НЕ очищаем языковые папки, только legacy)
        # self.clean_knowledge_dir() - закомментировано для безопасности
        
        # Шаг 2: Обработка файлов
        countries = self.process_all_files()
        
        if not countries:
            self.log("❌ Не создано ни одного документа")
            return
        
        # Шаг 3: Создание индекса
        self.create_index(countries)
        
        # Шаг 4: Создание лога
        self.create_build_log()
        
        # Итоговая статистика
        self.log("")
        self.log("=" * 60)
        self.log(f"✅ ЗАВЕРШЕНО: Создано {len(self.documents)} документов")
        self.log(f"📊 Категорий (стран): {len(countries)}")
        
        # Статистика по языкам
        if self.bilingual and self.documents_by_lang:
            self.log(f"🌍 Языковая статистика:")
            for lang in ['rus', 'eng']:
                count = len(self.documents_by_lang[lang])
                if count > 0:
                    self.log(f"   • {lang.upper()}: {count} документов")
        
        self.log(f"📅 Дата сборки: {self.build_date}")
        self.log("=" * 60)


def main():
    # Определяем пути
    base_dir = Path(__file__).parent
    raw_dir = base_dir / "raw"
    knowledge_dir = base_dir / "knowledge"
    
    # Создаем и запускаем сборщик
    builder = KnowledgeBaseBuilder(raw_dir, knowledge_dir)
    builder.build()


if __name__ == "__main__":
    main()

