"""Структура данных для автомобиля."""

import scrapy


class CarItem(scrapy.Item):
    """Автомобиль со всеми полями из карточки."""
    
    external_id = scrapy.Field()       # 10243115
    source = scrapy.Field()            # turbo.az
    url = scrapy.Field()               # полная ссылка
    
    brand = scrapy.Field()             # Chevrolet
    model = scrapy.Field()             # Trax
    year = scrapy.Field()              # 2018
    price = scrapy.Field()             # 18400
    currency = scrapy.Field()          # AZN
    
    engine_volume = scrapy.Field()     # 1.4 (L)
    engine_power = scrapy.Field()      # 138 (a.g.)
    fuel_type = scrapy.Field()         # Benzin
    
    mileage = scrapy.Field()           # 85000
    body_type = scrapy.Field()         # Offroader / SUV
    gearbox = scrapy.Field()           # Avtomat
    transmission = scrapy.Field()      # Tam
    
    is_new = scrapy.Field()            # False
    condition = scrapy.Field()         # Vuruğu yoxdur, rənglənməyib
    color = scrapy.Field()             # Qara
    
    city = scrapy.Field()              # Bakı
    posted_date = scrapy.Field()       # 2026-05-19 11:00:00
    photos_count = scrapy.Field()      # 5
    main_photo_url = scrapy.Field()    # ссылка на фото
    
    scraped_at = scrapy.Field()        # когда спарсили