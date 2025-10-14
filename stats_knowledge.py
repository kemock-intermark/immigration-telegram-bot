#!/usr/bin/env python3
"""
Скрипт для получения статистики по базе знаний
Показывает детальную информацию о документах, категориях и метаданных
"""

import re
from pathlib import Path
from typing import Dict, List
from collections import Counter


class KnowledgeStats:
    def __init__(self, knowledge_dir: str):
        self.knowledge_dir = Path(knowledge_dir)
        self.documents = []
        
    def extract_metadata(self, md_path: Path) -> Dict:
        """Извлечь метаданные из Markdown файла"""
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
            if not match:
                return {}
            
            yaml_content = match.group(1)
            body_content = match.group(2)
            
            metadata = {'body': body_content, 'file_path': md_path}
            for line in yaml_content.split('\n'):
                if ':' in line and not line.strip().startswith('-'):
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    metadata[key] = value
            
            return metadata
        except Exception as e:
            return {}
    
    def collect_all_documents(self):
        """Собрать все документы"""
        for md_file in self.knowledge_dir.rglob("*.md"):
            if md_file.name in ['00_index.md', 'build_log.md', 'update_log.md']:
                continue
            
            metadata = self.extract_metadata(md_file)
            if metadata:
                self.documents.append(metadata)
    
    def get_summary(self):
        """Получить общую статистику"""
        print("\n" + "=" * 80)
        print("📊 СТАТИСТИКА БАЗЫ ЗНАНИЙ")
        print("=" * 80)
        
        total_docs = len(self.documents)
        print(f"\n📚 Всего документов: {total_docs}")
        
        # Категории (страны)
        categories = Counter([doc.get('category', 'Unknown') for doc in self.documents])
        print(f"🌍 Категорий (стран): {len(categories)}")
        
        # Типы программ
        subcategories = Counter([doc.get('subcategory', 'Unknown') for doc in self.documents])
        
        print("\n" + "-" * 80)
        print("📋 РАСПРЕДЕЛЕНИЕ ПО ТИПАМ ПРОГРАММ:")
        print("-" * 80)
        
        type_names = {
            'citizenship': 'Гражданство',
            'residence-permit': 'Вид на жительство',
            'permanent-residence': 'Постоянное проживание',
            'passport': 'Паспорт',
            'golden-visa': 'Золотая виза',
            'general': 'Общая информация'
        }
        
        for subcat, count in subcategories.most_common():
            name = type_names.get(subcat, subcat)
            print(f"  • {name}: {count} документов")
        
        print("\n" + "-" * 80)
        print("🌍 ТОП-10 СТРАН ПО КОЛИЧЕСТВУ ДОКУМЕНТОВ:")
        print("-" * 80)
        
        for country, count in categories.most_common(10):
            print(f"  {count:2d}. {country}")
        
        # Вычисляем общий объём
        total_chars = sum(len(doc.get('body', '')) for doc in self.documents)
        total_words = sum(len(doc.get('body', '').split()) for doc in self.documents)
        
        print("\n" + "-" * 80)
        print("📏 ОБЪЁМ БАЗЫ ЗНАНИЙ:")
        print("-" * 80)
        print(f"  • Всего символов: {total_chars:,}")
        print(f"  • Всего слов: {total_words:,}")
        print(f"  • Среднее слов на документ: {total_words // total_docs if total_docs > 0 else 0:,}")
        
        # Источники
        sources = set()
        for doc in self.documents:
            body = doc.get('body', '')
            # Ищем ссылки на источники
            matches = re.findall(r'raw/([^\s→]+\.pdf)', body)
            sources.update(matches)
        
        print(f"\n📄 Исходных PDF файлов: {len(sources)}")
        
        print("\n" + "=" * 80)
    
    def get_detailed_by_country(self, country: str):
        """Детальная статистика по стране"""
        country_docs = [doc for doc in self.documents 
                       if country.lower() in doc.get('category', '').lower()]
        
        if not country_docs:
            print(f"\n❌ Документы для страны '{country}' не найдены")
            return
        
        print(f"\n" + "=" * 80)
        print(f"🌍 СТАТИСТИКА: {country.upper()}")
        print("=" * 80)
        print(f"\n📚 Всего документов: {len(country_docs)}")
        
        print("\n📋 Список документов:")
        for i, doc in enumerate(country_docs, 1):
            print(f"\n  {i}. {doc.get('title', 'Без названия')}")
            print(f"     Тип: {doc.get('subcategory', 'N/A')}")
            print(f"     Файл: {doc.get('file_path').relative_to(self.knowledge_dir)}")
            print(f"     Версия: {doc.get('version', 'N/A')}")
            print(f"     Дата: {doc.get('extraction_date', 'N/A')}")
    
    def list_all_countries(self):
        """Список всех стран"""
        categories = sorted(set([doc.get('category', 'Unknown') for doc in self.documents]))
        
        print("\n" + "=" * 80)
        print("🌍 ПОЛНЫЙ СПИСОК СТРАН В БАЗЕ ЗНАНИЙ")
        print("=" * 80)
        print(f"\nВсего: {len(categories)} стран/регионов\n")
        
        for i, country in enumerate(categories, 1):
            count = sum(1 for doc in self.documents if doc.get('category') == country)
            print(f"  {i:2d}. {country} ({count} документов)")


def main():
    import sys
    
    base_dir = Path(__file__).parent
    knowledge_dir = base_dir / "knowledge"
    
    if not knowledge_dir.exists():
        print("❌ Папка knowledge/ не найдена. Запустите сначала build_knowledge.py")
        sys.exit(1)
    
    stats = KnowledgeStats(knowledge_dir)
    stats.collect_all_documents()
    
    # Режим командной строки
    if len(sys.argv) > 1:
        if sys.argv[1] == "--country":
            if len(sys.argv) > 2:
                stats.get_detailed_by_country(sys.argv[2])
            else:
                print("❌ Укажите название страны")
        elif sys.argv[1] == "--list":
            stats.list_all_countries()
        else:
            stats.get_summary()
    else:
        # Интерактивный режим
        stats.get_summary()
        
        print("\n" + "=" * 80)
        print("Дополнительные команды:")
        print("  python3 stats_knowledge.py --list          # Список всех стран")
        print("  python3 stats_knowledge.py --country <название>  # Статистика по стране")
        print("=" * 80)


if __name__ == "__main__":
    main()

