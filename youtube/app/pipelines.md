# Pipeline to extract comments
- clean text
- choosing candidate topics from comments
    - regex based comments, like:
        - r"(?:make|create|upload|do|explain|cover|discuss)\s+(?:a\s+)?(?:video\s+)?(?:on|about)?\s+(?P<topic>[a-zA-Z0-9\s\-]{3,60})"
        - r"(?:can|could|would|will)\s+you\s+(?:make|create|explain|do|cover)?\s*(?:a\s+)?(?:video\s+)?(?:on|about)?\s+(?P<topic>[a-zA-Z0-9\s\-]{3,60})"

        - r"(?:how\s+(?:to|do\s+i|can\s+i)|tutorial\s+(?:on)?)\s+(?P<topic>[a-zA-Z0-9\s\-]{3,60})"

    - n-gram
        - bi gram
        - tri gram

- normalize text
    - lowercase
    - remove punctuation
    - trim

- score topics = count * 0.4 + log(likes+1) * 0.15 + length_bonus * 0.05+ intent_bonus * 0.4
    - length_bonus = min(len(topic) / 20, 1)
    - intent_bonus = 1 if topic matches regex else 0

- rank top 10 topics
- LLM to generate video titles


**Example of regex based topic extraction:**
def trim_topic(text: str) -> str:
    return re.split(r"\b(?:because|but|and|so|if)\b|[.,!?]", text)[0].strip()


for pattern in patterns:
    match = pattern.search(comment)
    if match:
        topic = match.group("topic")
        topic = trim_topic(topic)
        topic = normalize(topic)

