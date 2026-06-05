"""Логирование отправленных объявлений и действий пользователей."""

import os
from datetime import datetime


class NotificationLogger:
    """Пишет логи в текстовые файлы."""
    
    def __init__(self, notifications_file: str = "notifications.log",
                 actions_file: str = "user_actions.log"):
        self.notifications_file = notifications_file
        self.actions_file = actions_file
    
    # ========== ЛОГ ОТПРАВЛЕННЫХ МАШИН ==========
    
    def log_sent(self, user_id: str, car_info: dict, discount: float):
        """Записывает факт отправки машины пользователю."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        brand = car_info.get("brand", "?")
        model = car_info.get("model", "?")
        year = car_info.get("year", "?")
        price = car_info.get("price", 0)
        city = car_info.get("city", "?")
        
        line = (
            f"[{now}] | "
            f"User_ID: {user_id} | "
            f"Car: {brand} {model} {year} | "
            f"Price: {price:,.0f} AZN | "
            f"Discount: {discount:.1f}% | "
            f"City: {city}\n"
        )
        
        with open(self.notifications_file, "a", encoding="utf-8") as f:
            f.write(line)
    
    def get_recent_notifications(self, lines: int = 50) -> list[str]:
        """Читает последние N строк лога уведомлений."""
        if not os.path.exists(self.notifications_file):
            return []
        
        with open(self.notifications_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        
        return all_lines[-lines:]
    
    # ========== ЛОГ ДЕЙСТВИЙ ПОЛЬЗОВАТЕЛЯ ==========
    
    def log_action(self, user_id: str, action: str):
        """Записывает действие пользователя (нажатие кнопки, команду)."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        line = f"[{now}] | User_ID: {user_id} | Action: {action}\n"
        
        with open(self.actions_file, "a", encoding="utf-8") as f:
            f.write(line)
    
    def get_recent_actions(self, lines: int = 50) -> list[str]:
        """Читает последние N строк лога действий."""
        if not os.path.exists(self.actions_file):
            return []
        
        with open(self.actions_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        
        return all_lines[-lines:]
    
    # ========== ОБЩИЕ ==========
    
    def clear_notifications(self):
        """Очищает лог уведомлений."""
        if os.path.exists(self.notifications_file):
            open(self.notifications_file, "w").close()
    
    def clear_actions(self):
        """Очищает лог действий."""
        if os.path.exists(self.actions_file):
            open(self.actions_file, "w").close()