from pyxavi.config import Config
from echobot.parsers.telegram_parser import TelegramParser
from echobot.runners.runner_protocol import RunnerProtocol
import logging

#######
# This is meant to be run just once.
#
# It is shipped commented on purpose.
# Just go the last line of the file and uncomment it.
#
# Xavi
##

class TelegramLogin(RunnerProtocol):
    def __init__(
        self, config: Config = None, logger: logging = None, params: dict = None
    ) -> None:
        self._config = config
        self._logger = logger

    def run(self):
        self._logger.info("Run Login Telegram")
        # Initializing the client already asks for the credentials and creates the session file.
        telegram_client = TelegramParser(self._config)
        self._logger.info("End Login Telegram")
