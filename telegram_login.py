from pyxavi.config import Config
from pyxavi.logger import Logger
from echobot.parsers.telegram_parser import TelegramParser

#######
# This is meant to be run just once.
#
# It is shipped commented on purpose.
# Just go the last line of the file and uncomment it.
#
# Xavi
##

class TelegramLogin:
    def init(self):
        self._config = Config()
        self._logger = Logger(self._config).get_logger()
        self._logger.info("Init Login Telegram")

        return self

    def run(self):
        self._logger.info("Run Login Telegram")
        # Initializing the client already asks for the credentials and creates the session file.
        telegram_client = TelegramParser(self._config)
        self._logger.info("End Login Telegram")

if __name__ == '__main__':
    TelegramLogin().init().run()