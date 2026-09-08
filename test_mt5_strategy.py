import sys

sys.path.insert(0, "src")

from mt5_data import get_klines, get_last_completed_index
from indicators import calculate_indicators
from signals import get_signal


SYMBOLS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "AUDUSD",
]


def main():
    print("========================================")
    print(" CryptoNotifier MT5 Strategy Test")
    print("========================================")
    print()

    for symbol in SYMBOLS:
        print(f"--- {symbol} ---")

        try:
            df_4h = get_klines(symbol, "4h", 100)
            df_1d = get_klines(symbol, "1d", 100)

            df_4h = calculate_indicators(df_4h)
            df_1d = calculate_indicators(df_1d)

            completed_4h_index = get_last_completed_index(
                df_4h,
                "4h",
                symbol,
            )

            completed_1d_index = get_last_completed_index(
                df_1d,
                "1d",
                symbol,
            )

            if completed_4h_index < 1:
                raise RuntimeError(
                    "Not enough completed H4 candles"
                )

            if completed_1d_index < 0:
                raise RuntimeError(
                    "No completed D1 candle available"
                )

            previous_4h = df_4h.iloc[completed_4h_index - 1]
            current_4h = df_4h.iloc[completed_4h_index]
            current_1d = df_1d.iloc[completed_1d_index]

            signal = get_signal(
                previous_4h,
                current_4h,
                current_1d,
            )

            print(
                f"H4 completed candle : "
                f"{current_4h['open_time']}"
            )

            print(
                f"H4 Close             : "
                f"{current_4h['close']:.5f}"
            )

            print(
                f"H4 EMA20             : "
                f"{current_4h['ema20']:.5f}"
            )

            print(
                f"H4 EMA50             : "
                f"{current_4h['ema50']:.5f}"
            )

            print(
                f"H4 MACD              : "
                f"{current_4h['macd']:.5f}"
            )

            print(
                f"H4 MACD Signal       : "
                f"{current_4h['macd_signal']:.5f}"
            )

            print(
                f"H4 MACD Histogram    : "
                f"{current_4h['macd_hist']:.5f}"
            )

            print(
                f"Previous H4 Close    : "
                f"{previous_4h['close']:.5f}"
            )

            print(
                f"D1 completed candle  : "
                f"{current_1d['open_time']}"
            )

            print(
                f"D1 Close             : "
                f"{current_1d['close']:.5f}"
            )

            print(
                f"D1 EMA20             : "
                f"{current_1d['ema20']:.5f}"
            )

            print()
            print(f"Signal               : {signal or 'NONE'}")
            print()

        except Exception as e:
            print(f"ERROR: {e}")
            print()

    print("========================================")
    print(" Test complete")
    print("========================================")


if __name__ == "__main__":
    main()