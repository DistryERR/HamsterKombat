from src.config import Config, LoadConfig
from src.client import Client
from src.api import Clicker
from src import __version__
import time
import logging
import random
import sys
import argparse


def loop(clicker: Clicker, config: Config):
    nextTapTime = 0
    nextUpgradeTime = time.time() + config.AUTO_UPGRADE_INTERVAL
    nextSync = time.time() + 3600

    def logBalance():
        clickerUser = clicker.clickerUser
        logging.info(
            "Balance: %i (+%i). Energy: %i/%i [%is]",
            int(clickerUser["balanceCoins"]),
            clickerUser["earnPassivePerHour"],
            clickerUser["availableTaps"],
            clickerUser["maxTaps"],
            nextTapTime - time.time(),
        )

    time.sleep(5)
    while True:
        timestamp = int(time.time())
        try:

            if timestamp >= nextSync:
                clicker.sync()
                nextSync = time.time() + 3600

            if config.SEND_TAPS:
                if timestamp >= nextTapTime:
                    clickerUser = clicker.clickerUser

                    availableEnergy = (
                        clickerUser["availableTaps"]
                        + max(int(time.time()) - clickerUser["lastSyncUpdate"], 0)
                        * clickerUser["tapsRecoverPerSec"]
                    )

                    if availableEnergy / clickerUser["maxTaps"] >= 0.4:
                        taps, reward = clicker.tap()
                        clickerUser = clicker.clickerUser
                        availableEnergy = clickerUser["availableTaps"]
                        logging.info("Sended %i taps. Reward: %i", taps, reward)

                    nextTapTime = time.time() + (
                        max(
                            int((random.random() * 0.2 + 0.4) * clickerUser["maxTaps"])
                            - availableEnergy,
                            0,
                        )
                        // clickerUser["tapsRecoverPerSec"]
                    )
                    logBalance()
                    time.sleep(2)

            if config.CLAIM_DAILY_CIPHER:
                completed, reward, decodedCipher = clicker.claimDailyCipher()
                if completed:
                    logging.info(
                        "Daily cipher completed: %s. Reward: %i", decodedCipher, reward
                    )
                    logBalance()
                    time.sleep(2)

            if config.CLAIM_DAILY_TASK:
                completed, reward = clicker.claimDailyTask()
                if completed:
                    logging.info("Daily task completed. Reward: %i. ", reward)
                    logBalance()
                    time.sleep(2)

            if config.AUTO_UPGRADE:
                if timestamp >= nextUpgradeTime:
                    upgrade = clicker.getBestUpgrade(
                        config.MIN_BALANCE, config.MAX_UPGRADE_PRICE
                    )
                    cooldown = upgrade["cooldownSeconds"]
                    if upgrade:
                        if cooldown:
                            logging.info(
                                'An "%s" for %i coins (+%i) will be purchased in %i seconds',
                                upgrade["name"],
                                upgrade["price"],
                                upgrade["profitPerHourDelta"],
                                cooldown,
                            )
                            nextUpgradeTime = time.time() + min(
                                config.AUTO_UPGRADE_INTERVAL, cooldown
                            )
                        else:
                            clicker.buyUpgrade(upgrade["id"])
                            logging.info(
                                'Bought "%s" for %i coins (+%i)',
                                upgrade["name"],
                                upgrade["price"],
                                upgrade["profitPerHourDelta"],
                            )
                            logBalance()
                    else:
                        logging.info("No upgrades available")
                    nextUpgradeTime = time.time() + config.AUTO_UPGRADE_INTERVAL

            time.sleep(random.random() / 2 + 1)
        except OSError as e:
            logging.error("%s: %s", type(e).__name__, e, exc_info=1)
            time.sleep(60)


def main(args):
    logger = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(module)-6s | %(lineno)-3d | %(message)s",
        "%d.%m.%Y %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if args.debug else logging.INFO)

    logging.info("Version: %s", __version__)

    config = LoadConfig(args.file)

    client = Client(config.AUTH_TOKEN, config.DEVICE, config.HTTP_PROXY)
    clicker = Clicker(client)

    try:
        logging.info("Session started for %s", clicker.tg["username"])
        loop(clicker, config)
    except KeyboardInterrupt:
        logging.info("Session interrupted")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "file", help="configuration file", default="./default.json", nargs="?"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="enable DEBUG messages"
    )
    main(parser.parse_args())
