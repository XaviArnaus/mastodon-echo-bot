from pyxavi.terminal_color import TerminalColor
from pyxavi.config import Config
from pyxavi.logger import Logger
from echobot.publisher import Publisher
from definitions import ROOT_DIR

DEFAULT_NAMED_ACCOUNT = ["test", "default"]


class PublishTest:
    '''
    Runner that publishes a test
    '''

    def init(self):
        self._config = Config()
        self._logger = Logger(self._config).get_logger()

        return self

    def run(self):
        '''
        Just publish a test
        '''
        try:
            # Publish the message
            self._logger.info(
                f"{TerminalColor.MAGENTA}Publishing Test Message{TerminalColor.END}"
            )
            Publisher(
                config=self._config,
                base_path=ROOT_DIR
            )._execute_action({
                "action": "new",
                "media": None,
                "published_at": "2023-09-29 10:10:53+00:00",
                "status":"This is a test",
                "language":"en"
            })
        except Exception as e:
            self._logger.exception(e)
            print(e)

if __name__ == '__main__':
    PublishTest().init().run()