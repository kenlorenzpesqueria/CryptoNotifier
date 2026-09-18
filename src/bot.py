import requests

from google.cloud import firestore

from config import BOT_TOKEN, CHAT_ID, CANDLE_LIMIT
from binance import get_klines
from indicators import calculate_indicators
from positions import (
    update_position,
    close_position,
    load_positions,
    get_position,
    evaluate_position,
)
from telegram_sender import (
    format_position_evaluation,
)


db = firestore.Client(project="cryptonotifier-503415")

TELEGRAM_STATE_COLLECTION = "bot_state"
TELEGRAM_STATE_DOCUMENT = "telegram"


def load_offset():
    doc = (
        db.collection(TELEGRAM_STATE_COLLECTION)
        .document(TELEGRAM_STATE_DOCUMENT)
        .get()
    )

    if not doc.exists:
        return None

    return doc.to_dict().get("offset")


def save_offset(offset):
    (
        db.collection(TELEGRAM_STATE_COLLECTION)
        .document(TELEGRAM_STATE_DOCUMENT)
        .set(
            {
                "offset": offset
            },
            merge=True,
        )
    )


def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": text,
        },
        timeout=10,
    )

    response.raise_for_status()


def check_telegram():
    offset = load_offset()

    params = {
        "timeout": 5,
        "allowed_updates": ["message"],
    }

    if offset is not None:
        params["offset"] = offset

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

    response = requests.get(
        url,
        params=params,
        timeout=15,
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
        price,
    )

    send_message(
        f"POSITION RECORDED\n\n"
        f"Symbol: {symbol}\n"
        f"Side: {side}\n"
        f"Entry Price: {price:.4f}\n"
        f"Status: HEALTHY\n\n"
        f"CryptoNotifier will evaluate this "
        f"position every 4 hours."
    )


def evaluate_current_position(symbol, position):
    df_4h = get_klines(
        symbol,
        "4h",
        CANDLE_LIMIT,
    )

    df_1d = get_klines(
        symbol,
        "1d",
        CANDLE_LIMIT,
    )

    df_4h = calculate_indicators(df_4h)
    df_1d = calculate_indicators(df_1d)

    previous_4h = df_4h.iloc[-3]
    current_4h = df_4h.iloc[-2]
    current_1d = df_1d.iloc[-2]

    evaluate_position(
        symbol,
        position["side"],
        current_4h,
        current_1d,
    )

    updated_position = get_position(symbol)

    if updated_position is None:
        return None

    return {
        "position": updated_position,
        "previous_4h": previous_4h,
        "current_4h": current_4h,
        "current_1d": current_1d,
    }


def send_positions():
    positions = load_positions()

    positions = {
        symbol: position
        for symbol, position in positions.items()
        if position.get("side") in ("BUY", "SELL")
    }

    if not positions:
        send_message("NO ACTIVE POSITIONS")
        return

    messages = []

    for symbol, position in positions.items():
        try:
            evaluation = evaluate_current_position(
                symbol,
                position,
            )

            if evaluation is None:
                continue

            position = evaluation["position"]
            previous_4h = evaluation["previous_4h"]
            current_4h = evaluation["current_4h"]
            current_1d = evaluation["current_1d"]

            message = format_position_evaluation(
                symbol,
                position,
                previous_4h,
                current_4h,
                current_1d,
            )

            messages.append(message)

        except Exception as e:
            messages.append(
                f"📊 POSITION EVALUATION\n\n"
                f"Symbol: {symbol}\n"
                f"Position: "
                f"{position.get('side', 'UNKNOWN')}\n"
                f"Status: EVALUATION ERROR\n"
                f"Error: {e}"
            )

    if messages:
        send_message(
            "\n\n".join(messages)
        )