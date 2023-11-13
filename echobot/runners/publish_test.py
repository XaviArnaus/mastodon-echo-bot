from pyxavi.terminal_color import TerminalColor
from pyxavi.config import Config
from echobot.lib.publisher import Publisher
from echobot.runners.runner_protocol import RunnerProtocol
from definitions import ROOT_DIR
import logging

DEFAULT_NAMED_ACCOUNT = ["test", "default"]


class PublishTest(RunnerProtocol):
    '''
    Runner that publishes a test
    '''
    def __init__(
        self, config: Config = None, logger: logging = None, params: dict = None
    ) -> None:
        self._config = config
        self._logger = logger

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
