import json
from binance import get_klines
from indicators import calculate_indicators
from signals import get_signal
from telegram_sender import notify
from positions import should_send,update_position,get_position,evaluate_position
from logger import logger

def load_watchlist():
    with open("data/watchlist.json","r") as f:
        return json.load(f)

def run_scan():
    symbols=load_watchlist()
    logger.info(f"Scanning {len(symbols)} symbols")
    print(f"Watching {len(symbols)} coins\n")

    for symbol in symbols:
        print(f"Scanning {symbol}...")

        try:
            df_4h=get_klines(symbol,"4h",1000)
            df_1d=get_klines(symbol,"1d",1000)

            df_4h=calculate_indicators(df_4h)
            df_1d=calculate_indicators(df_1d)

            signal=get_signal(df_4h,df_1d)

            last_4h=df_4h.iloc[-2]
            last_1d=df_1d.iloc[-2]

            print(f"4H Close : {last_4h['close']}")
            print(f"4H EMA20 : {last_4h['ema20']:.4f}")
            print(f"4H EMA50 : {last_4h['ema50']:.4f}")
            print(f"1D Close : {last_1d['close']}")
            print(f"1D EMA20 : {last_1d['ema20']:.4f}")
            print(f"MACD     : {last_4h['macd']:.4f}")
            print(f"Signal   : {last_4h['macd_signal']:.4f}")

            position=get_position(symbol)

            if position:
                status=evaluate_position(
                    symbol,
                    position["side"],
                    last_4h
                )

                if status=="WEAKENING":
                    message=(
                        f"⚠️ POSITION WEAKENING\n\n"
                        f"Symbol: {symbol}\n"
                        f"Position: {position['side']}\n"
                        f"Price: {last_4h['close']:.4f}\n"
                        f"EMA20: {last_4h['ema20']:.4f}\n"
                        f"MACD: {last_4h['macd']:.4f}\n"
                        f"Signal: {last_4h['macd_signal']:.4f}"
                    )
                    notify(message)
                    logger.warning(f"{symbol} {position['side']} position weakening")
                    print("Position: WEAKENING")

                elif status=="HEALTHY":
                    print("Position: HEALTHY")
                else:
                    print(f"Position: {position['status']}")

            if signal and should_send(symbol,signal):
                update_position(symbol,signal,last_4h["close"])

                message=(
                    f"🚨 {signal} SIGNAL\n\n"
                    f"Symbol: {symbol}\n"
                    f"Price: {last_4h['close']:.4f}\n"
                    f"4H EMA20: {last_4h['ema20']:.4f}\n"
                    f"4H EMA50: {last_4h['ema50']:.4f}\n"
                    f"1D Close: {last_1d['close']:.4f}\n"
                    f"1D EMA20: {last_1d['ema20']:.4f}\n"
                    f"MACD: {last_4h['macd']:.4f}\n"
                    f"Signal: {last_4h['macd_signal']:.4f}"
                )

                notify(message)
                logger.info(f"{symbol} {signal}")
                print(f"Trade : {signal}")
            else:
                print("Trade : NONE")

            print()

        except Exception as e:
            logger.exception(symbol)
            print(f"{symbol}: {e}")