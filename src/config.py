from src.devices import DEVICES
import json
import logging
import random

class Config:
    AUTH_TOKEN: str = ""

    AUTO_UPGRADE: bool = False
    AUTO_UPGRADE_INTERVAL: int = 120
    MAX_UPGRADE_PRICE: int = 10000000
    MIN_BALANCE: int = 3000000

    SEND_TAPS: bool = True
    CLAIM_DAILY_CIPHER: bool = True
    CLAIM_DAILY_TASK: bool = True

    DEVICE: str = ""

    HTTP_PROXY: str = ""



class ConfigEncoder(json.JSONEncoder):
    def default(self, o: Config) -> dict:
        return dict(
            [
                (attr, o.__getattribute__(attr))
                for attr in Config.__dict__
                if not attr.startswith("__")
            ]
        )


class ConfigDecoder(json.JSONDecoder):
    def __init__(self, **kwargs) -> None:
        kwargs["object_hook"] = ConfigDecoder.object_hook
        super().__init__(**kwargs)

    def object_hook(o: dict) -> Config:
        config = Config()
        for attr in Config.__dict__:
            if not attr.startswith("__"):
                value = o.get(attr, None)
                annotation = Config.__annotations__.get(attr, None)
                if annotation and annotation != type(value):
                    value = Config.__dict__[attr]
                config.__setattr__(attr, value)
        return config


def LoadDefaultConfig() -> Config:
    return Config()


def SaveConfig(filename: str, config: Config) -> str:
    with open(filename, "w") as file:
        file.write(json.dumps(config, cls=ConfigEncoder, indent=4))
    return filename


def LoadConfig(filename: str) -> Config:
    if not filename:
        return LoadDefaultConfig()
    try:
        with open(filename, "r") as file:
            config = json.loads(file.read(), cls=ConfigDecoder)
            logging.info("Config loaded from %s", filename)
    except json.JSONDecodeError:
        config = LoadDefaultConfig()
        logging.warning("The config file is corrupted. Default config loaded")

    logging.info("Minimum balance: %i", config.MIN_BALANCE)
    if config.MAX_UPGRADE_PRICE:
        logging.info("Maximum upgrade price: %i", config.MAX_UPGRADE_PRICE)

    logging.info("Auto upgrade: %s",
                    "ENABLED" if config.AUTO_UPGRADE else "DISABLED")
    logging.info("Taps sending: %s",
                    "ENABLED" if config.SEND_TAPS else "DISABLED")

    if DEVICES.get(config.DEVICE, None) is None:
        config.DEVICE = random.choice(list(DEVICES.keys()))
    logging.info("Emulated device: %s", config.DEVICE)

    if config.HTTP_PROXY:
        logging.info("Use HTTP proxy: %s", config.HTTP_PROXY)
    
    SaveConfig(filename, config)
    return config
