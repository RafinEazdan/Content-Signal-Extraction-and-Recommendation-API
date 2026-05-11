import asyncio
import json
from datetime import datetime, timedelta

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.reddit_post import RedditTrendingPost
from app.redis.redis_client import RedisClient

CACHE_TTL = 3600     # Redis: 1 hour
DB_FRESHNESS = 7200  # DB tier: 2 hours

_RAPIDAPI_HEADERS = {
    "Content-Type": "application/json",
    "x-rapidapi-host": "reddit34.p.rapidapi.com",
    "x-rapidapi-key": settings.RAPIDAPI_KEY,
}


class RedditService:
    def __init__(self, db: Session, redis: RedisClient):
        self.db = db
        self.redis = redis

    # ------------------------------------------------------------------ #
    #  Public                                                              #
    # ------------------------------------------------------------------ #

    async def get_trending(self, mode: str, subreddits: list[str] | None) -> list[dict]:
        cache_key = self._build_cache_key(mode, subreddits)

        # Tier 1 — Redis
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # Tier 2 — DB
        posts = self._fetch_from_db(cache_key)
        if posts:
            await self.redis.set(cache_key, json.dumps(posts), expire=CACHE_TTL)
            return posts

        # Tier 3 — RapidAPI
        raw = await self._fetch_from_rapidapi(mode, subreddits)
        ranked = self._rank(raw)
        self._store_to_db(ranked, cache_key, mode)
        await self.redis.set(cache_key, json.dumps(ranked), expire=CACHE_TTL)
        return ranked

    # ------------------------------------------------------------------ #
    #  Private — cache key                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_cache_key(mode: str, subreddits: list[str] | None) -> str:
        if mode == "general":
            return "reddit:trending:general"
        subs = "+".join(sorted(s.lower() for s in subreddits))
        return f"reddit:trending:specific:{subs}"

    # ------------------------------------------------------------------ #
    #  Private — ranking                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _rank(posts: list[dict]) -> list[dict]:
        for p in posts:
            p["trend_score"] = round(p["upvotes"] + 0.5 * p["num_comments"], 2)
        return sorted(posts, key=lambda x: x["trend_score"], reverse=True)[:10]

    # ------------------------------------------------------------------ #
    #  Private — DB tier                                                   #
    # ------------------------------------------------------------------ #

    def _fetch_from_db(self, cache_key: str) -> list[dict] | None:
        cutoff = datetime.utcnow() - timedelta(seconds=DB_FRESHNESS)
        rows = (
            self.db.query(RedditTrendingPost)
            .filter(
                RedditTrendingPost.cache_key == cache_key,
                RedditTrendingPost.fetched_at > cutoff,
            )
            .order_by(RedditTrendingPost.trend_score.desc())
            .limit(10)
            .all()
        )
        if not rows:
            return None
        return [
            {
                "post_id": r.post_id,
                "title": r.title,
                "subreddit": r.subreddit,
                "upvotes": r.upvotes,
                "num_comments": r.num_comments,
                "trend_score": r.trend_score,
                "url": r.url,
            }
            for r in rows
        ]

    def _store_to_db(self, posts: list[dict], cache_key: str, mode: str) -> None:
        now = datetime.utcnow()
        for p in posts:
            self.db.add(
                RedditTrendingPost(
                    post_id=p["post_id"],
                    title=p["title"],
                    subreddit=p["subreddit"],
                    upvotes=p["upvotes"],
                    num_comments=p["num_comments"],
                    trend_score=p["trend_score"],
                    url=p.get("url"),
                    cache_key=cache_key,
                    mode=mode,
                    fetched_at=now,
                )
            )
        self.db.commit()

    # ------------------------------------------------------------------ #
    #  Private — RapidAPI tier                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    async def _fetch_from_rapidapi(mode: str, subreddits: list[str] | None) -> list[dict]:
        async with httpx.AsyncClient(timeout=30) as client:
            if mode == "general":
                return await RedditService._fetch_popular(client)

            # specific mode — fetch each subreddit concurrently then merge
            results = await asyncio.gather(
                *[RedditService._fetch_subreddit(client, sub) for sub in subreddits],
                return_exceptions=True,
            )
            posts = []
            for r in results:
                if isinstance(r, Exception):
                    raise HTTPException(status_code=502, detail=f"RapidAPI error: {r}")
                posts.extend(r)
            return posts

    @staticmethod
    async def _fetch_popular(client: httpx.AsyncClient) -> list[dict]:
        response = await client.get(
            "https://reddit34.p.rapidapi.com/getTopPopularPosts",
            params={"time": "week"},
            headers=_RAPIDAPI_HEADERS,
        )
        response.raise_for_status()
        return RedditService._parse_posts(response.json())

    @staticmethod
    async def _fetch_subreddit(client: httpx.AsyncClient, subreddit: str) -> list[dict]:
        response = await client.get(
            "https://reddit34.p.rapidapi.com/getTopPostsBySubreddit",
            params={"subreddit": subreddit, "time": "week"},
            headers=_RAPIDAPI_HEADERS,
        )
        response.raise_for_status()
        return RedditService._parse_posts(response.json())

    @staticmethod
    def _parse_posts(data) -> list[dict]:
        # response shape: {"success": true, "data": {"posts": [{"data": {...}}, ...]}}
        raw_posts = data.get("data", {}).get("posts", [])
        posts = []
        for item in raw_posts:
            p = item.get("data", {})
            if not p.get("title") or p.get("stickied"):
                continue
            posts.append(
                {
                    "post_id": p["id"],
                    "title": p["title"],
                    "subreddit": p["subreddit"],
                    "upvotes": int(p.get("score", 0)),
                    "num_comments": int(p.get("num_comments", 0)),
                    "url": p.get("url", ""),
                }
            )
        return posts
