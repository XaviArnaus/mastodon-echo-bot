from pyxavi.config import Config
from pyxavi.janitor import Janitor
from pyxavi.debugger import full_stack
from .parsers.mastodon_parser import MastodonParser
from .parsers.feed_parser import FeedParser
from .parsers.twitter_parser import TwitterParser
from .parsers.telegram_parser import TelegramParser
from .publisher import Publisher
from definitions import ROOT_DIR
import logging

class Echo:
    '''
    Main Runner of the Echo bot
    '''
    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._publisher = Publisher(
            config=self._config,
            base_path=ROOT_DIR,
            only_oldest=self._config.get("publisher.only_older_toot")
        )

    def run(self) -> None:
        '''
        Full run
        - Parses all registered mastodon accounts and RSS feeds
        - Adds al selected content to a queue to be published
        - Publishes the queue, one each run or all in one shot

        Set the behaviour in the config.yaml
        '''
        try:
            # Parses the defined mastodon accounts
            # and merges the toots to the already existing queue       
            mastodon_parser = MastodonParser(self._config)
            mastodon_parser.parse(self._publisher._mastodon)

            # Parses the defined feeds
            # and merges the toots to the already existing queue
            feed_parser = FeedParser(self._config)
            feed_parser.parse()

            # Parses the defined twitter accounts
            # and merges the toots to the already existing queue
            twitter_parser = TwitterParser(self._config)
            twitter_parser.parse()

            # Parses the defined Telegram channels
            # and merges the toots to the already existing queue
            telegram_parser = TelegramParser(self._config)
            telegram_parser.parse()

            # Read from the queue the toots to publish
            # and do so according to the config parameters
            difference = self._publisher.reload_queue()
            difference = f"+{str(difference)}" if difference > 0 else str(difference)
            self._logger.info(f"The queue has now {difference} elements")
            self._publisher.publish_all_from_queue()

        except Exception as e:
            if self._config.get("janitor.active", False):
                remote_url = self._config.get("janitor.remote_url")
                if remote_url is not None and not self._config.get("publisher.dry_run"):
                    app_name = self._config.get("app.name")
                    Janitor(remote_url).error(
                        message="```" + full_stack() + "```",
                        summary=f"Echo bot [{app_name}] failed: {e}"
                    )

            self._logger.exception(e)
