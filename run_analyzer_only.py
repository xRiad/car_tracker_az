import subprocess
import time

PROJECT_PATH = r"C:\Users\IamTheGreatest\Desktop\Projects\car tracker"
PYTHON = rf"{PROJECT_PATH}\venv\Scripts\python.exe"

# Ждём 5 минут при старте — даём скраперу накопить данные
time.sleep(300)

while True:
    print("Анализатор запущен...")
    subprocess.run([PYTHON, "-m", "car_tracker.market_analyzer"], cwd=PROJECT_PATH)
    print("Жду 24 часа...")
    time.sleep(86400)