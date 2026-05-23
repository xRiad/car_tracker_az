"""Обработчики команд бота — версия с кнопками и fuzzy поиском."""

import re
from datetime import datetime
from difflib import SequenceMatcher

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from car_tracker.db import Database

db = Database()

CURRENT_YEAR = datetime.now().year

CITIES = [
    "Ağcabədi", "Ağdam", "Ağdaş", "Ağstafa", "Ağsu", "Astara", "Babək",
    "Bakı", "Balakən", "Beyləqan", "Bərdə", "Biləsuvar", "Cəbrayıl",
    "Cəlilabad", "Culfa", "Daşkəsən", "Dəliməmmədli", "Füzuli", "Gədəbəy",
    "Gəncə", "Goranboy", "Göyçay", "Göygöl", "Hacıqabul", "Horadiz",
    "İmişli", "İsmayıllı", "Kürdəmir", "Laçın", "Lerik", "Lənkəran",
    "Masallı", "Mingəçevir", "Naftalan", "Naxçıvan", "Neftçala", "Oğuz",
    "Ordubad", "Qax", "Qazax", "Qəbələ", "Qobustan", "Quba", "Qusar",
    "Saatlı", "Sabirabad", "Şabran", "Salyan", "Şamaxı", "Samux", "Şəki",
    "Şəmkir", "Şirvan", "Siyəzən", "Sumqayıt", "Şuşa", "Tərtər", "Tovuz",
    "Ucar", "Xaçmaz", "Xankəndi", "Xırdalan", "Xızı", "Xocavənd", "Xudat",
    "Yardımlı", "Yevlax", "Zaqatala", "Zəngilan", "Zərdab"
]

MAIN_KEYBOARD = ReplyKeyboardMarkup([
    ["🔍 Axtar", "⚙️ Filtrlər"],
    ["📋 Filtrim"]
], resize_keyboard=True)

FILTER_KEYBOARD = ReplyKeyboardMarkup([
    ["📉 Endirim faizi", "📍 Şəhər", "💸 Qiymət"],
    ["🔄 Sıfırla", "🔙 Geri"]
], resize_keyboard=True)

DISCOUNT_KEYBOARD = ReplyKeyboardMarkup([
    ["14%", "20%"],
    ["🔙 Geri"]
], resize_keyboard=True)

PRICE_KEYBOARD = ReplyKeyboardMarkup([
    ["💰 Qiymətsiz", "🔙 Geri"]
], resize_keyboard=True)


def fuzzy_match(query: str, text: str) -> float:
    return SequenceMatcher(None, query.lower(), text.lower()).ratio()


def parse_search_query(text: str) -> dict:
    result = {"brand": None, "model": None, "year_from": None, "year_to": None}
    words = text.strip().split()
    if not words:
        return result

    year_pattern = re.compile(r"\b(19[4-9]\d|20[0-2]\d)\b")
    for i in range(len(words) - 1, -1, -1):
        match = year_pattern.search(words[i])
        if match:
            year = int(match.group())
            if 1940 <= year <= CURRENT_YEAR:
                result["year_from"] = year
                result["year_to"] = CURRENT_YEAR
                words.pop(i)
                break

    if not words:
        return result

    popular_brands = [row["brand"] for row in db.conn.execute(
        "SELECT DISTINCT brand FROM cars WHERE is_active=1"
    ).fetchall()]

    best_brand = None
    best_brand_score = 0
    for brand in popular_brands:
        score = fuzzy_match(words[0], brand)
        if score > best_brand_score:
            best_brand_score = score
            best_brand = brand

    if best_brand and best_brand_score > 0.5:
        result["brand"] = best_brand
        words.pop(0)
        if words:
            models = [row["model"] for row in db.conn.execute(
                "SELECT DISTINCT model FROM cars WHERE is_active=1 AND brand=?",
                (best_brand,)
            ).fetchall()]
            model_text = " ".join(words)
            best_model = None
            best_model_score = 0
            for model in models:
                score = fuzzy_match(model_text, model)
                if score > best_model_score:
                    best_model_score = score
                    best_model = model
            if best_model and best_model_score > 0.35:
                result["model"] = best_model
    else:
        if words:
            result["brand"] = words[0]
            if len(words) > 1:
                result["model"] = " ".join(words[1:])

    return result


def find_city(text: str) -> str | None:
    best_city = None
    best_score = 0
    for city in CITIES:
        score = fuzzy_match(text, city)
        if score > best_score:
            best_score = score
            best_city = city
    if best_city and best_score > 0.45:
        return best_city
    return None


