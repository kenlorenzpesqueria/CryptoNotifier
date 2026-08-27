from datetime import datetime
from zoneinfo import ZoneInfo

from scanner import run_scan
from bot import check_telegram
from telegram_sender import notify
from logger import logger


MANILA_TZ = ZoneInfo("Asia/Manila")


def send_daily_report(results):
    now = datetime.now(MANILA_TZ)

    buy_count = sum(
        1 for result in results
        if result["signal"] == "BUY"
    )

    sell_count = sum(
        1 for result in results
        if result["signal"] == "SELL"
    )

    none_count = sum(
        1 for result in results
        if result["signal"] is None
    )

    lines = [
        "📊 CRYPTONOTIFIER DAILY TRADE REPORT",
        "",
        f"📅 {now.strftime('%B %d, %Y')}",
        "🕛 12:00 AM PHT",
        "",
        "━━━━━━━━━━━━━━━━━━",
        "MARKET SCAN",
        "━━━━━━━━━━━━━━━━━━",
        "",
        f"🟢 BUY signals: {buy_count}",
        f"🔴 SELL signals: {sell_count}",
        f"⚪ NONE: {none_count}",
        "",
    ]

    for result in results:
        symbol = result["symbol"]
        signal = result["signal"]

        if signal == "BUY":
            icon = "🟢"
            trade = "BUY"
        elif signal == "SELL":
            icon = "🔴"
            trade = "SELL"
        else:
            icon = "⚪"
            trade = "NONE"

        lines.append(
            f"{icon} {symbol}: {trade}\n"
            f"   Price: {result['price']:.4f}\n"
            f"   4H EMA20: {result['ema20_4h']:.4f}\n"
            f"   1D EMA20: {result['ema20_1d']:.4f}"
        )

        if result["position"]:
            lines.append(
                f"   Position: {result['position']} "
                f"({result['position_status'] or 'UNKNOWN'})"
            )

        lines.append("")

    lines.extend([
        "━━━━━━━━━━━━━━━━━━",
        "CryptoNotifier",
        "4H scanner • 1D EMA20 filter",
    ])

    # The report is sent directly to Telegram.
    # It is NOT saved anywhere.
    notify("\n".join(lines))

    logger.info("Daily trade report sent")
    print("Daily trade report sent.")


def main():
    logger.info("Bot Started")
    print("CryptoNotifier starting...\n")

    # Check Telegram commands first.
    check_telegram()

    # Run the normal market scan.
    results = run_scan()

    now = datetime.now(MANILA_TZ)

    # The Cloud Scheduler runs every 4 hours:
    #
    # 00:00
    # 04:00
    # 08:00
    # 12:00
    # 16:00
    # 20:00
    #
    # Only the midnight execution sends the daily report.
    if now.hour == 0:
        send_daily_report(results)

    logger.info("Bot Finished")


if __name__ == "__main__":
    main()