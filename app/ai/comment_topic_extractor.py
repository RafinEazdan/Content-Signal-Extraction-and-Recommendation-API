import re
import math
import logging
import requests
from collections import Counter, defaultdict
from app.core.config import settings

OLLAMA_BASE_URL = settings.OLLAMA_BASE_URL
LLM_MODEL = settings.LLM_MODEL

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class CommentTopicExtractor:

    INTENT_PATTERNS = [
        re.compile(r"(?:make|create|upload|do|explain|cover|discuss)\s+(?:a\s+)?(?:video\s+)?(?:on|about)?\s+(?P<topic>[a-zA-Z0-9\s\-]{3,60})", re.IGNORECASE),
        re.compile(r"(?:can|could|would|will)\s+you\s+(?:make|create|explain|do|cover)?\s*(?:a\s+)?(?:video\s+)?(?:on|about)?\s+(?P<topic>[a-zA-Z0-9\s\-]{3,60})", re.IGNORECASE),
        re.compile(r"(?:how\s+(?:to|do\s+i|can\s+i)|tutorial\s+(?:on)?)\s+(?P<topic>[a-zA-Z0-9\s\-]{3,60})", re.IGNORECASE),
    ]

    # Weak single-word or meaningless phrases to discard from n-grams
    WEAK_PHRASES = {"this video", "this channel", "great video", "love this", "good job", "thank you", "keep up"}

    def __init__(self, top_n: int = 10, ollama_url: str = OLLAMA_BASE_URL):
        self.top_n = top_n
        self.ollama_url = ollama_url
        self.model = LLM_MODEL


    @staticmethod
    def _clean(text: str) -> str:
        """Remove URLs, emojis, and extra whitespace."""
        text = re.sub(r"http\S+", "", text)
        text = re.sub(r"[^\x00-\x7F]+", " ", text)   # strip non-ASCII (emojis)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _normalize(text: str) -> str:
        """Lowercase, remove punctuation, trim."""
        text = text.lower()
        text = re.sub(r"[^\w\s\-]", "", text)
        return text.strip()

    @staticmethod
    def _trim_topic(text: str) -> str:
        """Cut off at conjunctions or sentence-ending punctuation."""
        return re.split(r"\b(?:because|but|and|so|if|please|thanks)\b|[.,!?]", text)[0].strip()

    def _extract_regex_topics(self, comment: str) -> list[str]:
        """
        Find ALL intent-based matches in a comment (not just the first).
        Uses finditer so a comment like:
          "Make a video on X and also cover Y"
        yields both X and Y.
        """
        topics = []
        seen = set()                               
        for pattern in self.INTENT_PATTERNS:
            for match in pattern.finditer(comment):   
                raw   = match.group("topic")
                topic = self._normalize(self._trim_topic(raw))
                if len(topic) >= 3 and topic not in seen:
                    topics.append(topic)
                    seen.add(topic)
        return topics

    @staticmethod
    def _ngrams(tokens: list[str], n: int) -> list[str]:
        return [" ".join(tokens[i: i + n]) for i in range(len(tokens) - n + 1)]

    def _extract_ngram_topics(self, comment: str) -> list[str]:
        """
        Build bigrams and trigrams from the comment.
        - Reuses _trim_topic to cut trailing noise      (FIX 1)
        - Filters weak / generic phrases                (FIX 1)
        """
        # Apply trim before normalizing so conjunctions are cut cleanly
        trimmed    = self._trim_topic(comment)          # FIX 1: reuse _trim_topic
        normalized = self._normalize(trimmed)

        stopwords = {"the", "a", "an", "is", "it", "to", "of", "in", "on", "for", "i", "you", "me"}
        tokens    = [w for w in normalized.split() if w not in stopwords and len(w) > 2]

        candidates = self._ngrams(tokens, 2) + self._ngrams(tokens, 3)

        return [p for p in candidates if p not in self.WEAK_PHRASES]

    @staticmethod
    def _merge_topics(
        topic_counts: Counter,
        topic_likes: defaultdict,
        topic_intent_count: defaultdict,
    ) -> tuple[Counter, defaultdict, defaultdict]:

        topics = sorted(topic_counts.keys(), key=len, reverse=True)  # longest first
        merged: dict[str, str] = {}   # short_topic → canonical_topic

        for i, longer in enumerate(topics):
            for shorter in topics[i + 1:]:
                if shorter in longer and shorter not in merged:
                    merged[shorter] = longer

        for short, canonical in merged.items():
            topic_counts[canonical]        += topic_counts.pop(short)
            topic_likes[canonical]         += topic_likes.pop(short, 0)
            topic_intent_count[canonical]  += topic_intent_count.pop(short, 0)

        return topic_counts, topic_likes, topic_intent_count


    @staticmethod
    def _score(topic: str, count: int, total_likes: int, intent_count: int) -> float:
        """
        score = count*0.5 + log(likes+1)*0.2 + length_bonus*0.1 + intent_bonus*0.2
        """
        num_words    = len(topic.split())
        length_bonus = min(num_words / 3, 1.0)            
        intent_bonus = min(intent_count, 1.0)             
        return (
            count * 0.5
            + math.log(total_likes + 1) * 0.2
            + length_bonus * 0.1
            + intent_bonus * 0.2
        )

    def extract_topics(self, comments: list[dict]) -> list[dict]:

        topic_counts       = Counter()
        topic_likes        = defaultdict(int)
        topic_intent_count = defaultdict(int)   

        for entry in comments:
            raw_text = self._clean(entry.get("text", ""))
            likes    = int(entry.get("likes", 0))

            seen_topics: set[str] = set()

            # --- regex topics ---
            for topic in self._extract_regex_topics(raw_text):
                if topic not in seen_topics:
                    topic_counts[topic]        += 1
                    topic_likes[topic]         += likes
                    topic_intent_count[topic]  += 1   # FIX 1
                    seen_topics.add(topic)

            # --- n-gram topics ---
            for topic in self._extract_ngram_topics(raw_text):
                if topic not in seen_topics:          
                    topic_counts[topic]  += 1
                    topic_likes[topic]   += likes
                    seen_topics.add(topic)

        topic_counts, topic_likes, topic_intent_count = self._merge_topics(
            topic_counts, topic_likes, topic_intent_count
        )

        # Score every candidate
        scored = []
        for topic, count in topic_counts.items():
            score = self._score(
                topic,
                count,
                topic_likes[topic],
                topic_intent_count[topic],
            )
            scored.append({
                "topic":        topic,
                "score":        round(score, 4),
                "count":        count,
                "likes":        topic_likes[topic],
                "intent_count": topic_intent_count[topic],
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        top = scored[: self.top_n]

        logger.info("Top %d topics extracted out of %d candidates.", len(top), len(scored))
        return top

    def generate_titles(self, topics: list[dict]) -> list[str]:
        topic_lines = "\n".join(
            f"- {t['topic']} (score={t['score']}, count={t['count']}, intent_count={t['intent_count']})"
            for t in topics
        )

        prompt = (
            "You are a YouTube content strategist. "
            "Based on the following ranked topics extracted from viewer comments, "
            "generate one compelling, click-worthy video title for each topic. "
            "Keep titles concise (under 70 characters), engaging, and SEO-friendly.\n\n"
            f"Topics:\n{topic_lines}\n\n"
            "Return ONLY a numbered list of titles, one per line."
        )

        response = requests.post(
            f"{self.ollama_url}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        response.raise_for_status()

        raw = response.json()["message"]["content"].strip()
        titles = [
            re.sub(r"^\d+[\.\)]\s*", "", line).strip()
            for line in raw.splitlines()
            if line.strip()
        ]
        return titles

    def run(self, comments: list[dict]) -> dict:
        """
        Full pipeline: extract → rank → generate titles.
        Returns dict with keys: "topics" and "titles".
        """
        logger.info("Starting pipeline with %d comments.", len(comments))
        topics = self.extract_topics(comments)
        titles = self.generate_titles(topics)
        return {"topics": topics, "titles": titles}
