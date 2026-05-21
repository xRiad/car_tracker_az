import subprocess

PROJECT_PATH = r"C:\Users\IamTheGreatest\Desktop\Projects\car tracker"
PYTHON = rf"{PROJECT_PATH}\venv\Scripts\python.exe"

subprocess.run([PYTHON, "bot/main.py"], cwd=PROJECT_PATH)