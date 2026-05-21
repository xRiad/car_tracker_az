import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

BOT_NAME = "car_tracker"


TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

SPIDER_MODULES = ["car_tracker.spiders"]
NEWSPIDER_MODULE = "car_tracker.spiders"

ROBOTSTXT_OBEY = False

# ============= МАСКИРОВКА (fingerprint) =============
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

COOKIES_ENABLED = False

# ============= MIDDLEWARE =============
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 500,
}

# ============= PLAYWRIGHT =============
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "args": [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        # "--disable-gpu",
        "--window-position=-32000,-32000",
        "--disable-notifications",
        "--disable-infobars",
        "--no-startup-window",          # ← Не показывать окно при запуске
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-field-trial-config"
    ]
}

# ============= PIPELINE =============
ITEM_PIPELINES = {
    "car_tracker.pipelines.CarTrackerPipeline": 300,
}

# ============= СКОРОСТЬ =============
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 4
RANDOMIZE_DOWNLOAD_DELAY = True
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 3
AUTOTHROTTLE_MAX_DELAY = 15
# PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 4

# ============= ТАЙМАУТЫ =============
DOWNLOAD_TIMEOUT = 10

FEED_EXPORT_ENCODING = "utf-8"
LOG_LEVEL = "INFO"