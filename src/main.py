from bot import check_telegram
from scanner import run_scan
from logger import logger


def main():
    logger.info("Bot Started")
    print("CryptoNotifier starting...\n")

    check_telegram()
    run_scan()

    logger.info("Bot Finished")


if __name__ == "__main__":
    main()