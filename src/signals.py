def get_signal(previous_4h, current_4h, current_1d):
    buy = (
        previous_4h["close"] < previous_4h["ema20"]
        and current_4h["close"] > current_4h["ema20"]
        and current_4h["close"] > current_4h["ema50"]
        and current_4h["macd_hist"] > 0
        and current_1d["close"] > current_1d["ema20"]
    )

    sell = (
        previous_4h["close"] > previous_4h["ema20"]
        and current_4h["close"] < current_4h["ema20"]
        and current_4h["close"] < current_4h["ema50"]
        and current_4h["macd_hist"] < 0
        and current_1d["close"] < current_1d["ema20"]
    )

    if buy:
        return "BUY"

    if sell:
        return "SELL"

    return None