def format_filter_text(f: dict) -> str:
    lines = []
    if f.get("brand") and f.get("model"):
        lines.append(f"🚗 *{f['brand']} {f['model']}*")
    elif f.get("brand"):
        lines.append(f"🚗 *{f['brand']}*")
    else:
        lines.append("🚗 *Bütün maşınlar*")

    year_from = f.get("year_from")
    year_to = f.get("year_to")
    if year_from or year_to:
        lines.append(f"📅 *{year_from or '1940'}–{year_to or CURRENT_YEAR}*")
    else:
        lines.append(f"📅 *1940–{CURRENT_YEAR}*")

    price_from = f.get("price_from")
    price_to = f.get("price_to")
    if price_from or price_to:
        from_str = f"{price_from:,.0f}" if price_from else "0"
        to_str = f"{price_to:,.0f}" if price_to else "∞"
        lines.append(f"💸 *{from_str}-dən {to_str}-dək AZN*")

    lines.append(f"📉 *{f.get('min_discount', 14)}% bazardan aşağı*")
    lines.append(f"📍 *{f.get('city') or 'Bakı'}*")
    return "\n".join(lines)


def get_user_filter(telegram_id: str) -> dict:
    f = db.get_filter(telegram_id)
    if not f:
        db.save_filter(
            telegram_id=telegram_id,
            brand=None, model=None,
            engine_volume=None,
            year_from=None, year_to=None,
            price_from=None, price_to=None,
            min_discount=14,
            city="Bakı",
        )
        f = db.get_filter(telegram_id)
    return f


