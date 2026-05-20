"""Расчёт средних рыночных цен."""

from datetime import datetime
from .db import Database


class MarketAnalyzer:
    """Считает средние цены по данным из базы."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def calculate_all(self, min_listings: int = 3):
        """Пересчитываем средние для всех комбинаций."""
        # Берём активные машины за 14 дней
        cars = self.db.get_active_cars(days=14)
        
        if not cars:
            print("❌ Нет активных машин для расчёта")
            return 0
        
        # Группируем
        groups: dict[tuple, list[float]] = {}
        
        for car in cars:
            brand = (car.get("brand") or "").strip()
            model = (car.get("model") or "").strip()
            year = car.get("year")
            engine_volume = car.get("engine_volume") or 0
            fuel_type = (car.get("fuel_type") or "").strip()
            price = car.get("price")
            
            if not all([brand, model, year, price]):
                continue
            
            key = (brand, model, int(year), float(engine_volume), fuel_type)
            if key not in groups:
                groups[key] = []
            groups[key].append(float(price))
        
        total_combos = 0
        
        for (brand, model, year, engine_volume, fuel_type), prices in groups.items():
            if len(prices) < min_listings:
                continue
            
            prices_sorted = sorted(prices)
            n = len(prices_sorted)
            
            avg_price = sum(prices_sorted) / n
            median_price = prices_sorted[n // 2]
            min_price = prices_sorted[0]
            max_price = prices_sorted[-1]
            
            self.db.save_market_price(
                brand=brand,
                model=model,
                year=year,
                engine_volume=engine_volume,
                fuel_type=fuel_type,
                avg_price=round(avg_price, 2),
                median_price=round(median_price, 2),
                min_price=round(min_price, 2),
                max_price=round(max_price, 2),
                total_listings=n,
            )
            
            total_combos += 1
            print(
                f"📊 {brand} {model} {year} {engine_volume}L {fuel_type}: "
                f"средняя {avg_price:.0f} AZN ({n} машин)"
            )
        
        print(f"✅ Готово! Обработано {total_combos} комбинаций из {len(cars)} машин")
        return total_combos


# Запуск
if __name__ == "__main__":
    db = Database()
    analyzer = MarketAnalyzer(db)
    analyzer.calculate_all()
    db.close()