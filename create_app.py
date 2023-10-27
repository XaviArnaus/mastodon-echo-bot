from pyxavi.config import Config
from pyxavi.logger import Logger
from mastodon import Mastodon

#######
# This is meant to be run just once.
#
# It is shipped commented on purpose.
# Just go the last line of the file and uncomment it.
#
# Xavi
##

class CreateApp:
    def init(self):
        self._config = Config()
        self._logger = Logger(self._config).getLogger()
        self._logger.info("Init Create App")

        return self

    def run(self):
        self._logger.info("Run Create App")
        Mastodon.create_app(
            self._config.get("app.name"),
            api_base_url = self._config.get("app.api_base_url"),
            to_file = self._config.get("app.client_credentials")
        )
        self._logger.info("End Create App")

if __name__ == '__main__':
    CreateApp().init().run()