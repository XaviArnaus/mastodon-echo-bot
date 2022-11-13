from bundle.config import Config
from bundle.storage import Storage
from .mastodon_helper import MastodonHelper
from .spy import Spy
from .feed_parser import FeedParser
from .publisher import Publisher
import logging

class Echo:
    '''
    Main Runner of the Echo bot
    '''
    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))

    def run(self) -> None:
        '''
        Full run
        - It spies all registered accounts and queues toots
        - Re-toots the whole queue or just the older toot, according to the config.
        '''
        try:
            # All actions are done under a Mastodon API instance
            mastodon = MastodonHelper.get_instance(self._config)

            # Spy the defined accounts
            # and merge the toots to the already existing queue       
            spy = Spy(self._config)
            spy.maintain_toots_queue(mastodon)

            feed_parser = FeedParser(self._config)
            feed_parser.consume_feeds(mastodon)

            # Read from the queue the toots to publish
            # and do so according to the config parameters
            publisher = Publisher(self._config, mastodon)
            if self._config.get("publisher.only_older_toot"):
                self._logger.info("Publishing the older post")
                publisher.publish_older_from_queue()
            else:
                self._logger.info("Publishing the whole queue")
                publisher.publish_all_from_queue()
        except Exception as e:
            self._logger.exception(e)

