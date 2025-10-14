#!/usr/bin/env python3
"""
Скрипт для инкрементального обновления базы знаний
Обновляет только изменённые файлы на основе контрольных сумм
"""

import os
import sys
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Set

try:
    import PyPDF2
except ImportError:
    print("Установка необходимых библиотек...")
    os.system(f"{sys.executable} -m pip install PyPDF2 --quiet")
    import PyPDF2


class KnowledgeBaseUpdater:
    def __init__(self, raw_dir: str, knowledge_dir: str):
        self.raw_dir = Path(raw_dir)
        self.knowledge_dir = Path(knowledge_dir)
        self.update_date = datetime.now().strftime("%Y-%m-%d")
        self.update_log = []
        self.updated_count = 0
        self.skipped_count = 0
        self.new_count = 0
        self.documents = []
        
    def log(self, message: str):
        """Добавить запись в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.update_log.append(log_entry)
        print(log_entry)
    
    def calculate_checksum(self, file_path: Path) -> str:
        """Вычислить SHA256 хеш файла (первые 16 символов)"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]
    
    def extract_metadata_from_md(self, md_path: Path) -> Dict:
        """Извлечь метаданные из существующего Markdown файла"""
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Ищем YAML frontmatter
            match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
            if not match:
                return {}
            
            yaml_content = match.group(1)
            
            # Парсим YAML вручную (простой парсер)
            metadata = {}
            for line in yaml_content.split('\n'):
                if ':' in line and not line.strip().startswith('-'):
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    metadata[key] = value
            
            return metadata
        except Exception as e:
            self.log(f"⚠️  Ошибка чтения метаданных из {md_path.name}: {e}")
            return {}
    
    def find_md_for_source(self, source_filename: str) -> List[Path]:
        """Найти все MD файлы, связанные с исходным файлом"""
        md_files = []
        
        if not self.knowledge_dir.exists():
            return md_files
        
        # Рекурсивно ищем все .md файлы
        for md_file in self.knowledge_dir.rglob("*.md"):
            if md_file.name in ['00_index.md', 'build_log.md', 'update_log.md']:
                continue
            
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if f'raw/{source_filename}' in content:
                        md_files.append(md_file)
            except:
                continue
        
        return md_files
    
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
        match = re.match(r'Intermark\.\s+(.+?)\s+(Residence|Citizenship|Passport|visa|RP|PR|Permit)', 
                        filename, re.IGNORECASE)
        
        if match:
            country = match.group(1).strip()
        else:
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
        
        # Генерируем краткое описание
        lines = [l.strip() for l in content.split('\n') if l.strip() and not l.startswith('---')]
        summary = ' '.join(lines[:3])[:200] if lines else "Информация об иммиграционной программе"
        
        # Теги
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
                                 metadata: Dict) -> Tuple[str, str]:
        """Создать Markdown документ по шаблону"""
        checksum = self.calculate_checksum(pdf_file)
        
        # Формируем имя файла
        safe_name = re.sub(r'[^\w\s-]', '', metadata['country'])
        safe_name = re.sub(r'[-\s]+', '-', safe_name).strip('-').lower()
        md_filename = f"{safe_name}-{metadata['subcategory']}.md"
        
        # Создаем документ
        doc = f"""---
title: "{metadata['country']}: {metadata['program_type']}"
summary: "{metadata['summary']}"
category: "{metadata['country']}"
subcategory: "{metadata['subcategory']}"
tags: {metadata['tags']}
source_files:
  - path: "raw/{pdf_file.name}"
    slides: [1-{page_count}]
extraction_date: "{self.update_date}"
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
    
    def update_files(self):
        """Обновить изменённые файлы"""
        pdf_files = sorted(self.raw_dir.glob("*.pdf"))
        
        if not pdf_files:
            self.log("❌ Не найдено PDF файлов в папке raw/")
            return {}
        
        self.log(f"📚 Найдено {len(pdf_files)} PDF файлов для проверки")
        
        # Группировка по странам
        countries = {}
        
        for i, pdf_file in enumerate(pdf_files, 1):
            self.log(f"📄 [{i}/{len(pdf_files)}] Проверка: {pdf_file.name}")
            
            # Вычисляем текущий хеш
            current_checksum = self.calculate_checksum(pdf_file)
            
            # Ищем соответствующие MD файлы
            md_files = self.find_md_for_source(pdf_file.name)
            
            # Проверяем, нужно ли обновлять
            needs_update = False
            existing_md = None
            
            if not md_files:
                self.log(f"  ➕ Новый файл (не найден в базе)")
                needs_update = True
                self.new_count += 1
            else:
                existing_md = md_files[0]
                metadata = self.extract_metadata_from_md(existing_md)
                stored_checksum = metadata.get('checksum_sources', '')
                
                if stored_checksum != current_checksum:
                    self.log(f"  🔄 Файл изменён (хеш: {stored_checksum[:8]} → {current_checksum[:8]})")
                    needs_update = True
                    self.updated_count += 1
                else:
                    self.log(f"  ✅ Без изменений")
                    self.skipped_count += 1
                    
                    # Добавляем в список документов для индекса
                    doc_info = {
                        'country': metadata.get('category', 'Unknown'),
                        'title': metadata.get('title', pdf_file.stem),
                        'path': str(existing_md.relative_to(self.knowledge_dir)),
                        'summary': metadata.get('summary', ''),
                        'subcategory': metadata.get('subcategory', 'general'),
                        'tags': []
                    }
                    self.documents.append(doc_info)
                    
                    if doc_info['country'] not in countries:
                        countries[doc_info['country']] = []
                    countries[doc_info['country']].append(doc_info)
            
            # Обновляем файл если нужно
            if needs_update:
                # Извлекаем текст
                text, page_count = self.extract_text_from_pdf(pdf_file)
                
                if not text:
                    self.log(f"  ⚠️  Пропуск: не удалось извлечь текст")
                    continue
                
                # Определяем категорию
                file_metadata = self.categorize_file(pdf_file.name, text)
                
                # Создаем markdown
                md_filename, md_content = self.create_markdown_document(
                    pdf_file, text, page_count, file_metadata
                )
                
                # Создаем папку для страны
                country_dir = self.knowledge_dir / file_metadata['country']
                country_dir.mkdir(exist_ok=True)
                
                # Определяем путь для сохранения
                if existing_md:
                    md_path = existing_md
                else:
                    md_path = country_dir / md_filename
                    version = 2
                    while md_path.exists():
                        base_name = md_filename.replace('.md', '')
                        md_filename = f"{base_name}_v{version}.md"
                        md_path = country_dir / md_filename
                        version += 1
                
                # Сохраняем
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                
                # Добавляем в список документов
                doc_info = {
                    'country': file_metadata['country'],
                    'title': f"{file_metadata['country']}: {file_metadata['program_type']}",
                    'path': str(md_path.relative_to(self.knowledge_dir)),
                    'summary': file_metadata['summary'],
                    'subcategory': file_metadata['subcategory'],
                    'tags': file_metadata['tags']
                }
                self.documents.append(doc_info)
                
                if file_metadata['country'] not in countries:
                    countries[file_metadata['country']] = []
                countries[file_metadata['country']].append(doc_info)
                
                self.log(f"  ✅ Обновлён: {md_path.relative_to(self.knowledge_dir)}")
        
        return countries
    
    def create_index(self, countries: Dict):
        """Обновить индексный файл 00_index.md"""
        self.log("📑 Обновление индексного файла...")
        
        index_content = f"""---
