from pyxavi.config import Config
from echobot.lib.publisher import Publisher
from echobot.runners.runner_protocol import RunnerProtocol
from definitions import ROOT_DIR
import logging


class QueuePublisher(RunnerProtocol):
    '''
    Main Runner of the Echo bot
    '''

    def __init__(
        self, config: Config = None, logger: logging = None, params: dict = None
    ) -> None:
        self._config = config
        self._logger = logger
        self._publisher = Publisher(config=self._config, base_path=ROOT_DIR)

    def run(self):
        '''
        Just publishes the queue
        '''
        try:
            self._logger.info("Publishing the whole queue")
            self._publisher.publish_all_from_queue()
        except Exception as e:
            self._logger.exception(e)
