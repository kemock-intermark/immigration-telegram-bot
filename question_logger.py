#!/usr/bin/env python3
"""
Логирование всех вопросов из Telegram с автосинхронизацией через Git
"""

import json
import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
import threading
import time


class QuestionLogger:
    def __init__(self, log_dir: str):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Файл логов (JSON Lines формат)
        self.log_file = self.log_dir / "telegram_questions.jsonl"
        
        # Счётчик для автосинхронизации
        self.questions_since_sync = 0
        self.sync_threshold = 10  # Синхронизировать каждые 10 вопросов
        self.last_sync_time = time.time()
        self.sync_interval = 3600  # Или каждый час (в секундах)
        
        # Lock для thread-safety
        self.lock = threading.Lock()
        
        print(f"📝 Логирование вопросов в: {self.log_file}")
    
    def log_question(
        self,
        user_id: int,
        username: Optional[str],
        question: str,
        answer_found: bool,
        response_length: int = 0,
        lang: Optional[str] = None
    ):
        """Залогировать вопрос пользователя с указанием языка"""
        with self.lock:
            try:
                # Создаём запись
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "user_id": user_id,
                    "username": username or "anonymous",
                    "question": question,
                    "answer_found": answer_found,
                    "response_length": response_length,
                    "lang": lang or "unknown",  # Язык запроса
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "time": datetime.now().strftime("%H:%M:%S")
                }
                
                # Добавляем в файл (JSON Lines - каждая строка = JSON объект)
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                
                self.questions_since_sync += 1
                
                # Проверяем нужна ли синхронизация
                self._check_and_sync()
                
            except Exception as e:
                print(f"⚠️  Ошибка логирования вопроса: {e}")
    
    def _check_and_sync(self):
        """Проверить и синхронизировать логи с Git"""
        current_time = time.time()
        time_since_sync = current_time - self.last_sync_time
        
        # Синхронизируем если:
        # 1. Накопилось достаточно вопросов, ИЛИ
        # 2. Прошёл час с последней синхронизации
        should_sync = (
            self.questions_since_sync >= self.sync_threshold or
            time_since_sync >= self.sync_interval
        )
        
        if should_sync:
            # Запускаем синхронизацию в отдельном потоке чтобы не блокировать бота
            threading.Thread(target=self._sync_to_git, daemon=True).start()
            self.questions_since_sync = 0
            self.last_sync_time = current_time
    
    def _sync_to_git(self):
        """Синхронизировать логи с Git"""
        try:
            print("🔄 Синхронизация логов с Git...")
            
            # Переходим в директорию проекта
            project_dir = self.log_dir.parent
            
            # Добавляем файл логов в Git
            subprocess.run(
                ['git', 'add', str(self.log_file.relative_to(project_dir))],
                cwd=project_dir,
                capture_output=True,
                timeout=10
            )
            
            # Коммитим
            commit_msg = f"📊 Auto-sync: Telegram questions log ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
            result = subprocess.run(
                ['git', 'commit', '-m', commit_msg],
                cwd=project_dir,
                capture_output=True,
                timeout=10
            )
            
            # Если есть изменения - пушим
            if result.returncode == 0:
                subprocess.run(
                    ['git', 'push'],
                    cwd=project_dir,
                    capture_output=True,
                    timeout=30
                )
                print("✅ Логи синхронизированы с Git")
            else:
                # Нет изменений или ошибка - это нормально
                pass
                
        except subprocess.TimeoutExpired:
            print("⚠️  Таймаут синхронизации Git (пропускаем)")
        except Exception as e:
            print(f"⚠️  Ошибка синхронизации с Git: {e}")
    
    def get_stats(self) -> dict:
        """Получить статистику по логам"""
        try:
            if not self.log_file.exists():
                return {"total_questions": 0}
            
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            total = len(lines)
            answered = sum(1 for line in lines if json.loads(line).get('answer_found', False))
            
            # Уникальные пользователи
            users = set()
            for line in lines:
                entry = json.loads(line)
                users.add(entry.get('user_id'))
            
            return {
                "total_questions": total,
                "answered": answered,
                "not_answered": total - answered,
                "unique_users": len(users)
            }
        except Exception as e:
            print(f"⚠️  Ошибка получения статистики: {e}")
            return {"error": str(e)}


# Глобальный экземпляр логгера (будет создан при импорте)
_logger_instance = None


def get_logger(log_dir: str = None):
    """Получить глобальный экземпляр логгера"""
    global _logger_instance
    if _logger_instance is None and log_dir:
        _logger_instance = QuestionLogger(log_dir)
    return _logger_instance