title: "База знаний — Иммиграционные программы"
type: "index"
created: "{self.update_date}"
total_documents: {len(self.documents)}
total_categories: {len(countries)}
version: "{hashlib.md5(str(self.documents).encode()).hexdigest()[:8]}"
---

# База знаний — Иммиграционные программы

Полная база данных иммиграционных программ Intermark Global.

**Обновлено:** {self.update_date}  
**Всего документов:** {len(self.documents)}  
**Категорий (стран/регионов):** {len(countries)}

---

## Категории по странам

"""
        
        for country in sorted(countries.keys()):
            docs = countries[country]
            index_content += f"\n### {country}\n\n"
            
            for doc in sorted(docs, key=lambda x: x['subcategory']):
                index_content += f"- [{doc['title']}]({doc['path']})\n"
                summary_text = doc['summary'][:100] + "..." if len(doc['summary']) > 100 else doc['summary']
                index_content += f"  - *{summary_text}*\n"
        
        index_content += f"""

---

## Статистика

- Обработано файлов: {len(self.documents)}
- Категорий: {len(countries)}
- Дата обновления: {self.update_date}

---

*Сгенерировано автоматически из презентаций Intermark Global*
"""
        
        index_path = self.knowledge_dir / "00_index.md"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        self.log(f"✅ Обновлён индексный файл: 00_index.md")
    
    def create_update_log(self):
        """Создать лог обновления"""
        self.log("📋 Создание лога обновления...")
        
        log_content = f"""# Лог обновления базы знаний

**Дата:** {self.update_date}  
**Время начала:** {self.update_log[0].split(']')[0].strip('[')}  
**Время окончания:** {self.update_log[-1].split(']')[0].strip('[')}

## Результаты

- **Новых файлов:** {self.new_count}
- **Обновлено документов:** {self.updated_count}
- **Без изменений:** {self.skipped_count}
- **Всего проверено:** {self.new_count + self.updated_count + self.skipped_count}

## Подробный лог

"""
        
        for entry in self.update_log:
            log_content += f"{entry}\n"
        
        log_path = self.knowledge_dir / "update_log.md"
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        self.log(f"✅ Создан лог обновления: update_log.md")
    
    def update(self):
        """Главный метод обновления базы знаний"""
        self.log("🔄 Начало обновления базы знаний")
        self.log(f"📂 Исходная папка: {self.raw_dir}")
        self.log(f"📂 Целевая папка: {self.knowledge_dir}")
        
        # Проверяем существование папки knowledge
        if not self.knowledge_dir.exists():
            self.log("⚠️  Папка knowledge/ не существует. Запустите сначала /создать_базу")
            self.log("   Создаю новую структуру...")
            self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        # Обновляем файлы
        countries = self.update_files()
        
        if not countries:
            self.log("❌ Не создано/обновлено ни одного документа")
            return
        
        # Обновляем индекс
        self.create_index(countries)
        
        # Создаем лог
        self.create_update_log()
        
        # Итоговая статистика
        self.log("")
        self.log("=" * 60)
        self.log(f"✅ ЗАВЕРШЕНО")
        self.log(f"   Новых файлов: {self.new_count}")
        self.log(f"   Обновлено: {self.updated_count}")
        self.log(f"   Без изменений: {self.skipped_count}")
        self.log(f"📅 Дата обновления: {self.update_date}")
        self.log("=" * 60)


def main():
    base_dir = Path(__file__).parent
    raw_dir = base_dir / "raw"
    knowledge_dir = base_dir / "knowledge"
    
    updater = KnowledgeBaseUpdater(raw_dir, knowledge_dir)
    updater.update()


if __name__ == "__main__":
    main()

