from pyxavi.config import Config
from echobot.parsers.telegram_parser import TelegramParser
from echobot.runners.runner_protocol import RunnerProtocol
import logging


class TelegramLogin(RunnerProtocol):
    """
    Performs just an initialisation.
    If it's the first time it will ask for the login credentials.

    This is meant to be run just once.
    """

    def __init__(
        self, config: Config = None, logger: logging = None, params: dict = None
    ) -> None:
        self._config = config
        self._logger = logger

    def run(self):
        self._logger.info("Run Login Telegram")
        # Initializing the client already asks for the credentials and creates the session file.
        _ = TelegramParser(self._config)
        self._logger.info("End Login Telegram")
