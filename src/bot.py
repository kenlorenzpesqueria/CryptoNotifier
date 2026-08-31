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
    """
    Check Telegram for pending messages.

    Messages are NOT rejected based on age.
    Any unacknowledged Telegram update will be processed
    on the next scanner execution.

    The update_id is saved after processing so the same
    Telegram message is not processed again.
    """

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

        # Ignore updates that are not messages
        if not message:
            save_offset(update_id + 1)
            continue

        chat_id = str(
            message.get("chat", {}).get("id")
        )

        # Ignore messages from other chats
        if chat_id != str(CHAT_ID):
            save_offset(update_id + 1)
            continue

        text = message.get("text", "").strip()

        # Ignore empty messages
        if not text:
            save_offset(update_id + 1)
            continue

        print(
            f"Processing Telegram message "
            f"(update_id={update_id}): {text}"
        )

        try:
            process_command(text)

            # Acknowledge this Telegram update only after
            # successfully processing the command.
            save_offset(update_id + 1)

            print(
                f"Telegram update {update_id} acknowledged."
            )

        except Exception as e:
            print(
                f"Failed to process Telegram update "
                f"{update_id}: {e}"
            )

            # IMPORTANT:
            # Do NOT advance the offset if processing failed.
            #
            # This allows the message to be retried on
            # the next Cloud Run execution.

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

    # -----------------------------------------
    # CLOSE POSITION
    # /position BTCUSDT CLOSE
    # -----------------------------------------

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

    # -----------------------------------------
    # POSITION FORMAT CHECK
    # -----------------------------------------

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

    # -----------------------------------------
    # CHECK BUY / SELL
    # -----------------------------------------

    if side not in ("BUY", "SELL"):

        send_message(
            "Invalid position side.\n\n"
            "Use BUY or SELL.\n\n"
            "Example:\n"
            "/position BTCUSDT BUY 80457.60"
        )

        return

    # -----------------------------------------
    # CHECK ENTRY PRICE
    # -----------------------------------------

    try:

        price = float(parts[3])

    except ValueError:

        send_message(
            "Invalid entry price.\n\n"
            "Example:\n"
            "/position BTCUSDT BUY 80457.60"
        )

        return

    # -----------------------------------------
    # SAVE POSITION
    # -----------------------------------------

    update_position(
        symbol,
        side,
        price
    )

    # -----------------------------------------
    # CONFIRMATION
    # -----------------------------------------

    send_message(
        f"POSITION RECORDED\n\n"
        f"Symbol: {symbol}\n"
        f"Side: {side}\n"
        f"Entry: {price:.4f}\n\n"
        f"CryptoNotifier will monitor this "
        f"position on the next scan."
    )


def send_positions():

    positions = load_positions()

    if not positions:

        send_message(
            "No active positions recorded."
        )

        return

    lines = [
        "ACTIVE POSITIONS\n"
    ]

    for symbol, position in positions.items():

        lines.append(
            f"{symbol}\n"
            f"Side: {position.get('side', 'UNKNOWN')}\n"
            f"Entry: {position.get('entry_price', 'UNKNOWN')}\n"
            f"Status: {position.get('status', 'UNKNOWN')}\n"
        )

    send_message(
        "\n".join(lines)
    )