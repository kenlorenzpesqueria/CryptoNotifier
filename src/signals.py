def get_signal(df_4h, df_1d):
    previous_4h = df_4h.iloc[-3]
    current_4h = df_4h.iloc[-2]
    current_1d = df_1d.iloc[-2]

    buy_ema20_cross = (
        previous_4h["close"] < previous_4h["ema20"]
        and current_4h["close"] > current_4h["ema20"]
    )

    buy_ema50_cross = (
        previous_4h["close"] < previous_4h["ema50"]
        and current_4h["close"] > current_4h["ema50"]
    )

    buy = (
        (buy_ema20_cross or buy_ema50_cross)
        and current_4h["close"] > current_4h["ema20"]
        and current_4h["close"] > current_4h["ema50"]
        and current_4h["macd_hist"] > 0
        and current_1d["close"] > current_1d["ema20"]
    )

    sell_ema20_cross = (
        previous_4h["close"] > previous_4h["ema20"]
        and current_4h["close"] < current_4h["ema20"]
    )

    sell_ema50_cross = (
        previous_4h["close"] > previous_4h["ema50"]
        and current_4h["close"] < current_4h["ema50"]
    )

    sell = (
        (sell_ema20_cross or sell_ema50_cross)
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