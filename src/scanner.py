import json
from datetime import datetime, timedelta, timezone

from binance import get_klines
from config import CANDLE_LIMIT
from indicators import calculate_indicators
from signals import get_signal
from telegram_sender import notify, send_ema20_alert
from positions import (
    get_position,
    check_ema20_breach,
    get_signal_tracking,
    save_signal_tracking,
    clear_signal_tracking,
    load_positions,
)
from logger import logger


def load_watchlist():
    with open(
        "data/watchlist.json",
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def normalize_datetime(value):
    if value is None:
        return None

    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)

    if isinstance(value, str):
        value = value.strip()

        try:
            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError:
            parsed = datetime.strptime(
                value,
                "%Y-%m-%d %H:%M"
            )

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed.astimezone(timezone.utc)

    if isinstance(value, (int, float)):
        if value > 100000000000:
            value = value / 1000

        return datetime.fromtimestamp(
            value,
            tz=timezone.utc,
        )

    return None


def buy_confirmation_passes(
    current_4h,
    current_1d,
):
    return (
        current_4h["close"] > current_4h["ema20"]
        and current_4h["close"] > current_4h["ema50"]
        and current_4h["macd"] > 0
        and current_1d["close"] > current_1d["ema20"]
    )


def buy_has_improved(
    current_4h,
    tracking,
):
    return (
        current_4h["close"] > tracking["signal_close"]
        and current_4h["macd"] > tracking["signal_macd"]
    )


