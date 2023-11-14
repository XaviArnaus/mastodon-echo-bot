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
from ensta import Host
import logging
import re
from pyxavi.debugger import dd


class InstagramParser:
    '''
    Bla
    '''
    # MAX_SUMMARY_LENGTH = 300
    DEFAULT_STORAGE_FILE = "storage/instagram.yaml"
    MAX_POSTS_TO_RETRIEVE = 10

    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._instagram_storage = Storage(
            config.get("instagram_parser.storage_file", self.DEFAULT_STORAGE_FILE)
        )
        self._queue = Queue(config)
        # self._media = Media()
        # self._keywords_filter = KeywordsFilter(config)

        # Initialize Instagram Parser
        self._host = Host(
            config.get("instagram_parser.credentials.username"),
            config.get("instagram_parser.credentials.password")
        )

    # def _format_toot(self, post: dict, origin: str, insta_account_options: dict) -> str:

    #     title = post["title"]
    #     title_only_chars = re.sub("^[A-Za-z]*", "", title)
    #     if title_only_chars == title_only_chars.upper():
    #         title = " ".join([word.capitalize() for word in title.lower().split(" ")])
    #     link = post["link"]
    #     summary = post["summary"] + "\n\n" if "summary" in post and post[
    #         "summary"] and post["summary"] != "" else ""
    #     summary = ''.join(BeautifulSoup(summary, "html.parser").findAll(text=True))
    #     summary = summary.replace("\n\n\n", "\n\n")
    #     summary = re.sub("\\s+", ' ', summary)
    #     max_length = insta_account_options["max_summary_length"] \
    #         if "max_summary_length" in insta_account_options and insta_account_options["max_summary_length"] \
    #         else self.MAX_SUMMARY_LENGTH
    #     summary = (summary[:max_length] + '...') if len(summary) > max_length + 3 else summary

    #     text = f"{origin}:\n" if "show_name" in insta_account_options and insta_account_options["show_name"
    #                                                                           ] else ""

    #     return f"{text}\t{title}\n\n{summary}\n\n{link}"

    # def _parse_media(self, post: dict) -> dict:

    #     # Initiate
    #     result = []

    #     # Discover if we have a link to an image
    #     images = self._media.get_image_url_from_text(post["summary"])

    #     if images:
    #         for image_object in images:
    #             result.append(
    #                 {
    #                     "url": image_object["url"],
    #                     "alt_text": image_object["alt_text"]
    #                     if image_object["alt_text"] else None
    #                 }
    #             )

    #     return result

    def parse(self) -> None:

        # Do we have insta_accounts defined?
        accounts_params = self._config.get("instagram_parser.accounts", None)
        if not accounts_params:
            self._logger.info("No instagram accounts registered to parse, skipping,")
            return

        # For each user in the config
        for insta_account in accounts_params:

            self._logger.info("Getting possible stored data for %s", insta_account["user"])
            insta_account_data = self._instagram_storage.get_hashed(insta_account["user"], None)

            self._logger.info("Parsing Instagram account %s", insta_account["user"])
            posts = self._host.posts(insta_account["user"], self.MAX_POSTS_TO_RETRIEVE)

            for post in posts:
                dd(post, max_depth=1)
                if post.media_type != 2:
                    # 2 is video.
                    # 8 is photo (album of 10?)
                    exit()
                #(Post){
                # "instance": (Host)Max recursion depth of 1 reached.,
                # "share_url": (str[39])"https://www.instagram.com/p/CzjlHqbIHUd",
                # "taken_at": (int)1699813621,
                # "unique_key": (str[19])"3234592211691664669",
                # "media_type": (int)2,
                # "code": (str[11])"CzjlHqbIHUd",
                # "caption_is_edited": (bool)True,
                # "original_media_has_visual_reply_media": (bool)False,
                # "like_and_view_counts_disabled": (bool)False,
                # "can_viewer_save": (bool)True,
                # "profile_grid_control_enabled": (bool)False,
                # "is_comments_gif_composer_enabled": (bool)True,
                # "comment_threading_enabled": (bool)True,
                # "comment_count": (int)10,
                # "has_liked": (bool)False,
                # "user": (PostUser){
                #     "has_anonymous_profile_picture": (bool)False,
                #     "fbid_v2": (str[17])"17841401293695516",
                #     "transparency_product_enabled": (bool)False,
                #     "is_favorite": (bool)False,
                #     "is_unpublished": (bool)False,
                #     "uid": (str[9])"353067123",
                #     "username": (str[21])"centrehipic_talamanca",
                #     "full_name": (str[46])"Centre Rescat Hípic Talamanca | Vivirenmanada",
                #     "is_private": (bool)False,
                #     "is_verified": (bool)False,
                #     "profile_picture_id": (str[29])"2171090667450127739_353067123",
                #     "profile_picture_url": (str[311])"https://scontent-ham3-1.cdninstagram.com/v/t51.2885-19/72774649_595000187704787_3871794158419050496_n.jpg?stp=dst-jpg_s150x150&_nc_ht=scontent-ham3-1.cdninstagram.com&_nc_cat=111&_nc_ohc=sNlQcXpvze4AX9rkyZG&edm=ACWDqb8BAAAA&ccb=7-5&oh=00_AfBGRxi-PBaLcyDYsGrgs7cNCD0GUpUJK6TkPlNOx0mS8A&oe=655807B8&_nc_sid=ee9879",
                #     "account_badges": (list[0])[],
                #     "feed_post_reshare_disabled": (bool)False,
                #     "show_account_transparency_details": (bool)True,
                #     "third_party_downloads_enabled": (int)1,
                #     "latest_reel_media": (int)0,
                #     class methods: 
                # },
                # "can_viewer_reshare": (bool)True,
                # "like_count": (int)889,
                # "top_likers": (list[0])[],
                # "caption_text": (str[570])"text text text text text text text text text",
                # "is_caption_covered": (bool)False,
                # "caption_created_at": (int)1699872076,
                # "caption_share_enabled": (bool)False,
                # "caption_did_report_as_spam": (bool)False,
                # "is_paid_partnership": (bool)True,
                # "show_shop_entrypoint": (bool)False,
                # "deleted_reason": (int)0,
                # "integrity_review_decision": (str[7])"pending",
                # "ig_media_sharing_disabled": (bool)False,
                # "has_shared_to_fb": (int)0,
                # "is_unified_video": (bool)False,
                # "should_request_ads": (bool)False,
                # "is_visual_reply_commenter_notice_enabled": (bool)True,
                # "commerciality_status": (str[14])"not_commercial",
                # "explore_hide_comments": (bool)False,
                # "has_delayed_metadata": (bool)False,
                # "location_latitude": (float)41.7365664,
                # "location_longitude": (float)1.9741145,

            # if "language_default" in insta_account and insta_account["language_default"]:
            #     metadata = {"language": insta_account["language_default"]}
            # else:
            #     pass

            # if "entries" not in parsed_insta_account or not parsed_insta_account["entries"]:
            #     self._logger.warn("No entries in this feed, skipping.")

            # self._logger.info("Sorting %d entries ASC", len(parsed_insta_account["entries"]))
            # posts = sorted(parsed_insta_account["entries"], key=lambda x: x["published_parsed"])

            # # Keep track of the post seen.
            # urls_seen = insta_account_data["urls_seen"] if insta_account_data and "urls_seen" in insta_account_data else []

            # for post in posts:

            #     # Check if this post was already seen
            #     post_link = Url.clean(post["link"], {"scheme": True})
            #     if post_link in urls_seen:
            #         self._logger.info("Discarding post: already seen %s", post["title"])
            #         continue
            #     else:
            #         urls_seen.append(post_link)

            #     # In some cases we don't have a 'summary', but a 'description' field
            #     if "summary" not in post and "description" in post:
            #         self._logger.debug("Making out a [summary] from a [description]")
            #         post["summary"] = post["description"]
            #     elif "summary" not in post and "description" not in post:
            #         self._logger.debug("Could not fix not present [summary]. Discarding.")
            #         continue

            #     # Only in case that we need to filter per
            #     #   keywords and the filtering bans the content.
            #     if keywords_filter_profile and \
            #         not self._keywords_filter.profile_allows_text(
            #             keywords_filter_profile,
            #             post["summary"]):
            #         self._logger.info(
            #             "Filtering %s per keyword profile '%s', this Feed post is not allowed",
            #             insta_account["user"],
            #             keywords_filter_profile
            #         )
            #         continue

            #     # Calculate post date
            #     post_date = None
            #     if "published_parsed" in post and post["published_parsed"]:
            #         post_date = datetime.fromtimestamp(mktime(post["published_parsed"])
            #                                            ).replace(tzinfo=pytz.UTC)
            #     elif "published" in post and post["published"]:
            #         post_date = parser.parse(post["published"])
            #     else:
            #         self._logger.warn(
            #             "Discarding post: no usable published date, can't rely on it"
            #         )
            #         continue

            #     # We don't want anything older than 6 months
            #     #   and also older of the last entry we have registered
            #     if datetime.now().replace(tzinfo=pytz.UTC) - relativedelta(months=6
            #                                                                ) > post_date:
            #         self._logger.info("Discarding post: too old %s", post_date)
            #         continue

            #     # Prepare the new toot
            #     self._logger.debug("The post [%s] made it to the end.", post["title"])
            #     media = self._parse_media(post)
            #     self._logger.debug(
            #         "The post [%s] has %d media elements", post["title"], len(media)
            #     )
            #     self._queue.append(
            #         {
            #             "status": self._format_toot(post, insta_account["user"], insta_account),
            #             "media": media if media else None,
            #             "language": metadata["language"],
            #             "published_at": post_date,
            #             "action": "new"
            #         }
            #     )
            #     self._logger.debug("The post [%s] has been added tot he queue", post["title"])

        #     # Update our storage with what we found
        #     self._logger.debug("Updating gathered insta_account data for %s", insta_account["user"])
        #     self._feeds_storage.set_hashed(insta_account["url"], {"urls_seen": urls_seen})
        #     self._logger.info("Storing data for %s", insta_account["user"])
        #     self._feeds_storage.write_file()

        # # Update the toots queue, by adding the new ones at the end of the list
        # self._queue.update()
