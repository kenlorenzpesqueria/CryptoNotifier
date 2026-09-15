import json
from pathlib import Path
from datetime import datetime, timezone

from scanner import run_scan
from bot import check_telegram
from telegram_sender import notify
from logger import logger
from positions import load_positions
from mt5_data import (
    initialize_mt5,
    shutdown_mt5,
    get_klines,
    get_last_completed_index,
)
from config import CANDLE_LIMIT


UTC = timezone.utc
DAILY_REPORT_FILE = Path(
    "data/mt5_daily_report.json"
)


def get_latest_completed_d1_time():
    df = get_klines(
        "EURUSD",
        "1d",
        CANDLE_LIMIT,
    )

    if df is None or len(df) < 1:
        return None

    completed_index = get_last_completed_index(
        df,
        "1d",
        "EURUSD",
    )

    return df.iloc[completed_index]["open_time"]


def load_last_reported_d1():
    if not DAILY_REPORT_FILE.exists():
        return None

    try:
        with open(
            DAILY_REPORT_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        return data.get("open_time")

    except Exception as e:
        logger.exception(
            "Unable to load daily report state"
        )

        print(
            f"Daily report state error: {e}"
        )

        return None


def save_last_reported_d1(d1_time):
    DAILY_REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        DAILY_REPORT_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            {
                "open_time": d1_time.isoformat(),
            },
            file,
            indent=2,
        )


def send_daily_report(results):
    now = datetime.now(UTC)

    positions = load_positions()

    positions = {
        symbol: position
        for symbol, position in positions.items()
        if position.get("side") in (
            "BUY",
            "SELL",
        )
    }

    lines = [
        "📊 CRYPTONOTIFIER DAILY POSITION REPORT",
        "",
        f"📅 {now.strftime('%B %d, %Y')}",
        "🇵🇭 Philippines Time",
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

            side = position.get(
                "side",
                "UNKNOWN",
            )

            entry_price = position.get(
                "entry_price",
                "UNKNOWN",
            )

            status = position.get(
                "status",
                "UNKNOWN",
            )

            icon = (
                "🟢"
                if side == "BUY"
                else "🔴"
            )

            lines.append(
                f"{icon} {symbol}\n"
                f"   Position: {side}\n"
                f"   Entry Price: {entry_price}"
            )

            if result:
                lines.extend(
                    [
                        f"   Current Price: "
                        f"{result['price']:.5f}",
                        f"   4H EMA20: "
                        f"{result['ema20_4h']:.5f}",
                        f"   1D EMA20: "
                        f"{result['ema20_1d']:.5f}",
                    ]
                )

            lines.append(
                f"   Status: {status}"
            )

            lines.append("")

    if notify("\n".join(lines)):
        logger.info(
            "Daily position report sent"
        )

        print(
            "Daily position report sent."
        )

        return True

    logger.error(
        "Daily position report failed"
    )

    print(
        "Daily position report failed."
    )

    return False


def main():
    logger.info(
        "CryptoNotifier MT5 scheduled scan started"
    )

    print("========================================")
    print(" CryptoNotifier MT5")
    print(" Scheduled Scan")
    print("========================================")
    print()

    mt5_ready = False

    try:
        try:
            initialize_mt5()
            mt5_ready = True

            print(
                "MT5 terminal is ready."
            )

        except Exception as e:
            logger.exception(
                "MT5 initialization failed"
            )

            print(
                f"MT5 initialization error: {e}"
            )

            notify(
                "🚨 CRYPTONOTIFIER MT5 ERROR\n\n"
                "MT5 terminal failed to become ready.\n\n"
                f"Error: {e}"
            )

            return

        try:
            check_telegram()

            print(
                "Telegram command check complete."
            )

        except Exception as e:
            logger.exception(
                "Telegram check failed"
            )

            print(
                f"Telegram error: {e}"
            )

        print()
        print("Running H4 scan...")

        results = run_scan()

        print()
        print("H4 scan complete.")

        try:
            latest_d1 = (
                get_latest_completed_d1_time()
            )

            if latest_d1 is None:
                print(
                    "Unable to determine "
                    "latest completed D1 candle."
                )

            else:
                print(
                    "Latest completed D1 candle: "
                    f"{latest_d1}"
                )

                last_reported_d1 = (
                    load_last_reported_d1()
                )

                latest_d1_value = (
                    latest_d1.isoformat()
                )

                if (
                    last_reported_d1
                    != latest_d1_value
                ):
                    print(
                        "New completed D1 candle "
                        "detected."
                    )

                    report_sent = (
                        send_daily_report(
                            results
                        )
                    )

                    if report_sent:
                        save_last_reported_d1(
                            latest_d1
                        )

                else:
                    print(
                        "Daily report already sent "
                        "for this D1 candle."
                    )

        except Exception as e:
            logger.exception(
                "Daily report check failed"
            )

            print(
                f"Daily report error: {e}"
            )

        print()
        print("========================================")
        print(" Scheduled scan complete")
        print(" CryptoNotifier exiting")
        print("========================================")

        logger.info(
            "CryptoNotifier scheduled scan "
            "completed"
        )

    except Exception as e:
        logger.exception(
            "Scheduled scan failed"
        )

        print()
        print(
            f"Scheduled scan error: {e}"
        )

        raise

    finally:
        if mt5_ready:
            shutdown_mt5()


if __name__ == "__main__":
    main()