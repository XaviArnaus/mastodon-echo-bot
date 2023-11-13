from pyxavi.config import Config
from mastodon import Mastodon
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

class CreateApp(RunnerProtocol):
    def __init__(
        self, config: Config = None, logger: logging = None, params: dict = None
    ) -> None:
        self._config = config
        self._logger = logger

    def run(self):
        self._logger.info("Run Create App")
        Mastodon.create_app(
            self._config.get("app.name"),
            api_base_url = self._config.get("app.api_base_url"),
            to_file = self._config.get("app.client_credentials")
        )
        self._logger.info("End Create App")
