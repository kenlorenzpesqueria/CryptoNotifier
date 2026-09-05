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

    lines = [
        "📊 ACTIVE POSITION EVALUATION",
        "",
    ]

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

            entry_price = position.get(
                "entry_price",
                "UNKNOWN",
            )

            signal_time = position.get(
                "signal_time",
                "UNKNOWN",
            )

            side = position.get(
                "side",
                "UNKNOWN",
            )

            status = position.get(
                "status",
                "UNKNOWN",
            )

            if isinstance(entry_price, (int, float)):
                entry_text = f"{entry_price:.4f}"
            else:
                entry_text = str(entry_price)

            if current_4h["close"] > previous_4h["close"]:
                direction = "⬆️"
            elif current_4h["close"] < previous_4h["close"]:
                direction = "⬇️"
            else:
                direction = "➡️"

            if side == "BUY":
                price_ema20_ok = (
                    current_4h["close"]
                    >= current_4h["ema20"]
                )

                price_ema50_ok = (
                    current_4h["close"]
                    >= current_4h["ema50"]
                )

                macd_ok = (
                    current_4h["macd_hist"] >= 0
                )

                daily_ok = (
                    current_1d["close"]
                    >= current_1d["ema20"]
                )

            else:
                price_ema20_ok = (
                    current_4h["close"]
                    <= current_4h["ema20"]
                )

                price_ema50_ok = (
                    current_4h["close"]
                    <= current_4h["ema50"]
                )

                macd_ok = (
                    current_4h["macd_hist"] <= 0
                )

                daily_ok = (
                    current_1d["close"]
                    <= current_1d["ema20"]
                )

            lines.extend(
                [
                    f"{'🟢' if side == 'BUY' else '🔴'} {symbol}",
                    f"Position: {side}",
                    f"Entry Price: {entry_text}",
                    f"Opened: {signal_time}",
                    f"Status: {status}",
                    "",
                    "💰 CURRENT PRICE",
                    f"4H Close: "
                    f"{current_4h['close']:.4f} "
                    f"{direction}",
                    f"Previous 4H Close: "
                    f"{previous_4h['close']:.4f}",
                    "",
                    "📊 4H INDICATORS",
                    f"EMA20: "
                    f"{current_4h['ema20']:.4f}",
                    f"EMA50: "
                    f"{current_4h['ema50']:.4f}",
                    f"MACD: "
                    f"{current_4h['macd']:.4f}",
                    f"Signal: "
                    f"{current_4h['macd_signal']:.4f}",
                    f"Histogram: "
                    f"{current_4h['macd_hist']:.4f}",
                    "",
                    "📈 1D INDICATORS",
                    f"Close: "
                    f"{current_1d['close']:.4f}",
                    f"EMA20: "
                    f"{current_1d['ema20']:.4f}",
                    "",
                    "📋 POSITION CHECK",
                    f"{'✅' if price_ema20_ok else '❌'} "
                    f"4H Price vs EMA20",
                    f"{'✅' if price_ema50_ok else '❌'} "
                    f"4H Price vs EMA50",
                    f"{'✅' if macd_ok else '❌'} "
                    f"4H MACD Histogram vs 0",
                    f"{'✅' if daily_ok else '❌'} "
                    f"1D Close vs EMA20",
                    "",
                ]
            )

        except Exception as e:
            lines.extend(
                [
                    f"{symbol}",
                    f"Side: {position.get('side', 'UNKNOWN')}",
                    "Status: EVALUATION ERROR",
                    f"Error: {e}",
                    "",
                ]
            )

    send_message(
        "\n".join(lines)
    )