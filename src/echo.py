from pyxavi.config import Config
from pyxavi.janitor import Janitor
from pyxavi.debugger import full_stack
from .mastodon_helper import MastodonHelper
from .parsers.mastodon_parser import MastodonParser
from .parsers.feed_parser import FeedParser
from .parsers.twitter_parser import TwitterParser
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
        - Parses all registered mastodon accounts and RSS feeds
        - Adds al selected content to a queue to be published
        - Publishes the queue, one each run or all in one shot

        Set the behaviour in the config.yaml
        '''
        try:
            # All actions are done under a Mastodon API instance
            mastodon = MastodonHelper.get_instance(self._config)

            # Parses the defined mastodon accounts
            # and merges the toots to the already existing queue       
            mastodon_parser = MastodonParser(self._config)
            mastodon_parser.parse(mastodon)

            # Parses the defined feeds
            # and merges the toots to the already existing queue
            feed_parser = FeedParser(self._config)
            feed_parser.parse()

            # Parses the defined twitter accounts
            # and merges the toots to the already existing queue
            twitter_parser = TwitterParser(self._config)
            twitter_parser.parse()

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
            remote_url = self._config.get("janitor.remote_url")
            if remote_url is not None:
                app_name = self._config.get("app.name")
                Janitor(remote_url).error(
                    message="```" + full_stack() + "```",
                    summary=f"Echo bot [{app_name}] failed: {e}"
                )

            self._logger.exception(e)

