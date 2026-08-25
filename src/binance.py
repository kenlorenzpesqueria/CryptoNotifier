import requests
import pandas as pd

BASE_URL = "https://api.bybit.com"


def get_klines(symbol, interval, limit=1000):
    url = f"{BASE_URL}/v5/market/kline"

    interval_map = {
        "4h": "240",
        "1d": "D"
    }

    if interval not in interval_map:
        raise ValueError(f"Unsupported interval: {interval}")

    params = {
        "category": "spot",
        "symbol": symbol,
        "interval": interval_map[interval],
        "limit": min(limit, 1000)
    }

    response = requests.get(
        url,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    if data.get("retCode") != 0:
        raise RuntimeError(
            f"Bybit API error: {data.get('retMsg')}"
        )

    rows = data["result"]["list"]

    if not rows:
        raise RuntimeError(f"No kline data returned for {symbol}")

    df = pd.DataFrame(rows, columns=[
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "turnover"
    ])

    df["open_time"] = pd.to_datetime(
        pd.to_numeric(df["open_time"]),
        unit="ms",
        utc=True
    )

    for column in [
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.sort_values("open_time")
    df = df.reset_index(drop=True)

    return df