def run_scan():
    watchlist = load_watchlist()
    active_positions = load_positions()

    active_positions = {
        symbol: position
        for symbol, position in active_positions.items()
        if position.get("side") in ("BUY", "SELL")
    }

    symbols = list(
        dict.fromkeys(
            watchlist + list(active_positions.keys())
        )
    )

    results = []

    logger.info(
        f"Scanning {len(symbols)} symbols"
    )

    print(
        f"Watching {len(symbols)} coins\n"
    )

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

            current_h4_time = normalize_datetime(
                current_4h.get("open_time")
            )

            print(
                f"4H Candle: {current_h4_time}"
            )
            print(
                f"4H Close : {current_4h['close']}"
            )
            print(
                f"4H EMA20 : "
                f"{current_4h['ema20']:.4f}"
            )
            print(
                f"4H EMA50 : "
                f"{current_4h['ema50']:.4f}"
            )
            print(
                f"1D Close : "
                f"{current_1d['close']:.4f}"
            )
            print(
                f"1D EMA20 : "
                f"{current_1d['ema20']:.4f}"
            )
            print(
                f"MACD     : "
                f"{current_4h['macd']:.4f}"
            )
            print(
                f"Signal   : "
                f"{current_4h['macd_signal']:.4f}"
            )
            print(
                f"Histogram: "
                f"{current_4h['macd_hist']:.4f}"
            )

            position = get_position(symbol)

            # ==================================================
            # ACTIVE POSITION MONITORING
            # ==================================================

            if position:
                side = position.get(
                    "side",
                    "UNKNOWN",
                )

                ema20_breached = check_ema20_breach(
                    symbol,
                    side,
                    current_4h,
                )

                updated_position = get_position(
                    symbol
                )

                if updated_position is None:
                    print(
                        "Position no longer exists."
                    )
                    continue

                position = updated_position

                if ema20_breached:
                    send_ema20_alert(
                        symbol,
                        position,
                        current_4h,
                    )

                    logger.warning(
                        f"{symbol} {side} position "
                        f"closed below EMA20"
                    )

                    print(
                        "⚠️ Position closed below EMA20"
                    )
                else:
                    print(
                        "No EMA20 breach alert."
                    )

                position_status = position.get(
                    "status",
                    "UNKNOWN",
                )

                results.append({
                    "symbol": symbol,
                    "signal": None,
                    "price": float(
                        current_4h["close"]
                    ),
                    "ema20_4h": float(
                        current_4h["ema20"]
                    ),
                    "ema50_4h": float(
                        current_4h["ema50"]
                    ),
                    "ema20_1d": float(
                        current_1d["ema20"]
                    ),
                    "macd": float(
                        current_4h["macd"]
                    ),
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
                    "position": side,
                    "position_status": position_status,
                })

                print(
                    f"Position: {position_status}"
                )
                print("Trade : NONE")
                print()

                continue

            # ==================================================
            # BUY SIGNAL TRACKING
            # ==================================================

            tracking = get_signal_tracking(
                symbol
            )

            confirmation_checked = False
            confirmation_signal = False
            send_new_signal = False
            trigger_type = None

            if tracking:
                tracking_time = normalize_datetime(
                    tracking.get("signal_time")
                )

                if (
                    current_h4_time is not None
                    and tracking_time is not None
                ):
                    expected_confirmation_time = (
                        tracking_time
                        + timedelta(hours=4)
                    )

                    if (
                        current_h4_time
                        == expected_confirmation_time
                    ):
                        confirmation_checked = True

                        if tracking.get("side") == "BUY":
                            confirmation_passes = (
                                buy_confirmation_passes(
                                    current_4h,
                                    current_1d,
                                )
                            )

                            improved = (
                                buy_has_improved(
                                    current_4h,
                                    tracking,
                                )
                            )

                            if (
                                confirmation_passes
                                and improved
                            ):
                                send_new_signal = True
                                confirmation_signal = True

                            clear_signal_tracking(
                                symbol
                            )

                            if (
                                confirmation_passes
                                and improved
                            ):
                                logger.info(
                                    f"{symbol} BUY "
                                    f"confirmation passed"
                                )
                            else:
                                logger.info(
                                    f"{symbol} BUY "
                                    f"confirmation failed "
                                    f"and tracking cleared"
                                )

                        else:
                            clear_signal_tracking(
                                symbol
                            )

                    elif (
                        current_h4_time
                        > expected_confirmation_time
                    ):
                        clear_signal_tracking(
                            symbol
                        )

                        logger.info(
                            f"{symbol} stale signal "
                            f"tracking cleared"
                        )

                    elif (
                        current_h4_time
                        < expected_confirmation_time
                    ):
                        print(
                            "Signal tracking waiting "
                            "for next completed "
                            "4H candle"
                        )

                else:
                    clear_signal_tracking(
                        symbol
                    )

                    logger.info(
                        f"{symbol} invalid signal "
                        f"tracking cleared"
                    )

            signal = None

            if not confirmation_checked:
                signal = get_signal(
                    df_4h,
                    df_1d,
                )

            buy_ema20_cross = (
                previous_4h["close"]
                < previous_4h["ema20"]
                and current_4h["close"]
                > current_4h["ema20"]
            )

            buy_ema50_cross = (
                previous_4h["close"]
                < previous_4h["ema50"]
                and current_4h["close"]
                > current_4h["ema50"]
            )

            buy_conditions = {
                "EMA20 crossover up":
                    buy_ema20_cross,
                "EMA50 crossover up":
                    buy_ema50_cross,
                "4H close above EMA20":
                    current_4h["close"]
                    > current_4h["ema20"],
                "4H close above EMA50":
                    current_4h["close"]
                    > current_4h["ema50"],
                "4H MACD above 0":
                    current_4h["macd"] > 0,
                "1D close above EMA20":
                    current_1d["close"]
                    > current_1d["ema20"],
            }

            if confirmation_signal:
                signal_type = "BUY"

                conditions = {
                    "4H close above EMA20":
                        current_4h["close"]
                        > current_4h["ema20"],
                    "4H close above EMA50":
                        current_4h["close"]
                        > current_4h["ema50"],
                    "4H MACD above 0":
                        current_4h["macd"] > 0,
                    "1D close above EMA20":
                        current_1d["close"]
                        > current_1d["ema20"],
                }

            elif signal == "BUY":
                signal_type = "BUY"
                conditions = buy_conditions

                if (
                    buy_ema20_cross
                    and buy_ema50_cross
                ):
                    trigger_type = (
                        "EMA20 + EMA50 CROSSOVER"
                    )
                elif buy_ema20_cross:
                    trigger_type = (
                        "EMA20 CROSSOVER"
                    )
                elif buy_ema50_cross:
                    trigger_type = (
                        "EMA50 CROSSOVER"
                    )

                send_new_signal = True

            else:
                signal_type = None
                conditions = None

            results.append({
                "symbol": symbol,
                "signal": signal,
                "price": float(
                    current_4h["close"]
                ),
                "ema20_4h": float(
                    current_4h["ema20"]
                ),
                "ema50_4h": float(
                    current_4h["ema50"]
                ),
                "ema20_1d": float(
                    current_1d["ema20"]
                ),
                "macd": float(
                    current_4h["macd"]
                ),
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

            if (
                send_new_signal
                and signal_type
            ):
                condition_text = "\n".join(
                    f"{'✅' if value else '❌'} {name}"
                    for name, value
                    in conditions.items()
                )

                if confirmation_signal:
                    signal_title = (
                        "🚨 BUY CONFIRMATION"
                    )

                    trigger_text = (
                        "Trigger: Previous BUY "
                        "signal confirmation"
                    )
                else:
                    signal_title = (
                        f"🚨 {signal_type} SIGNAL"
                    )

                    trigger_text = (
                        f"Trigger: {trigger_type}"
                        if trigger_type
                        else "Trigger: EMA crossover"
                    )

                message = (
                    f"{signal_title}\n\n"
                    f"Symbol: {symbol}\n"
                    f"{trigger_text}\n\n"
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
                    f"🎯 Recommendation: "
                    f"{signal_type}"
                )

                notify(message)

                logger.info(
                    f"{symbol} {signal_type}"
                    f"{' confirmation' if confirmation_signal else ''}"
                )

                print(
                    f"Trade : {signal_type}"
                    f"{' CONFIRMATION' if confirmation_signal else ''}"
                )

                if (
                    signal_type == "BUY"
                    and not confirmation_signal
                ):
                    save_signal_tracking(
                        symbol,
                        "BUY",
                        current_4h["close"],
                        current_4h["macd"],
                        current_h4_time,
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