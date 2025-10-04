"""
Планировщик задач для автоматического обновления данных
"""

import threading
import time
import logging
from datetime import datetime
from stock_api import stock_api_service

logger = logging.getLogger(__name__)

class StockScheduler:
    """Планировщик для автоматического обновления акций"""
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """Запуск планировщика"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()
            logger.info("Планировщик запущен")
    
    def stop(self):
        """Остановка планировщика"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Планировщик остановлен")
    
    def _run_scheduler(self):
        """Основной цикл планировщика"""
        last_price_update = 0
        last_sync_update = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Обновляем цены каждые 5 минут
                if current_time - last_price_update > 300:  # 5 минут
                    logger.info("Запуск обновления цен...")
                    try:
                        stock_api_service.update_stock_prices()
                        last_price_update = current_time
                        logger.info("Цены обновлены успешно")
                    except Exception as e:
                        logger.error(f"Ошибка обновления цен: {e}")
                
                # Синхронизируем список акций каждые 6 часов
                if current_time - last_sync_update > 21600:  # 6 часов
                    logger.info("Запуск синхронизации акций и облигаций...")
                    try:
                        result = stock_api_service.sync_stocks_to_database()
                        if result['success']:
                            logger.info(f"Синхронизация завершена: добавлено {result['added']}, обновлено {result['updated']}")
                        # Синхронизация облигаций
                        bonds_result = stock_api_service.sync_bonds_to_database()
                        if bonds_result and bonds_result.get('success'):
                            logger.info(f"Синхронизация облигаций завершена: добавлено {bonds_result['added']}, обновлено {bonds_result['updated']}")
                        last_sync_update = current_time
                    except Exception as e:
                        logger.error(f"Ошибка синхронизации бумаг: {e}")
                
                # Спим 30 секунд перед следующей проверкой
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
                time.sleep(60)  # Спим минуту при ошибке

# Глобальный экземпляр планировщика
scheduler = StockScheduler()
