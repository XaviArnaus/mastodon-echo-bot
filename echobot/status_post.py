from __future__ import annotations
from datetime import datetime
from strenum import LowercaseStrEnum


class StatusPost:
    """
    Object to manage the status posts to be published through the Mastodon API.
    Mastodon.py wrapper version 1.8.0

    Should support Pleroma variations
    """

    status: str = None
    in_reply_to_id: int = None
    media_ids: list[int] = None
    sensitive: bool = None
    visibility: StatusPostVisibility = None
    spoiler_text: str = None
    language: str = None
    idempotency_key: str = None
    content_type: StatusPostContentType = None
    scheduled_at: datetime = None
    poll: any = None  # Poll not supported. It should be here a Poll object
    quote_id: int = None

    def __init__(
        self,
        status: str = None,
        in_reply_to_id: int = None,
        media_ids: list[int] = None,
        sensitive: bool = None,
        visibility: StatusPostVisibility = None,
        spoiler_text: str = None,
        language: str = None,
        idempotency_key: str = None,
        content_type: StatusPostContentType = None,
        scheduled_at: datetime = None,
        poll: any = None,
        quote_id: int = None
    ) -> None:

        self.status = status
        self.in_reply_to_id = in_reply_to_id
        self.media_ids = media_ids
        self.sensitive = sensitive if sensitive is not None else False
        self.visibility = visibility if visibility is not None\
            else StatusPostVisibility.PUBLIC
        self.spoiler_text = spoiler_text
        self.language = language
        self.idempotency_key = idempotency_key
        self.content_type = content_type if content_type is not None\
            else StatusPostContentType.PLAIN
        self.scheduled_at = scheduled_at
        self.poll = poll
        self.quote_id = quote_id

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "in_reply_to_id": self.in_reply_to_id,
            "media_ids": self.media_ids,
            "sensitive": self.sensitive,
            "visibility": self.visibility,
            "spoiler_text": self.spoiler_text,
            "language": self.language,
            "idempotency_key": self.idempotency_key,
            "content_type": self.content_type,
            "scheduled_at": self.scheduled_at.timestamp()
            if self.scheduled_at is not None else None,
            "poll": self.poll,
            "quote_id": self.quote_id,
        }

    def from_dict(status_post_dict: dict) -> StatusPost:
        return StatusPost(
            status_post_dict["status"] if "status" in status_post_dict else None,
            status_post_dict["in_reply_to_id"]
            if "in_reply_to_id" in status_post_dict else None,
            status_post_dict["media_ids"] if "media_ids" in status_post_dict else None,
            status_post_dict["sensitive"] if "sensitive" in status_post_dict else None,
            StatusPostVisibility.valid_or_raise(status_post_dict["visibility"])
            if "visibility" in status_post_dict else None,
            status_post_dict["spoiler_text"] if "spoiler_text" in status_post_dict else None,
            status_post_dict["language"] if "language" in status_post_dict else None,
            status_post_dict["idempotency_key"]
            if "idempotency_key" in status_post_dict else None,
            StatusPostContentType.valid_or_raise(status_post_dict["content_type"])
            if "content_type" in status_post_dict else None,
            datetime.fromtimestamp(status_post_dict["scheduled_at"])
            if "scheduled_at" in status_post_dict else None,
            status_post_dict["poll"] if "poll" in status_post_dict else None,
            status_post_dict["quote_id"] if "quote_id" in status_post_dict else None,
        )


class StatusPostVisibility(LowercaseStrEnum):
    """
    The visibility parameter is a string value and accepts any of:

    "direct" - post will be visible only to mentioned users
    "private" - post will be visible only to followers
    "unlisted" - post will be public but not appear on the public timeline
    "public" - post will be public
    """
    DIRECT = "direct"
    PRIVATE = "private"
    UNLISTED = "unlisted"
    PUBLIC = "public"

    def valid_or_raise(value: str) -> StatusPostVisibility:
        valid_items = [
            StatusPostVisibility.DIRECT,
            StatusPostVisibility.PRIVATE,
            StatusPostVisibility.UNLISTED,
            StatusPostVisibility.PUBLIC
        ]

        if value not in valid_items:
            raise RuntimeError(f"Value [{value}] is not a valid StatusPostVisibility")

        return value


class StatusPostContentType(LowercaseStrEnum):
    """
    Specific to “pleroma” feature set:: Specify content_type
    to set the content type of your post on Pleroma. It accepts:

    "text/plain" (default)
    "text/markdown"
    "text/html"
    "text/bbcode"

    This parameter is not supported on Mastodon servers, but will be safely ignored if set.
    """

    PLAIN = "text/plain"
    MARKDOWN = "text/markdown"
    HTML = "text/html"
    BBCODE = "text/bbcode"

    def valid_or_raise(value: str) -> StatusPostContentType:
        valid_items = [
            StatusPostContentType.PLAIN,
            StatusPostContentType.MARKDOWN,
            StatusPostContentType.HTML,
            StatusPostContentType.BBCODE
        ]

        if value not in valid_items:
            raise RuntimeError(f"Value [{value}] is not a valid StatusPostContentType")

        return value
