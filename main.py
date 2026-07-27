import os
import subprocess
import sys

print("Starting Telegram Bot...")
os.chdir(os.path.join(os.path.dirname(__file__), 'telegram-bot'))
subprocess.run([sys.executable, 'bot.py'])