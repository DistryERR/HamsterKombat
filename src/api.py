from src.client import Client
from http.client import HTTPException
import json
import time
import base64
import re


class Clicker:
    def __init__(self, client: Client) -> None:
        self.client = client

        self.__clickerUser = {}

        self.__clickerConfig = {}
        self.__clickerConfigLastUpdate = 0

        self.__dailyCipher = {}
        self.__dailyCipherLastUpdate = 0

        self.__dailyTask = {}
        self.__dailyTaskLastUpdate = 0

        self.__upgradesForBuy = []
        self.__upgradesForBuyLastUpdate = 0

        self.tg = self.client.post("/auth/me-telegram")["telegramUser"]
        self.getConfig()
        self.sync()
        self.getUpgradesForBuy()
        self.dailyTask
        self.client.post("/clicker/list-airdrop-tasks")

    def getConfig(self):
        responseData = self.client.post("/clicker/config")
        self.__clickerConfig = responseData["clickerConfig"]
        self.__dailyCipher = responseData["dailyCipher"]
        self.__clickerConfigLastUpdate = self.__dailyCipherLastUpdate = time.time()
        return self.__clickerConfig

    def sync(self):
        try:
            self.__clickerUser = self.client.post("/clicker/sync")["clickerUser"]
        except HTTPException:
            if self.client.lastResponseCode != 500:
                raise
            match = re.match(
                r"Couchbase error.+Data=",
                self.client.lastResponseData.decode(),
            )
            if not match:
                raise
            self.__clickerUser = json.loads(self.lastResponseData[len(match[0]) :])
        return self.__clickerUser

    def getUpgradesForBuy(self):
        responseData = self.client.post("/clicker/upgrades-for-buy")
        self.__upgradesForBuyLastUpdate = time.time()
        self.__upgradesForBuy = responseData["upgradesForBuy"]
        return self.__upgradesForBuy

    def buyUpgrade(self, upgradeId: str):
        responseData = self.client.post(
            "/clicker/buy-upgrade",
            {"upgradeId": upgradeId, "timestamp": int(time.time())},
        )
        self.__clickerUser = responseData["clickerUser"]
        self.__upgradesForBuy = responseData["upgradesForBuy"]
        self.__upgradesForBuyLastUpdate = time.time()
        return self.__upgradesForBuy

    def getListTasks(self):
        responseData = self.client.post("/clicker/list-tasks")
        return responseData["tasks"]

    def checkTask(self, taskId: str):
        responseData = self.client.post("/clicker/check-task", {"taskId": taskId})
        self.__clickerUser = responseData["clickerUser"]
        return responseData["task"]

    def tap(self, taps: int = 0):
        clickerUser = self.clickerUser

        timeleft = max(int(time.time()) - clickerUser["lastSyncUpdate"], 0)
        availableEnergy = availableEnergy = min(
            clickerUser["availableTaps"] + clickerUser["tapsRecoverPerSec"] * timeleft,
            clickerUser["maxTaps"],
        )

        maxAvailableTaps = availableEnergy // clickerUser["earnPerTap"]
        taps = min(taps, maxAvailableTaps) if taps > 0 else maxAvailableTaps
        requiredEnergy = taps * clickerUser["earnPerTap"]

        try:
            responseData = self.client.post(
                "/clicker/tap",
                {
                    "availableTaps": availableEnergy - requiredEnergy,
                    "count": taps,
                    "timestamp": int(time.time()),
                },
            )
            self.__clickerUser = responseData["clickerUser"]

        except HTTPException:
            if self.client.lastResponseCode != 500:
                raise
            match = re.match(
                r"Couchbase error.+Data=", self.client.lastResponseData.decode()
            )
            if not match:
                raise
            self.__clickerUser = json.loads(self.lastResponseData[len(match[0]) :])

        return taps, requiredEnergy

    def claimDailyCipher(self):
        dailyCipher = self.dailyCipher
        if dailyCipher["isClaimed"]:
            return False, None, None
        cipher = dailyCipher["cipher"]
        decodedCipher = base64.b64decode(cipher[:3] + cipher[4:]).decode()
        responseData = self.client.post(
            "/clicker/claim-daily-cipher", {"cipher": decodedCipher}
        )
        self.__clickerUser = responseData["clickerUser"]
        self.__dailyCipher = responseData["dailyCipher"]
        self.__dailyCipherLastUpdate = time.time()
        return True, dailyCipher["bonusCoins"], decodedCipher

    def claimDailyTask(self):
        dailyTask = self.dailyTask

        rewardCoins = dailyTask.get("rewardCoins", 0)
        if dailyTask.get("isCompleted", True):
            return False, rewardCoins

        dailyTask = self.checkTask("streak_days")

        self.__dailyTask = dailyTask
        self.__dailyTaskLastUpdate = time.time()

        return dailyTask["isCompleted"], rewardCoins

    @property
    def clickerUser(self) -> dict:
        if time.time() - self.__clickerUser.get("lastSyncUpdate", 0) >= 4500:
            self.sync()
        return self.__clickerUser

    @property
    def clickerConfig(self) -> dict:
        if time.time() - self.__clickerConfigLastUpdate >= 10800:
            self.getConfig()
        return self.__clickerConfig

    @property
    def dailyCipher(self) -> dict:
        if time.time() - self.__dailyCipherLastUpdate >= 1800:
            self.getConfig()
        return self.__dailyCipher

    @property
    def dailyTask(self) -> list:
        if time.time() - self.__dailyTaskLastUpdate >= 3600:
            tasks = self.getListTasks()
            dailyTask = next((t for t in tasks if t["id"] == "streak_days"), {})
            self.__dailyTask = dailyTask
            self.__dailyTaskLastUpdate = time.time()
        return self.__dailyTask

    @property
    def upgradesForBuy(self) -> list:
        if time.time() - self.__upgradesForBuyLastUpdate >= 600:
            self.getUpgradesForBuy()
        return self.__upgradesForBuy

    @property
    def balance(self) -> float:
        clickerUser = self.clickerUser
        timeleft = max(time.time() - clickerUser["lastSyncUpdate"], 0)
        return clickerUser["balanceCoins"] + clickerUser["earnPassivePerSec"] * timeleft

    def getBestUpgrade(self, minBalance=0, maxPrice=0) -> dict:
        balance = self.balance - max(minBalance, 0)
        clickerUser = self.__clickerUser
        earnPerSec = clickerUser["earnPassivePerSec"]

        if not earnPerSec:
            return {}

        upgradesForBuy = self.upgradesForBuy
        timeleft = time.time() - self.__upgradesForBuyLastUpdate

        bestUp = {}
        bestUpPaybackTime = 0
        bestUpCooldown = 0
        for up in upgradesForBuy:
            price = up["price"]
            profitPerHourDelta = up["profitPerHourDelta"]

            if (
                not profitPerHourDelta
                or (price > maxPrice and maxPrice > 0)
                or not up["isAvailable"]
                or up["isExpired"]
            ):
                continue

            cooldown = max(
                0,
                up.get("cooldownSeconds", 0) - timeleft,
                (price - balance) / earnPerSec,
            )
            paybackTime = (price / profitPerHourDelta) * 3600 + cooldown

            if bestUpPaybackTime > paybackTime or not bestUp:
                bestUp = up
                bestUpPaybackTime = paybackTime
                bestUpCooldown = cooldown

        if not bestUp:
            return {}

        result = bestUp.copy()
        result["paybackTime"] = bestUpPaybackTime
        result["cooldownSeconds"] = bestUpCooldown
        return result
