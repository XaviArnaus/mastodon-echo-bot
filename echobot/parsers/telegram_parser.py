from pyxavi.config import Config
from pyxavi.storage import Storage
from pyxavi.terminal_color import TerminalColor
from pyxavi.queue_stack import Queue, SimpleQueueItem
from echobot.lib.queue_post import QueuePost, QueuePostMedia
from echobot.parsers.parser_protocol import ParserProtocol
from telethon import TelegramClient
from telethon.types import Message as TelegramMessage
import logging
from datetime import datetime, timedelta
from string import Template
from dateutil.relativedelta import relativedelta
import pytz
import math
import copy
from hashlib import sha1
from pyxavi.debugger import dd


class TelegramParser(ParserProtocol):

    ACCEPTED_NUM_MONTHS_AGO = 6
    MAX_MEDIA_PER_STATUS = 4
    MAX_STATUS_LENGTH = 400
    DATE_FORMAT = "%Y-%m-%d"
    DEFAULT_TELEGRAM_FILE = "storage/telegram.yaml"
    # DEFAULT_QUEUE_FILE = "storage/queue.yaml"
    DEFAULT_LANGUAGE = "en"

    # Whatever we have in body, we thread info.
    TEMPLATE_THREAD_INFO = "🧵 $current/$total"
    TEMPLATE_BODY_WITH_THREAD = "$body\n\n$thread"
    # This template only adds origin into the body
    TEMPLATE_BODY_WITH_ORIGIN= "$origin\t$body"

    _telegram: TelegramClient

    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._chats_storage = Storage(
            self._config.get("telegram_parser.storage_file", self.DEFAULT_TELEGRAM_FILE)
        )
        # The ID here that is coming as "chat_id" is actually an "entity.id"
        #   Remember this when referring by source
        self._sources = {x["name"]: x for x in self._get_conversations()}
        self._sources_name_to_id = {x["name"]: str(abs(x["id"])) for x in self._get_conversations()}
        self._already_seen = {} # type: dict[str, list]
        # self._queue = Queue(
        #     logger=self._logger,
        #     storage_file=config.get("toots_queue_storage.file", self.DEFAULT_QUEUE_FILE)
        # )
        self._max_media_per_status = self._config.get(
            "default.max_media_per_status",
            self.MAX_MEDIA_PER_STATUS
        )
        self._max_status_length = self._config.get(
            "default.max_length",
            self.MAX_STATUS_LENGTH
        )
        self._telegram = self._initialize_client()
        
    
    def get_sources(self) -> dict:
        return self._sources

    def _initialize_client(self) -> TelegramClient:
        api_id = self._config.get("telegram_parser.api_id")
        api_hash = self._config.get("telegram_parser.api_hash")
        session_name = self._config.get(
            "telegram_parser.session_name", self._config.get("app.name", "echo bot")
        )

        self._logger.debug("Setting up Telegram Client, reusing if exists...")
        client = TelegramClient(
            session_name, api_id, api_hash, base_logger=self._logger
        ).start()
        self._logger.debug("Telegram Client is set up")

        return client
    
    def _get_conversations(self) -> list:
        # Chats and channels are managed equally, but under different entities.
        chats = self._config.get("telegram_parser.chats", [])
        chats += self._config.get("telegram_parser.channels", [])
        return chats
    
    def get_raw_content_for_source(self, source: str, params: dict = None) -> list[QueuePost]:
        """
        The Telegram wrapper is reactive. You can't parse a list of messages but
        react on an incomming message.
        """

        # Do we have this source defined?
        if source not in self._sources:
            raise RuntimeError(f"Source of data [{source}] not found.")
        
        # Initialisation
        ignore_offsets = self._config.get("telegram_parser.ignore_offsets", False)
        date_to_start_from = self._config.get("telegram_parser.date_to_start_from", None)
        offset_date = datetime.strptime(
            date_to_start_from,
            self.DATE_FORMAT
        ) if date_to_start_from else None
        language = self._sources[source]["language"] if "language" in self._sources[source]\
                      else self.DEFAULT_LANGUAGE

        # We only need the chat IDs to then retrieve later the Entities.
        # chat_ids = list(
        #     filter(
        #         bool, [abs(chat["id"]) if "id" in chat else False\
        #                for chat in self._get_conversations()]
        #     )
        # )
        # Also, build a dict for the configuration
        # chats_params = {}
        # for chat in self._get_conversations():
        #     chats_params[str(abs(chat["id"]))] = chat
        # The following is discarded because we're gathering per source, not all
        #   in one shot: chat_ids and entities
        # chat_ids = list(map(lambda x: int(x), self._sources.keys()))
        # # Get the entities that match with the given IDs.
        # self._logger.debug("Get matching entities from the current user's dialogs")
        # entities = list(
        #     filter(
        #         bool,
        #         [
        #             dialog.entity if dialog.entity.id in chat_ids else False
        #             for dialog in self._telegram.iter_dialogs()
        #         ]
        #     )
        # )
        entities = list(
            filter(
                bool,
                [
                    dialog.entity\
                        if dialog.entity.id == self.__get_entity_id_from_source(source)\
                        else False for dialog in self._telegram.iter_dialogs()
                ]
            )
        )

        # If no entities found, return.
        logger_string = f"Got {len(entities)} entities."
        if not entities:
            logger_string += " Returning."
            self._logger.debug(logger_string)
            return []
        self._logger.debug(logger_string)

        # Now work with the messages for each entity
        for entity in entities:

            # What comes now is a gathering of information that will be used
            #   to request for the message for this entity.
            source_name = self.__get_source_name_from_entity_id(entity.id)
            seen_message_ids = self._already_seen[source_name]\
                if source_name in self._already_seen else []

            # First we get all messages in queue.
            # We must use the iter_messages to avoid using asyncs
            messages_to_post = []
            # Retrieving messages:
            #   reverse=True -> from oldest to newest, to keep the posting order
            #   offset_id -> avoid retrieving messages that we already know
            #   offset_date -> avoid retrieving messages older than the given datetime
            for message in self._telegram.iter_messages(
                    entity=entity,
                    reverse=True,
                    offset_id=max(seen_message_ids)
                    if seen_message_ids and not ignore_offsets else 0,
                    offset_date=offset_date if offset_date and not ignore_offsets else None):
                
                # Filtering out messages for diverse reasons happen in the caller
                #   therefore here we only pack the object
                messages_to_post.append(
                    QueuePost(
                        id=message.id,
                        raw_content={
                            "telegram_message": message,
                            "telegram_entity": entity
                        },
                        raw_combined_content=message.text,
                        published_at=message.date,
                        language=language
                    )
                )
        
        return messages_to_post
    

    def __get_entity_id_from_source(self, source: str) -> int:
        return self._sources_name_to_id[source]
    
    def __get_source_name_from_entity_id(self, entity_id: int) -> str:
        return list(self._sources_name_to_id.keys())[list(self._sources_name_to_id.values()).index(entity_id)]

    def __load_already_seen_for_source(self, source: str) -> None:

        entity_id = self.__get_entity_id_from_source(source)

        self._logger.debug("Getting possible stored data for %s", source)
        # It was: list(self._chats_storage.get(f"entity_{entity.id}", []))
        self._already_seen[source] = list(self._chats_storage.get(f"entity_{entity_id}", []))
    

    def is_id_already_seen_for_source(self, source: str, id: any) -> bool:
        """Identifies if this ID is already registered in the state"""

        if source not in self._already_seen or self._already_seen[source] is None:
            self.__load_already_seen_for_source(source)
        
        return True if id in self._already_seen[source] else False

    def set_ids_as_seen_for_source(self, source: str, list_of_ids: list) -> None:
        """Performs the saving of the seen state"""
        
        for new_message_id in list_of_ids:
            self._already_seen[source].append(new_message_id)
        
        self._logger.debug(f"Updating seen Message IDs for {source}")
        self._chats_storage.set(
            f"entity_{self.__get_entity_id_from_source(source)}",
            self._already_seen[source]
        )
        self._chats_storage.write_file()
    
    def post_process_for_source(self, source: str, posts: list[QueuePost]) -> list[QueuePost]:
        
        # TODO: elif 1 single post or 1 post per entity just return it
        if len(posts) == 0:
            self._logger.info("No messages to publish")
            return []
        else:
            self._logger.info(f"Received {len(posts)} messages to publish.")

            # Now we need to group messages, as images are sent one per message,
            # if we have an original message with several pictures we'll receive
            # several messages with one picture with a very short time in between.
            self._logger.debug("Grouping the messages.")
            grouped_posts = self._group_posts(posts=posts)
            self._logger.info(f"There are {len(grouped_posts)} groups of posts.")

            # Lastly we loop the grouped messages and send each group to be posted,
            # which means an async task that downloads all possible media, builds and
            # formats the posts and sends them to the Mastodon API
            self._logger.debug("Starting post preparation process")
            final_stack_of_posts = []
            for group_of_posts in grouped_posts:

                # From here on we make it async, because we need the media downloaded
                # and attached to the message, and the lib functions are async.
                self._logger.debug(
                    f"Preparing group of {len(group_of_posts)} post(s)."
                )
                # self.post_group_of_messages(
                #     messages=group_of_messages,
                #     entity=entity,
                #     chat_params=self._sources[source]
                # )
                posts_to_publish = self._process_group_of_posts_for_source(source, group_of_posts)
                final_stack_of_posts = final_stack_of_posts + posts_to_publish
            
            return final_stack_of_posts
    
    def _group_posts(self, posts: list[QueuePost]) -> list[list]:

        # In the previous implementation we did not have a wrapping QueuePost object, it was
        #   direct TelegramMessage objects.
        #   Now,
        #   - post.published_at contains the old message.date
        #   - post.raw_content["telegram_message"] contains the whole message, therefore
        #       post.raw_content["telegram_message"].text contains the text
        #
        #   We want to keep the wrapping object as it contains also the Entity
        #   where the message belongs to.
        #
        #   WARNING! TODO!
        #   The grouping can only happen within the same entity!

        groups = []
        current_group = []
        last_post = None
        for post in posts:
            # If we don't have a last post, it's the first post
            if last_post is None:
                self._logger.debug(f"Post {post.published_at} is the first one. Creating group.")
                last_post = post
                current_group.append(post)
            else:
                # This is a new group if:
                # - The date diff between last post and this post is more than a minute.
                # OR
                # - This post has text
                if last_post.published_at + timedelta(0, 0, 0, 0, 1) < post.published_at \
                   or (post.raw_content["telegram_message"].text is not None\
                   and len(post.raw_content["telegram_message"].text) > 0):
                    # We need to close the current group and start a new one
                    self._logger.debug(
                        f"Post {post.published_at} requires a new group. Creating."
                    )
                    groups.append(current_group)
                    current_group = []

                # Now add this post to the current group.
                # It will be a new group if the previous check reset it.
                self._logger.debug(
                    f"Added {post.published_at} into a group that has {len(current_group)} elements"
                )
                current_group.append(post)
                last_post = post

        # Outside the loop, if we still have a current group, we merge it.
        groups.append(current_group)

        return groups
    
    def _process_group_of_posts_for_source(self, source: str, posts: list[QueuePost]):

        # The responsibility of this one is:
        #   - Unroll the text into the amount of posts needed by the defined max_length
        #   - Pack the possible media into the amount of media per post defined
        #   - Link all the posts in a group with a same group id so that
        #       later we post them together
        #
        # Why is that?
        #   - We receive ONE message that may contain a lot of text. Needs to be split.
        #   - We may receive A LOT of empty messages that contain a single media.
        #       Mastodon allows until 4 media attachments per post. Needs packing.
        #
        # What happens with the current wrapping QueuePost objects and the Messages?
        #   - All wrapping QueuePost object will be gone. We'll create new ones.
        #
        # In the previous implementation:
        #   - We also downloaded the media here.
        #       Now is done from the runner just before queuing
        #   - We also added the message into the queue.
        #       Now is done from the runner
        #   - It was all about TelegramMessages.
        #       Now we play with the wrapper QueuePost object so we can pack
        #       other objects together

        # First of all let's accummulate all text and media.
        text = ""
        media_stack = []
        status_date = None
        language = None
        for post in posts:
            self._logger.debug(f"Post {post.id} in group")

            # Let's make us the life a bit easier...
            message = post.raw_content["telegram_message"]

            # Identify if this post is wrapping a message that contains an image.
            #   Remember, it can be a single media without text.
            if message.file is not None:
                media_stack.append(message)

            # Now add the text to the text stack
            if message.text is not None and len(message.text) > 0:
                text += f"\n\n{message.text}" if len(text) > 0 else message.text

            if status_date is None:
                status_date = message.date
            
            # Other data that we kept in the wrapper object
            language = post.language
        
        # Now, we split based on:
        # - The text may be too long
        # - The amount of media is more than 4 items
        num_of_statuses_by_text = num_of_statuses_by_media = 1
        max_status_length = self.__calculate_max_status_length()
        if len(media_stack) > self._max_media_per_status:
            num_of_statuses_by_media = math.ceil(len(media_stack) / self._max_media_per_status)
        if len(text) > max_status_length:
            num_of_statuses_by_text = math.ceil(len(text) / max_status_length)
        num_of_statuses = max(num_of_statuses_by_text, num_of_statuses_by_media)
        self._logger.debug(
            f"Ideal num of status: {num_of_statuses_by_text} for text" +
            f" and {num_of_statuses_by_media} for media." +
            f" Generating {num_of_statuses} statuses"
        )
        identification = sha1(text.encode()).hexdigest()

        # Now we execute the splitting and prepare the stack of Posts to publish
        posts_to_publish = []
        self._logger.debug(f"This group of status has the ID: {identification}")
        for idx in range(num_of_statuses):
            status_num = idx + 1

            # Take as max media as possible from the stack
            media_to_post = []
            while media_stack:
                media_to_post.append(media_stack.pop(0))
                if len(media_to_post) >= self.MAX_MEDIA_PER_STATUS:
                    break

            # Take as max text as possible from the stack
            #   Only if needed.
            if num_of_statuses > 1:
                text_to_post = Template(self.TEMPLATE_BODY_WITH_THREAD).substitute(
                    body=text[0:max_status_length],
                    thread=Template(self.TEMPLATE_THREAD_INFO).substitute(
                        current=status_num,
                        total=num_of_statuses
                    )
                )
                # Leave the remaining text
                if len(text) > max_status_length:
                    text = text[max_status_length:len(text)]
                else:
                    text = ""
            else:
                text_to_post = text

            # Finally we build the message to be posted
            posts_to_publish.append(
                QueuePost(
                    id=sha1(text_to_post.encode()).hexdigest(),
                    raw_content={
                        "body": text_to_post,
                        "telegram_media_messages": media_to_post
                    },
                    group=identification,
                    published_at=status_date,
                    language=language,
                )
            )
        
        return posts_to_publish

    def format_post_for_source(self, source: str, post: QueuePost) -> None:

         # Do we need to add the source name into the title?
        if "show_name" in self._sources[source] and self._sources[source]["show_name"]:
            body = Template(self.TEMPLATE_BODY_WITH_ORIGIN).substitute(
                origin=source,
                body=post.raw_content["body"]
            )
        else:
            body = post.raw_content["body"]
        
        post.text = body


    def __calculate_max_status_length(
            self,
            digits_current: int = 2,
            digits_total: int = 2
    ) -> int:

        max_length_wanted = self._max_status_length
        length_thread_suffix = len(Template(self.TEMPLATE_THREAD_INFO).substitute(
            current="".zfill(digits_current),
            total="".zfill(digits_total)
        )) + len("\n\n")
        return max_length_wanted - length_thread_suffix


    def parse_media(self, post: QueuePost) -> None:
        # Initialise first
        if post.media is None:
            post.media = []

        # Work if there's anything to work on
        if "telegram_media_messages" in post.raw_content and\
           len(post.raw_content["telegram_media_messages"]) > 0:
            for message in post.raw_content["telegram_media_messages"]:
                # Where to store it
                file_name = str(message.file.media.id)
                if message.file.name is not None:
                    file_name = message.file.name
                filename = f"storage/media/{file_name}.{message.file.ext}"
                # Use the Telegram's async functionality
                self._logger.debug(f"Downloading media to {filename}")
                path = self._loop_async_download(message=message, filename=filename)
                # Append a new Media object
                post.media.append(
                    QueuePostMedia(
                        path=path,
                        mime_type=message.file.mime_type
                    )
                )
    
    def _loop_async_download(self, message: TelegramMessage, filename: str) -> str:
        # This abstraction is only to be able to test
        return self._telegram.loop.run_until_complete(
            self._download_media(message=message, filename=filename)
        )

    async def _download_media(self, message: TelegramMessage, filename: str) -> None:
        # Download the media. Returns the path where it finally got downloaded.
        path = await self._telegram.download_media(message=message, file=filename)
        self._logger.debug(f"File {filename} has been downloaded")
        return path
