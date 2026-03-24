import json
import logging

import httpx

from app.core.config import settings
from app.redis.redis_client import RedisClient

logger = logging.getLogger(__name__)

REDDIT_CACHE_TTL = 600  # 10 minutes


class RedditService:
    """
    Fetches posts from Reddit using OAuth2 app-only auth,
    converts them to the same format as YouTube comments,
    and caches results in Redis.
    """

    TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
    BASE_URL = "https://oauth.reddit.com"
    USER_AGENT = "random-thoughts-trend-bot/1.0"

    def __init__(self):
        self.client_id = settings.REDDIT_CLIENT_ID
        self.client_secret = settings.REDDIT_CLIENT_SECRET
        self.redis = RedisClient()
        self._access_token: str | None = None

    # ------------------------------------------------------------------ #
    #  OAuth2 — app-only (client_credentials)                              #
    # ------------------------------------------------------------------ #

    async def _authenticate(self) -> str:
        """Obtain an app-only OAuth2 bearer token from Reddit."""
        if self._access_token:
            return self._access_token

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                self.TOKEN_URL,
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": self.USER_AGENT},
            )
            resp.raise_for_status()
            self._access_token = resp.json()["access_token"]
            return self._access_token

    # ------------------------------------------------------------------ #
    #  Core fetcher                                                        #
    # ------------------------------------------------------------------ #

    async def fetch_reddit_posts(
        self, subreddit: str, limit: int = 20
    ) -> list[dict]:
        """
        Fetch hot posts from a subreddit.

        Returns
        -------
        list[dict]
            Each dict has keys: "text" (str) and "likes" (int).
            This is the SAME format CommentTopicExtractor expects.
        """

        # ---------- check cache first ----------
        cache_key = f"reddit:{subreddit}:{limit}"
        cached = await self.redis.get(cache_key)
        if cached:
            logger.info("Reddit cache HIT for r/%s", subreddit)
            return json.loads(cached)

        logger.info("Reddit cache MISS — fetching r/%s from API", subreddit)

        # ---------- authenticate ----------
        token = await self._authenticate()

        # ---------- fetch from Reddit ----------
        url = f"{self.BASE_URL}/r/{subreddit}/hot.json"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                url,
                params={"limit": limit},
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": self.USER_AGENT,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        # ---------- convert to pipeline format ----------
        posts: list[dict] = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            title = post.get("title", "")
            selftext = post.get("selftext", "")
            ups = post.get("ups", 0)

            text = f"{title} {selftext}".strip()
            if text:
                posts.append({"text": text, "likes": ups})

        # ---------- cache ----------
        await self.redis.set(cache_key, json.dumps(posts), expire=REDDIT_CACHE_TTL)
        logger.info("Cached %d posts from r/%s", len(posts), subreddit)

        return posts
