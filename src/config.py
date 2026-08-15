from dotenv import load_dotenv
import os

load_dotenv()

CANDLE_LIMIT=1000

TIMEFRAME_4H="4h"
TIMEFRAME_1D="1d"

EMA_FAST=20
EMA_SLOW=50

MACD_FAST=6
MACD_SLOW=17
MACD_SIGNAL=9

BOT_TOKEN=os.getenv("BOT_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")