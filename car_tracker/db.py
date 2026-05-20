"""Работа с базой данных."""

import os
import sqlite3
import time
from datetime import datetime


print("DB PATH:", os.path.abspath("cars.db"))
class Database:
    """Обёртка для SQLite / PostgreSQL."""
    
    def __init__(self, db_type: str = "sqlite", connection_string: str = ""):
        self.db_type = db_type
        self.connection_string = connection_string or "cars.db"
        self._conn = None
        self._connect()
    
    def _connect(self):
        """Создаём соединение с базой."""
        if self.db_type == "sqlite":
            self._conn = sqlite3.connect(
                self.connection_string,
                timeout=30,
                check_same_thread=False,
                isolation_level=None,  # Автокоммит включен
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._create_tables()
        else:
            raise NotImplementedError("PostgreSQL пока не настроен")
    
    @property
    def conn(self):
        try:
            self._conn.execute("SELECT 1")
        except (sqlite3.ProgrammingError, sqlite3.OperationalError, AttributeError):
            self._connect()
        return self._conn
    
    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                url TEXT NOT NULL,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                year INTEGER NOT NULL,
                price REAL NOT NULL,
                currency TEXT DEFAULT 'AZN',
                engine_volume REAL,
                engine_power INTEGER,
                fuel_type TEXT,
                mileage INTEGER,
                body_type TEXT,
                gearbox TEXT,
                transmission TEXT,
                is_new INTEGER DEFAULT 0,
                condition TEXT,
                color TEXT,
                city TEXT,
                posted_date TIMESTAMP,
                main_photo_url TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_cars_external_id ON cars(external_id);
            CREATE INDEX IF NOT EXISTS idx_cars_brand_model ON cars(brand, model, year);
            CREATE INDEX IF NOT EXISTS idx_cars_posted_date ON cars(posted_date);
            CREATE TABLE IF NOT EXISTS market_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                year INTEGER NOT NULL,
                engine_volume REAL NOT NULL,
                fuel_type TEXT NOT NULL,
                avg_price REAL NOT NULL,
                median_price REAL NOT NULL,
                min_price REAL NOT NULL,
                max_price REAL NOT NULL,
                total_listings INTEGER NOT NULL,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(brand, model, year, engine_volume, fuel_type, calculated_at)
            );
        """)
        # Без commit() — isolation_level=None делает автокоммит
    
    def car_exists(self, external_id: str) -> bool:
        for _ in range(3):
            try:
                cursor = self.conn.execute(
                    "SELECT 1 FROM cars WHERE external_id = ?", (external_id,)
                )
                return cursor.fetchone() is not None
            except sqlite3.OperationalError:
                time.sleep(0.3)
        return False
    
    def save_car(self, item: dict) -> None:
        for attempt in range(3):
            try:
                self.conn.execute("""
                    INSERT OR IGNORE INTO cars (
                        external_id, source, url,
                        brand, model, year, price, currency,
                        engine_volume, engine_power, fuel_type,
                        mileage, body_type, gearbox, transmission,
                        is_new, condition,color, city, posted_date,
                        main_photo_url, scraped_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item["external_id"], item["source"], item["url"],
                    item["brand"], item["model"], item["year"],
                    item["price"], item.get("currency", "AZN"),
                    item.get("engine_volume"), item.get("engine_power"),
                    item.get("fuel_type"),
                    item.get("mileage"), item.get("body_type"),
                    item.get("gearbox"), item.get("transmission"),
                    1 if item.get("is_new") else 0,
                    item.get("condition"), item.get("color"),
                    item.get("city"),
                    item.get("posted_date"),
                    item.get("main_photo_url"),
                    item.get("scraped_at", datetime.now().isoformat())
                ))
                return  # Успешно — выходим
            except sqlite3.OperationalError:
                time.sleep(0.3 * (attempt + 1))
    
    def get_active_cars(self, days: int = 14) -> list[dict]:
        cursor = self.conn.execute(
            "SELECT * FROM cars WHERE is_active = 1 AND posted_date >= datetime('now', ?)",
            (f"-{days} days",)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def deactivate_old_cars(self, days: int = 14) -> int:
        cursor = self.conn.execute(
            "UPDATE cars SET is_active = 0 WHERE posted_date < datetime('now', ?)",
            (f"-{days} days",)
        )
        return cursor.rowcount
    
    def save_market_price(self, brand, model, year, engine_volume, fuel_type,
                          avg_price, median_price, min_price, max_price, total_listings):
        self.conn.execute("""
            INSERT OR REPLACE INTO market_prices (
                brand, model, year, engine_volume, fuel_type,
                avg_price, median_price, min_price, max_price,
                total_listings, calculated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            brand, model, year, engine_volume, fuel_type,
            avg_price, median_price, min_price, max_price,
            total_listings, datetime.now().isoformat()
        ))
    
    def close(self):
        if self._conn:
            self._conn.close()