#!/usr/bin/env python3
"""
Скрипт для поиска в базе знаний
Поддерживает поиск по странам, тегам, типам программ и полнотекстовый поиск
"""

import sys
import re
from pathlib import Path
from typing import List, Dict


class KnowledgeSearcher:
    def __init__(self, knowledge_dir: str):
        self.knowledge_dir = Path(knowledge_dir)
        
    def extract_metadata(self, md_path: Path) -> Dict:
        """Извлечь метаданные из Markdown файла"""
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Ищем YAML frontmatter
            match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
            if not match:
                return {}
            
            yaml_content = match.group(1)
            body_content = match.group(2)
            
            # Парсим метаданные
            metadata = {'body': body_content}
            for line in yaml_content.split('\n'):
                if ':' in line and not line.strip().startswith('-'):
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    metadata[key] = value
            
            return metadata
        except Exception as e:
            return {}
    
    def search_by_country(self, country: str) -> List[Path]:
        """Поиск по стране"""
        results = []
        country_lower = country.lower()
        
        for md_file in self.knowledge_dir.rglob("*.md"):
            if md_file.name in ['00_index.md', 'build_log.md', 'update_log.md']:
                continue
            
            metadata = self.extract_metadata(md_file)
            file_country = metadata.get('category', '').lower()
            
            if country_lower in file_country:
                results.append(md_file)
        
        return results
    
    def search_by_type(self, program_type: str) -> List[Path]:
        """Поиск по типу программы"""
        results = []
        type_map = {
            'citizenship': 'citizenship',
            'гражданство': 'citizenship',
            'residence': 'residence-permit',
            'вид': 'residence-permit',
            'permanent': 'permanent-residence',
            'постоянное': 'permanent-residence',
            'passport': 'passport',
            'паспорт': 'passport'
        }
        
        search_type = type_map.get(program_type.lower(), program_type.lower())
        
        for md_file in self.knowledge_dir.rglob("*.md"):
            if md_file.name in ['00_index.md', 'build_log.md', 'update_log.md']:
                continue
            
            metadata = self.extract_metadata(md_file)
            file_type = metadata.get('subcategory', '').lower()
            
            if search_type in file_type:
                results.append(md_file)
        
        return results
    
    def search_fulltext(self, query: str) -> List[tuple]:
        """Полнотекстовый поиск"""
        results = []
        query_lower = query.lower()
        
        for md_file in self.knowledge_dir.rglob("*.md"):
            if md_file.name in ['00_index.md', 'build_log.md', 'update_log.md']:
                continue
            
            metadata = self.extract_metadata(md_file)
            body = metadata.get('body', '').lower()
            
            if query_lower in body:
                # Находим контекст
                body_lower = metadata.get('body', '').lower()
                index = body_lower.find(query_lower)
                start = max(0, index - 100)
                end = min(len(body), index + len(query) + 100)
                context = metadata.get('body', '')[start:end].strip()
                
                results.append((md_file, context))
        
        return results
    
    def print_results(self, results, query_type=""):
        """Вывести результаты поиска"""
        if not results:
            print(f"\n❌ Ничего не найдено по запросу: {query_type}")
            return
        
        print(f"\n✅ Найдено результатов: {len(results)}")
        print("=" * 80)
        
        for i, item in enumerate(results, 1):
            if isinstance(item, tuple):
                md_file, context = item
                metadata = self.extract_metadata(md_file)
                print(f"\n{i}. {metadata.get('title', md_file.name)}")
                print(f"   📁 {md_file.relative_to(self.knowledge_dir)}")
                print(f"   📝 Категория: {metadata.get('category', 'N/A')}")
                print(f"   🔍 Контекст: ...{context}...")
            else:
                md_file = item
                metadata = self.extract_metadata(md_file)
                print(f"\n{i}. {metadata.get('title', md_file.name)}")
                print(f"   📁 {md_file.relative_to(self.knowledge_dir)}")
                print(f"   📝 Категория: {metadata.get('category', 'N/A')}")
                print(f"   📌 Тип: {metadata.get('subcategory', 'N/A')}")
                print(f"   💬 {metadata.get('summary', 'N/A')[:150]}...")


def main():
    base_dir = Path(__file__).parent
    knowledge_dir = base_dir / "knowledge"
    
    if not knowledge_dir.exists():
        print("❌ Папка knowledge/ не найдена. Запустите сначала build_knowledge.py")
        sys.exit(1)
    
    searcher = KnowledgeSearcher(knowledge_dir)
    
    # Интерактивный режим
    if len(sys.argv) == 1:
        print("🔍 Поиск в базе знаний")
        print("=" * 80)
        print("\nВыберите тип поиска:")
        print("1. Поиск по стране")
        print("2. Поиск по типу программы")
        print("3. Полнотекстовый поиск")
        print("0. Выход")
        
        choice = input("\nВаш выбор (0-3): ").strip()
        
        if choice == "1":
            country = input("Введите страну: ").strip()
            results = searcher.search_by_country(country)
            searcher.print_results(results, f"страна: {country}")
        elif choice == "2":
            ptype = input("Введите тип (citizenship/residence/permanent/passport): ").strip()
            results = searcher.search_by_type(ptype)
            searcher.print_results(results, f"тип: {ptype}")
        elif choice == "3":
            query = input("Введите поисковый запрос: ").strip()
            results = searcher.search_fulltext(query)
            searcher.print_results(results, f"текст: {query}")
    
    # Режим командной строки
    else:
        if sys.argv[1] == "--country":
            results = searcher.search_by_country(sys.argv[2])
            searcher.print_results(results, f"страна: {sys.argv[2]}")
        elif sys.argv[1] == "--type":
            results = searcher.search_by_type(sys.argv[2])
            searcher.print_results(results, f"тип: {sys.argv[2]}")
        elif sys.argv[1] == "--search":
            results = searcher.search_fulltext(sys.argv[2])
            searcher.print_results(results, f"текст: {sys.argv[2]}")
        else:
            print("Использование:")
            print("  python3 search_knowledge.py --country <название>")
            print("  python3 search_knowledge.py --type <тип>")
            print("  python3 search_knowledge.py --search <запрос>")


if __name__ == "__main__":
    main()