```
import re
import math
import logging
from collections import Counter, defaultdict
from anthropic import Anthropic

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class CommentTopicExtractor:
    """
    Extracts and ranks video topic suggestions from YouTube comments,
    then uses an LLM to generate compelling video titles.
    """

    INTENT_PATTERNS = [
        re.compile(r"(?:make|create|upload|do|explain|cover|discuss)\s+(?:a\s+)?(?:video\s+)?(?:on|about)?\s+(?P<topic>[a-zA-Z0-9\s\-]{3,60})", re.IGNORECASE),
        re.compile(r"(?:can|could|would|will)\s+you\s+(?:make|create|explain|do|cover)?\s*(?:a\s+)?(?:video\s+)?(?:on|about)?\s+(?P<topic>[a-zA-Z0-9\s\-]{3,60})", re.IGNORECASE),
        re.compile(r"(?:how\s+(?:to|do\s+i|can\s+i)|tutorial\s+(?:on)?)\s+(?P<topic>[a-zA-Z0-9\s\-]{3,60})", re.IGNORECASE),
    ]

    def __init__(self, top_n: int = 10):
        self.top_n = top_n
        self.client = Anthropic()

    # ------------------------------------------------------------------ #
    #  Text helpers                                                        #
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    #  Extraction                                                          #
    # ------------------------------------------------------------------ #

    def _extract_regex_topics(self, comment: str) -> list[str]:
        topics = []
        for pattern in self.INTENT_PATTERNS:
            match = pattern.search(comment)
            if match:
                raw = match.group("topic")
                topic = self._normalize(self._trim_topic(raw))
                if len(topic) >= 3:
                    topics.append(topic)
        return topics

    @staticmethod
    def _ngrams(tokens: list[str], n: int) -> list[str]:
        return [" ".join(tokens[i: i + n]) for i in range(len(tokens) - n + 1)]

    def _extract_ngram_topics(self, comment: str) -> list[str]:
        normalized = self._normalize(comment)
        # Remove very common stopwords to keep n-grams meaningful
        stopwords = {"the", "a", "an", "is", "it", "to", "of", "in", "on", "for", "i", "you", "me"}
        tokens = [w for w in normalized.split() if w not in stopwords and len(w) > 2]

        bigrams  = self._ngrams(tokens, 2)
        trigrams = self._ngrams(tokens, 3)
        return bigrams + trigrams

    # ------------------------------------------------------------------ #
    #  Scoring                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _score(topic: str, count: int, total_likes: int, is_intent: bool) -> float:
        """
        score = count*0.5 + log(likes+1)*0.2 + length_bonus*0.1 + intent_bonus*0.2
        """
        length_bonus = min(len(topic) / 20, 1.0)
        intent_bonus = 1.0 if is_intent else 0.0
        return (
            count * 0.5
            + math.log(total_likes + 1) * 0.2
            + length_bonus * 0.1
            + intent_bonus * 0.2
        )

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def extract_topics(self, comments: list[dict]) -> list[dict]:
        """
        Parameters
        ----------
        comments : list of dicts with keys:
            - "text"  (str)  : comment text
            - "likes" (int)  : number of likes on that comment

        Returns
        -------
        Ranked list of dicts: {topic, score, count, likes, is_intent}
        """
        topic_counts  = Counter()
        topic_likes   = defaultdict(int)
        topic_intent  = defaultdict(bool)

        for entry in comments:
            raw_text = self._clean(entry.get("text", ""))
            likes    = int(entry.get("likes", 0))

            # --- regex (intent-based) topics ---
            for topic in self._extract_regex_topics(raw_text):
                topic_counts[topic]  += 1
                topic_likes[topic]   += likes
                topic_intent[topic]   = True          # mark as intent-based

            # --- n-gram topics ---
            for topic in self._extract_ngram_topics(raw_text):
                topic_counts[topic]  += 1
                topic_likes[topic]   += likes
                # don't overwrite True with False
                topic_intent.setdefault(topic, False)

        # Score every candidate
        scored = []
        for topic, count in topic_counts.items():
            score = self._score(
                topic,
                count,
                topic_likes[topic],
                topic_intent[topic],
            )
            scored.append({
                "topic":     topic,
                "score":     round(score, 4),
                "count":     count,
                "likes":     topic_likes[topic],
                "is_intent": topic_intent[topic],
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        top = scored[: self.top_n]

        logger.info("Top %d topics extracted out of %d candidates.", len(top), len(scored))
        return top

    def generate_titles(self, topics: list[dict]) -> list[str]:
        """
        Send top topics to Claude and get back a list of video title suggestions.
        """
        topic_lines = "\n".join(
            f"- {t['topic']} (score={t['score']}, count={t['count']}, intent={'yes' if t['is_intent'] else 'no'})"
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

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
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


# ------------------------------------------------------------------ #
#  Quick demo                                                          #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    sample_comments = [
        {"text": "Can you make a video on machine learning for beginners?", "likes": 120},
        {"text": "Please do a tutorial on Python decorators!", "likes": 85},
        {"text": "Would you cover system design interviews?", "likes": 200},
        {"text": "How to build a REST API with FastAPI?", "likes": 95},
        {"text": "machine learning for beginners is what I need", "likes": 40},
        {"text": "I loved this video! system design interviews would be great next", "likes": 30},
        {"text": "Please explain transformer architecture", "likes": 150},
        {"text": "Create a video about Docker and Kubernetes", "likes": 110},
        {"text": "How do I learn data structures and algorithms?", "likes": 75},
        {"text": "Can you cover Python decorators in depth?", "likes": 60},
        {"text": "transformer architecture explained please!", "likes": 90},
        {"text": "docker and kubernetes setup tutorial needed", "likes": 55},
    ]

    extractor = CommentTopicExtractor(top_n=10)
    results = extractor.run(sample_comments)

    print("\n=== TOP TOPICS ===")
    for i, t in enumerate(results["topics"], 1):
        intent_flag = "[intent]" if t["is_intent"] else "[ngram] "
        print(f"{i:>2}. {intent_flag} {t['topic']:<40} score={t['score']:.3f}  count={t['count']}  likes={t['likes']}")

    print("\n=== GENERATED VIDEO TITLES ===")
    for i, title in enumerate(results["titles"], 1):
        print(f"{i:>2}. {title}")
```