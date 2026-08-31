from config import EMA_FAST, EMA_SLOW, MACD_FAST, MACD_SLOW, MACD_SIGNAL


def calculate_indicators(df):
    close = df["close"]

    df["ema20"] = close.ewm(
        span=EMA_FAST,
        adjust=False
    ).mean()

    df["ema50"] = close.ewm(
        span=EMA_SLOW,
        adjust=False
    ).mean()

    ema_fast = close.ewm(
        span=MACD_FAST,
        adjust=False
    ).mean()

    ema_slow = close.ewm(
        span=MACD_SLOW,
        adjust=False
    ).mean()

    df["macd"] = ema_fast - ema_slow

    df["macd_signal"] = df["macd"].ewm(
        span=MACD_SIGNAL,
        adjust=False
    ).mean()

    df["macd_hist"] = (
        df["macd"] - df["macd_signal"]
    )

    return df