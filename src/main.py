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
        lines.extend([
            "NO ACTIVE POSITIONS",
            "━━━━━━━━━━━━━━━━━━",
        ])
    else:
        lines.extend([
            "ACTIVE POSITIONS",
            "━━━━━━━━━━━━━━━━━━",
            "",
        ])

        result_map = {
            result["symbol"]: result
            for result in results
        }

        for symbol, position in positions.items():
            result = result_map.get(symbol)

            side = position.get("side", "UNKNOWN")
            entry_price = position.get(
                "entry_price",
                "UNKNOWN",
            )
            status = position.get(
                "status",
                "UNKNOWN",
            )

            icon = "🟢" if side == "BUY" else "🔴"

            lines.append(
                f"{icon} {symbol}\n"
                f"   Position: {side}\n"
                f"   Entry Price: {entry_price}"
            )

            if result:
                lines.extend([
                    f"   Current Price: {result['price']:.5f}",
                    f"   4H EMA20: {result['ema20_4h']:.5f}",
                    f"   1D EMA20: {result['ema20_1d']:.5f}",
                ])

            lines.append(
                f"   Status: {status}"
            )

            lines.append("")

    notify("\n".join(lines))

    logger.info("Daily position report sent")
    print("Daily position report sent.")


def main():
    now = datetime.now(UTC)

    logger.info(
        f"CryptoNotifier MT5 check started at {now.isoformat()}"
    )

    print("========================================")
    print(" CryptoNotifier MT5")
    print(" One-Shot 4H Checker")
    print("========================================")
    print()
    print(f"UTC Time: {now.isoformat()}")
    print()

    try:
        try:
            check_telegram()
            print("Telegram commands checked.")
        except Exception as e:
            logger.exception("Telegram check failed")
            print(f"Telegram error: {e}")

        print()
        print("Starting MT5 market scan...")

        results = run_scan()

        print()
        print("MT5 market scan completed.")

        if now.hour == 0:
            try:
                send_daily_report(results)
            except Exception as e:
                logger.exception(
                    "Daily report failed"
                )
                print(
                    f"Daily report error: {e}"
                )

        print()
        print("========================================")
        print(" Check completed.")
        print(" CryptoNotifier MT5 exiting.")
        print("========================================")

        logger.info(
            "CryptoNotifier MT5 check completed"
        )

    except KeyboardInterrupt:
        print()
        print("CryptoNotifier stopped manually.")

        logger.info(
            "CryptoNotifier stopped manually"
        )

    except Exception as e:
        logger.exception(
            "CryptoNotifier MT5 check failed"
        )

        print()
        print(
            f"CryptoNotifier MT5 check failed: {e}"
        )

        notify(
            "🚨 CRYPTONOTIFIER MT5 ERROR\n\n"
            f"{e}"
        )


if __name__ == "__main__":
    main()