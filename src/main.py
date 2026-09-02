from datetime import datetime, timezone

from scanner import run_scan
from bot import check_telegram
from telegram_sender import notify
from logger import logger
from positions import load_positions


UTC = timezone.utc


def send_daily_report(results):
    now = datetime.now(UTC)
    positions = load_positions()

    positions = {
        symbol: position
        for symbol, position in positions.items()
        if position.get("side") in ("BUY", "SELL")
    }

    lines = [
        "📊 CRYPTONOTIFIER DAILY POSITION REPORT",
        "",
        f"📅 {now.strftime('%B %d, %Y')}",
        "🕛 12:00 AM UTC",
        "🇵🇭 8:00 AM PHT",
        "",
        "━━━━━━━━━━━━━━━━━━",
    ]

    if not positions:
        lines.extend(
            [
                "NO ACTIVE POSITIONS",
                "━━━━━━━━━━━━━━━━━━",
            ]
        )
    else:
        lines.extend(
            [
                "ACTIVE POSITIONS",
                "━━━━━━━━━━━━━━━━━━",
                "",
            ]
        )

        result_map = {
            result["symbol"]: result
            for result in results
        }

        for symbol, position in positions.items():
            result = result_map.get(symbol)

            side = position.get("side", "UNKNOWN")
            entry_price = position.get("entry_price", "UNKNOWN")
            status = position.get("status", "UNKNOWN")

            if side == "BUY":
                icon = "🟢"
            else:
                icon = "🔴"

            lines.append(
                f"{icon} {symbol}\n"
                f"   Position: {side}\n"
                f"   Entry Price: {entry_price}"
            )

            if result:
                lines.extend(
                    [
                        f"   Current Price: {result['price']:.4f}",
                        f"   4H EMA20: {result['ema20_4h']:.4f}",
                        f"   1D EMA20: {result['ema20_1d']:.4f}",
                    ]
                )

            lines.append(
                f"   Status: {status}"
            )

            lines.append("")

    notify("\n".join(lines))

    logger.info("Daily position report sent")
    print("Daily position report sent.")


def main():
    logger.info("Bot Started")
    print("CryptoNotifier starting...\n")

    check_telegram()

    results = run_scan()

    now = datetime.now(UTC)

    print(f"DEBUG UTC TIME: {now.isoformat()}")
    print(f"DEBUG UTC HOUR: {now.hour}")
    print(f"DEBUG UTC MINUTE: {now.minute}")

    if now.hour == 0:
        send_daily_report(results)

    logger.info("Bot Finished")


if __name__ == "__main__":
    main()