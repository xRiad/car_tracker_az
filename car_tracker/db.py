"""Работа с базой данных."""

import os
import sqlite3
import time
from datetime import datetime, timedelta


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
                telegram_id TEXT UNIQUE,
                phone TEXT,
                username TEXT,
                first_name TEXT,
                role TEXT DEFAULT 'user',
                is_activated INTEGER DEFAULT 0,
                activated_at TIMESTAMP,
                expires_at TIMESTAMP,
                activated_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS partners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE NOT NULL,
                activation_credits INTEGER DEFAULT 10,
                activated_count INTEGER DEFAULT 0,
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
                min_discount INTEGER DEFAULT 10,
                city TEXT,
                mileage_from INTEGER,
                mileage_to INTEGER DEFAULT 250000,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sent_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT NOT NULL,
                external_id TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(telegram_id, external_id)
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
    
    def find_similar_car(self, brand: str, model: str, year: int,
                         price: float, city: str, mileage: int = None,
                         engine_volume: float = None, current_id: str = None,
                         days: int = 3) -> bool:
        """Проверяет, была ли похожая машина за последние N дней."""
        query = """SELECT 1 FROM cars 
                   WHERE brand = ? 
                   AND model = ? 
                   AND year = ?
                   AND price = ?
                   AND city = ?
                   AND scraped_at >= datetime('now', ?)"""
        params = [brand, model, year, price, city, f"-{days} days"]
        
        if current_id:
            query += " AND external_id != ?"
            params.append(current_id)
        
        if mileage is not None:
            query += " AND mileage = ?"
            params.append(mileage)
        
        if engine_volume is not None:
            query += " AND engine_volume = ?"
            params.append(engine_volume)
        
        query += " LIMIT 1"
        
        cursor = self.conn.execute(query, params)
        return cursor.fetchone() is not None
    
    # ============ FREQUENCY ============
    
    def get_daily_frequency(self, brand: str, model: str, year: int,
                             engine_volume: float, fuel_type: str) -> float:
        """Среднее количество машин этой модели в день за последние 7 дней."""
        cursor = self.conn.execute(
            """SELECT COUNT(*) as cnt FROM cars 
               WHERE brand=? AND model=? AND year=?
               AND engine_volume=? AND fuel_type=?
               AND scraped_at >= datetime('now', '-7 days')""",
            (brand, model, year, engine_volume, fuel_type)
        )
        count = cursor.fetchone()["cnt"]
        return count / 7.0
    
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
        self.conn.execute(
            """INSERT OR IGNORE INTO users (telegram_id, username, first_name)
               VALUES (?, ?, ?)""",
            (telegram_id, username, first_name)
        )
        cursor = self.conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        return dict(cursor.fetchone())
    
    def get_user_by_phone(self, phone: str) -> dict | None:
        cursor = self.conn.execute("SELECT * FROM users WHERE phone = ?", (phone,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_user_by_telegram(self, telegram_id: str) -> dict | None:
        cursor = self.conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def link_telegram_to_phone(self, telegram_id: str, phone: str,
                                username: str = None, first_name: str = None):
        blank = self.conn.execute(
            "SELECT * FROM users WHERE phone=? AND telegram_id IS NULL", (phone,)
        ).fetchone()
        existing_tg = self.conn.execute(
            "SELECT * FROM users WHERE telegram_id=?", (telegram_id,)
        ).fetchone()
        
        if blank and existing_tg:
            if blank["is_activated"]:
                self.conn.execute(
                    "UPDATE users SET is_activated=1, activated_at=?, expires_at=?, activated_by=?, phone=?, username=?, first_name=? WHERE telegram_id=?",
                    (blank["activated_at"], blank["expires_at"], blank["activated_by"], phone, username, first_name, telegram_id)
                )
            else:
                self.conn.execute(
                    "UPDATE users SET phone=?, username=?, first_name=? WHERE telegram_id=?",
                    (phone, username, first_name, telegram_id)
                )
            self.conn.execute("DELETE FROM users WHERE id=?", (blank["id"],))
        elif blank:
            self.conn.execute(
                "UPDATE users SET telegram_id=?, username=?, first_name=? WHERE id=?",
                (telegram_id, username, first_name, blank["id"])
            )
        elif existing_tg:
            self.conn.execute(
                "UPDATE users SET phone=?, username=?, first_name=? WHERE telegram_id=?",
                (phone, username, first_name, telegram_id)
            )
        else:
            self.conn.execute(
                """INSERT INTO users (telegram_id, phone, username, first_name)
                VALUES (?, ?, ?, ?)""",
                (telegram_id, phone, username, first_name)
            )
    
    def activate_user(self, phone: str, days: int, activated_by: str) -> None:
        now = datetime.now()
        expires = now + timedelta(days=days)
        cursor = self.conn.execute(
            """UPDATE users SET is_activated=1, activated_at=?, expires_at=?, activated_by=?
               WHERE phone=?""",
            (now.isoformat(), expires.isoformat(), activated_by, phone)
        )
        if cursor.rowcount == 0:
            self.conn.execute(
                """INSERT INTO users (phone, is_activated, activated_at, expires_at, activated_by)
                   VALUES (?, 1, ?, ?, ?)""",
                (phone, now.isoformat(), expires.isoformat(), activated_by)
            )
    
    def get_expiring_users(self, days: int = 3) -> list[dict]:
        cursor = self.conn.execute(
            """SELECT * FROM users WHERE is_activated=1 
               AND expires_at BETWEEN datetime('now') AND datetime('now', ?)""",
            (f"+{days} days",)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    # ============ PARTNERS ============
    
    def get_partner(self, telegram_id: str) -> dict | None:
        cursor = self.conn.execute(
            "SELECT * FROM partners WHERE telegram_id=?", (telegram_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def decrement_credits(self, telegram_id: str) -> None:
        self.conn.execute(
            """UPDATE partners SET activation_credits=activation_credits-1, 
               activated_count=activated_count+1 WHERE telegram_id=?""",
            (telegram_id,)
        )
    
    # ============ USER FILTERS ============
    
    def save_filter(self, telegram_id: str, brand: str = None, model: str = None,
                    engine_volume: float = None, year_from: int = None,
                    year_to: int = None, price_from: float = None,
                    price_to: float = None, min_discount: int = 10,
                    city: str = None, mileage_from: int = None,
                    mileage_to: int = 250000) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO user_filters
            (telegram_id, brand, model, engine_volume, year_from, year_to,
                price_from, price_to, min_discount, city, mileage_from, mileage_to, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (telegram_id, brand, model, engine_volume, year_from, year_to,
            price_from, price_to, min_discount, city, mileage_from, mileage_to,
            datetime.now().isoformat())
        )
    
    def get_filter(self, telegram_id: str) -> dict | None:
        cursor = self.conn.execute(
            "SELECT * FROM user_filters WHERE telegram_id = ?", (telegram_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def delete_filter(self, telegram_id: str) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM user_filters WHERE telegram_id = ?", (telegram_id,)
        )
        return cursor.rowcount > 0
    
    def get_matching_filters(self, brand: str, model: str, year: int,
                              engine_volume: float, price: float,
                              city: str = None, mileage: int = None) -> list[dict]:
        query = """SELECT * FROM user_filters
               WHERE (brand IS NULL OR LOWER(brand) = LOWER(?))
               AND (model IS NULL OR LOWER(model) = LOWER(?))
               AND (year_from IS NULL OR ? >= year_from)
               AND (year_to IS NULL OR ? <= year_to)
               AND (engine_volume IS NULL OR engine_volume = ?)
               AND (price_from IS NULL OR ? >= price_from)
               AND (price_to IS NULL OR ? <= price_to)"""
        params = [brand, model, year, year, engine_volume, price, price]
        
        if city:
            query += " AND (city IS NULL OR LOWER(city) LIKE '%' || LOWER(?) || '%')"
            params.append(city)
        
        if mileage is not None:
            query += " AND (mileage_from IS NULL OR ? >= mileage_from)"
            params.append(mileage)
            query += " AND (mileage_to IS NULL OR ? <= mileage_to)"
            params.append(mileage)
        
        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ============ SENT NOTIFICATIONS ============
    
    def is_already_sent(self, telegram_id: str, external_id: str) -> bool:
        cursor = self.conn.execute(
            "SELECT 1 FROM sent_notifications WHERE telegram_id = ? AND external_id = ?",
            (telegram_id, external_id)
        )
        return cursor.fetchone() is not None

    def mark_as_sent(self, telegram_id: str, external_id: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO sent_notifications (telegram_id, external_id) VALUES (?, ?)",
            (telegram_id, external_id)
        )

    def close(self):
        if self._conn:
            self._conn.close()