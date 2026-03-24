import logging
from collections import defaultdict

from app.ai.comment_topic_extractor import CommentTopicExtractor
from app.services.reddit_service import RedditService

logger = logging.getLogger(__name__)


class TrendService:
    """
    Orchestrates multi-source topic extraction and merging.
    Uses the SAME CommentTopicExtractor pipeline for every source.
    """

    SOURCE_BONUS = 0.1  # bonus when a topic appears in multiple sources

    def __init__(self, db):
        self.db = db
        self.extractor = CommentTopicExtractor()
        self.reddit_service = RedditService()

    # ------------------------------------------------------------------ #
    #  Source-specific data fetchers                                        #
    # ------------------------------------------------------------------ #

    def _get_youtube_comments(self, video_db_id: int) -> list[dict]:
        """Fetch YouTube comments from the DB in pipeline format."""
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "SELECT text, like_count FROM comments WHERE video_db_id::integer = %s;",
                (video_db_id,),
            )
            rows = cursor.fetchall()
            return [{"text": r["text"], "likes": r["like_count"] or 0} for r in rows]
        except Exception:
            logger.warning("Could not fetch YouTube comments for video_db_id=%s", video_db_id)
            return []
        finally:
            cursor.close()

    async def _get_reddit_posts(self, subreddit: str, limit: int = 20) -> list[dict]:
        """Fetch Reddit posts (cached) in pipeline format."""
        return await self.reddit_service.fetch_reddit_posts(subreddit, limit)

    # ------------------------------------------------------------------ #
    #  Single-source topic extraction                                      #
    # ------------------------------------------------------------------ #

    def extract_youtube_topics(self, video_db_id: int) -> list[dict]:
        """Run the extractor on YouTube comments."""
        comments = self._get_youtube_comments(video_db_id)
        if not comments:
            return []
        topics = self.extractor.extract_topics(comments)
        for t in topics:
            t["sources"] = ["youtube"]
        return topics

    async def extract_reddit_topics(self, subreddit: str, limit: int = 20) -> list[dict]:
        """Run the extractor on Reddit posts."""
        posts = await self._get_reddit_posts(subreddit, limit)
        if not posts:
            return []
        topics = self.extractor.extract_topics(posts)
        for t in topics:
            t["sources"] = ["reddit"]
        return topics

    # ------------------------------------------------------------------ #
    #  Multi-source merge (the critical part)                               #
    # ------------------------------------------------------------------ #

    async def get_merged_topics(
        self,
        video_db_id: int | None = None,
        subreddit: str | None = None,
        reddit_limit: int = 20,
    ) -> list[dict]:
        """
        Merge topics from all available sources at the TOPIC level.

        Applies source_bonus when a topic appears across multiple sources.

        Returns
        -------
        list[dict]
            Ranked list: {topic, score, count, likes, intent_count, sources}
        """
        yt_topics = []
        reddit_topics = []

        if video_db_id is not None:
            yt_topics = self.extract_youtube_topics(video_db_id)

        if subreddit is not None:
            reddit_topics = await self.extract_reddit_topics(subreddit, reddit_limit)

        # ---- merge at topic level ----
        merged: dict[str, dict] = {}

        for t in yt_topics + reddit_topics:
            key = t["topic"]
            if key in merged:
                existing = merged[key]
                existing["count"] += t["count"]
                existing["likes"] += t["likes"]
                existing["intent_count"] += t["intent_count"]
                existing["base_score"] += t["score"]
                # combine source lists (dedupe)
                for s in t["sources"]:
                    if s not in existing["sources"]:
                        existing["sources"].append(s)
            else:
                merged[key] = {
                    "topic": key,
                    "base_score": t["score"],
                    "count": t["count"],
                    "likes": t["likes"],
                    "intent_count": t["intent_count"],
                    "sources": list(t["sources"]),
                }

        # ---- apply source_bonus and compute final score ----
        results = []
        for entry in merged.values():
            source_bonus = self.SOURCE_BONUS if len(entry["sources"]) > 1 else 0
            final_score = entry["base_score"] + source_bonus
            results.append({
                "topic": entry["topic"],
                "score": round(final_score, 4),
                "count": entry["count"],
                "likes": entry["likes"],
                "intent_count": entry["intent_count"],
                "sources": entry["sources"],
            })

        results.sort(key=lambda x: x["score"], reverse=True)

        logger.info("Merged %d topics from sources: youtube=%s, reddit=%s",
                     len(results),
                     "yes" if yt_topics else "no",
                     "yes" if reddit_topics else "no")
        return results

    # ------------------------------------------------------------------ #
    #  Persist topics to DB                                                #
    # ------------------------------------------------------------------ #

    def _get_or_create_source(self, source_type: str, external_id: str) -> int:
        """Return the source id, creating the row if needed."""
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT id FROM sources WHERE type = %s AND external_id = %s;",
            (source_type, external_id),
        )
        row = cursor.fetchone()
        if row:
            return row["id"]

        cursor.execute(
            "INSERT INTO sources (type, external_id) VALUES (%s, %s) RETURNING id;",
            (source_type, external_id),
        )
        new_id = cursor.fetchone()["id"]
        self.db.commit()
        return new_id

    def store_topics(self, topics: list[dict], source_type: str, external_id: str):
        """Persist extracted topics to the topics table."""
        source_id = self._get_or_create_source(source_type, external_id)

        cursor = self.db.cursor()
        for t in topics:
            cursor.execute(
                """
                INSERT INTO topics (source_id, topic, score, count, likes, intent_count, source_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """,
                (source_id, t["topic"], t["score"], t["count"], t["likes"], t["intent_count"], source_type),
            )
        self.db.commit()
        logger.info("Stored %d topics for %s:%s", len(topics), source_type, external_id)
