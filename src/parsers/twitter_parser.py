from bundle.config import Config
from bundle.storage import Storage
from datetime import timedelta
from tweepy import Client
import tweepy as twitter
import logging
import re
from bundle.debugger import dd

class TwitterParser:
    '''
    Parses the tweets from the registered twitter accounts
    and write in a queue list the content and other valuable data of the tweet to toot

    '''

    TWEET_FIELDS = ["lang", "created_at", "referenced_tweets", "id", "text"]
    URL_REGEX = "(http|ftp|https):\/\/([\w\-_]+(?:(?:\.[\w\-_]+)+))([\w\-\.,@?^=%&:/~\+#]*[\w\-\@?^=%&/~\+#])?"

    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(config.get("logger.name"))
        self._toots_queue = Storage(self._config.get("toots_queue_storage.file"))
        self._twitter_accounts = Storage(self._config.get("twitter_parser.storage_file"))

    def _format_toot(self, toot: dict, account: str) -> str:

        text = toot["text"]
        account_name = account["name"]
        account_username = account["user"]

        if "referenced" in toot and "user" in toot["referenced"]:
            original_username = toot["referenced"]["user"]["username"]
            original_name = toot["referenced"]["user"]["name"]

        if toot["type"] == "retweet":
            # Remove the "RT @username: "
            text = text.replace(f"RT @{original_username}: ", "")

            # Add an own text:
            text = f"{account_name} ({account_username}@twitter)\n\tha retuitejat de {original_name} (@{original_username}@twitter):\n\n{text}"
        elif toot["type"] == "quote":
            quoted_text = toot["referenced"]["text"]
            # Remove the quoted URL
            text_without_url = re.sub(self.URL_REGEX, "", text)

            # Add an own text:
            text = f"{account_name} ({account_username}@twitter) ha dit:\n{text_without_url}\n\n\tcitant a {original_name} (@{original_username}@twitter):\n{quoted_text}"
        elif toot["type"] == "reply":
            # Remove the "@username: "
            text = text.replace(f"{original_username} ", "")

            # Add an own text:
            text = f"{account_name} ({account_username}@twitter)\n\tha respost a {original_name} (@{original_username}@twitter):\n\n{text}"
        elif toot["type"] == "own":
            text = f"{account_name} ({account_username}@twitter) ha dit:\n\n{text}"

        # Now set the field that is used in the publisher
        toot["status"] = text

        return toot
    
    def _parse_tweet_response(self, tweet: dict) -> dict:
        result = {
            "id": tweet["id"],
            "text": tweet["text"],
            "published_at": tweet["created_at"],
            "language": tweet["lang"]
        }
 
        if "referenced_tweets" in tweet and tweet["referenced_tweets"]:
            result["reference_id"] = tweet["referenced_tweets"][0]["id"]
            if tweet["referenced_tweets"][0]["type"] == "replied_to":
                result["type"] = "reply"
            else:
                result["type"] = "retweet" if tweet["referenced_tweets"][0]["type"] == "retweeted" else "quote"
        else:
            result["type"] = "own"

        return result
    
    def _resolve_tweet_reference(self, client: Client, tweet_data: dict) -> dict:
        # Here we need to get the referenced tweet
        referenced = client.get_tweet(
            id=tweet_data["reference_id"],
            tweet_fields=self.TWEET_FIELDS,
            user_fields=["id", "name", "username", "url", "profile_image_url"],
            expansions=["referenced_tweets.id", "referenced_tweets.id.author_id"]
        )

        return {
            **tweet_data,
            **{
                "referenced": {
                    "id": referenced[0]["id"],
                    "text": referenced[0]["text"],
                    "published_at": referenced[0]["created_at"],
                    "language": referenced[0]["lang"],
                    "user": {
                        "name": referenced[1]["users"][0]["name"],
                        "username": referenced[1]["users"][0]["username"],
                        "id": referenced[1]["users"][0]["id"],
                        "profile_image_url": referenced[1]["users"][0]["profile_image_url"]
                    }
                },
            }
        }

    def parse(self) -> None:
        # This will contain the queue to toot
        toots_queue = []

        # Do we have accounts defined?
        accounts_params = self._config.get("twitter_parser.accounts", None)
        if not accounts_params:
            self._logger.info("No accounts registered to parse, skipping,")
            return

        client = twitter.Client(
            bearer_token=self._config.get("twitter_parser.bearer_token")
        )

        # For each user in the config
        for account_params in accounts_params:
            
            last_seen_tweet_date = None

            # Do we have any config relating this user already?
            self._logger.info("Getting possible stored data for %s", account_params["user"])
            user = self._twitter_accounts.get_hashed(account_params["user"])
            if user:
                self._logger.info("Reusing stored data for %s", account_params["user"])

                if not self._config.get("twitter_parser.ignore_tweets_offset") \
                    and user["last_seen_tweet_date"]:
                    last_seen_tweet_date = user["last_seen_tweet_date"]
            else:
                # Get the account ID from the given user string
                self._logger.info("Searching for %s", account_params["user"])
                user_queried = client.get_user(username=account_params["user"].replace("@", ""))

                if not user_queried:
                    self._logger.warn("No account found for %s, skipping", account_params["user"])
                    continue
                else:
                    user = {
                        "id": user_queried[0]["id"],
                        "name": user_queried[0]["name"],
                        "user": account_params["user"]
                    }

            # Get the tweets from the given account ID
            self._logger.info(
                "Getting max %d tweets from %s since %s",
                self._config.get("twitter_parser.max_tweets_to_retrieve", 10),
                user["user"],
                last_seen_tweet_date + timedelta(minutes=1) if last_seen_tweet_date else None
            )
            tweets = client.get_users_tweets(
                user["id"],
                max_results=self._config.get("twitter_parser.max_tweets_to_retrieve", 10),
                tweet_fields=self.TWEET_FIELDS,
                start_time=last_seen_tweet_date + timedelta(minutes=1) if last_seen_tweet_date else None
            )

            # If no toots, just go for the next account
            if tweets[3]["result_count"] == 0:
                self._logger.info("No tweets found, skipping")
                continue
            else:
                self._logger.info("got %s", len(tweets[0]))

            # We want to keep track of the last tweet seen
            last_seen_tweet_date = tweets[0][0]["created_at"]

            # For each status
            for tweet in tweets[0]:

                new_toot = self._parse_tweet_response(tweet)

                # Is an own tweet?
                if new_toot["type"] == "own" \
                    and account_params["tweets"]:
                    toots_queue.append(self._format_toot(new_toot, user))

                # Is a reply?
                if new_toot["type"] == "reply" \
                    and account_params["replies"]:
                    new_toot = self._resolve_tweet_reference(
                        client,
                        new_toot
                    )
                    toots_queue.append(self._format_toot(new_toot, user))

                # Is a retweet?
                if new_toot["type"] == "retweet" \
                    and account_params["retweets"]:
                    new_toot = self._resolve_tweet_reference(
                        client,
                        new_toot
                    )
                    toots_queue.append(self._format_toot(new_toot, user))

                # Is a quote?
                if new_toot["type"] == "quote" \
                    and account_params["quotes"]:
                    new_toot = self._resolve_tweet_reference(
                        client,
                        new_toot
                    )
                    toots_queue.append(self._format_toot(new_toot, user))

            # Update our storage with what we found
            self._logger.debug("Updating gathered account data for %s", user["user"])
            self._twitter_accounts.set_hashed(
                user["user"],
                {
                    "id": user["id"],
                    "name": user["name"],
                    "user": user["user"],
                    "last_seen_tweet_date": last_seen_tweet_date
                }
            )
            self._logger.info("Storing data for %s", user["user"])
            self._twitter_accounts.write_file()

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

        
            
            