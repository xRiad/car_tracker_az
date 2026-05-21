# bot/checker.py
"""Проверка новых машин и отправка уведомлений."""

from datetime import datetime
from telegram.ext import ContextTypes
from car_tracker.db import Database
from bot.card import format_car_card

db = Database()

last_check = datetime.now()


async def check_new_deals(context: ContextTypes.DEFAULT_TYPE):
    """Проверяет новые машины и отправляет уведомления подписчикам."""
    global last_check
    
    now = datetime.now()
    minutes_ago = int((now - last_check).total_seconds() / 60) + 1
    last_check = now
    
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
        
        median = market["median_price"]
        if median == 0:
            continue
        
        discount = (median - car["price"]) / median * 100
        
        for f in filters:
            min_disc = f.get("min_discount", 10)
            if discount < min_disc:
                continue
            try:
                text, keyboard = format_car_card(car, market, discount)
                
                # Отправляем фото с подписью
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
                print(f"📤 Bildiriş göndərildi: {f['telegram_id']} → {car['brand']} {car['model']}")
            except Exception as e:
                print(f"❌ Göndərmə xətası {f['telegram_id']}: {e}")