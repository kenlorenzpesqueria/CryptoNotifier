import requests
from config import BOT_TOKEN, CHAT_ID

URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def notify(message):
    response = requests.post(
        URL,
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=10
    )

    response.raise_for_status()