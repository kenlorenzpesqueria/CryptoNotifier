import time
from datetime import datetime, timezone

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

MT5_INITIALIZE_ATTEMPTS = 30
MT5_INITIALIZE_DELAY = 2

MT5_DATA_ATTEMPTS = 5
MT5_DATA_DELAY = 2


_mt5_initialized = False


def initialize_mt5():
    global _mt5_initialized

    if _mt5_initialized:
        return True

    last_error = None

    for attempt in range(1, MT5_INITIALIZE_ATTEMPTS + 1):
        if mt5.initialize():
            terminal = mt5.terminal_info()

            if terminal is not None and terminal.connected:
                account = mt5.account_info()

                if account is not None:
                    _mt5_initialized = True

                    print(
                        "MT5 initialized successfully."
                    )
                    print(
                        f"MT5 terminal: {terminal.name}"
                    )
                    print(
                        f"MT5 connected: {terminal.connected}"
                    )
                    print(
                        f"MT5 account: {account.login}"
                    )
                    print(
                        f"MT5 server: {account.server}"
                    )

                    return True

                last_error = mt5.last_error()

            else:
                last_error = mt5.last_error()

        else:
            last_error = mt5.last_error()

        print(
            f"MT5 not ready "
            f"(attempt {attempt}/{MT5_INITIALIZE_ATTEMPTS}): "
            f"{last_error}"
        )

        time.sleep(MT5_INITIALIZE_DELAY)

    raise RuntimeError(
        "MT5 terminal did not become ready after "
        f"{MT5_INITIALIZE_ATTEMPTS} attempts. "
        f"Last error: {last_error}"
    )


def shutdown_mt5():
    global _mt5_initialized

    if _mt5_initialized:
        mt5.shutdown()
        _mt5_initialized = False
        print("MT5 shutdown complete.")


def ensure_symbol(symbol):
    initialize_mt5()

    symbol_info = mt5.symbol_info(symbol)

    if symbol_info is None:
        raise RuntimeError(
            f"{symbol}: symbol not found in MT5: "
            f"{mt5.last_error()}"
        )

    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(
            f"{symbol}: unable to select symbol in MT5: "
            f"{mt5.last_error()}"
        )

    return symbol_info


def get_klines(symbol, interval, limit=1000):
    if interval not in TIMEFRAME_MAP:
        raise ValueError(
            f"Unsupported timeframe: {interval}"
        )

    initialize_mt5()
    ensure_symbol(symbol)

    timeframe = TIMEFRAME_MAP[interval]

    last_error = None

    for attempt in range(1, MT5_DATA_ATTEMPTS + 1):
        terminal = mt5.terminal_info()

        if terminal is None:
            last_error = mt5.last_error()

            print(
                f"{symbol} {interval}: "
                f"MT5 terminal unavailable "
                f"(attempt {attempt}/{MT5_DATA_ATTEMPTS}): "
                f"{last_error}"
            )

            time.sleep(MT5_DATA_DELAY)
            continue

        if not terminal.connected:
            last_error = mt5.last_error()

            print(
                f"{symbol} {interval}: "
                f"MT5 terminal disconnected "
                f"(attempt {attempt}/{MT5_DATA_ATTEMPTS}): "
                f"{last_error}"
            )

            time.sleep(MT5_DATA_DELAY)
            continue

        rates = mt5.copy_rates_from_pos(
            symbol,
            timeframe,
            0,
            limit,
        )

        if rates is not None and len(rates) > 0:
            df = pd.DataFrame(rates)

            df["open_time"] = pd.to_datetime(
                df["time"],
                unit="s",
                utc=True,
            )

            return df

        last_error = mt5.last_error()

        print(
            f"{symbol} {interval}: "
            f"MT5 data request failed "
            f"(attempt {attempt}/{MT5_DATA_ATTEMPTS}): "
            f"{last_error}"
        )

        time.sleep(MT5_DATA_DELAY)

    raise RuntimeError(
        f"{symbol}: no MT5 data returned after "
        f"{MT5_DATA_ATTEMPTS} attempts: "
        f"{last_error}"
    )


def get_last_completed_index(df, interval, symbol):
    if interval not in TIMEFRAME_SECONDS:
        raise ValueError(
            f"Unsupported timeframe: {interval}"
        )

    if df is None or len(df) == 0:
        raise ValueError(
            "No candle data available"
        )

    initialize_mt5()
    ensure_symbol(symbol)

    latest_open_time = int(
        df.iloc[-1]["time"]
    )

    timeframe_seconds = TIMEFRAME_SECONDS[interval]

    latest_close_time = (
        latest_open_time
        + timeframe_seconds
    )

    current_utc_time = int(
        datetime.now(timezone.utc).timestamp()
    )

    if latest_close_time <= current_utc_time:
        return len(df) - 1

    if len(df) < 2:
        raise RuntimeError(
            f"{symbol}: insufficient completed "
            f"candle data"
        )

    return len(df) - 2