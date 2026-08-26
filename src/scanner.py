import json

from binance import get_klines
from config import CANDLE_LIMIT
from indicators import calculate_indicators
from signals import get_signal
from telegram_sender import notify
from positions import (
    should_send,
    update_position,
    get_position,
    evaluate_position
)
from logger import logger


def load_watchlist():
    with open("data/watchlist.json", "r") as f:
        return json.load(f)


def run_scan():
    symbols = load_watchlist()

    logger.info(f"Scanning {len(symbols)} symbols")
    print(f"Watching {len(symbols)} coins\n")

    errors = []

    for symbol in symbols:
        print(f"Scanning {symbol}...")

        try:
            df_4h = get_klines(symbol, "4h", CANDLE_LIMIT)
            df_1d = get_klines(symbol, "1d", CANDLE_LIMIT)

            df_4h = calculate_indicators(df_4h)
            df_1d = calculate_indicators(df_1d)

            signal = get_signal(df_4h, df_1d)

            previous_4h = df_4h.iloc[-3]
            current_4h = df_4h.iloc[-2]
            current_1d = df_1d.iloc[-2]

            buy_conditions = {
                "Previous 4H close below EMA20":
                    previous_4h["close"] < previous_4h["ema20"],
                "Current 4H close above EMA20":
                    current_4h["close"] > current_4h["ema20"],
                "Current 4H close above EMA50":
                    current_4h["close"] > current_4h["ema50"],
                "4H MACD above 0":
                    current_4h["macd"] > 0,
                "1D close above EMA20":
                    current_1d["close"] > current_1d["ema20"]
            }

            sell_conditions = {
                "Previous 4H close above EMA20":
                    previous_4h["close"] > previous_4h["ema20"],
                "Current 4H close below EMA20":
                    current_4h["close"] < current_4h["ema20"],
                "Current 4H close below EMA50":
                    current_4h["close"] < current_4h["ema50"],
                "4H MACD below 0":
                    current_4h["macd"] < 0,
                "1D close below EMA20":
                    current_1d["close"] < current_1d["ema20"]
            }

            print(f"4H Close : {current_4h['close']}")
            print(f"4H EMA20 : {current_4h['ema20']:.4f}")
            print(f"4H EMA50 : {current_4h['ema50']:.4f}")
            print(f"1D Close : {current_1d['close']:.4f}")
            print(f"1D EMA20 : {current_1d['ema20']:.4f}")
            print(f"MACD     : {current_4h['macd']:.4f}")
            print(f"Signal   : {current_4h['macd_signal']:.4f}")

            position = get_position(symbol)

            if position:
                status = evaluate_position(
                    symbol,
                    position["side"],
                    current_4h
                )

                if status == "WEAKENING":
                    if position["side"] == "BUY":
                        price_ok = current_4h["close"] >= current_4h["ema20"]
                        macd_ok = current_4h["macd"] >= 0
                    else:
                        price_ok = current_4h["close"] <= current_4h["ema20"]
                        macd_ok = current_4h["macd"] <= 0

                    message = (
                        f"⚠️ POSITION WEAKENING\n\n"
                        f"Symbol: {symbol}\n"
                        f"Position: {position['side']}\n\n"
                        f"💰 Price: {current_4h['close']:.4f}\n"
                        f"📊 EMA20: {current_4h['ema20']:.4f}\n"
                        f"📈 EMA50: {current_4h['ema50']:.4f}\n"
                        f"MACD: {current_4h['macd']:.4f}\n"
                        f"Signal: {current_4h['macd_signal']:.4f}\n\n"
                        f"{'✅' if price_ok else '❌'} Price vs EMA20\n"
                        f"{'✅' if macd_ok else '❌'} MACD vs 0\n\n"
                        f"⚠️ Review your {position['side']} position."
                    )

                    notify(message)
                    logger.warning(
                        f"{symbol} {position['side']} position weakening"
                    )
                    print("Position: WEAKENING")

                elif status == "HEALTHY":
                    print("Position: HEALTHY")
                else:
                    print(f"Position: {position['status']}")

            if signal and should_send(symbol, signal):
                conditions = (
                    buy_conditions
                    if signal == "BUY"
                    else sell_conditions
                )

                condition_text = "\n".join(
                    f"{'✅' if value else '❌'} {name}"
                    for name, value in conditions.items()
                )

                message = (
                    f"🚨 {signal} SIGNAL\n\n"
                    f"Symbol: {symbol}\n\n"
                    f"💰 Price: {current_4h['close']:.4f}\n\n"
                    f"📊 4H CONDITIONS\n"
                    f"{condition_text}\n\n"
                    f"📈 INDICATORS\n"
                    f"4H EMA20: {current_4h['ema20']:.4f}\n"
                    f"4H EMA50: {current_4h['ema50']:.4f}\n"
                    f"1D Close: {current_1d['close']:.4f}\n"
                    f"1D EMA20: {current_1d['ema20']:.4f}\n"
                    f"MACD: {current_4h['macd']:.4f}\n"
                    f"Signal: {current_4h['macd_signal']:.4f}\n\n"
                    f"🎯 Recommendation: {signal}"
                )

                update_position(
                    symbol,
                    signal,
                    current_4h["close"]
                )

                notify(message)
                logger.info(f"{symbol} {signal}")
                print(f"Trade : {signal}")
            else:
                print("Trade : NONE")

            print()

        except Exception as e:
            errors.append(f"{symbol}: {e}")
            logger.exception(symbol)
            print(f"{symbol}: {e}\n")

    if errors:
        message = (
            "🚨 CRYPTONOTIFIER ERROR\n\n"
            + "\n".join(errors)
        )
        notify(message)