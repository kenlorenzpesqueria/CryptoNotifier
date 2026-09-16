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
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Telegram notification sent.")
    except requests.RequestException as e:
        logger.error(f"Telegram notification failed: {e}")


def send_position_evaluation(
    symbol,
    position,
    previous_4h,
    current_4h,
    current_1d,
):
    side = position.get("side", "UNKNOWN")
    entry_price = position.get("entry_price", "UNKNOWN")
    status = position.get("status", "UNKNOWN")

    if current_4h["close"] > previous_4h["close"]:
        direction = "⬆️"
    elif current_4h["close"] < previous_4h["close"]:
        direction = "⬇️"
    else:
        direction = "➡️"

    if side == "BUY":
        price_ema20_ok = current_4h["close"] >= current_4h["ema20"]
        price_ema50_ok = current_4h["close"] >= current_4h["ema50"]
        macd_ok = current_4h["macd_hist"] >= 0
        daily_ok = current_1d["close"] >= current_1d["ema20"]
    else:
        price_ema20_ok = current_4h["close"] <= current_4h["ema20"]
        price_ema50_ok = current_4h["close"] <= current_4h["ema50"]
        macd_ok = current_4h["macd_hist"] <= 0
        daily_ok = current_1d["close"] <= current_1d["ema20"]

    entry_text = (
        f"{entry_price:.4f}"
        if isinstance(entry_price, (int, float))
        else str(entry_price)
    )

    message = (
        f"📊 POSITION EVALUATION\n\n"
        f"Symbol: {symbol}\n"
        f"Position: {side}\n"
        f"Entry Price: {entry_text}\n\n"
        f"💰 CURRENT PRICE\n"
        f"4H Close: {current_4h['close']:.4f} {direction}\n"
        f"Previous 4H Close: {previous_4h['close']:.4f}\n\n"
        f"📊 4H INDICATORS\n"
        f"EMA20: {current_4h['ema20']:.4f}\n"
        f"EMA50: {current_4h['ema50']:.4f}\n"
        f"MACD: {current_4h['macd']:.4f}\n"
        f"Signal: {current_4h['macd_signal']:.4f}\n"
        f"Histogram: {current_4h['macd_hist']:.4f}\n\n"
        f"📈 1D INDICATORS\n"
        f"Close: {current_1d['close']:.4f}\n"
        f"EMA20: {current_1d['ema20']:.4f}\n\n"
        f"📋 POSITION CHECK\n"
        f"{'✅' if price_ema20_ok else '❌'} "
        f"4H Price vs EMA20\n"
        f"{'✅' if price_ema50_ok else '❌'} "
        f"4H Price vs EMA50\n"
        f"{'✅' if macd_ok else '❌'} "
        f"4H MACD Histogram vs 0\n"
        f"{'✅' if daily_ok else '❌'} "
        f"1D Close vs EMA20\n\n"
        f"Status: {status}"
    )

    notify(message)

    logger.info(
        f"{symbol} {side} position evaluation sent"
    )