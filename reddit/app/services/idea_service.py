import re

import httpx

from app.core.config import settings


class IdeaService:
    def __init__(self):
        self.llm_url = settings.LLM_SERVICE_URL

    # ------------------------------------------------------------------ #
    #  Public                                                              #
    # ------------------------------------------------------------------ #

    def generate_video_ideas(self, posts: list[dict]) -> list[str]:
        prompt = self._build_prompt(posts)
        response = httpx.post(
            f"{self.llm_url}/generate",
            json={"prompt": prompt},
            timeout=120,
        )
        response.raise_for_status()
        return self._parse_response(response.json()["text"])

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_prompt(posts: list[dict]) -> str:
        post_lines = "\n".join(
            f"{i + 1}. \"{p['title']}\" "
            f"(r/{p['subreddit']} — {p['upvotes']} upvotes, {p['num_comments']} comments, "
            f"trend_score={p['trend_score']:.0f})"
            for i, p in enumerate(posts)
        )
        return (
            "You are a YouTube content strategist. "
            "The posts below are currently trending on Reddit, ranked by "
            "trend_score = upvotes + 0.5 x comments. "
            "For each post, generate one compelling YouTube video idea inspired by its topic. "
            "The idea must be educational or entertaining, under 100 characters, "
            "and suitable for a general audience.\n\n"
            f"Trending posts:\n{post_lines}\n\n"
            "Return ONLY a numbered list of video ideas, one per line, matching the post order."
        )

    @staticmethod
    def _parse_response(raw: str) -> list[str]:
        return [
            re.sub(r"^\d+[\.\)]\s*", "", line).strip()
            for line in raw.strip().splitlines()
            if line.strip()
        ]