# ============ ОБРАБОТЧИКИ ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user
    db.get_or_create_user(
        telegram_id=str(user.id),
        username=user.username,
        first_name=user.first_name,
    )
    get_user_filter(str(user.id))

    await update.message.reply_text(
        f"👋 Salam, {user.first_name}!\n\n"
        "Mən Turbo.az-da bazardan ucuz maşınları tapıb sənə xəbər verirəm.\n\n"
        "Defolt olaraq *Bakı* üzrə *14% endirimli* maşınlar sizə gələcək.\n\n"
        "Nə etmək istəyirsən?",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    text = update.message.text.strip()
    telegram_id = str(update.effective_user.id)

    # --- Режим ожидания минимальной цены ---
    if context.user_data.get("awaiting_price_from"):
        if text == "💰 Qiymətsiz":
            context.user_data["price_from"] = None
            context.user_data["awaiting_price_from"] = False
            context.user_data["awaiting_price_to"] = True
            await update.message.reply_text(
                "Minimum: *limitsiz*\n\nMaximum qiyməti yazın:",
                parse_mode="Markdown",
                reply_markup=PRICE_KEYBOARD,
            )
            return
        elif text == "🔙 Geri":
            context.user_data["awaiting_price_from"] = False
            f = get_user_filter(telegram_id)
            await update.message.reply_text(
                format_filter_text(f) + "\n\nNəyi dəyişmək istəyirsən?",
                parse_mode="Markdown",
                reply_markup=FILTER_KEYBOARD,
            )
            return
        else:
            try:
                price = float(text.replace(" ", ""))
                if price < 0 or price > 10_000_000:
                    raise ValueError
                context.user_data["price_from"] = price
                context.user_data["awaiting_price_from"] = False
                context.user_data["awaiting_price_to"] = True
                await update.message.reply_text(
                    f"Minimum: *{price:,.0f} AZN*\n\nMaximum qiyməti yazın:",
                    parse_mode="Markdown",
                    reply_markup=PRICE_KEYBOARD,
                )
                return
            except ValueError:
                await update.message.reply_text(
                    "❌ Düzgün qiymət yazın. Məsələn: 8000",
                    reply_markup=PRICE_KEYBOARD,
                )
                return

    # --- Режим ожидания максимальной цены ---
    if context.user_data.get("awaiting_price_to"):
        if text == "💰 Qiymətsiz":
            context.user_data["price_to"] = None
        elif text == "🔙 Geri":
            context.user_data["awaiting_price_to"] = False
            f = get_user_filter(telegram_id)
            await update.message.reply_text(
                format_filter_text(f) + "\n\nNəyi dəyişmək istəyirsən?",
                parse_mode="Markdown",
                reply_markup=FILTER_KEYBOARD,
            )
            return
        else:
            try:
                price = float(text.replace(" ", ""))
                if price < 0 or price > 10_000_000:
                    raise ValueError
                context.user_data["price_to"] = price
            except ValueError:
                await update.message.reply_text(
                    "❌ Düzgün qiymət yazın. Məsələn: 50000",
                    reply_markup=PRICE_KEYBOARD,
                )
                return

        f = get_user_filter(telegram_id)
        db.save_filter(
            telegram_id=telegram_id,
            brand=f.get("brand"), model=f.get("model"),
            engine_volume=f.get("engine_volume"),
            year_from=f.get("year_from"), year_to=f.get("year_to"),
            price_from=context.user_data.get("price_from"),
            price_to=context.user_data.get("price_to"),
            min_discount=f.get("min_discount", 14),
            city=f.get("city"),
        )
        context.user_data["awaiting_price_to"] = False
        context.user_data["price_from"] = None
        context.user_data["price_to"] = None
        f = get_user_filter(telegram_id)
        await update.message.reply_text(
            "✅ Qiymət yeniləndi!\n\n" + format_filter_text(f),
            parse_mode="Markdown",
            reply_markup=MAIN_KEYBOARD,
        )
        return

    # --- Режим ожидания города ---
    if context.user_data.get("awaiting_city"):
        context.user_data["awaiting_city"] = False
        if text == "🔙 Geri":
            f = get_user_filter(telegram_id)
            await update.message.reply_text(
                format_filter_text(f) + "\n\nNəyi dəyişmək istəyirsən?",
                parse_mode="Markdown",
                reply_markup=FILTER_KEYBOARD,
            )
            return
        city = find_city(text)
        if city:
            f = get_user_filter(telegram_id)
            db.save_filter(
                telegram_id=telegram_id,
                brand=f.get("brand"), model=f.get("model"),
                engine_volume=f.get("engine_volume"),
                year_from=f.get("year_from"), year_to=f.get("year_to"),
                price_from=f.get("price_from"), price_to=f.get("price_to"),
                min_discount=f.get("min_discount", 14),
                city=city,
            )
            f = get_user_filter(telegram_id)
            await update.message.reply_text(
                f"✅ Şəhər yeniləndi: *{city}*\n\n" + format_filter_text(f),
                parse_mode="Markdown",
                reply_markup=MAIN_KEYBOARD,
            )
        else:
            await update.message.reply_text(
                "❌ Şəhəri anlaya bilmədim. Yenidən yaz.",
                reply_markup=MAIN_KEYBOARD,
            )
        return

    # --- Режим поиска ---
    if context.user_data.get("awaiting_search"):
        context.user_data["awaiting_search"] = False
        if text in {"🔙 Geri", "📋 Filtrim", "⚙️ Filtrlər", "🔍 Axtar"}:
            pass
        else:
            parsed = parse_search_query(text)
            if not any([parsed.get("brand"), parsed.get("year_from")]):
                await update.message.reply_text(
                    "❌ Heç nə anlaya bilmədim.\nNümunə: `toyota prius 2018`",
                    parse_mode="Markdown",
                    reply_markup=MAIN_KEYBOARD,
                )
                return

            if parsed.get("brand") and not any(
                parsed["brand"].lower() == b.lower()
                for b in [row["brand"] for row in db.conn.execute(
                    "SELECT DISTINCT brand FROM cars WHERE is_active=1"
                ).fetchall()]
            ):
                await update.message.reply_text(
                    f"❌ \"{parsed['brand']}\" markasını anlaya bilmədim.\n"
                    "Məsələn: `toyota prius 2018`",
                    parse_mode="Markdown",
                    reply_markup=MAIN_KEYBOARD,
                )
                return

            context.user_data["temp_filter"] = parsed
            lines = []
            if parsed.get("brand"):
                if parsed.get("model"):
                    lines.append(f"🚗 *{parsed['brand']} {parsed['model']}*")
                else:
                    lines.append(f"🚗 *{parsed['brand']}*")
            else:
                lines.append("🚗 *Bütün maşınlar*")
            if parsed.get("year_from"):
                lines.append(f"📅 *{parsed['year_from']}–{parsed.get('year_to', CURRENT_YEAR)}*")

            await update.message.reply_text(
                "Mən belə başa düşdüm:\n\n" + "\n".join(lines) + "\n\nDoğrudur?",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup([["✅ Bəli", "✏️ Dəyiş"], ["🔙 Geri"]], resize_keyboard=True),
            )
            return

    # --- Навигация ---
    if text == "🔍 Axtar":
        await update.message.reply_text(
            "Maşını təsvir et.\nNümunə: `toyota prius 2018`\nSadəcə `2018` də yaza bilərsən.",
            parse_mode="Markdown",
        )
        context.user_data["awaiting_search"] = True
        return

    elif text == "⚙️ Filtrlər":
        f = get_user_filter(telegram_id)
        await update.message.reply_text(
            format_filter_text(f) + "\n\nNəyi dəyişmək istəyirsən?",
            parse_mode="Markdown",
            reply_markup=FILTER_KEYBOARD,
        )
        return

    elif text == "📋 Filtrim":
        f = get_user_filter(telegram_id)
        await update.message.reply_text(
            format_filter_text(f),
            parse_mode="Markdown",
            reply_markup=MAIN_KEYBOARD,
        )
        return

    elif text == "📉 Endirim faizi":
        await update.message.reply_text("Nə qədər endirim istəyirsən?", reply_markup=DISCOUNT_KEYBOARD)
        return

    elif text in ["14%", "20%"]:
        discount = int(text.replace("%", ""))
        f = get_user_filter(telegram_id)
        db.save_filter(
            telegram_id=telegram_id,
            brand=f.get("brand"), model=f.get("model"),
            engine_volume=f.get("engine_volume"),
            year_from=f.get("year_from"), year_to=f.get("year_to"),
            price_from=f.get("price_from"), price_to=f.get("price_to"),
            min_discount=discount,
            city=f.get("city"),
        )
        f = get_user_filter(telegram_id)
        await update.message.reply_text(
            "✅ Yeniləndi!\n\n" + format_filter_text(f),
            parse_mode="Markdown",
            reply_markup=MAIN_KEYBOARD,
        )
        return

    elif text == "📍 Şəhər":
        await update.message.reply_text(
            "Şəhəri yazın.\nMəsələn: Bakı, Gəncə, Sumqayıt, Naxçıvan...",
            parse_mode="Markdown",
        )
        context.user_data["awaiting_city"] = True
        return

    elif text == "💸 Qiymət":
        f = get_user_filter(telegram_id)
        current = ""
        if f.get("price_from") or f.get("price_to"):
            pf = f"{f['price_from']:,.0f}" if f.get("price_from") else "0"
            pt = f"{f['price_to']:,.0f}" if f.get("price_to") else "∞"
            current = f"\nHal-hazırda: *{pf}–{pt} AZN*"
        await update.message.reply_text(
            f"Minimum qiyməti yazın (AZN):{current}\n\nMəsələn: 8000",
            parse_mode="Markdown",
            reply_markup=PRICE_KEYBOARD,
        )
        context.user_data["awaiting_price_from"] = True
        return

    elif text == "🔄 Sıfırla":
        db.save_filter(
            telegram_id=telegram_id,
            brand=None, model=None,
            engine_volume=None,
            year_from=None, year_to=None,
            price_from=None, price_to=None,
            min_discount=14,
            city="Bakı",
        )
        f = get_user_filter(telegram_id)
        await update.message.reply_text(
            "🔄 Filtr sıfırlandı!\n\n" + format_filter_text(f),
            parse_mode="Markdown",
            reply_markup=MAIN_KEYBOARD,
        )
        return

    elif text == "🔙 Geri":
        f = get_user_filter(telegram_id)
        await update.message.reply_text(
            format_filter_text(f),
            parse_mode="Markdown",
            reply_markup=MAIN_KEYBOARD,
        )
        return

    elif text == "✅ Bəli":
        parsed = context.user_data.get("temp_filter", {})
        if parsed:
            f = get_user_filter(telegram_id)
            db.save_filter(
                telegram_id=telegram_id,
                brand=parsed.get("brand") or f.get("brand"),
                model=parsed.get("model") or f.get("model"),
                engine_volume=f.get("engine_volume"),
                year_from=parsed.get("year_from"),
                year_to=parsed.get("year_to"),
                price_from=f.get("price_from"),
                price_to=f.get("price_to"),
                min_discount=f.get("min_discount", 14),
                city=f.get("city"),
            )
            context.user_data["temp_filter"] = {}
            f = get_user_filter(telegram_id)
            await update.message.reply_text(
                "✅ Filtr yeniləndi!\n\n" + format_filter_text(f),
                parse_mode="Markdown",
                reply_markup=MAIN_KEYBOARD,
            )
        return

    elif text == "✏️ Dəyiş":
        await update.message.reply_text("Yenidən yaz. Nümunə: `toyota prius 2018`", parse_mode="Markdown")
        context.user_data["awaiting_search"] = True
        return

    await update.message.reply_text(
        "Başa düşmədim. Zəhmət olmasa düymələrdən istifadə et.",
        reply_markup=MAIN_KEYBOARD,
    )


async def set_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Axtarış üçün 🔍 Axtar düyməsini istifadə et.", reply_markup=MAIN_KEYBOARD)

async def my_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Filtrinə baxmaq üçün 📋 Filtrim düyməsini istifadə et.", reply_markup=MAIN_KEYBOARD)

async def stop_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Sıfırlamaq üçün ⚙️ Filtrlər → 🔄 Sıfırla düyməsini istifadə et.", reply_markup=MAIN_KEYBOARD)