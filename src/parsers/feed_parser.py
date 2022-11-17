from bundle.config import Config
from bundle.storage import Storage
from bundle.media import Media
from ..queue import Queue
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
    CLEANR = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
    MAX_SUMMARY_LENGTH = 300

    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._toots_queue = Storage(self._config.get("toots_queue_storage.file"))
        self._feeds_storage = Storage(self._config.get("feed_parser.storage_file"))
        self._queue = Queue(config)
        self._media = Media()

    def _format_toot(self, post: dict, origin: str) -> str:

        title = post["title"]
        title_only_chars = re.sub("^[A-Za-z]*", "", title)
        if title_only_chars == title_only_chars.upper():
            title = " ".join([word.capitalize() for word in title.lower().split(" ")])
        link = post["link"]
        summary = post["summary"] + "\n\n" if "summary" in post and post["summary"] and post["summary"] != "" else ""
        summary = re.sub(self.CLEANR, '', summary)
        summary = summary.replace("\n\n\n", "\n\n")
        summary = re.sub("\s+", ' ', summary)
        summary = (summary[:self.MAX_SUMMARY_LENGTH] + '...') if len(summary) > self.MAX_SUMMARY_LENGTH+3 else summary
        
        return f"{origin}:\n\t{title}\n\n{summary}\n{link}"
    
    def _parse_media(self, post: dict) -> dict:

        # Initiate
        result = []

        # Discover if we have a link to an image
        images = self._media.get_media_url_from_text(post["summary"])

        if images:
            for image_object in images:
                result.append(
                    {
                        "url": image_object["url"],
                        "alt_text": image_object["alt_text"] if image_object["alt_text"] else None
                    }
                )

        return result

    def parse(self) -> None:
        
        # Do we have sites defined?
        sites_params = self._config.get("feed_parser.sites", None)
        if not sites_params:
            self._logger.info("No sites registered to parse, skipping,")
            return

        # For each user in the config
        for site in sites_params:

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

            # Keep track of the post seen.
            urls_seen = site_data["urls_seen"] if "urls_seen" in site_data else []

            for post in posts:

                # Check if this post was already seen
                if post["link"] in urls_seen:
                    self._logger.info("Discarding post: already seen %s", post["title"])
                    continue
                else:
                    urls_seen.append(post["link"])

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
                
                # Prepare the new toot
                media = self._parse_media(post)
                self._queue.append(
                    {
                        "status": self._format_toot(post, site["name"]),
                        "media": media if media else None,
                        "language": metadata["language"],
                        "published_at": post_date,
                        "action": "new"
                    }
                )

            # Update our storage with what we found
            self._logger.debug("Updating gathered site data for %s", site["name"])
            self._feeds_storage.set_hashed(
                site["url"],
                {
                    "urls_seen": urls_seen
                }
            )
            self._logger.info("Storing data for %s", site["name"])
            self._feeds_storage.write_file()
            
        # Update the toots queue, by adding the new ones at the end of the list
        self._queue.update()
            
            