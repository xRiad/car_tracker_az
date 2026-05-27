"""Паук для tap.az."""

import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

import scrapy
from scrapy_playwright.page import PageMethod

from ..items import CarItem


class TapSpider(scrapy.Spider):
    name = "tap"
    allowed_domains = ["tap.az"]
    
    BASE_URL = "https://tap.az/elanlar/neqliyyat/avtomobiller"
    
    max_scrolls = 10
    max_age_minutes = 15
    
    def start_requests(self):
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
        
        yield scrapy.Request(
            url=self.BASE_URL,
            callback=self.parse_list,
            errback=self.handle_error,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_context_kwargs": {
                    "user_agent": user_agent,
                    "viewport": {"width": 1920, "height": 1080},
                },
                "scroll_count": 0,
            },
        )
    
    async def parse_list(self, response):
        """Парсим страницу выдачи с бесконечным скроллом."""
        page = response.meta["playwright_page"]
        scroll_count = response.meta["scroll_count"]
        
        # Блокируем рекламу
        await page.route(
            "**/*",
            lambda route: route.abort()
            if any(
                domain in route.request.url.lower()
                for domain in [
                    "doubleclick", "googlesyndication", "google-analytics",
                    "facebook.com/tr", "mc.yandex", "adriver",
                    "creativecdn", "33across",
                ]
            )
            else route.continue_()
        )
        
        # Скроллим вниз чтобы подгрузить карточки
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 800)")
            await page.wait_for_timeout(500)
        
        html = await page.content()
        response = response.replace(body=html)
        
        # Берём ТОЛЬКО обычные объявления (секция "Elanlar", не VIP)
        cards = response.css("[data-testid='latest-ads-section'] [data-testid='ad-card']")
        
        newest_time = None
        card_count = 0
        stopped_by_time = False
        
        for card in cards:
            link = card.css("a::attr(href)").get()
            if not link:
                continue
            
            datetime_text = card.css("[data-testid='ad-card-additional']::text").get()
            posted_date = self._parse_datetime(datetime_text)
            
            if posted_date:
                age = datetime.now() - posted_date
                if age > timedelta(minutes=self.max_age_minutes):
                    self.logger.info(f"⏰ Старше {self.max_age_minutes} мин, стоп")
                    stopped_by_time = True
                    break
                newest_time = posted_date
            
            full_url = urljoin(response.url, link)
            
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_car,
                errback=self.handle_error,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "domcontentloaded"),
                        PageMethod("wait_for_timeout", 500),
                    ],
                    "playwright_context_kwargs": {
                        "user_agent": response.meta["playwright_context_kwargs"]["user_agent"],
                    },
                    "playwright_page_goto_kwargs": {
                        "timeout": 8000,
                        "wait_until": "domcontentloaded",
                    },
                    "posted_date": posted_date.isoformat() if posted_date else None,
                },
                dont_filter=True,
            )
            card_count += 1
        
        self.logger.info(f"📄 Скролл {scroll_count}: {card_count} карточек")
        
        # Скроллим дальше если не остановились по времени и не достигли лимита
        if not stopped_by_time and scroll_count < self.max_scrolls:
            await page.evaluate("window.scrollBy(0, 3000)")
            await page.wait_for_timeout(2000)
            
            yield scrapy.Request(
                url=response.url,
                callback=self.parse_list,
                errback=self.handle_error,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_context_kwargs": {
                        "user_agent": response.meta["playwright_context_kwargs"]["user_agent"],
                    },
                    "scroll_count": scroll_count + 1,
                },
                dont_filter=True,
            )
        
        await page.close()
    
    async def parse_car(self, response):
        """Парсим внутреннюю страницу машины."""
        item = CarItem()
        
        external_id = re.search(r"/avtomobiller/(\d+)", response.url)
        if external_id:
            item["external_id"] = external_id.group(1)
        else:
            return
        
        item["source"] = "tap.az"
        item["url"] = response.url
        item["posted_date"] = response.meta.get("posted_date")
        item["scraped_at"] = datetime.now().isoformat()
        
        # Заголовок: "Chevrolet Cruze, 2013 il"
        title = response.css("h1.product-title::text").get()
        if title:
            self._parse_title(title, item)
        
        # Свойства из product-properties
        for row in response.css(".product-properties__i"):
            name = row.css(".product-properties__i-name::text").get()
            value = row.css(".product-properties__i-value::text, "
                           ".product-properties__i-value a::text").getall()
            if name and value:
                value_text = " ".join(v.strip() for v in value if v.strip())
                name_clean = name.strip().lower()
                
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
                elif name_clean == "mühərrik, sm³":
                    if value_text.isdigit():
                        raw_volume = float(value_text) / 1000
                        item["engine_volume"] = round(raw_volume, 1)
                elif name_clean == "yanacaq növü":
                    item["fuel_type"] = value_text
                elif name_clean == "yürüş, km":
                    item["mileage"] = self._parse_number(value_text)
                elif name_clean == "kuzov növü":
                    item["body_type"] = value_text
                elif name_clean == "sürətlər qutusu":
                    item["gearbox"] = value_text
                elif name_clean == "rəng":
                    item["color"] = value_text
        
        # Цена
        price_text = response.css(".product-price .price-val::text").get()
        currency_text = response.css(".product-price .price-cur::text").get()
        if price_text:
            item["price"], item["currency"] = self._parse_price(
                f"{price_text} {currency_text}" if currency_text else price_text
            )
        else:
            item["price"] = 0.0
            item["currency"] = "AZN"
        
        # Главное фото
        main_photo = response.css("meta[property='og:image']::attr(content)").get()
        if main_photo:
            item["main_photo_url"] = main_photo
        
        required_fields = ["brand", "model", "year", "price"]
        for f in required_fields:
            if item.get(f) is None:
                self.logger.info(f"SKIP: нет {f}")
                return
        
        yield item
        
        page = response.meta["playwright_page"]
        await page.close()
    
    def _parse_datetime(self, text: str | None) -> datetime | None:
        """Парсим дату из карточки tap.az.
        Форматы: 'Bakı, Bu gün, 13:12', 'Bakı, Dünən, 15:24', 'Bakı, 11 May 2026'.
        """
        if not text:
            return None
        
        text = text.strip()
        now = datetime.now()
        
        # "Bakı, Bu gün, 13:12" или "Bakı, Bugün, 13:12"
        if "bugün" in text.lower() or "bu gün" in text.lower():
            time_match = re.search(r"(\d{1,2}):(\d{2})", text)
            if time_match:
                return now.replace(
                    hour=int(time_match.group(1)),
                    minute=int(time_match.group(2)),
                    second=0, microsecond=0,
                )
        
        # "Bakı, Dünən, 15:24"
        if "dünən" in text.lower():
            time_match = re.search(r"(\d{1,2}):(\d{2})", text)
            if time_match:
                yesterday = now - timedelta(days=1)
                return yesterday.replace(
                    hour=int(time_match.group(1)),
                    minute=int(time_match.group(2)),
                    second=0, microsecond=0,
                )
        
        # "Bakı, 11 May 2026"
        date_match = re.search(r"(\d{1,2})\s+(yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr)\s+(\d{4})", text, re.IGNORECASE)
        if not date_match:
            # Английские месяцы: "11 May 2026"
            date_match = re.search(r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", text, re.IGNORECASE)
        
        if date_match:
            months = {
                "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4,
                "may": 5, "iyun": 6, "iyul": 7, "avqust": 8,
                "sentyabr": 9, "oktyabr": 10, "noyabr": 11, "dekabr": 12,
                "january": 1, "february": 2, "march": 3, "april": 4,
                "june": 6, "july": 7, "august": 8, "september": 9,
                "october": 10, "november": 11, "december": 12,
            }
            day = int(date_match.group(1))
            month = months.get(date_match.group(2).lower(), 1)
            year = int(date_match.group(3))
            return datetime(year, month, day)
        
        return None
    
    def _parse_title(self, title: str, item: CarItem):
        """Парсим 'Chevrolet Cruze, 2013 il'."""
        parts = [p.strip() for p in title.split(",")]
        
        if len(parts) >= 1:
            brand_model = parts[0].strip().split(" ", 1)
            if len(brand_model) >= 1:
                item["brand"] = brand_model[0]
            if len(brand_model) >= 2:
                item["model"] = brand_model[1]
        
        for part in parts[1:]:
            part = part.strip()
            year_match = re.match(r"(\d{4})\s*il", part, re.IGNORECASE)
            if year_match:
                item["year"] = int(year_match.group(1))
    
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
        
        return price, currency
    
    @staticmethod
    def _parse_number(text: str) -> int | None:
        if not text:
            return None
        digits = re.sub(r"[^\d]", "", text)
        return int(digits) if digits else None
    
    def handle_error(self, failure):
        self.logger.error(f"🔴 ЗАПРОС ПРОВАЛЕН: {failure.request.url}")
        self.logger.error(f"🔴 Причина: {repr(failure.value)}")