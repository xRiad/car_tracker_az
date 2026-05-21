"""Обработчики команд бота."""

from telegram import Update
from telegram.ext import ContextTypes
from car_tracker.db import Database

db = Database()

# Алиасы ключей (транслит)
ALIASES = {
    "marka": "marka", "m": "marka",
    "model": "model", "mod": "model",
    "il": "il", "y": "il", "year": "il",
    "muherrik": "muherrik", "eng": "muherrik", "muh": "muherrik",
    "qiymet": "qiymet", "q": "qiymet", "p": "qiymet", "price": "qiymet",
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие."""
    user = update.effective_user
    db.get_or_create_user(
        telegram_id=str(user.id),
        username=user.username,
        first_name=user.first_name,
    )
    
    await update.message.reply_text(
        f"👋 Salam, {user.first_name}!\n\n"
        "Mən Turbo.az-da bazar qiymətindən ucuz maşınları tapıb sənə xəbər verirəm.\n\n"
        "📌 *Komandalar:*\n"
        "/filter — filtr yarat və bildiriş al\n"
        "/myfilter — filtrinə bax\n"
        "/stopfilter — filtri sil\n\n"
        "*Nümunə:* `/filter marka:bmw model:x5 il:2019-2025 qiymet:0-50000 muherrik:2.0`\n\n"
        "*Açarlar:* `marka:`, `model:`, `il:`, `muherrik:`, `qiymet:`\n"
        "Hamısı könüllüdür — istədiyini seç.",
        parse_mode="Markdown",
    )


async def set_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка фильтра: /filter marka:bmw model:x5 il:2019-2025 qiymet:0-50000 muherrik:2.0"""
    args = " ".join(context.args) if context.args else ""
    
    if not args.strip():
        await update.message.reply_text(
            "❌ *Format:* `/filter açar:dəyər açar:dəyər ...`\n\n"
            "*Açarlar:*\n"
            "`marka:` — Marka (bmw, mercedes, toyota...)\n"
            "`model:` — Model (x5, e200, camry...)\n"
            "`il:` — İl aralığı (2019-2025) və ya tək il (2020)\n"
            "`muherrik:` — Mühərrik həcmi, L (2.0, 1.5...)\n"
            "`qiymet:` — Qiymət aralığı (8000-50000, 0-30000, 10000-)\n\n"
            "*Nümunələr:*\n"
            "`/filter marka:bmw model:x5 il:2019-2025 qiymet:0-50000 muherrik:2.0`\n"
            "`/filter il:2014-2026 muherrik:2.0 qiymet:8000-50000`\n"
            "`/filter marka:toyota qiymet:0-30000`\n"
            "`/filter muherrik:1.5`",
            parse_mode="Markdown",
        )
        return
    
    # Значения по умолчанию: всё открыто
    params = {
        "marka": None, "model": None,
        "il_from": None, "il_to": None,
        "muherrik": None,
        "qiymet_from": None, "qiymet_to": None,
    }
    
    parts = args.split()
    for part in parts:
        if ":" not in part:
            continue
        
        key, value = part.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        
        # Применяем алиас
        key = ALIASES.get(key, key)
        
        if key == "marka":
            params["marka"] = None if value == "-" else value
        elif key == "model":
            params["model"] = None if value == "-" else value
        elif key == "il":
            if value == "-":
                params["il_from"] = None
                params["il_to"] = None
            elif "-" in value:
                y_from, y_to = value.split("-", 1)
                params["il_from"] = int(y_from) if y_from else None
                params["il_to"] = int(y_to) if y_to else None
            else:
                params["il_from"] = int(value)
                params["il_to"] = int(value)
        elif key == "muherrik":
            params["muherrik"] = None if value == "-" else (float(value) if value else None)
        elif key == "qiymet":
            if value == "-":
                params["qiymet_from"] = None
                params["qiymet_to"] = None
            elif "-" in value:
                p_from, p_to = value.split("-", 1)
                params["qiymet_from"] = float(p_from) if p_from else None
                params["qiymet_to"] = float(p_to) if p_to else None
            else:
                # Одно число = "до этой цены"
                params["qiymet_from"] = 0
                params["qiymet_to"] = float(value)
    
    if not any(params.values()):
        await update.message.reply_text("❌ Heç bir filtr seçilməyib.")
        return
    
    telegram_id = str(update.effective_user.id)
    db.save_filter(
        telegram_id,
        brand=params["marka"],
        model=params["model"],
        engine_volume=params["muherrik"],
        year_from=params["il_from"],
        year_to=params["il_to"],
        price_from=params["qiymet_from"],
        price_to=params["qiymet_to"],
    )
    
    # Формируем ответ
    hisseler = []
    if params["marka"]: hisseler.append(f"🚗 *Marka:* {params['marka']}")
    if params["model"]: hisseler.append(f"*Model:* {params['model']}")
    if params["muherrik"]: hisseler.append(f"*Mühərrik:* {params['muherrik']}L")
    if params["il_from"] or params["il_to"]:
        hisseler.append(f"*İl:* {params['il_from'] or '1900'}–{params['il_to'] or '2026'}")
    else:
        hisseler.append(f"*İl:* hamısı")
    if params["qiymet_from"] or params["qiymet_to"]:
        hisseler.append(f"*Qiymət:* {params['qiymet_from'] or '0'}–{params['qiymet_to'] or '∞'} AZN")
    else:
        hisseler.append(f"*Qiymət:* limitsiz")
    
    await update.message.reply_text(
        "✅ *Filtr saxlanıldı!*\n\n" + "\n".join(hisseler) +
        "\n\n🔔 Sərfəli maşın çıxan kimi xəbər verəcəm.",
        parse_mode="Markdown",
    )


async def my_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает текущий фильтр."""
    telegram_id = str(update.effective_user.id)
    f = db.get_filter(telegram_id)
    
    if not f:
        await update.message.reply_text(
            "❌ *Aktiv filtriniz yoxdur.*\n\n"
            "Yarat: `/filter marka:bmw model:x5 il:2019-2025 qiymet:0-50000`",
            parse_mode="Markdown",
        )
        return
    
    hisseler = []
    if f.get("brand"): hisseler.append(f"🚗 *Marka:* {f['brand']}")
    if f.get("model"): hisseler.append(f"*Model:* {f['model']}")
    if f.get("engine_volume"): hisseler.append(f"*Mühərrik:* {f['engine_volume']}L")
    if f.get("year_from") or f.get("year_to"):
        hisseler.append(f"*İl:* {f.get('year_from') or '1900'}–{f.get('year_to') or '2026'}")
    else:
        hisseler.append(f"*İl:* hamısı")
    if f.get("price_from") or f.get("price_to"):
        hisseler.append(f"*Qiymət:* {f.get('price_from') or '0'}–{f.get('price_to') or '∞'} AZN")
    else:
        hisseler.append(f"*Qiymət:* limitsiz")
    
    await update.message.reply_text(
        "📋 *Filtriniz:*\n\n" + "\n".join(hisseler) +
        "\n\nℹ️ Silmək üçün: /stopfilter",
        parse_mode="Markdown",
    )


async def stop_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет фильтр."""
    telegram_id = str(update.effective_user.id)
    deleted = db.delete_filter(telegram_id)
    
    if deleted:
        await update.message.reply_text("🔕 *Filtr silindi.* Bildirişlər dayandırıldı.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Aktiv filtriniz yoxdur.")