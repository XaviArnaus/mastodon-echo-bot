from __future__ import annotations
from echobot.objects.status_post import StatusPostContentType, StatusPostVisibility


class MastodonConnectionParams():

    TYPE_MASTODON = "mastodon"
    TYPE_PLEROMA = "pleroma"
    TYPE_FIREFISH = "firefish"

    VALID_TYPES = [TYPE_MASTODON, TYPE_PLEROMA, TYPE_FIREFISH]

    DEFAULT_INSTANCE_TYPE = TYPE_MASTODON

    app_name: str
    instance_type: str
    api_base_url: str
    credentials: MastodonCredentials
    status_params: MastodonStatusParams

    def __init__(
        self,
        app_name: str = None,
        instance_type: str = None,
        api_base_url: str = None,
        credentials: MastodonCredentials = None,
        status_params: MastodonStatusParams = None
    ) -> None:
        self.app_name = app_name
        self.instance_type = instance_type\
            if instance_type is not None else self.DEFAULT_INSTANCE_TYPE
        self.api_base_url = api_base_url
        self.credentials = credentials
        # Status Params has always to come, even with the default values
        if status_params is None:
            self.status_params = MastodonStatusParams()
        else:
            self.status_params = status_params

    def to_dict(self) -> dict:
        return {
            "app_name": self.app_name,
            "instance_type": self.instance_type,
            "api_base_url": self.api_base_url,
            "credentials": self.credentials.to_dict()
            if isinstance(self.credentials, MastodonCredentials) else None,
            "status_params": self.status_params.to_dict()
            if isinstance(self.status_params, MastodonStatusParams) else None
        }

    @staticmethod
    def from_dict(connection_params_dict: dict) -> MastodonConnectionParams:
        return MastodonConnectionParams(
            app_name=connection_params_dict["app_name"]
            if "app_name" in connection_params_dict else None,
            instance_type=connection_params_dict["instance_type"]
            if "instance_type" in connection_params_dict else None,
            api_base_url=connection_params_dict["api_base_url"]
            if "api_base_url" in connection_params_dict else None,
            credentials=MastodonCredentials.from_dict(connection_params_dict["credentials"])
            if "credentials" in connection_params_dict else None,
            status_params=MastodonStatusParams.from_dict(
                connection_params_dict["status_params"]
            ) if "status_params" in connection_params_dict and
            connection_params_dict["status_params"] is not None else None
        )


class MastodonCredentials():

    DEFAULT_USER_FILE = "user.secret"
    DEFAULT_CLIENT_FILE = "client.secret"

    user_file: str
    client_file: str
    user: MastodonUser

    def __init__(
        self,
        user_file: str = None,
        client_file: str = None,
        user: MastodonUser = None
    ) -> None:
        self.user_file = user_file\
            if user_file is not None else self.DEFAULT_USER_FILE
        self.client_file = client_file\
            if client_file is not None else self.DEFAULT_CLIENT_FILE
        self.user = user

    def to_dict(self) -> dict:
        return {
            "user_file": self.user_file,
            "client_file": self.client_file,
            "user": self.user.to_dict() if isinstance(self.user, MastodonUser) else None
        }

    @staticmethod
    def from_dict(credentials_dict: dict) -> MastodonCredentials:
        return MastodonCredentials(
            user_file=credentials_dict["user_file"]
            if "user_file" in credentials_dict else None,
            client_file=credentials_dict["client_file"]
            if "client_file" in credentials_dict else None,
            user=MastodonUser.from_dict(credentials_dict["user"])
            if "user" in credentials_dict else None
        )


class MastodonUser():

    email: str
    password: str

    def __init__(self, email: str = None, password: str = None) -> None:
        self.email = email
        self.password = password

    def to_dict(self) -> dict:
        return {"email": self.email, "password": self.password}

    @staticmethod
    def from_dict(credentials_dict: dict) -> MastodonUser:
        return MastodonUser(
            email=credentials_dict["email"] if "email" in credentials_dict else None,
            password=credentials_dict["password"] if "password" in credentials_dict else None
        )


class MastodonStatusParams():

    DEFAULT_MAX_LENGTH = 500
    DEFAULT_CONTENT_TYPE = StatusPostContentType.PLAIN
    DEFAULT_VISIBILITY = StatusPostVisibility.PUBLIC

    max_length: int
    content_type: StatusPostContentType
    visibility: StatusPostVisibility
    username_to_dm: str

    def __init__(
        self,
        max_length: int = None,
        content_type: StatusPostContentType = None,
        visibility: StatusPostVisibility = None,
        username_to_dm: str = None
    ) -> None:
        self.max_length = max_length if max_length is not None else self.DEFAULT_MAX_LENGTH
        self.content_type = StatusPostContentType.valid_or_raise(content_type)\
            if content_type is not None else self.DEFAULT_CONTENT_TYPE
        if visibility is None:
            self.visibility = self.DEFAULT_VISIBILITY
        else:
            self.visibility = StatusPostVisibility.valid_or_raise(visibility)
            if self.visibility == StatusPostVisibility.DIRECT\
               and username_to_dm is None:
                raise ValueError(
                    "The field username_to_dm is mandatory if visibility" +
                    f" is {StatusPostVisibility.DIRECT}"
                )
        self.username_to_dm = username_to_dm

    def to_dict(self) -> dict:
        return {
            "max_length": self.max_length,
            "content_type": self.content_type,
            "visibility": self.visibility,
            "username_to_dm": self.username_to_dm
        }

    @staticmethod
    def from_dict(status_params: dict) -> MastodonStatusParams:
        return MastodonStatusParams(
            max_length=status_params["max_length"] if "max_length" in status_params else None,
            content_type=status_params["content_type"]
            if "content_type" in status_params else None,
            visibility=status_params["visibility"] if "visibility" in status_params else None,
            username_to_dm=status_params["username_to_dm"]
            if "username_to_dm" in status_params else None
        )
