import requests

from config import BOT_TOKEN, CHAT_ID


BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def notify(message):
    response = requests.post(
        f"{BASE_URL}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=10
    )

    response.raise_for_status()


def get_updates(offset=None):
    params = {
        "timeout": 5,
        "allowed_updates": ["message"]
    }

    if offset is not None:
        params["offset"] = offset

    response = requests.get(
        f"{BASE_URL}/getUpdates",
        params=params,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(data)

    return data.get("result", [])
