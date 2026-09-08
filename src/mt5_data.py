import MetaTrader5 as mt5
import pandas as pd

TIMEFRAME_MAP = {
    "4h": mt5.TIMEFRAME_H4,
    "1d": mt5.TIMEFRAME_D1,
}

TIMEFRAME_SECONDS = {
    "4h": 4 * 60 * 60,
    "1d": 24 * 60 * 60,
}


def initialize_mt5():
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")


def get_klines(symbol, interval, limit=1000):
    if interval not in TIMEFRAME_MAP:
        raise ValueError(f"Unsupported timeframe: {interval}")

    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")

    timeframe = TIMEFRAME_MAP[interval]

    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(
            f"{symbol}: unable to select symbol in MT5"
        )

    rates = mt5.copy_rates_from_pos(
        symbol,
        timeframe,
        0,
        limit,
    )

    if rates is None or len(rates) == 0:
        raise RuntimeError(
            f"{symbol}: no MT5 data returned: {mt5.last_error()}"
        )

    df = pd.DataFrame(rates)

    df["open_time"] = pd.to_datetime(
        df["time"],
        unit="s",
        utc=True,
    )

    return df


def get_last_completed_index(df, interval, symbol):
    if interval not in TIMEFRAME_SECONDS:
        raise ValueError(f"Unsupported timeframe: {interval}")

    if df is None or len(df) == 0:
        raise ValueError("No candle data available")

    tick = mt5.symbol_info_tick(symbol)

    if tick is None:
        raise RuntimeError(
            f"{symbol}: unable to retrieve MT5 tick time"
        )

    current_mt5_time = int(tick.time)

    latest_open_time = int(df.iloc[-1]["time"])
    timeframe_seconds = TIMEFRAME_SECONDS[interval]
    latest_close_time = latest_open_time + timeframe_seconds

    if latest_close_time <= current_mt5_time:
        return len(df) - 1

    if len(df) < 2:
        raise RuntimeError(
            f"{symbol}: insufficient completed candle data"
        )

    return len(df) - 2