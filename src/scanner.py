import json

from binance import get_klines
from config import CANDLE_LIMIT
from indicators import calculate_indicators
from signals import get_signal
from telegram_sender import notify
from positions import (
    get_position,
    evaluate_position,
    get_signal_tracking,
    save_signal_tracking,
    clear_signal_tracking,
    load_positions,
)
from logger import logger


def load_watchlist():
    with open("data/watchlist.json", "r") as f:
        return json.load(f)


def buy_confirmation_passes(current_4h, current_1d):
    return (
        current_4h["close"] > current_4h["ema20"]
        and current_4h["close"] > current_4h["ema50"]
        and current_4h["macd_hist"] > 0
        and current_1d["close"] > current_1d["ema20"]
    )


def buy_has_improved(current_4h, tracking):
    return (
        current_4h["close"] > tracking["signal_close"]
        and current_4h["macd_hist"] > tracking["signal_macd_hist"]
    )


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


def run_scan():
    watchlist = load_watchlist()
    active_positions = load_positions()

    active_positions = {
        symbol: position
        for symbol, position in active_positions.items()
        if position.get("side") in ("BUY", "SELL")
    }

    symbols = list(dict.fromkeys(
        watchlist + list(active_positions.keys())
    ))

    results = []

    logger.info(f"Scanning {len(symbols)} symbols")
    print(f"Watching {len(symbols)} coins\n")

    errors = []

    for symbol in symbols:
        print(f"Scanning {symbol}...")

        try:
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

            print(
                f"4H Close : {current_4h['close']}"
            )
            print(
                f"4H EMA20 : {current_4h['ema20']:.4f}"
            )
            print(
                f"4H EMA50 : {current_4h['ema50']:.4f}"
            )
            print(
                f"1D Close : {current_1d['close']:.4f}"
            )
            print(
                f"1D EMA20 : {current_1d['ema20']:.4f}"
            )
            print(
                f"MACD     : {current_4h['macd']:.4f}"
            )
            print(
                f"Signal   : {current_4h['macd_signal']:.4f}"
            )
            print(
                f"Histogram: {current_4h['macd_hist']:.4f}"
            )

            position = get_position(symbol)
            position_status = None

            if position:
                status = evaluate_position(
                    symbol,
                    position["side"],
                    current_4h,
                    current_1d,
                )

                updated_position = get_position(symbol)

                if updated_position is None:
                    print("Position no longer exists.")
                    continue

                position = updated_position
                position_status = position.get(
                    "status",
                    "UNKNOWN",
                )

                send_position_evaluation(
                    symbol,
                    position,
                    previous_4h,
                    current_4h,
                    current_1d,
                )

                if status == "WEAKENING":
                    logger.warning(
                        f"{symbol} {position['side']} "
                        f"position weakening"
                    )

                print(
                    f"Position: {position_status}"
                )

                clear_signal_tracking(symbol)

                results.append({
                    "symbol": symbol,
                    "signal": None,
                    "price": float(current_4h["close"]),
                    "ema20_4h": float(current_4h["ema20"]),
                    "ema50_4h": float(current_4h["ema50"]),
                    "ema20_1d": float(current_1d["ema20"]),
                    "macd": float(current_4h["macd"]),
                    "macd_signal": float(
                        current_4h["macd_signal"]
                    ),
                    "macd_hist": float(
                        current_4h["macd_hist"]
                    ),
                    "previous_4h_close": float(
                        previous_4h["close"]
                    ),
                    "daily_close": float(
                        current_1d["close"]
                    ),
                    "position": position["side"],
                    "position_status": position_status,
                })

                print("Trade : NONE")
                print()

                continue

            signal = get_signal(
                df_4h,
                df_1d,
            )

            buy_conditions = {
                "Previous 4H close below EMA20":
                    previous_4h["close"] < previous_4h["ema20"],
                "Current 4H close above EMA20":
                    current_4h["close"] > current_4h["ema20"],
                "Current 4H close above EMA50":
                    current_4h["close"] > current_4h["ema50"],
                "4H MACD Histogram above 0":
                    current_4h["macd_hist"] > 0,
                "1D close above EMA20":
                    current_1d["close"] > current_1d["ema20"],
            }

            sell_conditions = {
                "Previous 4H close above EMA20":
                    previous_4h["close"] > previous_4h["ema20"],
                "Current 4H close below EMA20":
                    current_4h["close"] < current_4h["ema20"],
                "Current 4H close below EMA50":
                    current_4h["close"] < current_4h["ema50"],
                "4H MACD Histogram below 0":
                    current_4h["macd_hist"] < 0,
                "1D close below EMA20":
                    current_1d["close"] < current_1d["ema20"],
            }

            results.append({
                "symbol": symbol,
                "signal": signal,
                "price": float(current_4h["close"]),
                "ema20_4h": float(current_4h["ema20"]),
                "ema50_4h": float(current_4h["ema50"]),
                "ema20_1d": float(current_1d["ema20"]),
                "macd": float(current_4h["macd"]),
                "macd_signal": float(
                    current_4h["macd_signal"]
                ),
                "macd_hist": float(
                    current_4h["macd_hist"]
                ),
                "previous_4h_close": float(
                    previous_4h["close"]
                ),
                "daily_close": float(
                    current_1d["close"]
                ),
                "position": None,
                "position_status": None,
            })

            tracking = get_signal_tracking(symbol)

            send_new_signal = False
            confirmation_signal = False

            if signal == "BUY":
                if tracking and tracking.get("side") == "BUY":
                    confirmation_passes = (
                        buy_confirmation_passes(
                            current_4h,
                            current_1d,
                        )
                    )

                    improved = buy_has_improved(
                        current_4h,
                        tracking,
                    )

                    if confirmation_passes and improved:
                        send_new_signal = True
                        confirmation_signal = True
                else:
                    send_new_signal = True

            elif signal == "SELL":
                if tracking and tracking.get("side") == "SELL":
                    send_new_signal = False
                else:
                    send_new_signal = True

            if send_new_signal:
                conditions = (
                    buy_conditions
                    if signal == "BUY"
                    else sell_conditions
                )

                condition_text = "\n".join(
                    f"{'✅' if value else '❌'} {name}"
                    for name, value in conditions.items()
                )

                if confirmation_signal:
                    signal_title = "🚨 BUY CONFIRMATION"
                else:
                    signal_title = f"🚨 {signal} SIGNAL"

                message = (
                    f"{signal_title}\n\n"
                    f"Symbol: {symbol}\n\n"
                    f"💰 Price: "
                    f"{current_4h['close']:.4f}\n\n"
                    f"📊 4H CONDITIONS\n"
                    f"{condition_text}\n\n"
                    f"📈 INDICATORS\n"
                    f"4H EMA20: "
                    f"{current_4h['ema20']:.4f}\n"
                    f"4H EMA50: "
                    f"{current_4h['ema50']:.4f}\n"
                    f"1D Close: "
                    f"{current_1d['close']:.4f}\n"
                    f"1D EMA20: "
                    f"{current_1d['ema20']:.4f}\n"
                    f"MACD: "
                    f"{current_4h['macd']:.4f}\n"
                    f"Signal: "
                    f"{current_4h['macd_signal']:.4f}\n"
                    f"Histogram: "
                    f"{current_4h['macd_hist']:.4f}\n\n"
                    f"🎯 Recommendation: {signal}"
                )

                notify(message)

                logger.info(
                    f"{symbol} {signal}"
                    f"{' confirmation' if confirmation_signal else ''}"
                )

                print(
                    f"Trade : {signal}"
                    f"{' CONFIRMATION' if confirmation_signal else ''}"
                )

                if signal == "BUY":
                    save_signal_tracking(
                        symbol,
                        "BUY",
                        current_4h["close"],
                        current_4h["macd_hist"],
                    )

            else:
                if (
                    tracking
                    and tracking.get("side") == "BUY"
                ):
                    print("Trade : NONE")
                    print(
                        "BUY setup waiting for improvement"
                    )
                else:
                    print("Trade : NONE")

            print()

        except Exception as e:
            errors.append(
                f"{symbol}: {e}"
            )

            logger.exception(symbol)

            print(
                f"{symbol}: {e}\n"
            )

    if errors:
        message = (
            "🚨 CRYPTONOTIFIER ERROR\n\n"
            + "\n".join(errors)
        )

        notify(message)

    return results