"""Работа с базой данных."""

import os
import sqlite3
import time
from datetime import datetime


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
                isolation_level=None,
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
            
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                is_premium INTEGER DEFAULT 0,
                searches_today INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS user_filters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE NOT NULL,
                brand TEXT,
                model TEXT,
                engine_volume REAL,
                year_from INTEGER,
                year_to INTEGER,
                price_from REAL,
                price_to REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    
    # ============ CARS ============
    
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
                        is_new, condition, color, city, posted_date,
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
                return
            except sqlite3.OperationalError:
                time.sleep(0.3 * (attempt + 1))
    
    def get_active_cars(self, days: int = 14) -> list[dict]:
        cursor = self.conn.execute(
            "SELECT * FROM cars WHERE is_active = 1 AND posted_date >= datetime('now', ?)",
            (f"-{days} days",)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def search_active_cars(self, brand: str = None, model: str = None,
                           hours: int = 24) -> list[dict]:
        """Поиск активных машин по марке и модели."""
        query = """SELECT * FROM cars WHERE is_active = 1 
                   AND scraped_at >= datetime('now', ?)"""
        params = [f"-{hours} hours"]
        
        if brand:
            query += " AND LOWER(brand) LIKE LOWER(?)"
            params.append(f"%{brand}%")
        if model:
            query += " AND LOWER(model) LIKE LOWER(?)"
            params.append(f"%{model}%")
        
        query += " ORDER BY price ASC"
        
        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def deactivate_old_cars(self, days: int = 14) -> int:
        cursor = self.conn.execute(
            "UPDATE cars SET is_active = 0 WHERE posted_date < datetime('now', ?)",
            (f"-{days} days",)
        )
        return cursor.rowcount
    
    # ============ MARKET PRICES ============
    
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
    
    def get_market_price(self, brand: str, model: str, year: int,
                         engine_volume: float, fuel_type: str) -> dict | None:
        """Последняя рыночная цена для модели."""
        cursor = self.conn.execute(
            """SELECT * FROM market_prices
               WHERE brand=? AND model=? AND year=?
               AND engine_volume=? AND fuel_type=?
               ORDER BY calculated_at DESC LIMIT 1""",
            (brand, model, year, engine_volume, fuel_type)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # ============ USERS ============
    
    def get_or_create_user(self, telegram_id: str, username: str = None,
                           first_name: str = None) -> dict:
        """Создаёт пользователя если его нет."""
        self.conn.execute(
            """INSERT OR IGNORE INTO users (telegram_id, username, first_name)
               VALUES (?, ?, ?)""",
            (telegram_id, username, first_name)
        )
        cursor = self.conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        return dict(cursor.fetchone())
    
    # ============ USER FILTERS ============
    
    def save_filter(self, telegram_id: str, brand: str = None, model: str = None,
                    engine_volume: float = None, year_from: int = None,
                    year_to: int = None, price_from: float = None,
                    price_to: float = None) -> None:
        """Сохраняет или обновляет фильтр пользователя."""
        self.conn.execute(
            """INSERT OR REPLACE INTO user_filters
               (telegram_id, brand, model, engine_volume, year_from, year_to,
                price_from, price_to, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (telegram_id, brand, model, engine_volume, year_from, year_to,
             price_from, price_to, datetime.now().isoformat())
        )
    
    def get_filter(self, telegram_id: str) -> dict | None:
        """Получает фильтр пользователя."""
        cursor = self.conn.execute(
            "SELECT * FROM user_filters WHERE telegram_id = ?", (telegram_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def delete_filter(self, telegram_id: str) -> bool:
        """Удаляет фильтр пользователя."""
        cursor = self.conn.execute(
            "DELETE FROM user_filters WHERE telegram_id = ?", (telegram_id,)
        )
        return cursor.rowcount > 0
    
    def get_matching_filters(self, brand: str, model: str, year: int,
                              engine_volume: float, price: float) -> list[dict]:
        """Находит все фильтры подходящие под машину."""
        cursor = self.conn.execute(
            """SELECT * FROM user_filters
               WHERE (brand IS NULL OR LOWER(brand) = LOWER(?))
               AND (model IS NULL OR LOWER(model) = LOWER(?))
               AND (year_from IS NULL OR ? >= year_from)
               AND (year_to IS NULL OR ? <= year_to)
               AND (engine_volume IS NULL OR engine_volume = ?)
               AND (price_from IS NULL OR ? >= price_from)
               AND (price_to IS NULL OR ? <= price_to)""",
            (brand, model, year, year, engine_volume, price, price)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        if self._conn:
            self._conn.close()