from bundle.config import Config
from bundle.storage import Storage
from .mastodon_helper import MastodonHelper
from mastodon import Mastodon
import feedparser
import logging
from bundle.debugger import dd

class FeedParser:
    '''
    FeedParser

    This class is responsible to go through the posts from the registered RSS feeds
    and write in a queue list the content and other valuable data of the posts to toot

    '''
    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._toots_queue = Storage(self._config.get("toots_queue_storage.file"))

    def _format_toot(self, post: str) -> str:

        title = post["title"]
        link = post["link"]
        published_at = post["published_parsed"] if "published_parsed" in post else post["published"]
        summary = post["summary"] if "summary" in post and post["summary"] and post["summary"] is not "" else None

        dd(post)
        
        template = f"{title}"

    def consume_feeds(self, mastodon: Mastodon) -> None:
        # This will contain the queue to toot
        toots_queue = []

        # For each user in the config
        for site in self._config.get("feeds.sites"):

            # status, in_reply_to_id=None, media_ids=None, sensitive=False, visibility=None, spoiler_text=None, language=None, idempotency_key=None, content_type=None, scheduled_at=None, poll=None, quote_id=None
        
            self._logger.info("Parsing site %s", site["name"])
            parsed_site = feedparser.parse(site["url"])

            metadata = {
                "language": parsed_site["feed"]["language"] if "language" in parsed_site["feed"] else site["language_default"]
            }

            if "entries" in parsed_site:
                for post in parsed_site["entries"]:
                    
                    new_toot = {
                        "status": self._format_toot(post)
                    }
                    
            
            