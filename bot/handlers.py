"""Обработчики команд бота."""

from telegram import Update
from telegram.ext import ContextTypes
from car_tracker.db import Database

db = Database()

ALIASES = {
    "marka": "marka", "m": "marka",
    "model": "model", "mod": "model",
    "il": "il", "y": "il", "year": "il",
    "muherrik": "muherrik", "eng": "muherrik", "muh": "muherrik",
    "qiymet": "qiymet", "q": "qiymet", "p": "qiymet", "price": "qiymet",
    "endirim": "endirim", "end": "endirim",
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие + авто-подписка на все выгодные машины."""
    if not update.message:
        return

    user = update.effective_user
    db.get_or_create_user(
        telegram_id=str(user.id),
        username=user.username,
        first_name=user.first_name,
    )

    existing = db.get_filter(str(user.id))
    if not existing:
        db.save_filter(
            telegram_id=str(user.id),
            brand=None, model=None,
            engine_volume=None,
            year_from=None, year_to=None,
            price_from=None, price_to=None,
            min_discount=5,
        )

    await update.message.reply_text(
        f"👋 Salam, {user.first_name}!\n\n"
        "Mən Turbo.az-da bazar qiymətindən ucuz maşınları tapıb sənə xəbər verirəm.\n\n"
        "🔔 *Siz artıq bütün sərfəli maşınlara abunə oldunuz!*\n"
        "Heç bir filtr yoxdur — bazardan ucuz olan bütün maşınlar sizə gələcək.\n\n"
        "📌 *Komandalar:*\n"
        "/filter — filtr əlavə et (marka, model, il, qiymət, endirim)\n"
        "/myfilter — filtrinizə bax\n"
        "/stopfilter — filtri sil\n\n"
        "*Açarlar:* `marka:`, `model:`, `il:`, `muherrik:`, `qiymet:`, `endirim:`\n"
        "Hamısı könüllüdür — istədiyini seç.\n\n"
        "*Nümunə:* `/filter marka:bmw model:x5 il:2019-2025 qiymet:0-50000 endirim:10`",
        parse_mode="Markdown",
    )


async def set_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка фильтра: /filter marka:bmw model:x5 il:2019-2025 qiymet:0-50000 endirim:10"""
    args = " ".join(context.args) if context.args else ""

    if not args.strip():
        await update.message.reply_text(
            "❌ *Format:* `/filter açar:dəyər açar:dəyər ...`\n\n"
            "*Açarlar:*\n"
            "`marka:` — Marka (bmw, mercedes, toyota...)\n"
            "`model:` — Model (x5, e200, camry...)\n"
            "`il:` — İl aralığı (2019-2025) və ya tək il (2020)\n"
            "`muherrik:` — Mühərrik həcmi, L (2.0, 1.5...)\n"
            "`qiymet:` — Qiymət aralığı (8000-50000, 0-30000, 10000-)\n"
            "`endirim:` — Min. endirim faizi (5, 10, 15...)\n\n"
            "*Nümunələr:*\n"
            "`/filter marka:bmw model:x5 il:2019-2025 qiymet:0-50000 endirim:10`\n"
            "`/filter il:2014-2026 muherrik:2.0 qiymet:8000-50000 endirim:15`\n"
            "`/filter marka:toyota qiymet:0-30000`\n"
            "`/filter endirim:20`",
            parse_mode="Markdown",
        )
        return

    params = {
        "marka": None, "model": None,
        "il_from": None, "il_to": None,
        "muherrik": None,
        "qiymet_from": None, "qiymet_to": None,
        "min_discount": 10,
    }

    parts = args.split()
    for part in parts:
        if ":" not in part:
            continue

        key, value = part.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
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
                params["qiymet_from"] = 0
                params["qiymet_to"] = float(value)
        elif key == "endirim":
            params["min_discount"] = int(value)

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
        min_discount=params.get("min_discount", 5),
    )

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
    hisseler.append(f"*Min. endirim:* {params.get('min_discount', 5)}%")

    await update.message.reply_text(
        "✅ *Filtr saxlanıldı!*\n\n" + "\n".join(hisseler) +
        "\n\n🔔 Sərfəli maşın çıxan kimi xəbər verəcəm.",
        parse_mode="Markdown",
    )


async def my_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает текущий фильтр."""
    if not update.message:
        return

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
    if f.get("min_discount"):
        hisseler.append(f"*Min. endirim:* {f['min_discount']}%")

    await update.message.reply_text(
        "📋 *Filtriniz:*\n\n" + "\n".join(hisseler) +
        "\n\nℹ️ Silmək üçün: /stopfilter",
        parse_mode="Markdown",
    )


async def stop_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбрасывает фильтр к дефолту (все машины, от 5%)."""
    if not update.message:
        return

    telegram_id = str(update.effective_user.id)
    
    # Сбрасываем на дефолтный фильтр (всё, от 5%)
    db.save_filter(
        telegram_id=telegram_id,
        brand=None, model=None,
        engine_volume=None,
        year_from=None, year_to=None,
        price_from=None, price_to=None,
        min_discount=10,
    )

    await update.message.reply_text(
        "🔄 *Filtr sıfırlandı.*\n"
        "Yenidən bütün sərfəli maşınlar (min. 10% endirim) sizə gələcək.",
        parse_mode="Markdown",
    )