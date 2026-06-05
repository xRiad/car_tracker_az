"""Паук для turbo.az."""

import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

import scrapy
from scrapy_playwright.page import PageMethod

from ..items import CarItem
# from ..db import Database


class TurboSpider(scrapy.Spider):
    name = "turbo"
    allowed_domains = ["turbo.az"]
    
    BASE_URL = (
        "https://turbo.az/autos?"
        "q%5Bsort%5D=&"
        "q%5Bmake%5D%5B%5D=&q%5Bmodel%5D%5B%5D=&"
        "q%5Bused%5D=&q%5Bregion%5D%5B%5D=&"
        "q%5Bprice_from%5D=&q%5Bprice_to%5D=&"
        "q%5Bcurrency%5D=azn&"
        "q%5Bloan%5D=0&q%5Bbarter%5D=0&"
        "q%5Bcategory%5D%5B%5D=9&q%5Bcategory%5D%5B%5D=127&"
        "q%5Bcategory%5D%5B%5D=16&q%5Bcategory%5D%5B%5D=61&"
        "q%5Bcategory%5D%5B%5D=62&q%5Bcategory%5D%5B%5D=14&"
        "q%5Bcategory%5D%5B%5D=63&q%5Bcategory%5D%5B%5D=64&"
        "q%5Bcategory%5D%5B%5D=2&q%5Bcategory%5D%5B%5D=11&"
        "q%5Bcategory%5D%5B%5D=26&q%5Bcategory%5D%5B%5D=65&"
        "q%5Bcategory%5D%5B%5D=3&q%5Bcategory%5D%5B%5D=28&"
        "q%5Bcategory%5D%5B%5D=66&q%5Bcategory%5D%5B%5D=7&"
        "q%5Bcategory%5D%5B%5D=67&q%5Bcategory%5D%5B%5D=5&"
        "q%5Bcategory%5D%5B%5D=68&q%5Bcategory%5D%5B%5D=21&"
        "q%5Bcategory%5D%5B%5D=69&q%5Bcategory%5D%5B%5D=70&"
        "q%5Bcategory%5D%5B%5D=6&q%5Bcategory%5D%5B%5D=71&"
        "q%5Bcategory%5D%5B%5D=22&q%5Bcategory%5D%5B%5D=8&"
        "q%5Bcategory%5D%5B%5D=1&q%5Bcategory%5D%5B%5D=73&"
        "q%5Bcategory%5D%5B%5D=72&q%5Bcategory%5D%5B%5D=74&"
        "q%5Bcategory%5D%5B%5D=128&q%5Bcategory%5D%5B%5D=75&"
        "q%5Bcategory%5D%5B%5D=4&q%5Bcategory%5D%5B%5D=19&"
        "q%5Bcategory%5D%5B%5D=13&"
        "q%5Byear_from%5D=&q%5Byear_to%5D=&"
        "q%5Bcolor%5D%5B%5D=&q%5Bfuel_type%5D%5B%5D=&"
        "q%5Bgear%5D%5B%5D=&q%5Btransmission%5D%5B%5D=&"
        "q%5Bengine_volume_from%5D=&q%5Bengine_volume_to%5D=&"
        "q%5Bpower_from%5D=&q%5Bpower_to%5D=&"
        "q%5Bmileage_from%5D=&q%5Bmileage_to%5D=&"
        "q%5Bonly_shops%5D=0&"
        "q%5Bprior_owners_count%5D%5B%5D=&q%5Bseats_count%5D%5B%5D=&"
        "q%5Bmarket%5D%5B%5D=&"
        "q%5Bcrashed%5D=0&q%5Bpainted%5D=1&"
        "q%5Bfor_spare_parts%5D=0&"
        "q%5Bavailability_status%5D="
    )
    
    max_pages = 6
    max_age_minutes = 15
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.db = Database()
    
    def start_requests(self):
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
        
        url = self.BASE_URL + "&page=1"
        
        yield scrapy.Request(
            url=url,
            callback=self.parse_list,
            errback=self.handle_error,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_context_kwargs": {
                    "user_agent": user_agent,
                    "viewport": {"width": 1920, "height": 1080},
                },
                "page": 1,
            },
        )
        def errback_handler(self, failure):
            self.logger.error(f"🔴🔴🔴 ОШИБКА ЗАПРОСА: {failure.value}")
            self.logger.error(f"🔴 URL: {failure.request.url}")
    
    async def parse_list(self, response):
        """Парсим страницу выдачи."""
        page = response.meta["playwright_page"]
        page_num = response.meta["page"]

        self.logger.debug(f"🟡 parse_list СТРАНИЦА {page_num}: ЗАГРУЖЕНА")
        
            # БЛОКИРУЕМ рекламу и трекеры
        await page.route(
            "**/*",
            lambda route: route.abort()
            if any(
                domain in route.request.url.lower()
                for domain in [
                    "doubleclick", "googlesyndication", "google-analytics",
                    "facebook.com/tr", "mc.yandex", "adriver",
                    "creativecdn", "33across", "beeline",
                ]
            )
            else route.continue_()
        )

        # Скроллим вниз чтобы подгрузить все карточки
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)
        html = await page.content()
        response = response.replace(body=html)
        
        cards = response.css(".products-i:not(.vipped):not(.featured):not(.rounded)")
        self.logger.debug(f"🟡 Карточек найдено: {len(cards)}")
        
        newest_time = None
        card_count = 0
        
        for card in cards:
            link = card.css(".products-i__link::attr(href)").get()
            if not link:
                self.logger.debug(f"🟡 Пропущена карточка без ссылки")
                continue

            self.logger.debug(f"🟡 Карточка {card_count + 1}: {link}")

            datetime_text = card.css(".products-i__datetime::text").get()
            posted_date = self._parse_datetime(datetime_text)
            
            if posted_date:
                age = datetime.now() - posted_date
                if age > timedelta(minutes=self.max_age_minutes):
                    self.logger.info(
                        f"⏰ Старше {self.max_age_minutes} мин, стоп на стр. {page_num}"
                    )
                    break
                newest_time = posted_date
            
            full_url = urljoin(response.url, link)

            self.logger.debug(f"🟡 Отправляю запрос: {full_url}")
            
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_car,
                errback=self.handle_error,  # <-- добавить
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "domcontentloaded"),
                        PageMethod("wait_for_timeout", 500),  # уменьшил до 500мс
                    ],
                    "playwright_context_kwargs": {
                        "user_agent": response.meta["playwright_context_kwargs"]["user_agent"],
                    },
                    "playwright_page_goto_kwargs": {
                        "timeout": 8000,  # 8 секунд
                        "wait_until": "domcontentloaded",
                    },
                    "posted_date": posted_date.isoformat() if posted_date else None,
                },
                dont_filter=True,
            )
            card_count += 1
        self.logger.debug(f"🟡 Страница {page_num}: ВСЕ КАРТОЧКИ ОТПРАВЛЕНЫ")
        
        self.logger.info(f"📄 Стр. {page_num}: {card_count} карточек")
        self.logger.info(f"🔍 page_num={page_num}, max_pages={self.max_pages}")

        await page.close()
        
        if page_num < self.max_pages:
            next_page = page_num + 1
            self.logger.info(f"➡️ Переходим на страницу {next_page}")
            yield scrapy.Request(
                url=self.BASE_URL + f"&page={next_page}",
                callback=self.parse_list,
                errback=self.handle_error,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_context_kwargs": {
                        "user_agent": response.meta["playwright_context_kwargs"]["user_agent"],
                    },
                    "page": next_page,
                },
            )
        else:
            self.logger.info(f"🛑 Достигнут лимит страниц ({self.max_pages})")
    
    async def parse_car(self, response):
        """Парсим внутреннюю страницу машины."""
        self.logger.debug(f"🟢 ЗАШЛИ в parse_car: {response.url}")
        item = CarItem()
        print("STEP1:", response.url)

        external_id = re.search(r"/autos/(\d+)", response.url)
        if external_id:
            item["external_id"] = external_id.group(1)
            self.logger.debug(f"🆔 ID: {item['external_id']}")
        else:
            self.logger.error(f"🔴 НЕТ ID: {response.url}")
            return
        
        # if self.db.car_exists(item["external_id"]):
        #     self.logger.info(f"⏭️ Уже есть: {item['external_id']}")
        #     return

        self.logger.debug(f"📦 Парсим данные...")
        
        item["source"] = "turbo.az"
        item["url"] = response.url
        item["posted_date"] = response.meta.get("posted_date")
        item["scraped_at"] = datetime.now().isoformat()

        
        title = response.css("h1.product-title::text").getall()
        title_text = " ".join(t.strip() for t in title if t.strip())
        
        if title_text:
            self._parse_title(title_text, item)
        
            for row in response.css(".product-properties__i"):
                name = row.css(".product-properties__i-name::text").get()
                value_parts = row.css(".product-properties__i-value ::text").getall()

                if name and value_parts:
                    value_text = " ".join(v.strip() for v in value_parts if v.strip())

                    name_clean = " ".join(name.split()).strip().lower()

                    if name_clean == "marka":
                        item["brand"] = value_text
                    elif name_clean == "model":
                        item["model"] = value_text
                    elif name_clean == "buraxılış ili":
                        try:
                            item["year"] = int(value_text)
                        except ValueError:
                            pass
                    elif name_clean == "şəhər":
                        item["city"] = value_text
                    elif name_clean == "mühərrik":
                        self._parse_engine(value_text, item)
                    elif name_clean == "yürüş":
                        item["mileage"] = self._parse_number(value_text)
                    elif name_clean == "ban növü":
                        item["body_type"] = value_text
                    elif name_clean == "sürətlər qutusu":
                        item["gearbox"] = value_text
                    elif name_clean == "ötürücü":
                        item["transmission"] = value_text
                    elif name_clean == "yeni":
                        item["is_new"] = value_text.lower() == "bəli"
                    elif name_clean == "rəng":
                        item["color"] = value_text
                    elif name_clean == "vəziyyəti":
                        item["condition"] = value_text
        
        
        # Все тексты из блока цены, берём первый с ₼
        price_parts = response.css(".product-price .product-price__i::text").getall()
        price_text = None
        for p in price_parts:
            p_clean = p.strip()
            if ("₼" in p_clean or "AZN" in p_clean.upper()) and "≈" not in p_clean:
                price_text = p_clean
                break
        
        # Если не нашли без ≈ — берём первую с ₼ (с ≈)
        if not price_text:
            for p in price_parts:
                if "₼" in p or "AZN" in p.upper():
                    price_text = p.strip()
                    break
        
        if not price_text:
            price_text = response.css("meta[property='og:price:amount']::attr(content)").get()
        if not price_text:
            price_text = response.css(".product-price *::text").get()
        
        if price_text:
            item["price"], item["currency"] = self._parse_price(price_text)
        else:
            item["price"] = 0.0
            item["currency"] = "AZN"

        # Не сохраняем машины дешевле 1000 AZN
        if item["price"] < 800:
            self.logger.debug(f"⏭️ Пропущена (цена < 800): {item.get('external_id')}")
            return

        required_fields = ["brand", "model", "year", "price"]

        for f in required_fields:
            if item.get(f) is None:
                print("SKIP ITEM missing:", f, item.get("external_id"))
                return

        print(
            "SAVE CAR:",
            item.get("external_id"),
            item.get("brand"),
            item.get("model"),
            item.get("year"),
            item.get("price")
        )
        
        # desc_parts = response.css(".product-description ::text").getall()
        # if not desc_parts:
        #     desc_parts = response.css("article ::text, .description ::text").getall()
        # item["description"] = " ".join(d.strip() for d in desc_parts if d.strip() and len(d.strip()) > 3)
        
        # photos = response.css(".product-photos img, .gallery img, .swiper-slide img")
        # photos = response.css("section.product-photos img[src*='turbo.azstatic.com/uploads/f660x496']")
        # item["photos_count"] = len(photos)
        main_photo = response.css("meta[property='og:image']::attr(content)").get()
        if main_photo:
            item["main_photo_url"] = main_photo
        # if photos:
        #     item["main_photo_url"] = photos[0].attrib.get("src", "")

        self.logger.debug(f"✅ Готово: {item.get('brand')} {item.get('model')} — {item.get('price')} AZN")

        print("FINAL ITEM:", dict(item))
        yield item
        page = response.meta["playwright_page"]
        await page.close()
        self.logger.debug(f"📤 Item отправлен в pipeline")
    
    def _parse_datetime(self, text: str | None) -> datetime | None:
        if not text:
            return None
        
        text = text.strip()
        now = datetime.now()
        
        if "," in text:
            parts = text.split(",")
            date_part = parts[-1].strip() if len(parts) > 1 else text
        else:
            date_part = text
        
        if "bugün" in date_part.lower():
            time_match = re.search(r"(\d{1,2}):(\d{2})", date_part)
            if time_match:
                return now.replace(
                    hour=int(time_match.group(1)),
                    minute=int(time_match.group(2)),
                    second=0, microsecond=0,
                )
        
        if "dünən" in date_part.lower():
            time_match = re.search(r"(\d{1,2}):(\d{2})", date_part)
            if time_match:
                yesterday = now - timedelta(days=1)
                return yesterday.replace(
                    hour=int(time_match.group(1)),
                    minute=int(time_match.group(2)),
                    second=0, microsecond=0,
                )
        
        date_match = re.search(
            r"(\d{1,2})\s+(yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr)\s+(\d{4})",
            date_part, re.IGNORECASE
        )
        if date_match:
            months = {
                "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4,
                "may": 5, "iyun": 6, "iyul": 7, "avqust": 8,
                "sentyabr": 9, "oktyabr": 10, "noyabr": 11, "dekabr": 12,
            }
            day = int(date_match.group(1))
            month = months.get(date_match.group(2).lower(), 1)
            year = int(date_match.group(3))
            
            dt = datetime(year, month, day)
            time_match = re.search(r"(\d{1,2}):(\d{2})", date_part)
            if time_match:
                dt = dt.replace(
                    hour=int(time_match.group(1)),
                    minute=int(time_match.group(2)),
                )
            return dt
        
        return None
    
    def _parse_title(self, title: str, item: CarItem):
        parts = [p.strip() for p in title.split(",")]
        
        if len(parts) >= 1:
            brand_model = parts[0].strip().split(" ", 1)
            if len(brand_model) >= 1:
                item["brand"] = brand_model[0]
            if len(brand_model) >= 2:
                item["model"] = brand_model[1]
        
        for part in parts[1:]:
            part = part.strip()
            
            volume_match = re.match(r"([\d.]+)\s*L", part, re.IGNORECASE)
            if volume_match:
                item["engine_volume"] = float(volume_match.group(1))
                continue
            
            year_match = re.match(r"(\d{4})\s*il", part, re.IGNORECASE)
            if year_match:
                item["year"] = int(year_match.group(1))
                continue
            
            mileage_match = re.search(r"([\d\s]+)\s*km", part, re.IGNORECASE)
            if mileage_match:
                item["mileage"] = self._parse_number(mileage_match.group(1))
                continue
    
    def _parse_engine(self, text: str, item: CarItem):
        text = text.strip()
        
        volume_match = re.search(r"([\d.]+)\s*L", text, re.IGNORECASE)
        if volume_match:
            item["engine_volume"] = float(volume_match.group(1))
        
        power_match = re.search(r"(\d+)\s*a\.g\.", text, re.IGNORECASE)
        if power_match:
            item["engine_power"] = int(power_match.group(1))
        
        if "benzin" in text.lower():
            item["fuel_type"] = "Benzin"
        elif "dizel" in text.lower():
            item["fuel_type"] = "Dizel"
        elif "hibrid" in text.lower():
            item["fuel_type"] = "Hibrid"
        elif "elektro" in text.lower():
            item["fuel_type"] = "Elektro"
    
    def _parse_price(self, text: str) -> tuple[float, str]:
        if not text:
            return 0.0, "AZN"
        
        text_clean = text.replace("≈", "").replace("₼", "").replace("AZN", "").replace("USD", "").strip()
        try:
            price = float(text_clean.replace(" ", "").replace(",", "."))
        except ValueError:
            price = 0.0
        
        currency = "AZN"
        if "USD" in text or "$" in text:
            currency = "USD"
            price = price * 1.70  # Конвертация в AZN
        
        return price, currency

    def handle_error(self, failure):
        """Обработка ошибок загрузки страницы."""
        self.logger.error(f"🔴🔴🔴 ЗАПРОС ПРОВАЛЕН: {failure.request.url}")
        self.logger.error(f"🔴 Причина: {repr(failure.value)}")
    
    @staticmethod
    @staticmethod
    def _parse_number(text: str) -> int | None:
        if not text:
            return None
        # Убираем всё кроме цифр
        import re
        digits = re.sub(r"[^\d]", "", text)
        if digits:
            return int(digits)
        return None
    
    # def closed(self, reason):
    #     self.db.close()