import subprocess
import time

PROJECT_PATH = r"C:\Users\IamTheGreatest\Desktop\Projects\car tracker"
PYTHON = rf"{PROJECT_PATH}\venv\Scripts\python.exe"

while True:
    print("Tap скрапер запущен...")
    subprocess.run([PYTHON, "-m", "scrapy", "crawl", "tap"], cwd=PROJECT_PATH)
    print("Жду 15 минут...")
    time.sleep(900)