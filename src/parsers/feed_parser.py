from bundle.config import Config
from bundle.storage import Storage
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil import parser
import pytz
from time import mktime
import feedparser
import logging
import re

class FeedParser:
    '''
    Parses the posts from the registered RSS feeds
    and write in a queue list the content and other valuable data of the posts to toot

    '''
    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._toots_queue = Storage(self._config.get("toots_queue_storage.file"))
        self._feeds_storage = Storage(self._config.get("feed_parser.storage_file"))

    def _format_toot(self, post: dict, origin: str) -> str:

        title = post["title"]
        title_only_chars = re.sub("^[A-Za-z]*", "", title)
        if title_only_chars == title_only_chars.upper():
            title = " ".join([word.capitalize() for word in title.lower().split(" ")])
        link = post["link"]
        summary = post["summary"] + "\n\n" if "summary" in post and post["summary"] and post["summary"] != "" else ""
        
        return f"{origin}:\n\t{title}\n\n{summary}{link}"

    def parse(self) -> None:
        # This will contain the queue to toot
        toots_queue = []

        # For each user in the config
        for site in self._config.get("feed_parser.sites"):

            self._logger.info("Getting possible stored data for %s", site["name"])
            site_data = self._feeds_storage.get_hashed(site["url"], None)
        
            self._logger.info("Parsing site %s", site["name"])
            parsed_site = feedparser.parse(site["url"])

            metadata = {
                "language": parsed_site["feed"]["language"] if "language" in parsed_site["feed"] else site["language_default"]
            }

            if not "entries" in parsed_site or not parsed_site["entries"]:
                self._logger.warn("No entries in this feed, skipping.")

            self._logger.info("Sorting %d entries ASC", len(parsed_site["entries"]))
            posts = sorted(parsed_site["entries"], key=lambda x: x["published_parsed"])

            # Keep track of the last post date seen.
            # Defaults to the current, will be updated with any new one
            last_published_post_date = site_data["last_published_post_date"] if site_data and "last_published_post_date" in site_data else None

            for post in posts:

                # Calculate post date
                post_date = None
                if "published_parsed" in post and post["published_parsed"]:
                    post_date = datetime.fromtimestamp(mktime(post["published_parsed"])).replace(tzinfo=pytz.UTC)
                elif "published" in post and post["published"]:
                    post_date = parser.parse(post["published"])
                else:
                    self._logger.warn("Discarding post: no usable published date, can't rely on it")
                    continue

                # We don't want anything older than 6 months and also older of the last entry we have registered
                if datetime.now().replace(tzinfo=pytz.UTC) - relativedelta(months=6) > post_date:
                    self._logger.info("Discarding post: too old %s", post_date)
                    continue

                # We don't want to repeat posts that we saw in previous parsings
                if site_data and "last_published_post_date" in site_data \
                    and site_data["last_published_post_date"] >= post_date:
                    self._logger.info("Discarding post: already seen %s", post_date)
                    continue
                
                # Prepare the new toot
                toots_queue.append({
                    "status": self._format_toot(post, site["name"]),
                    "language": metadata["language"],
                    "published_at": post_date
                })

                # Update the last post seen
                last_published_post_date = post_date

            # Update our storage with what we found
            self._logger.debug("Updating gathered site data for %s", site["name"])
            self._feeds_storage.set_hashed(
                site["url"],
                {
                    "last_published_post_date": last_published_post_date
                }
            )
            self._logger.info("Storing data for %s", site["name"])
            self._feeds_storage.write_file()
            
        # Update the toots queue, by adding the new ones at the end of the list
        if not toots_queue:
            self._logger.info("No new toots to queue, skipping.")
        else:
            self._logger.info("Reading queue")
            saved_queue = self._toots_queue.get("queue", [])
            self._logger.info("Adding %d to the queue", len(toots_queue))
            for toot in toots_queue:
                saved_queue.append({
                    **toot,
                    **{"action": "new"}
                })

            self._logger.info("Ensuring that the queue is sorted by date ASC and without duplications")
            saved_queue = sorted(saved_queue, key=lambda x: x["published_at"])
            processed_queue = []
            [processed_queue.append(x) for x in saved_queue if x not in processed_queue]
            self._logger.info("Saving the queue")
            self._toots_queue.set("queue", processed_queue)
            self._toots_queue.write_file()
            
            