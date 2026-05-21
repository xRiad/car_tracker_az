# bot/card.py
"""Форматирование карточки машины для отправки в Telegram."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def format_car_card(car: dict, market: dict, discount: float) -> tuple[str, InlineKeyboardMarkup]:
    """Создаёт текст и кнопку для карточки машины."""
    
    # Эмодзи в зависимости от выгодности
    if discount >= 15:
        emoji = "🔥🔥🔥 ÇOX SƏRFƏLİ!"
    elif discount >= 10:
        emoji = "🔥 SƏRFƏLİ!"
    elif discount >= 5:
        emoji = "👍 Ucuz"
    else:
        emoji = "📊 Bazar qiyməti"
    
    text = (
        f"{emoji}\n\n"
        f"🚗 *{car['brand']} {car['model']}* ({car['year']})\n\n"
        f"💸 *Qiymət:* {car['price']:,.0f} AZN\n"
        f"📊 *Bazar qiyməti:* {market['median_price']:,.0f} AZN\n"
        f"📉 *Fərq:* {discount:.1f}% bazardan ucuz\n"
    )
    
    if car.get("engine_volume"):
        text += f"🔧 *Mühərrik:* {car['engine_volume']}L"
        if car.get("fuel_type"):
            text += f" / {car['fuel_type']}"
        text += "\n"
    
    if car.get("mileage"):
        text += f"🛣 *Yürüş:* {car['mileage']:,} km\n".replace(",", " ")
    
    if car.get("city"):
        text += f"📍 *Şəhər:* {car['city']}\n"
    
    if car.get("gearbox"):
        text += f"⚙️ *Sürətlər qutusu:* {car['gearbox']}\n"
    
    if car.get("condition"):
        text += f"✅ *Vəziyyət:* {car['condition']}\n"
    
    # Кнопка для открытия на Turbo.az
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Turbo.az-da bax", url=car['url'])]
    ])
    
    return text, keyboard