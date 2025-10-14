#!/usr/bin/env python3
"""
Скрипт для создания базы знаний из PDF презентаций
Извлекает текст, структурирует по темам и сохраняет в формате Markdown
"""

import os
import sys
import hashlib
import re
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil

try:
    import PyPDF2
except ImportError:
    print("Установка необходимых библиотек...")
    os.system(f"{sys.executable} -m pip install PyPDF2 --quiet")
    import PyPDF2

# Настройки производительности
MAX_WORKERS = min(os.cpu_count() - 1 if os.cpu_count() else 1, 6)
BATCH_SIZE = 4


class KnowledgeBaseBuilder:
    def __init__(self, raw_dir: str, knowledge_dir: str):
        self.raw_dir = Path(raw_dir)
        self.knowledge_dir = Path(knowledge_dir)
        self.build_date = datetime.now().strftime("%Y-%m-%d")
        self.documents = []
        self.build_log = []
        
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
    
    def categorize_file(self, filename: str, content: str) -> Dict[str, any]:
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
        
        return {
            'country': country,
            'program_type': program_type,
            'subcategory': subcategory,
            'summary': summary,
            'tags': tags
        }
    
    def create_markdown_document(self, pdf_file: Path, text: str, page_count: int, 
                                 metadata: Dict) -> str:
        """Создать Markdown документ по шаблону"""
        checksum = self.calculate_checksum(pdf_file)
        
        # Формируем имя файла для markdown
        safe_name = re.sub(r'[^\w\s-]', '', metadata['country'])
        safe_name = re.sub(r'[-\s]+', '-', safe_name).strip('-').lower()
        md_filename = f"{safe_name}-{metadata['subcategory']}.md"
        
        # Создаем метаданные
        doc = f"""---
title: "{metadata['country']}: {metadata['program_type']}"
summary: "{metadata['summary']}"
category: "{metadata['country']}"
subcategory: "{metadata['subcategory']}"
tags: {metadata['tags']}
source_files:
  - path: "raw/{pdf_file.name}"
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
            
            # Определяем категорию
            metadata = self.categorize_file(pdf_file.name, text)
            
            # Создаем markdown документ
            md_filename, md_content = self.create_markdown_document(
                pdf_file, text, page_count, metadata
            )
            
            # Создаем папку для страны если нужно
            country_dir = self.knowledge_dir / metadata['country']
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
            
            # Готовим информацию о документе
            doc_info = {
                'country': metadata['country'],
                'title': f"{metadata['country']}: {metadata['program_type']}",
                'path': f"{metadata['country']}/{md_filename}",
                'summary': metadata['summary'],
                'subcategory': metadata['subcategory'],
                'tags': metadata['tags'],
                'source_file': str(pdf_file.name),
                'checksum': self.calculate_checksum(pdf_file)[0]
            }
            
            return doc_info, f"✅ Создан: {metadata['country']}/{md_filename}"
            
        except Exception as e:
            return None, f"❌ Ошибка при обработке {pdf_file.name}: {e}"
    
    def process_all_files(self):
        """Обработать все PDF файлы в папке raw (с параллелизмом)"""
        pdf_files = sorted(self.raw_dir.glob("*.pdf"))
        
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
        """Сохранить manifest.json"""
        try:
            manifest = {
                'version': f"build_{self.build_date}_{datetime.now().strftime('%H-%M')}",
                'created': datetime.now().isoformat(),
                'sources': sources,
                'total_documents': len(self.documents),
                'total_sources': len(sources)
            }
            
            manifest_path = self.knowledge_dir / 'manifest.json'
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            self.log(f"✅ Создан manifest: {len(sources)} источников")
        except Exception as e:
            self.log(f"⚠️  Ошибка создания manifest: {e}")
    
    def create_build_log(self):
        """Создать лог сборки"""
        self.log("📋 Создание лога сборки...")
        
        log_content = f"""# Лог сборки базы знаний

**Дата:** {self.build_date}  
**Время начала:** {self.build_log[0].split(']')[0].strip('[')}  
**Время окончания:** {self.build_log[-1].split(']')[0].strip('[')}

## Результаты

- **Обработано файлов:** {len(self.documents)}
- **Создано документов:** {len(self.documents)}
- **Категорий:** {len(set(doc['country'] for doc in self.documents))}

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
        
        # Шаг 1: Очистка
        self.clean_knowledge_dir()
        
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
        self.log(f"✅ ЗАВЕРШЕНО: Создано {len(self.documents)} документов из {len(list(self.raw_dir.glob('*.pdf')))} презентаций")
        self.log(f"📊 Категорий (стран): {len(countries)}")
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

