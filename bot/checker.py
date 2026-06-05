# bot/checker.py
"""Проверка новых машин, напоминаний об истечении, и отправка уведомлений."""

from datetime import datetime
from telegram.ext import ContextTypes
from car_tracker.db import Database
from bot.card import format_car_card
from bot.config import FREQUENCY_DISCOUNT, FREQUENCY_DAYS
from bot.logger import NotificationLogger

db = Database()
log = NotificationLogger()

last_check = datetime.now()


def get_min_discount_for_model(brand: str, model: str, year: int,
                                engine_volume: float, fuel_type: str) -> int:
    """Возвращает минимальный порог скидки на основе частоты модели."""
    freq = db.get_daily_frequency(brand, model, year, engine_volume, fuel_type)
    
    for threshold, discount in FREQUENCY_DISCOUNT:
        if freq >= threshold:
            return discount
    
    return FREQUENCY_DISCOUNT[-1][1]


async def check_new_deals(context: ContextTypes.DEFAULT_TYPE):
    """Проверяет новые машины и отправляет уведомления подписчикам."""
    global last_check
    
    now = datetime.now()
    minutes_ago = int((now - last_check).total_seconds() / 60) + 1
    last_check = now

    # ========== Напоминания об истечении доступа ==========
    expiring = db.get_expiring_users(days=3)
    for user in expiring:
        expiry_key = "EXPIRY_" + (user.get("expires_at") or "")
        if db.is_already_sent(user["telegram_id"], expiry_key):
            continue
        try:
            expires = datetime.fromisoformat(user["expires_at"]) if user.get("expires_at") else None
            days_left = (expires - now).days if expires else 0
            await context.bot.send_message(
                chat_id=user["telegram_id"],
                text=(
                    "⚠️ *Diqqət!* Proqram müddətiniz bitmək üzrədir.\n"
                    f"Qalan gün: *{days_left}*\n"
                    "Müddəti uzatmaq üçün adminlə əlaqə saxlayın."
                ),
                parse_mode="Markdown",
            )
            db.mark_as_sent(user["telegram_id"], expiry_key)
        except Exception as e:
            print(f"❌ Xəbərdarlıq xətası {user['telegram_id']}: {e}")

    # ========== Поиск новых машин ==========
    new_cars = db.search_active_cars(hours=max(1, minutes_ago // 60 + 1))
    
    if not new_cars:
        print(f"🔍 Yoxlama: yeni maşın yoxdur")
        return
    
    print(f"🔍 Yoxlama: {len(new_cars)} maşın (son {minutes_ago} dəq)")
    
    for car in new_cars:
        if not car.get("brand") or not car.get("model"):
            continue
        
        filters = db.get_matching_filters(
            brand=car["brand"],
            model=car["model"],
            year=car["year"],
            engine_volume=car.get("engine_volume") or 0,
            price=car["price"],
            city=car.get("city", ""),
            mileage=car.get("mileage"),
        )
        
        if not filters:
            continue
        
        market = db.get_market_price(
            brand=car["brand"],
            model=car["model"],
            year=car["year"],
            engine_volume=car.get("engine_volume") or 0,
            fuel_type=car.get("fuel_type") or "",
        )
        
        if not market:
            continue
        
        if market.get("total_listings", 0) < 8:
            continue

        median = market["median_price"]
        if median == 0:
            continue
        
        discount = (median - car["price"]) / median * 100
        
        # Только динамический порог из конфига
        effective_min = get_min_discount_for_model(
            brand=car["brand"],
            model=car["model"],
            year=car["year"],
            engine_volume=car.get("engine_volume") or 0,
            fuel_type=car.get("fuel_type") or "",
        )
        
        if discount < effective_min:
            continue
        
        for f in filters:
            user = db.get_user_by_telegram(f["telegram_id"])
            if not user or not user.get("is_activated"):
                continue
            if user.get("expires_at"):
                expires = datetime.fromisoformat(user["expires_at"])
                if expires <= now:
                    continue
            
            if db.is_already_sent(f["telegram_id"], car["external_id"]):
                continue
            
            # Проверка на дубликат (перезалив объявления)
            if db.find_similar_car(
                brand=car["brand"],
                model=car["model"],
                year=car["year"],
                price=car["price"],
                city=car.get("city", ""),
                mileage=car.get("mileage"),
                engine_volume=car.get("engine_volume"),
                current_id=car["external_id"]
            ):
                print(f"🔄 Dublikat keçildi: {car['brand']} {car['model']} ({car['year']}) - {car['price']} AZN")
                continue
            
            try:
                text, keyboard = format_car_card(car, market, discount)
                
                if car.get("main_photo_url"):
                    await context.bot.send_photo(
                        chat_id=f["telegram_id"],
                        photo=car["main_photo_url"],
                        caption=text,
                        reply_markup=keyboard,
                        parse_mode="Markdown",
                    )
                else:
                    await context.bot.send_message(
                        chat_id=f["telegram_id"],
                        text=text,
                        reply_markup=keyboard,
                        parse_mode="Markdown",
                    )
                
                # Логируем отправку
                log.log_sent(f["telegram_id"], car, discount)
                
                print(f"📤 Bildiriş göndərildi: {f['telegram_id']} → {car['brand']} {car['model']}")
                db.mark_as_sent(f["telegram_id"], car["external_id"])
            except Exception as e:
                print(f"❌ Göndərmə xətası {f['telegram_id']}: {e}")