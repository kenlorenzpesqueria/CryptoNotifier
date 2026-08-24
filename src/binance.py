import requests
import pandas as pd

BASE_URL="https://api.binance.com"

def get_klines(symbol,interval,limit):
    url=f"{BASE_URL}/api/v3/klines"
    params={
        "symbol":symbol,
        "interval":interval,
        "limit":limit
    }
    response=requests.get(url,params=params,timeout=10)
    response.raise_for_status()
    df=pd.DataFrame(response.json(),columns=[
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_asset_volume",
        "trades",
        "taker_buy_base",
        "taker_buy_quote",
        "ignore"
    ])
    for column in ["open","high","low","close","volume"]:
        df[column]=df[column].astype(float)
    return df