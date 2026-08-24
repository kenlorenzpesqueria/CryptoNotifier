import os
import requests

bot_token=os.environ["BOT_TOKEN"]
chat_id=os.environ["CHAT_ID"]

message=(
    "🧪 CRYPTONOTIFIER TEST\n\n"
    "Telegram notifications are working correctly. ✅\n\n"
    "📊 Sample BUY SIGNAL\n\n"
    "Symbol: BTCUSDT\n"
    "Price: 78443.65\n\n"
    "📊 4H CONDITIONS\n"
    "✅ Close crossed above EMA20\n"
    "✅ Close above EMA50\n"
    "✅ EMA20 above EMA50\n"
    "✅ MACD bullish crossover\n"
    "✅ 1D close above EMA20\n\n"
    "🎯 Recommendation: BUY\n\n"
    "This is only a test. No position was created."
)

url=f"https://api.telegram.org/bot{bot_token}/sendMessage"

response=requests.post(
    url,
    data={
        "chat_id":chat_id,
        "text":message
    },
    timeout=10
)

response.raise_for_status()
print("Telegram test message sent successfully.")