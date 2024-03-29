from pyxavi.config import Config
from pyxavi.janitor import Janitor
from pyxavi.debugger import full_stack
from pyxavi.terminal_color import TerminalColor
from echobot.parsers.mastodon_parser import MastodonParser
from echobot.parsers.feed_parser import FeedParser
from echobot.parsers.telegram_parser import TelegramParser
from echobot.lib.publisher import Publisher
from echobot.runners.runner_protocol import RunnerProtocol
from definitions import ROOT_DIR
import logging


class Echo(RunnerProtocol):
    '''
    Main Runner of the Echo bot
    '''

    def __init__(
        self, config: Config = None, logger: logging = None, params: dict = None
    ) -> None:
        self._config = config
        self._logger = logger
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
            self._logger.info(f"{TerminalColor.MAGENTA}Main EchoBot run{TerminalColor.END}")
            # Parses the defined mastodon accounts
            # and merges the toots to the already existing queue
            self._logger.info(
                f"{TerminalColor.YELLOW}Parsing Mastodon accounts{TerminalColor.END}"
            )
            mastodon_parser = MastodonParser(self._config)
            mastodon_parser.parse(self._publisher._mastodon)

            # Parses the defined feeds
            # and merges the toots to the already existing queue
            self._logger.info(f"{TerminalColor.YELLOW}Parsing RSS sites{TerminalColor.END}")
            feed_parser = FeedParser(self._config)
            feed_parser.parse()

            # Parses the defined Telegram channels
            # and merges the toots to the already existing queue
            self._logger.info(
                f"{TerminalColor.YELLOW}Parsing Telegram accounts{TerminalColor.END}"
            )
            telegram_parser = TelegramParser(self._config)
            telegram_parser.parse()

            # Read from the queue the toots to publish
            # and do so according to the config parameters
            difference = self._publisher.reload_queue()
            difference = f"+{str(difference)}" if difference > 0 else str(difference)
            self._logger.info(f"The queue differs now as per {difference} elements")
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


if __name__ == '__main__':
    Echo().run()
