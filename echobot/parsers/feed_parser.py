from pyxavi.config import Config
from pyxavi.storage import Storage
from pyxavi.media import Media
from pyxavi.url import Url
from echobot.lib.queue import Queue
from echobot.parsers.keywords_filter import KeywordsFilter
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil import parser
from bs4 import BeautifulSoup
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
    DEFAULT_STORAGE_FILE = "storage/feeds.yaml"

    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._feeds_storage = Storage(self._config.get("feed_parser.storage_file", self.DEFAULT_STORAGE_FILE))
        self._queue = Queue(config)
        self._media = Media()
        self._keywords_filter = KeywordsFilter(config)

    def _format_toot(self, post: dict, origin: str, site_options: dict) -> str:

        title = post["title"]
        title_only_chars = re.sub("^[A-Za-z]*", "", title)
        if title_only_chars == title_only_chars.upper():
            title = " ".join([word.capitalize() for word in title.lower().split(" ")])
        link = post["link"]
        summary = post["summary"] + "\n\n" if "summary" in post and post["summary"] and post["summary"] != "" else ""
        summary = ''.join(BeautifulSoup(summary, "html.parser").findAll(text=True))
        summary = summary.replace("\n\n\n", "\n\n")
        summary = re.sub("\s+", ' ', summary)
        max_length = site_options["max_summary_length"] \
            if "max_summary_length" in site_options and site_options["max_summary_length"] \
                else self.MAX_SUMMARY_LENGTH
        summary = (summary[:max_length] + '...') if len(summary) > max_length+3 else summary

        text = f"{origin}:\n" if "show_name" in site_options and site_options["show_name"] else ""
        
        return f"{text}\t{title}\n\n{summary}\n\n{link}"
    
    def _parse_media(self, post: dict) -> dict:

        # Initiate
        result = []

        # Discover if we have a link to an image
        images = self._media.get_image_url_from_text(post["summary"])

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

            keywords_filter_profile = site["keywords_filter_profile"] \
                if "keywords_filter_profile" in site and site["keywords_filter_profile"] else None

            self._logger.info("Getting possible stored data for %s", site["name"])
            site_data = self._feeds_storage.get_hashed(site["url"], None)
        
            self._logger.info("Parsing site %s", site["name"])
            parsed_site = feedparser.parse(site["url"])

            if "language_overwrite" in site and "language_default" in site and site["language_default"] and site["language_overwrite"]:
                metadata = {"language": site["language_default"]}
            else:
                metadata = {
                    "language": parsed_site["feed"]["language"] if "language" in parsed_site["feed"] else site["language_default"]
                }

            if not "entries" in parsed_site or not parsed_site["entries"]:
                self._logger.warn("No entries in this feed, skipping.")

            self._logger.info("Sorting %d entries ASC", len(parsed_site["entries"]))
            posts = sorted(parsed_site["entries"], key=lambda x: x["published_parsed"])

            # Keep track of the post seen.
            urls_seen = site_data["urls_seen"] if site_data and "urls_seen" in site_data else []

            for post in posts:
                
                # Check if this post was already seen
                post_link = Url.clean(post["link"], {"scheme": True})
                if post_link in urls_seen:
                    self._logger.info("Discarding post: already seen %s", post["title"])
                    continue
                else:
                    urls_seen.append(post_link)
                
                # In some cases we don't have a 'summary', but a 'description' field
                if "summary" not in post and "description" in post:
                    self._logger.debug("Making out a [summary] from a [description]")
                    post["summary"] = post["description"]
                elif "summary" not in post and "description" not in post:
                    self._logger.debug("Could not fix not present [summary]. Discarding.")
                    continue
                
                # Only in case that we need to filter per keywords and the filtering bans the content.
                if keywords_filter_profile and \
                    not self._keywords_filter.profile_allows_text(
                        keywords_filter_profile,
                        post["summary"]):
                    self._logger.info("Filtering %s per keyword profile '%s', this Feed post is not allowed", site["name"], keywords_filter_profile)
                    continue

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
                self._logger.debug("The post [%s] made it to the end.", post["title"])
                media = self._parse_media(post)
                self._logger.debug("The post [%s] has %d media elements", post["title"], len(media))
                self._queue.append(
                    {
                        "status": self._format_toot(post, site["name"],site),
                        "media": media if media else None,
                        "language": metadata["language"],
                        "published_at": post_date,
                        "action": "new"
                    }
                )
                self._logger.debug("The post [%s] has been added tot he queue", post["title"])

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
            
            