import requests
import os
from config import BOT_TOKEN, CHAT_ID
from positions import update_position, load_positions, save_positions

OFFSET_FILE = "data/telegram_offset.json"


def load_offset():
    try:
        with open(OFFSET_FILE, "r") as f:
            return f.read().strip()
    except:
        return None


def save_offset(offset):
    os.makedirs("data", exist_ok=True)

    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))


def check_telegram():
    offset = load_offset()

    params = {
        "timeout": 5
    }

    if offset:
        params["offset"] = int(offset)

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
    if len(parts) == 4:
        symbol = parts[1].upper()
        side = parts[2].upper()

        try:
            price = float(parts[3])
        except ValueError:
            send_message(
                "❌ Invalid entry price.\n\n"
                "Use:\n"
                "/position BTCUSDT BUY 80457.60"
            )
            return

        if side not in ("BUY", "SELL"):
            send_message(
                "❌ Side must be BUY or SELL.\n\n"
                "Example:\n"
                "/position BTCUSDT BUY 80457.60"
            )
            return

        update_position(symbol, side, price)

        send_message(
            f"✅ Position recorded\n\n"
            f"Symbol: {symbol}\n"
            f"Side: {side}\n"
            f"Entry: {price}"
        )

        return

    if len(parts) == 3 and parts[2].upper() == "CLOSE":
        symbol = parts[1].upper()

        positions = load_positions()

        if symbol not in positions:
            send_message(
                f"❌ No tracked position for {symbol}."
            )
            return

        del positions[symbol]
        save_positions(positions)

        send_message(
            f"✅ Position closed\n\n"
            f"Symbol: {symbol}"
        )

        return

    send_message(
        "❌ Invalid position command.\n\n"
        "Open position:\n"
        "/position BTCUSDT BUY 80457.60\n\n"
        "Short position:\n"
        "/position BTCUSDT SELL 80457.60\n\n"
        "Close position:\n"
        "/position BTCUSDT CLOSE"
    )


def send_positions():
    positions = load_positions()

    if not positions:
        send_message("📭 No tracked positions.")
        return

    lines = ["📊 TRACKED POSITIONS\n"]

    for symbol, position in positions.items():
        lines.append(
            f"{symbol}\n"
            f"Side: {position['side']}\n"
            f"Entry: {position['entry_price']}\n"
            f"Status: {position.get('status', 'HEALTHY')}\n"
        )

    send_message("\n".join(lines))


def send_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=10
    )