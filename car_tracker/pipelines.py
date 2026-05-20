"""Pipeline для сохранения машин в базу данных."""

from .db import Database

class CarTrackerPipeline:
    """Сохраняет Item в SQLite и проверяет дубликаты."""
    
    def __init__(self):
        
        self.db = None
    
    def open_spider(self, spider):
        """Открываем соединение с БД при старте паука."""
        self.db = Database()
        spider.logger.info(f"DB IN USE: {self.db.conn}")
    
    def process_item(self, item, spider):
        """Сохраняем машину если её ещё нет."""
        external_id = item.get("external_id")
        
        if not external_id:
            spider.logger.error("❌ Нет external_id, пропускаем")
            return item
        
        # Пропускаем дубликаты
        if self.db.car_exists(external_id):
            spider.logger.debug(f"⏭️ Пропущен дубликат: {external_id}")
            return item
        
        # Сохраняем
        car_data = dict(item)
        try:
            self.db.save_car(car_data)
            spider.logger.info("💾 SAVED TO DB OK")
        except Exception as e:
            spider.logger.error(f"DB SAVE ERROR: {e}")
        
        spider.logger.info(
            f"💾 Сохранено: {item.get('brand')} {item.get('model')} "
            f"({item.get('year')}) — {item.get('price')} AZN"
        )
        
        return item
    
    def close_spider(self, spider):
        """Закрываем соединение с БД."""
        if self.db:
            self.db.close()