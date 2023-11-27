from pyxavi.config import Config
from pyxavi.janitor import Janitor
from pyxavi.debugger import full_stack
from pyxavi.terminal_color import TerminalColor
from pyxavi.queue_stack import Queue
from echobot.lib.publisher import Publisher
from echobot.lib.keywords_filter import KeywordsFilter
from echobot.runners.runner_protocol import RunnerProtocol
from echobot.lib.queue_post import QueuePost
from definitions import ROOT_DIR, CONFIG_DIR
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz
import logging
import os

from echobot.parsers.parser_protocol import ParserProtocol
from echobot.parsers.mastodon_parser import MastodonParser
from echobot.parsers.feed_parser import FeedParser
from echobot.parsers.telegram_parser import TelegramParser


class Echo(RunnerProtocol):
    '''
    Main Runner of the Echo bot
    '''

    PARSERS = {
        "RSS Feed": {
            "module": FeedParser,
        },
        "Telegram": {
            "module": TelegramParser,
        },
        "Mastodon": {
            "module": MastodonParser,
            "active": False
        }
    }
    MONTHS_POST_TOO_OLD = 6
    DEFAULT_QUEUE_FILE = "storage/queue.yaml"

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
        self._keywords_filter = KeywordsFilter(config)
        self._queue = Queue(
            logger=self._logger,
            storage_file=config.get("toots_queue_storage.file", self.DEFAULT_QUEUE_FILE)
        )
    
    def run(self) -> None:

        self._logger.info(f"{TerminalColor.MAGENTA}Main EchoBot run{TerminalColor.END}")
        try:

            # Get the parsers that are active fro the defined ones above.
            parsers = self.load_active_parsers() # type: dict[str, ParserProtocol]

            # Get a config object specially prepared for the parsers
            parsers_config = self.prepare_config_for_parsers()

            for name, module in parsers.items():
                self._logger.info(
                    f"{TerminalColor.YELLOW}Processing {name}{TerminalColor.END}"
                )
                # Instantiate this parser
                instance = module(config=parsers_config) # type: ParserProtocol

                # Walk through all sources defined in the parser's config
                for source, parameters in instance.get_sources().items():

                    self._logger.info(
                        f"{TerminalColor.BLUE}Processing source {source}{TerminalColor.END}"
                    )

                    # Get all the raw data related to this source
                    posts = instance.get_raw_content_for_source(source)

                    # Walk the posts to process them
                    valid_posts = [] # type: list[QueuePost]
                    discarded_posts = 0
                    for post in posts:

                        # Apply filters
                        if self._is_already_seen(post=post, source=source, instance=instance)\
                           or not self._is_valid_date(post=post)\
                           or not self._is_valid_keyword_profile(
                               post=post, source_params=parameters
                           ):
                            discarded_posts += 1
                            continue
                        valid_posts.append(post)

                    color = TerminalColor.END if discarded_posts == 0 else TerminalColor.RED
                    self._logger.info(
                        f"{color}Discarded {discarded_posts} posts.{TerminalColor.END}"
                    )

                    # At this point, we should add these new posts into the state
                    instance.set_ids_as_seen_for_source(source, [x.id for x in valid_posts])

                    # In some cases the instance wants to post process the resulting list.
                    processed_posts = instance.post_process_elements(valid_posts)

                    # And finally walk them to download media and apply format
                    for post in processed_posts:

                        # Parse the content searching for media.
                        #   Some parsers would download them, some others would just
                        #   identify them and let the Publisher download them.
                        instance.parse_media(post)

                        # Format the post, according to what the instance wants.
                        instance.format_post_for_source(source, post)

                        # And finally, add it into the queue
                        self._queue.append(post)
                
                # Trying to isolate the possible issues between parsers,
                #   we secure the current queue before we move to the next parser.
                self._queue.deduplicate()
                self._queue.sort()
                self._queue.save()


        
        except Exception as e:
            # if self._config.get("janitor.active", False):
            #     remote_url = self._config.get("janitor.remote_url")
            #     if remote_url is not None and not self._config.get("publisher.dry_run"):
            #         app_name = self._config.get("app.name")
            #         Janitor(remote_url).error(
            #             message="```" + full_stack() + "```",
            #             summary=f"Echo bot [{app_name}] failed: {e}"
            #         )

            self._logger.exception(e)


    def load_active_parsers(self) -> dict:
        """Get the list of parsers that are active"""
        return {name: x for name, x in self.PARSERS if "active" not in x or x["active"] == True}
    
    def prepare_config_for_parsers(self) -> Config:
        parsers_config = Config(params=self._config.get_all())
        parsers_config.merge_from_dict(parameters={
            "mastodon": self._publisher._mastodon
        })
        return parsers_config
    
    def _is_valid_date(self, post: QueuePost) -> bool:
        # From the post we receive a datetime in the [published_at]
        #   Careful, the datetime is not UTF safe.
        initial_outdated_day = datetime.now().replace(tzinfo=pytz.UTC)\
            - relativedelta(months=self.MONTHS_POST_TOO_OLD)
        
        if initial_outdated_day > post.published_at.replace(tzinfo=pytz.UTC):
            return True

        self._logger.debug(
            f"Discarding post {post.id}: Older than {self.MONTHS_POST_TOO_OLD} months"
        )
        return False
    
    def _is_valid_keyword_profile(self, post: QueuePost, source_params: dict) -> bool:
        # From the source_params we receive a str in [keywords_filter_profile]
        #   it can be str or None
        if "keywords_filter_profile" not in source_params:
            return True
        
        # The content to analyse comes in [raw_combined_body]
        #   and it is unclean, so it could come unnormalized.
        if self._keywords_filter.profile_allows_text(
                        source_params["keywords_filter_profile"],
                        post.raw_combined_content):
            return True
        
        self._logger.debug(
            f"Discarding post {post.id}: Do not pass keywords profile " +
            f"{post.filters['keywords_profile']}"
        )
        return False

    def _is_already_seen(self, post: QueuePost, source: str, instance: ParserProtocol) -> bool:
        # From the post we get the ID. should never be None
        if instance.is_id_already_seen_for_source(source=source, id=post.id):
             self._logger.debug(f"Discarding post {post.id}: Already seen")
             return True
        
        return False


    # def run_old(self) -> None:
    #     '''
    #     Full run
    #     - Parses all registered mastodon accounts and RSS feeds
    #     - Adds al selected content to a queue to be published
    #     - Publishes the queue, one each run or all in one shot

    #     Set the behaviour in the config.yaml
    #     '''
    #     try:
    #         self._logger.info(f"{TerminalColor.MAGENTA}Main EchoBot run{TerminalColor.END}")
    #         # Parses the defined mastodon accounts
    #         # and merges the toots to the already existing queue
    #         self._logger.info(
    #             f"{TerminalColor.YELLOW}Parsing Mastodon accounts{TerminalColor.END}"
    #         )
    #         mastodon_parser = MastodonParser(self._config)
    #         mastodon_parser.parse({"mastodon": self._publisher._mastodon})

    #         # Parses the defined feeds
    #         # and merges the toots to the already existing queue
    #         self._logger.info(f"{TerminalColor.YELLOW}Parsing RSS sites{TerminalColor.END}")
    #         feed_parser = FeedParser(self._config)
    #         feed_parser.parse()

    #         # Parses the defined Telegram channels
    #         # and merges the toots to the already existing queue
    #         self._logger.info(
    #             f"{TerminalColor.YELLOW}Parsing Telegram accounts{TerminalColor.END}"
    #         )
    #         telegram_parser = TelegramParser(self._config)
    #         telegram_parser.parse()

    #         # Read from the queue the toots to publish
    #         # and do so according to the config parameters
    #         difference = self._publisher.reload_queue()
    #         difference = f"+{str(difference)}" if difference > 0 else str(difference)
    #         self._logger.info(f"The queue differs now as per {difference} elements")
    #         self._publisher.publish_all_from_queue()

    #     except Exception as e:
    #         if self._config.get("janitor.active", False):
    #             remote_url = self._config.get("janitor.remote_url")
    #             if remote_url is not None and not self._config.get("publisher.dry_run"):
    #                 app_name = self._config.get("app.name")
    #                 Janitor(remote_url).error(
    #                     message="```" + full_stack() + "```",
    #                     summary=f"Echo bot [{app_name}] failed: {e}"
    #                 )

    #         self._logger.exception(e)


if __name__ == '__main__':
    Echo().run()
