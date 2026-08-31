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
        "timeout": 5,
        "allowed_updates": ["message"]
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

    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(data)

    updates = data.get("result", [])

    if not updates:
        print("No new Telegram messages.")
        return

    for update in updates:

        update_id = update["update_id"]

        message = update.get("message")

        if not message:
            save_offset(update_id + 1)
            continue

        chat_id = str(
            message.get("chat", {}).get("id")
        )

        if chat_id != str(CHAT_ID):
            save_offset(update_id + 1)
            continue

        text = message.get("text", "").strip()

        if not text:
            save_offset(update_id + 1)
            continue

        print(
            f"Processing Telegram message "
            f"(update_id={update_id}): {text}"
        )

        try:
            process_command(text)

            save_offset(update_id + 1)

            print(
                f"Telegram update {update_id} acknowledged."
            )

        except Exception as e:
            print(
                f"Failed to process Telegram update "
                f"{update_id}: {e}"
            )

            raise


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
                f"POSITION CLOSED\n\n"
                f"Symbol: {symbol}\n\n"
                f"CryptoNotifier will no longer monitor "
                f"this position."
            )

        else:

            send_message(
                f"NO ACTIVE POSITION\n\n"
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

    update_position(
        symbol,
        side,
        price
    )

    send_message(
        f"POSITION RECORDED\n\n"
        f"Symbol: {symbol}\n"
        f"Side: {side}\n"
        f"Entry Price: {price:.4f}\n"
        f"Status: HEALTHY\n\n"
        f"CryptoNotifier will monitor this "
        f"position on the next scan."
    )


def send_positions():

    positions = load_positions()

    positions = {
        symbol: position
        for symbol, position in positions.items()
        if position.get("side") in ("BUY", "SELL")
    }

    if not positions:

        send_message(
            "NO ACTIVE POSITIONS"
        )

        return

    lines = [
        "ACTIVE POSITIONS",
        ""
    ]

    for symbol, position in positions.items():

        entry_price = position.get(
            "entry_price",
            "UNKNOWN"
        )

        signal_time = position.get(
            "signal_time",
            "UNKNOWN"
        )

        side = position.get(
            "side",
            "UNKNOWN"
        )

        status = position.get(
            "status",
            "UNKNOWN"
        )

        if isinstance(entry_price, (int, float)):
            entry_text = f"{entry_price:.4f}"
        else:
            entry_text = str(entry_price)

        lines.append(
            f"{symbol}\n"
            f"Side: {side}\n"
            f"Entry Price: {entry_text}\n"
            f"Status: {status}\n"
            f"Opened: {signal_time}\n"
        )

    send_message(
        "\n".join(lines)
    )