from pyxavi.logger import Logger
from pyxavi.config import Config
from echobot.publisher import Publisher
from definitions import ROOT_DIR

class QueuePublisher:
    '''
    Main Runner of the Echo bot
    '''
    def init(self):
        self._config = Config()
        self._logger = Logger(self._config).get_logger()
        self._publisher = Publisher(
            config=self._config, base_path=ROOT_DIR
        )

        return self

    def run(self):
        '''
        Just publishes the queue
        '''
        try:
            self._logger.info("Publishing the whole queue")
            self._publisher.publish_all_from_queue()
        except Exception as e:
            self._logger.exception(e)

if __name__ == '__main__':
    QueuePublisher().init().run()

