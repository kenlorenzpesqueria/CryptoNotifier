import os

import requests
from dotenv import load_dotenv

from logger import logger


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def notify(message):
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set.")
        return

    if not CHAT_ID:
        logger.error("CHAT_ID is not set.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=10,
        )

        response.raise_for_status()

        logger.info("Telegram notification sent.")

    except requests.RequestException as e:
        logger.error(
            f"Telegram notification failed: {e}"
        )


def format_ema20_alert(
    symbol,
    position,
    current_4h,
):
    side = position.get("side", "UNKNOWN")
    entry_price = position.get(
        "entry_price",
        "UNKNOWN",
    )

    entry_text = (
        f"{entry_price:.4f}"
        if isinstance(entry_price, (int, float))
        else str(entry_price)
    )

    return (
        f"⚠️ POSITION ALERT\n\n"
        f"Symbol: {symbol}\n"
        f"Position: {side}\n"
        f"Entry Price: {entry_text}\n\n"
        f"📉 4H EMA20 BREAK\n"
        f"4H Close: {current_4h['close']:.4f}\n"
        f"EMA20: {current_4h['ema20']:.4f}\n\n"
        f"The completed 4H candle "
        f"closed below EMA20.\n\n"
        f"Status: WEAKENING"
    )


def send_ema20_alert(
    symbol,
    position,
    current_4h,
):
    message = format_ema20_alert(
        symbol,
        position,
        current_4h,
    )

    notify(message)

    logger.info(
        f"{symbol} {position.get('side', 'UNKNOWN')} "
        f"EMA20 breach alert sent"
    )