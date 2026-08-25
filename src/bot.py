import requests
import os

from config import BOT_TOKEN, CHAT_ID
from positions import (
    update_position,
    close_position,
    load_positions
)


OFFSET_FILE = "data/telegram_offset.json"


def load_offset():
    try:
        with open(OFFSET_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return None


def save_offset(offset):
    os.makedirs("data", exist_ok=True)

    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))


def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": text
        },
        timeout=10
    )

    response.raise_for_status()


def check_telegram():
    offset = load_offset()

    params = {
        "timeout": 5
    }

    if offset is not None:
        params["offset"] = offset

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

    response = requests.get(
        url,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    updates = response.json().get("result", [])

    for update in updates:
        update_id = update["update_id"]

        save_offset(update_id + 1)

        message = update.get("message")

        if not message:
            continue

        chat_id = str(message.get("chat", {}).get("id"))

        if chat_id != str(CHAT_ID):
            continue

        text = message.get("text", "").strip()

        if not text:
            continue

        process_command(text)


def process_command(text):
    parts = text.split()

    if not parts:
        return

    command = parts[0].lower()

    if command == "/position":
        handle_position(parts)
        return

    if command == "/positions":
        send_positions()
        return


def handle_position(parts):
    if len(parts) == 3 and parts[2].upper() == "CLOSE":
        symbol = parts[1].upper()

        if close_position(symbol):
            send_message(
                f"✅ POSITION CLOSED\n\n"
                f"Symbol: {symbol}\n\n"
                f"CryptoNotifier will no longer monitor this position."
            )
        else:
            send_message(
                f"❌ NO ACTIVE POSITION\n\n"
                f"Symbol: {symbol}\n\n"
                f"No position was found."
            )

        return

    if len(parts) != 4:
        send_message(
            "Invalid format.\n\n"
            "Use:\n"
            "/position BTCUSDT BUY 80457.60\n"
            "/position BTCUSDT SELL 80457.60\n"
            "/position BTCUSDT CLOSE"
        )
        return

    symbol = parts[1].upper()
    side = parts[2].upper()

    if side not in ("BUY", "SELL"):
        send_message(
            "Invalid position side.\n\n"
            "Use BUY or SELL.\n\n"
            "Example:\n"
            "/position BTCUSDT BUY 80457.60"
        )
        return

    try:
        price = float(parts[3])
    except ValueError:
        send_message(
            "Invalid entry price.\n\n"
            "Example:\n"
            "/position BTCUSDT BUY 80457.60"
        )
        return

    update_position(symbol, side, price)

    send_message(
        f"✅ POSITION RECORDED\n\n"
        f"Symbol: {symbol}\n"
        f"Side: {side}\n"
        f"Entry: {price:.4f}\n\n"
        f"CryptoNotifier will monitor this position on the next scan."
    )


def send_positions():
    positions = load_positions()

    if not positions:
        send_message("No active positions recorded.")
        return

    lines = ["📊 ACTIVE POSITIONS\n"]

    for symbol, position in positions.items():
        lines.append(
            f"{symbol}\n"
            f"Side: {position.get('side', 'UNKNOWN')}\n"
            f"Entry: {position.get('entry_price', 'UNKNOWN')}\n"
            f"Status: {position.get('status', 'UNKNOWN')}\n"
        )

    send_message("\n".join(lines))